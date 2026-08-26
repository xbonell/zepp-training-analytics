from typer.testing import CliRunner

from fitness.cli import app

runner = CliRunner()


def test_status_without_credentials(monkeypatch, tmp_path):
    monkeypatch.delenv("ZEPP_APP_TOKEN", raising=False)
    monkeypatch.delenv("ZEPP_USER_ID", raising=False)
    monkeypatch.setenv("DATA_RAW_DIR", str(tmp_path))
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "credentials" in result.stdout.lower() or "missing" in result.stdout.lower()


def test_sync_without_credentials(monkeypatch, tmp_path):
    monkeypatch.delenv("ZEPP_APP_TOKEN", raising=False)
    monkeypatch.delenv("ZEPP_USER_ID", raising=False)
    monkeypatch.setenv("DATA_RAW_DIR", str(tmp_path))
    result = runner.invoke(app, ["sync"])
    assert result.exit_code != 0
    assert (
        "zepp-auth" in result.stdout.lower()
        or "zepp-auth" in (result.stderr or "").lower()
        or "ZEPP_" in result.stdout
    )
