import os
from pathlib import Path

import pytest

from fitness.config import ConfigError, credentials_ready, load_settings, require_credentials


def test_defaults_without_credentials(monkeypatch, tmp_path):
    monkeypatch.delenv("ZEPP_APP_TOKEN", raising=False)
    monkeypatch.delenv("ZEPP_USER_ID", raising=False)
    monkeypatch.setenv("DATA_RAW_DIR", str(tmp_path / "raw"))
    s = load_settings()
    assert s.zepp_host == "api-mifit-us3.zepp.com"
    assert s.zepp_region == "eu"
    assert credentials_ready(s) is False


def test_credentials_ready_when_both_set(monkeypatch, tmp_path):
    monkeypatch.setenv("ZEPP_APP_TOKEN", "tok")
    monkeypatch.setenv("ZEPP_USER_ID", "uid")
    monkeypatch.setenv("DATA_RAW_DIR", str(tmp_path / "raw"))
    s = load_settings()
    assert credentials_ready(s) is True
    require_credentials(s)  # does not raise


def test_require_credentials_raises(monkeypatch, tmp_path):
    monkeypatch.delenv("ZEPP_APP_TOKEN", raising=False)
    monkeypatch.setenv("ZEPP_USER_ID", "uid")
    monkeypatch.setenv("DATA_RAW_DIR", str(tmp_path / "raw"))
    s = load_settings()
    with pytest.raises(ConfigError):
        require_credentials(s)


def test_duckdb_path_default(tmp_path, monkeypatch):
    monkeypatch.delenv("DUCKDB_PATH", raising=False)
    monkeypatch.delenv("DATA_RAW_DIR", raising=False)
    settings = load_settings()
    assert settings.duckdb_path.name == "zepp.duckdb"
    assert settings.duckdb_path.parent.name == "data"


def test_duckdb_path_from_env(tmp_path, monkeypatch):
    target = tmp_path / "custom.duckdb"
    monkeypatch.setenv("DUCKDB_PATH", str(target))
    settings = load_settings()
    assert settings.duckdb_path == target
