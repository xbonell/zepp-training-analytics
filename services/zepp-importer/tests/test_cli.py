from typer.testing import CliRunner

from fitness.client import ZeppAuthError
from fitness.cli import app
from fitness.config import Settings
from fitness.sync import SyncReport

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


class FakeCliClient:
    def __init__(self, *args, **kwargs):
        self.closed = False

    def close(self):
        self.closed = True


def _configure_sync(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "fitness.cli.load_settings",
        lambda: Settings(
            zepp_app_token="token",
            zepp_user_id="user",
            data_raw_dir=tmp_path,
        ),
    )
    monkeypatch.setattr("fitness.cli.ZeppClient", FakeCliClient)


def test_sync_auth_error_exits_nonzero_with_guidance(monkeypatch, tmp_path):
    _configure_sync(monkeypatch, tmp_path)

    def fail_sync(*args, **kwargs):
        raise ZeppAuthError("Re-extract apptoken — see docs/zepp-auth.md")

    monkeypatch.setattr("fitness.cli.run_sync", fail_sync)

    result = runner.invoke(app, ["sync"])

    assert result.exit_code == 1
    assert "re-extract" in result.output.lower()


def test_sync_report_errors_exit_nonzero(monkeypatch, tmp_path):
    _configure_sync(monkeypatch, tmp_path)
    monkeypatch.setattr(
        "fitness.cli.run_sync",
        lambda *args, **kwargs: SyncReport(errors=["HTTP 503 on history"]),
    )

    result = runner.invoke(app, ["sync"])

    assert result.exit_code == 1
    assert "errors=1" in result.output
