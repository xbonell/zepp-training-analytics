from unittest.mock import patch

from fastapi.testclient import TestClient

from fitness_api.config import Settings
from fitness_api.connection import save_connection
from fitness_api.main import create_app
from fitness_api.sync_job import SyncJobState, write_sync_job


def _client(tmp_path):
    settings = Settings(
        duckdb_path=tmp_path / "zepp.duckdb",
        profile_path=tmp_path / "profile.json",
        zepp_env_path=tmp_path / "zepp.env",
        data_raw_dir=tmp_path / "raw",
        sync_job_path=tmp_path / "sync_job.json",
        cors_origin="http://localhost:5173",
    )
    save_connection(
        settings.zepp_env_path,
        user_id="1",
        app_token="tok",
        replace_token=True,
    )
    return TestClient(create_app(settings)), settings


def test_get_sync_idle(tmp_path):
    client, _ = _client(tmp_path)
    assert client.get("/api/settings/sync").json()["status"] == "idle"


def test_post_sync_conflict_when_running(tmp_path):
    client, settings = _client(tmp_path)
    write_sync_job(
        settings.sync_job_path,
        SyncJobState(
            status="running",
            started_at=None,
            finished_at=None,
            error=None,
        ),
    )
    assert client.post("/api/settings/sync").status_code == 409


def test_post_sync_starts_job(tmp_path):
    client, settings = _client(tmp_path)

    def fake_start(**kwargs):
        state = SyncJobState(
            status="running",
            started_at=None,
            finished_at=None,
            error=None,
        )
        write_sync_job(settings.sync_job_path, state)
        return state

    with patch("fitness_api.main.start_sync_job", side_effect=fake_start):
        response = client.post("/api/settings/sync")
    assert response.status_code == 200
    assert response.json()["status"] == "running"
