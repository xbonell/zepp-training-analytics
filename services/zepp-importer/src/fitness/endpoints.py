APP_NAME = "com.xiaomi.hm.health"
APP_PLATFORM = "web"


def history_path() -> str:
    return "/v1/sport/run/history.json"


def detail_path() -> str:
    return "/v1/sport/run/detail.json"


def heart_rate_path(user_id: str) -> str:
    return f"/users/{user_id}/heartRate"


def history_params(from_track_id: int | None = None) -> dict[str, str | int]:
    if from_track_id is None:
        return {}
    return {"trackid": from_track_id}


def detail_params(track_id: str, source: str) -> dict[str, str]:
    return {"trackid": track_id, "source": source}


def heart_rate_params(start: str, end: str) -> dict[str, str]:
    """Return provisional, unverified Zepp heart-rate query parameters."""
    return {"start": start, "end": end}
