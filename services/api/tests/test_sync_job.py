import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from fitness_api.connection import save_connection
from fitness_api.sync_job import (
    SyncJobBusy,
    SyncJobState,
    read_sync_job,
    start_sync_job,
    write_sync_job,
)


def test_read_missing_job_is_idle(tmp_path):
    assert read_sync_job(tmp_path / "sync_job.json").status == "idle"


def test_start_rejects_when_running(tmp_path):
    path = tmp_path / "sync_job.json"
    write_sync_job(
        path,
        SyncJobState(
            status="running",
            started_at=datetime.now(timezone.utc),
            finished_at=None,
            error=None,
        ),
    )
    with pytest.raises(SyncJobBusy):
        start_sync_job(
            sync_job_path=path,
            zepp_env_path=tmp_path / "zepp.env",
            data_raw_dir=tmp_path / "raw",
            duckdb_path=tmp_path / "zepp.duckdb",
        )


def test_successful_sync_runs_normalize(tmp_path):
    env = tmp_path / "zepp.env"
    save_connection(env, user_id="1", app_token="tok", replace_token=True)
    calls: list[str] = []

    def fake_sync(**kwargs):
        calls.append("sync")
        return type("R", (), {"errors": []})()

    def fake_normalize(**kwargs):
        calls.append("normalize")
        return type("R", (), {"errors": []})()

    state = start_sync_job(
        sync_job_path=tmp_path / "job.json",
        zepp_env_path=env,
        data_raw_dir=tmp_path / "raw",
        duckdb_path=tmp_path / "db.duckdb",
        run_sync_fn=fake_sync,
        run_normalize_fn=fake_normalize,
        wait=True,
    )
    assert calls == ["sync", "normalize"]
    assert state.status == "ok"
    assert read_sync_job(tmp_path / "job.json").status == "ok"


def test_auth_error_message(tmp_path):
    from fitness.client import ZeppAuthError

    env = tmp_path / "zepp.env"
    save_connection(env, user_id="1", app_token="tok", replace_token=True)

    def boom(**kwargs):
        raise ZeppAuthError("nope")

    state = start_sync_job(
        sync_job_path=tmp_path / "job.json",
        zepp_env_path=env,
        data_raw_dir=tmp_path / "raw",
        duckdb_path=tmp_path / "db.duckdb",
        run_sync_fn=boom,
        run_normalize_fn=lambda **k: None,
        wait=True,
    )
    assert state.status == "error"
    assert "token expired" in (state.error or "").lower()
