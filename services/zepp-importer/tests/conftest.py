import pytest


@pytest.fixture(autouse=True)
def isolate_repository_dotenv(monkeypatch, tmp_path):
    monkeypatch.setattr("fitness.config._repo_root", lambda: tmp_path)
