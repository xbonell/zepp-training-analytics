import json
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class Profile(BaseModel):
    sex: str | None = None
    birth_date: date | None = None
    resting_hr: int | None = None
    hrmax_override: float | None = Field(default=None, gt=0)
    theme_preference: Literal["light", "dark", "system"] = "system"
    display_timezone: str = "Europe/Madrid"


def load_profile(path: Path) -> Profile:
    if not path.exists():
        return Profile()
    return Profile.model_validate_json(path.read_text(encoding="utf-8"))


def save_profile(profile: Profile, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(profile.model_dump(mode="json"), indent=2)
    path.write_text(f"{payload}\n", encoding="utf-8")
