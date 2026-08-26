from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _default_duckdb_path() -> Path:
    return _repo_root() / "data" / "zepp.duckdb"


def _default_profile_path() -> Path:
    return _repo_root() / "data" / "profile.json"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_repo_root() / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    duckdb_path: Path = Field(default_factory=_default_duckdb_path)
    profile_path: Path = Field(default_factory=_default_profile_path)
    cors_origin: str = Field(
        default="http://localhost:5173",
        validation_alias="API_CORS_ORIGIN",
    )
