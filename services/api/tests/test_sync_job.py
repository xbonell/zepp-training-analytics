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


def test_soft_sync_errors_still_run_normalize_and_report_ok_with_message(tmp_path):
    env = tmp_path / "zepp.env"
    save_connection(env, user_id="1", app_token="tok", replace_token=True)
    calls: list[str] = []

    def fake_sync(**kwargs):
        calls.append("sync")
        return type("R", (), {"errors": ["one activity failed to download"]})()

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
    assert state.error is None
    assert state.message is not None
    assert "one activity failed to download" in state.message
    stored = read_sync_job(tmp_path / "job.json")
    assert stored.status == "ok"
    assert stored.message == state.message


def test_soft_sync_errors_with_normalize_failure_reports_error(tmp_path):
    env = tmp_path / "zepp.env"
    save_connection(env, user_id="1", app_token="tok", replace_token=True)

    def fake_sync(**kwargs):
        return type("R", (), {"errors": ["sync warning"]})()

    def fake_normalize(**kwargs):
        return type("R", (), {"errors": ["normalize failed"]})()

    state = start_sync_job(
        sync_job_path=tmp_path / "job.json",
        zepp_env_path=env,
        data_raw_dir=tmp_path / "raw",
        duckdb_path=tmp_path / "db.duckdb",
        run_sync_fn=fake_sync,
        run_normalize_fn=fake_normalize,
        wait=True,
    )

    assert state.status == "error"
    assert "sync warning" in state.error
    assert "normalize failed" in state.error


def test_sync_raising_skips_normalize(tmp_path):
    env = tmp_path / "zepp.env"
    save_connection(env, user_id="1", app_token="tok", replace_token=True)
    calls: list[str] = []

    def boom(**kwargs):
        calls.append("sync")
        raise RuntimeError("network exploded")

    def fake_normalize(**kwargs):
        calls.append("normalize")
        return type("R", (), {"errors": []})()

    state = start_sync_job(
        sync_job_path=tmp_path / "job.json",
        zepp_env_path=env,
        data_raw_dir=tmp_path / "raw",
        duckdb_path=tmp_path / "db.duckdb",
        run_sync_fn=boom,
        run_normalize_fn=fake_normalize,
        wait=True,
    )

    assert calls == ["sync"]
    assert state.status == "error"
    assert "network exploded" in state.error


def test_start_sync_job_passes_configured_zepp_host(tmp_path):
    env = tmp_path / "zepp.env"
    save_connection(env, user_id="1", app_token="tok", replace_token=True)
    seen_hosts: list[str] = []

    def fake_sync(**kwargs):
        seen_hosts.append(kwargs["settings"].zepp_host)
        return type("R", (), {"errors": []})()

    def fake_normalize(**kwargs):
        return type("R", (), {"errors": []})()

    start_sync_job(
        sync_job_path=tmp_path / "job.json",
        zepp_env_path=env,
        data_raw_dir=tmp_path / "raw",
        duckdb_path=tmp_path / "db.duckdb",
        zepp_host="custom-zepp-host.example.com",
        run_sync_fn=fake_sync,
        run_normalize_fn=fake_normalize,
        wait=True,
    )

    assert seen_hosts == ["custom-zepp-host.example.com"]


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
