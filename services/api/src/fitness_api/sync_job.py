from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Literal

from pydantic import BaseModel

from fitness.archive import RawArchive
from fitness.client import ZeppAuthError, ZeppClient
from fitness.config import Settings as ImporterSettings
from fitness.normalize.load import run_normalize
from fitness.sync import SyncOptions, run_sync

from fitness_api.connection import load_connection
from fitness_api.db import DUCKDB_LOCK

_JOB_LOCK = threading.Lock()

AUTH_ERROR_MESSAGE = (
    "Zepp token expired or rejected; update Connection settings"
)
MISSING_CREDENTIALS_MESSAGE = (
    "Missing Zepp credentials; update Connection settings"
)


class SyncJobBusy(Exception):
    pass


class SyncJobState(BaseModel):
    status: Literal["idle", "running", "ok", "error"]
    started_at: datetime | None
    finished_at: datetime | None
    error: str | None
    message: str | None = None


def read_sync_job(path: Path) -> SyncJobState:
    if not path.exists():
        return SyncJobState(
            status="idle",
            started_at=None,
            finished_at=None,
            error=None,
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    return SyncJobState.model_validate(data)


def write_sync_job(path: Path, state: SyncJobState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        state.model_dump_json(indent=2),
        encoding="utf-8",
    )


def _default_run_sync(**kwargs: Any) -> Any:
    settings: ImporterSettings = kwargs["settings"]
    data_raw_dir: Path = kwargs["data_raw_dir"]
    archive = RawArchive(data_raw_dir)
    assert settings.zepp_app_token and settings.zepp_user_id
    client = ZeppClient(
        settings.zepp_host,
        settings.zepp_app_token,
        settings.zepp_user_id,
    )
    try:
        return run_sync(
            settings,
            client,
            archive,
            SyncOptions(),
        )
    finally:
        client.close()


def _default_run_normalize(**kwargs: Any) -> Any:
    return run_normalize(kwargs["data_raw_dir"], kwargs["duckdb_path"])


def _run_job(
    *,
    sync_job_path: Path,
    settings: ImporterSettings,
    data_raw_dir: Path,
    duckdb_path: Path,
    run_sync_fn: Callable[..., Any],
    run_normalize_fn: Callable[..., Any],
) -> SyncJobState:
    started_at = datetime.now(timezone.utc)
    job_kwargs = {
        "settings": settings,
        "data_raw_dir": data_raw_dir,
        "duckdb_path": duckdb_path,
    }

    try:
        report = run_sync_fn(**job_kwargs)
        sync_errors = getattr(report, "errors", None)
        sync_warning = (
            "Sync completed with warnings: " + "; ".join(sync_errors)
            if sync_errors
            else None
        )

        # Sync returned (didn't raise) even with soft errors, so there may
        # still be new raw data worth normalizing. Only a raised exception
        # (auth failure or otherwise, handled below) skips normalize.
        # Serialize with API read queries; see fitness_api.db.DUCKDB_LOCK.
        with DUCKDB_LOCK:
            normalize_report = run_normalize_fn(**job_kwargs)
        finished_at = datetime.now(timezone.utc)
        normalize_errors = getattr(normalize_report, "errors", None)
        if normalize_errors:
            error = "; ".join(normalize_errors)
            if sync_warning:
                error = f"{sync_warning}; {error}"
            state = SyncJobState(
                status="error",
                started_at=started_at,
                finished_at=finished_at,
                error=error,
            )
            write_sync_job(sync_job_path, state)
            return state

        state = SyncJobState(
            status="ok",
            started_at=started_at,
            finished_at=finished_at,
            error=None,
            message=sync_warning,
        )
        write_sync_job(sync_job_path, state)
        return state
    except ZeppAuthError:
        finished_at = datetime.now(timezone.utc)
        state = SyncJobState(
            status="error",
            started_at=started_at,
            finished_at=finished_at,
            error=AUTH_ERROR_MESSAGE,
        )
        write_sync_job(sync_job_path, state)
        return state
    except Exception as exc:
        finished_at = datetime.now(timezone.utc)
        state = SyncJobState(
            status="error",
            started_at=started_at,
            finished_at=finished_at,
            error=str(exc),
        )
        write_sync_job(sync_job_path, state)
        return state


def start_sync_job(
    *,
    sync_job_path: Path,
    zepp_env_path: Path,
    data_raw_dir: Path,
    duckdb_path: Path,
    zepp_host: str = "api-mifit-us3.zepp.com",
    run_sync_fn: Callable[..., Any] = _default_run_sync,
    run_normalize_fn: Callable[..., Any] = _default_run_normalize,
    wait: bool = False,
) -> SyncJobState:
    with _JOB_LOCK:
        current = read_sync_job(sync_job_path)
        if current.status == "running":
            raise SyncJobBusy

        connection = load_connection(zepp_env_path)
        if not connection.user_id or not connection.app_token:
            now = datetime.now(timezone.utc)
            state = SyncJobState(
                status="error",
                started_at=now,
                finished_at=now,
                error=MISSING_CREDENTIALS_MESSAGE,
            )
            write_sync_job(sync_job_path, state)
            return state

        started_at = datetime.now(timezone.utc)
        running = SyncJobState(
            status="running",
            started_at=started_at,
            finished_at=None,
            error=None,
        )
        write_sync_job(sync_job_path, running)

        settings = ImporterSettings(
            zepp_app_token=connection.app_token,
            zepp_user_id=connection.user_id,
            zepp_host=zepp_host,
            data_raw_dir=data_raw_dir,
            duckdb_path=duckdb_path,
        )

        job_args = {
            "sync_job_path": sync_job_path,
            "settings": settings,
            "data_raw_dir": data_raw_dir,
            "duckdb_path": duckdb_path,
            "run_sync_fn": run_sync_fn,
            "run_normalize_fn": run_normalize_fn,
        }

    if wait:
        return _run_job(**job_args)

    thread = threading.Thread(
        target=_run_job,
        kwargs=job_args,
        daemon=True,
    )
    thread.start()
    return running
