from pathlib import Path

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


def test_normalize_cli_writes_duckdb(tmp_path, monkeypatch):
    raw = tmp_path / "raw"
    (raw / "activity-lists").mkdir(parents=True)
    (raw / "activity-details").mkdir(parents=True)
    list_src = Path(__file__).parent / "fixtures" / "normalize_list.json"
    detail_src = Path(__file__).parent / "fixtures" / "normalize_detail.json"
    (raw / "activity-lists" / "trackid-start.json").write_bytes(list_src.read_bytes())
    (raw / "activity-details" / "1700000100.json").write_bytes(detail_src.read_bytes())
    db = tmp_path / "out.duckdb"
    monkeypatch.delenv("ZEPP_APP_TOKEN", raising=False)
    monkeypatch.delenv("ZEPP_USER_ID", raising=False)
    monkeypatch.setenv("DATA_RAW_DIR", str(raw))
    monkeypatch.setenv("DUCKDB_PATH", str(db))
    result = runner.invoke(app, ["normalize"])
    assert result.exit_code == 0, result.output
    assert db.exists()
    assert "activities_upserted=" in result.output


def test_normalize_passes_on_progress_kwarg(tmp_path, monkeypatch):
    raw = tmp_path / "raw"
    (raw / "activity-lists").mkdir(parents=True)
    (raw / "activity-details").mkdir(parents=True)
    fixtures = Path(__file__).parent / "fixtures"
    (raw / "activity-lists" / "trackid-start.json").write_bytes(
        (fixtures / "normalize_list.json").read_bytes()
    )
    (raw / "activity-details" / "1700000100.json").write_bytes(
        (fixtures / "normalize_detail.json").read_bytes()
    )
    db = tmp_path / "out.duckdb"
    monkeypatch.setenv("DATA_RAW_DIR", str(raw))
    monkeypatch.setenv("DUCKDB_PATH", str(db))
    monkeypatch.delenv("ZEPP_APP_TOKEN", raising=False)
    monkeypatch.delenv("ZEPP_USER_ID", raising=False)

    seen = {}

    def capture_normalize(raw_dir, duckdb_path, on_progress=None):
        seen["on_progress"] = on_progress
        from fitness.normalize.load import NormalizeReport

        return NormalizeReport(activities_upserted=1)

    monkeypatch.setattr("fitness.cli.run_normalize", capture_normalize)
    monkeypatch.setattr(
        "fitness.progress.sys",
        type(
            "S",
            (),
            {"stderr": type("E", (), {"isatty": lambda self: False})()},
        )(),
    )

    result = runner.invoke(app, ["normalize"])
    assert result.exit_code == 0
    assert seen["on_progress"] is None


def test_normalize_wires_callback_when_tty(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_RAW_DIR", str(tmp_path))
    monkeypatch.setenv("DUCKDB_PATH", str(tmp_path / "out.duckdb"))
    monkeypatch.delenv("ZEPP_APP_TOKEN", raising=False)
    monkeypatch.delenv("ZEPP_USER_ID", raising=False)

    seen = {}

    def capture_normalize(raw_dir, duckdb_path, on_progress=None):
        seen["on_progress"] = on_progress
        from fitness.normalize.load import NormalizeReport

        return NormalizeReport()

    monkeypatch.setattr("fitness.cli.run_normalize", capture_normalize)
    monkeypatch.setattr(
        "fitness.progress.sys",
        type(
            "S",
            (),
            {"stderr": type("E", (), {"isatty": lambda self: True})()},
        )(),
    )

    result = runner.invoke(app, ["normalize"])
    assert result.exit_code == 0
    assert callable(seen["on_progress"])
