from __future__ import annotations

import base64
from datetime import date, datetime, timedelta, timezone

BAND_HR_SENTINEL = 254
BAND_HR_MINUTES = 1440
BAND_HR_BPM_MIN = 30
BAND_HR_BPM_MAX = 220


def decode_data_hr(blob: bytes, day: date) -> list[tuple[datetime, int]]:
    if len(blob) != BAND_HR_MINUTES:
        raise ValueError(f"data_hr length must be {BAND_HR_MINUTES}, got {len(blob)}")
    start = datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc)
    points: list[tuple[datetime, int]] = []
    for i, value in enumerate(blob):
        if value == BAND_HR_SENTINEL:
            continue
        if value < BAND_HR_BPM_MIN or value > BAND_HR_BPM_MAX:
            continue
        points.append((start + timedelta(minutes=i), int(value)))
    return points


def decode_data_hr_b64(b64: str, day: date) -> list[tuple[datetime, int]]:
    return decode_data_hr(base64.b64decode(b64), day)
