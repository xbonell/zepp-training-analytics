from fastapi.testclient import TestClient

from fitness_api.config import Settings
from fitness_api.main import create_app


def test_settings_use_repo_data_defaults(monkeypatch):
    monkeypatch.delenv("DUCKDB_PATH", raising=False)
    monkeypatch.delenv("PROFILE_PATH", raising=False)
    monkeypatch.delenv("API_CORS_ORIGIN", raising=False)

    settings = Settings(_env_file=None)

    assert settings.duckdb_path.name == "zepp.duckdb"
    assert settings.duckdb_path.parent.name == "data"
    assert settings.profile_path.name == "profile.json"
    assert settings.profile_path.parent.name == "data"
    assert settings.cors_origin == "http://localhost:5173"


def test_settings_read_api_environment(monkeypatch, tmp_path):
    duckdb_path = tmp_path / "custom.duckdb"
    profile_path = tmp_path / "custom-profile.json"
    monkeypatch.setenv("DUCKDB_PATH", str(duckdb_path))
    monkeypatch.setenv("PROFILE_PATH", str(profile_path))
    monkeypatch.setenv("API_CORS_ORIGIN", "https://dashboard.example")

    settings = Settings()

    assert settings.duckdb_path == duckdb_path
    assert settings.profile_path == profile_path
    assert settings.cors_origin == "https://dashboard.example"


def test_health_reports_missing_duckdb(tmp_path):
    settings = Settings(
        duckdb_path=tmp_path / "missing.duckdb",
        profile_path=tmp_path / "profile.json",
    )

    response = TestClient(create_app(settings)).get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "duckdb": False}


def test_health_reports_present_duckdb(tmp_path):
    duckdb_path = tmp_path / "zepp.duckdb"
    duckdb_path.touch()
    settings = Settings(
        duckdb_path=duckdb_path,
        profile_path=tmp_path / "profile.json",
    )

    response = TestClient(create_app(settings)).get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "duckdb": True}


def test_app_allows_configured_cors_origin(tmp_path):
    origin = "http://localhost:4173"
    settings = Settings(
        duckdb_path=tmp_path / "missing.duckdb",
        profile_path=tmp_path / "profile.json",
        cors_origin=origin,
    )

    response = TestClient(create_app(settings)).options(
        "/api/health",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
