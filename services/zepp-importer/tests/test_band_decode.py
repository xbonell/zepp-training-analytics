import base64
from datetime import date, datetime, timezone

import pytest

from fitness.normalize.band import decode_data_hr, decode_data_hr_b64


def test_decode_omits_sentinel_and_keeps_in_range():
    raw = bytearray([254] * 1440)
    raw[0] = 72
    raw[1] = 20  # below 30 → omit
    raw[2] = 221  # above 220 → omit
    raw[60] = 80
    points = decode_data_hr(bytes(raw), date(2026, 8, 18))
    assert points == [
        (datetime(2026, 8, 18, 0, 0, tzinfo=timezone.utc), 72),
        (datetime(2026, 8, 18, 1, 0, tzinfo=timezone.utc), 80),
    ]


def test_decode_rejects_wrong_length():
    with pytest.raises(ValueError, match="1440"):
        decode_data_hr(b"\x00" * 10, date(2026, 1, 1))


def test_decode_b64_roundtrip():
    raw = bytearray([254] * 1440)
    raw[3] = 90
    points = decode_data_hr_b64(base64.b64encode(bytes(raw)).decode(), date(2026, 1, 2))
    assert points == [(datetime(2026, 1, 2, 0, 3, tzinfo=timezone.utc), 90)]
