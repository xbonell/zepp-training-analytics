from datetime import datetime, timezone

from fitness_api.config import Settings
from fitness_api.main import INTERRUPTED_SYNC_MESSAGE, create_app
from fitness_api.sync_job import SyncJobState, read_sync_job, write_sync_job


def _settings(tmp_path) -> Settings:
    return Settings(
        duckdb_path=tmp_path / "zepp.duckdb",
        profile_path=tmp_path / "profile.json",
        sync_job_path=tmp_path / "_meta" / "sync_job.json",
        zepp_env_path=tmp_path / "zepp.env",
        data_raw_dir=tmp_path / "raw",
        _env_file=None,
    )


def test_startup_rewrites_stale_running_status_to_error(tmp_path):
    settings = _settings(tmp_path)
    write_sync_job(
        settings.sync_job_path,
        SyncJobState(
            status="running",
            started_at=datetime.now(timezone.utc),
            finished_at=None,
            error=None,
        ),
    )

    create_app(settings)

    state = read_sync_job(settings.sync_job_path)
    assert state.status == "error"
    assert state.error == INTERRUPTED_SYNC_MESSAGE
    assert state.finished_at is not None


def test_startup_leaves_non_running_status_untouched(tmp_path):
    settings = _settings(tmp_path)
    write_sync_job(
        settings.sync_job_path,
        SyncJobState(
            status="ok",
            started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
            error=None,
        ),
    )

    create_app(settings)

    state = read_sync_job(settings.sync_job_path)
    assert state.status == "ok"


def test_startup_with_no_existing_sync_job_is_noop(tmp_path):
    settings = _settings(tmp_path)

    create_app(settings)

    assert not settings.sync_job_path.exists()
