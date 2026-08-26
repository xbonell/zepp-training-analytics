from datetime import date, datetime, time, timedelta, timezone

APP_NAME = "com.xiaomi.hm.health"
APP_PLATFORM = "web"

# Continuous HR via /users/.../heartRate (HTTP 200 but empty items on this account).
HEART_RATE_TYPE_CONTINUOUS = "2"

# All-day HR lives in band_data detail payloads (verified live 2026-08-26).
BAND_DATA_QUERY_TYPE = "detail"
BAND_DATA_DEVICE_TYPE = "0"


def history_path() -> str:
    return "/v1/sport/run/history.json"


def detail_path() -> str:
    return "/v1/sport/run/detail.json"


def heart_rate_path(user_id: str) -> str:
    return f"/users/{user_id}/heartRate"


def band_data_path() -> str:
    return "/v1/data/band_data.json"


def history_params(from_track_id: int | None = None) -> dict[str, str | int]:
    if from_track_id is None:
        return {}
    return {"trackid": from_track_id}


def detail_params(track_id: str, source: str) -> dict[str, str]:
    return {"trackid": track_id, "source": source}


def _utc_day_start_ms(day: str) -> int:
    parsed = date.fromisoformat(day)
    start = datetime.combine(parsed, time.min, tzinfo=timezone.utc)
    return int(start.timestamp() * 1000)


def _utc_day_end_ms(day: str) -> int:
    parsed = date.fromisoformat(day)
    next_midnight = datetime.combine(
        parsed + timedelta(days=1), time.min, tzinfo=timezone.utc
    )
    return int(next_midnight.timestamp() * 1000) - 1


def heart_rate_params(start: str, end: str) -> dict[str, str]:
    """Return /heartRate query params (often empty items; prefer band_data)."""
    return {
        "startTime": str(_utc_day_start_ms(start)),
        "endTime": str(_utc_day_end_ms(end)),
        "type": HEART_RATE_TYPE_CONTINUOUS,
    }


def band_data_params(user_id: str, day: str) -> dict[str, str]:
    """Return band_data detail params for one calendar day (includes data_hr)."""
    return {
        "query_type": BAND_DATA_QUERY_TYPE,
        "from_date": day,
        "to_date": day,
        "userid": user_id,
        "device_type": BAND_DATA_DEVICE_TYPE,
    }
