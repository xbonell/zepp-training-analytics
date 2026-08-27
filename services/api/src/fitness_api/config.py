from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _default_duckdb_path() -> Path:
    return _repo_root() / "data" / "zepp.duckdb"


def _default_profile_path() -> Path:
    return _repo_root() / "data" / "profile.json"


def _default_zepp_env_path() -> Path:
    return _repo_root() / "data" / "zepp.env"


def _default_data_raw_dir() -> Path:
    return _repo_root() / "data" / "raw"


def _default_sync_job_path() -> Path:
    return _repo_root() / "data" / "_meta" / "sync_job.json"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_repo_root() / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    duckdb_path: Path = Field(default_factory=_default_duckdb_path)
    profile_path: Path = Field(default_factory=_default_profile_path)
    zepp_env_path: Path = Field(
        default_factory=_default_zepp_env_path,
        validation_alias="ZEPP_ENV_PATH",
    )
    data_raw_dir: Path = Field(
        default_factory=_default_data_raw_dir,
        validation_alias="DATA_RAW_DIR",
    )
    sync_job_path: Path = Field(
        default_factory=_default_sync_job_path,
        validation_alias="SYNC_JOB_PATH",
    )
    cors_origin: str = Field(
        default="http://localhost:5173",
        validation_alias="API_CORS_ORIGIN",
    )
    zepp_host: str = Field(
        default="api-mifit-us3.zepp.com",
        validation_alias="ZEPP_HOST",
    )
