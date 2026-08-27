from fastapi.testclient import TestClient

from fitness_api.config import Settings
from fitness_api.main import create_app


def _client(tmp_path):
    settings = Settings(
        duckdb_path=tmp_path / "zepp.duckdb",
        profile_path=tmp_path / "profile.json",
        zepp_env_path=tmp_path / "zepp.env",
        data_raw_dir=tmp_path / "raw",
        sync_job_path=tmp_path / "_meta" / "sync_job.json",
        cors_origin="http://localhost:5173",
    )
    return TestClient(create_app(settings))


def test_connection_put_get_masks_token(tmp_path):
    client = _client(tmp_path)
    put = client.put(
        "/api/settings/connection",
        json={"user_id": "99", "app_token": "super-secret-token"},
    )
    assert put.status_code == 200
    body = put.json()
    assert body["user_id"] == "99"
    assert body["token_set"] is True
    assert body["token_hint"] == "oken"
    assert "super-secret" not in put.text

    got = client.get("/api/settings/connection")
    assert got.json() == body


def test_connection_put_without_token_keeps_existing(tmp_path):
    client = _client(tmp_path)
    client.put(
        "/api/settings/connection",
        json={"user_id": "1", "app_token": "abcdefgh"},
    )
    response = client.put("/api/settings/connection", json={"user_id": "2"})
    assert response.json()["user_id"] == "2"
    assert response.json()["token_set"] is True
    assert response.json()["token_hint"] == "efgh"
