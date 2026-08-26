import base64
import json
from pathlib import Path

import duckdb

from fitness.normalize.load import NormalizeReport, run_normalize


def _write_band_day(raw: Path, day: str, minutes: dict[int, int]) -> Path:
    blob = bytearray([254] * 1440)
    for minute, bpm in minutes.items():
        blob[minute] = bpm
    path = raw / "band-data" / f"{day}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "code": 1,
                "data": [
                    {
                        "date_time": day,
                        "data_hr": base64.b64encode(bytes(blob)).decode(),
                    }
                ],
            }
        )
    )
    return path


def test_normalize_loads_band_hr_samples(tmp_path: Path):
    raw = tmp_path / "raw"
    _write_band_day(raw, "2026-08-18", {0: 72, 60: 80})
    db = tmp_path / "zepp.duckdb"

    report = run_normalize(raw, db)

    assert report.band_days_upserted == 1
    assert report.band_samples_written == 2
    assert report.errors == []
    conn = duckdb.connect(str(db))
    conn.execute("SET TimeZone='UTC'")
    rows = conn.execute(
        "SELECT recorded_at, hr_bpm, source FROM heart_rate_samples ORDER BY recorded_at"
    ).fetchall()
    conn.close()
    assert len(rows) == 2
    assert rows[0][1:] == (72, "band")
    assert rows[1][1:] == (80, "band")


def test_normalize_skips_unchanged_band_day(tmp_path: Path):
    raw = tmp_path / "raw"
    _write_band_day(raw, "2026-08-18", {0: 72})
    db = tmp_path / "zepp.duckdb"

    first = run_normalize(raw, db)
    second = run_normalize(raw, db)

    assert first.band_days_upserted == 1
    assert second.band_days_skipped == 1
    assert second.band_samples_written == 0


def test_normalize_replaces_band_day_on_change(tmp_path: Path):
    raw = tmp_path / "raw"
    _write_band_day(raw, "2026-08-18", {0: 72})
    db = tmp_path / "zepp.duckdb"
    run_normalize(raw, db)
    _write_band_day(raw, "2026-08-18", {0: 90})

    report = run_normalize(raw, db)

    assert report.band_samples_written == 1
    conn = duckdb.connect(str(db))
    bpm = conn.execute("SELECT hr_bpm FROM heart_rate_samples").fetchone()[0]
    conn.close()
    assert bpm == 90


def test_normalize_report_includes_band_counters():
    report = NormalizeReport(
        band_days_upserted=1, band_days_skipped=2, band_samples_written=3
    )

    assert str(report) == (
        "activities_upserted=0, activities_skipped=0, samples_written=0, "
        "band_days_upserted=1, band_days_skipped=2, band_samples_written=3, errors=0"
    )
