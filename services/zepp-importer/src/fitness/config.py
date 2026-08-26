from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigError(Exception):
    pass


def _repo_root() -> Path:
    # services/zepp-importer/src/fitness/config.py → repo root is parents[4]
    return Path(__file__).resolve().parents[4]


def _default_raw_dir() -> Path:
    return _repo_root() / "data" / "raw"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
        extra="ignore",
    )

    zepp_app_token: str | None = None
    zepp_user_id: str | None = None
    zepp_host: str = "api-mifit-us3.zepp.com"
    zepp_region: str = "eu"
    data_raw_dir: Path = Field(default_factory=_default_raw_dir)


def load_settings() -> Settings:
    repo_env = _repo_root() / ".env"
    if repo_env.exists():
        load_dotenv(repo_env)
    return Settings()


def credentials_ready(settings: Settings) -> bool:
    return bool(settings.zepp_app_token) and bool(settings.zepp_user_id)


def require_credentials(settings: Settings) -> None:
    if not credentials_ready(settings):
        raise ConfigError(
            "Missing ZEPP_APP_TOKEN and/or ZEPP_USER_ID. "
            "See docs/zepp-auth.md"
        )
