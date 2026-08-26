from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import duckdb

from fitness.normalize.decode import decode_heart_rate
from fitness.normalize.band import decode_data_hr_b64
from fitness.normalize.schema import ensure_schema


@dataclass
class NormalizeReport:
    activities_upserted: int = 0
    activities_skipped: int = 0
    samples_written: int = 0
    band_days_upserted: int = 0
    band_days_skipped: int = 0
    band_samples_written: int = 0
    errors: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        return (
            f"activities_upserted={self.activities_upserted}, "
            f"activities_skipped={self.activities_skipped}, "
            f"samples_written={self.samples_written}, "
            f"band_days_upserted={self.band_days_upserted}, "
            f"band_days_skipped={self.band_days_skipped}, "
            f"band_samples_written={self.band_samples_written}, "
            f"errors={len(self.errors)}"
        )


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def item_content_sha256(item: dict[str, Any]) -> str:
    stable = json.dumps(item, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(stable.encode("utf-8")).hexdigest()


def null_sentinel(value: Any) -> Any:
    if value in (None, "", -1, "-1"):
        return None
    return value


def unix_to_utc(ts: str | int) -> datetime:
    return datetime.fromtimestamp(int(ts), tz=timezone.utc)


def run_normalize(raw_dir: Path, duckdb_path: Path) -> NormalizeReport:
    report = NormalizeReport()
    duckdb_path.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(duckdb_path))
    try:
        conn.execute("SET TimeZone='UTC'")
        ensure_schema(conn)
        _load_lists(conn, raw_dir, report)
        _load_details(conn, raw_dir, report)
        _load_band_data(conn, raw_dir, report)
    finally:
        conn.close()
    return report


def _rel(raw_dir: Path, path: Path) -> str:
    return path.relative_to(raw_dir).as_posix()


def _load_lists(
    conn: duckdb.DuckDBPyConnection, raw_dir: Path, report: NormalizeReport
) -> None:
    lists_dir = raw_dir / "activity-lists"
    if not lists_dir.exists():
        return

    # Multiple list files can describe the same activity_id (e.g. M1's
    # "conflict siblings" from overlapping history pulls). Hashing the whole
    # file for list_content_sha256 made the skip check depend on file
    # ordering and unrelated items in the same file, so re-running normalize
    # over unchanged raw data never converged to a stable skip. Instead,
    # gather one summary item per activity_id across all list files first
    # (last file wins, in sorted filename order -> deterministic pick), then
    # hash and upsert per item below. The digest then reflects only the
    # winning item's own content, so unchanged reruns settle into a skip.
    items_by_id: dict[str, tuple[dict[str, Any], Path]] = {}
    for path in sorted(lists_dir.glob("*.json")):
        try:
            payload = json.loads(path.read_text())
        except Exception as exc:
            report.errors.append(f"{type(exc).__name__} on list {_rel(raw_dir, path)}")
            continue
        summary = (payload.get("data") or {}).get("summary") or []
        for item in summary:
            if not isinstance(item, dict):
                continue
            activity_id = str(item.get("trackid", ""))
            if not activity_id:
                report.errors.append(f"list missing trackid in {_rel(raw_dir, path)}")
                continue
            items_by_id[activity_id] = (item, path)

    for activity_id, (item, path) in sorted(items_by_id.items()):
        try:
            digest = item_content_sha256(item)
            existing = conn.execute(
                "SELECT list_content_sha256 FROM activities WHERE activity_id = ?",
                [activity_id],
            ).fetchone()
            if existing and existing[0] == digest:
                report.activities_skipped += 1
                continue
            conn.execute(
                """
                INSERT INTO activities AS a (
                  activity_id, sport_type, source, bind_device,
                  started_at, ended_at, duration_s, distance_m, calories,
                  avg_hr, max_hr, min_hr, te, exercise_load,
                  list_raw_file, list_content_sha256
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (activity_id) DO UPDATE SET
                  sport_type = excluded.sport_type,
                  source = excluded.source,
                  bind_device = excluded.bind_device,
                  started_at = excluded.started_at,
                  ended_at = excluded.ended_at,
                  duration_s = excluded.duration_s,
                  distance_m = excluded.distance_m,
                  calories = excluded.calories,
                  avg_hr = excluded.avg_hr,
                  max_hr = excluded.max_hr,
                  min_hr = excluded.min_hr,
                  te = excluded.te,
                  exercise_load = excluded.exercise_load,
                  list_raw_file = excluded.list_raw_file,
                  list_content_sha256 = excluded.list_content_sha256
                """,
                [
                    activity_id,
                    item.get("type"),
                    item.get("source"),
                    null_sentinel(item.get("bind_device")),
                    unix_to_utc(item["trackid"]),
                    unix_to_utc(item["end_time"])
                    if item.get("end_time") not in (None, "")
                    else None,
                    int(item["run_time"])
                    if null_sentinel(item.get("run_time")) is not None
                    else None,
                    float(item["dis"])
                    if null_sentinel(item.get("dis")) is not None
                    else None,
                    float(item["calorie"])
                    if null_sentinel(item.get("calorie")) is not None
                    else None,
                    float(item["avg_heart_rate"])
                    if null_sentinel(item.get("avg_heart_rate")) is not None
                    else None,
                    null_sentinel(item.get("max_heart_rate")),
                    null_sentinel(item.get("min_heart_rate")),
                    null_sentinel(item.get("te")),
                    null_sentinel(item.get("exercise_load")),
                    _rel(raw_dir, path),
                    digest,
                ],
            )
            report.activities_upserted += 1
        except Exception as exc:
            report.errors.append(
                f"{type(exc).__name__} on activity {activity_id} in {_rel(raw_dir, path)}"
            )


def _load_details(
    conn: duckdb.DuckDBPyConnection, raw_dir: Path, report: NormalizeReport
) -> None:
    details_dir = raw_dir / "activity-details"
    if not details_dir.exists():
        return

    for path in sorted(details_dir.glob("*.json")):
        try:
            digest = sha256_file(path)
            activity_id = path.stem
            existing = conn.execute(
                "SELECT detail_content_sha256 FROM activities WHERE activity_id = ?",
                [activity_id],
            ).fetchone()
            if existing and existing[0] == digest:
                continue

            payload = json.loads(path.read_text())
            data = payload.get("data") or {}
            points = decode_heart_rate(data.get("heart_rate") or "")
            if existing is None:
                conn.execute(
                    """
                    INSERT INTO activities (
                      activity_id, source, started_at, detail_raw_file,
                      detail_content_sha256
                    ) VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT (activity_id) DO NOTHING
                    """,
                    [
                        activity_id,
                        data.get("source"),
                        unix_to_utc(activity_id),
                        _rel(raw_dir, path),
                        digest,
                    ],
                )
            conn.execute("DELETE FROM activity_samples WHERE activity_id = ?", [activity_id])
            for elapsed_s, hr_bpm in points:
                conn.execute(
                    """
                    INSERT INTO activity_samples
                      (activity_id, elapsed_s, hr_bpm, detail_raw_file, detail_content_sha256)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    [activity_id, elapsed_s, hr_bpm, _rel(raw_dir, path), digest],
                )
            conn.execute(
                """
                UPDATE activities SET
                  detail_raw_file = ?,
                  detail_content_sha256 = ?
                WHERE activity_id = ?
                """,
                [_rel(raw_dir, path), digest, activity_id],
            )
            report.samples_written += len(points)
        except Exception as exc:
            report.errors.append(f"{type(exc).__name__} on detail {_rel(raw_dir, path)}")


def _load_band_data(
    conn: duckdb.DuckDBPyConnection, raw_dir: Path, report: NormalizeReport
) -> None:
    band_dir = raw_dir / "band-data"
    if not band_dir.exists():
        return

    for path in sorted(band_dir.glob("*.json")):
        try:
            digest = sha256_file(path)
            rel = _rel(raw_dir, path)
            existing = conn.execute(
                """
                SELECT 1 FROM heart_rate_samples
                WHERE raw_file = ? AND content_sha256 = ?
                LIMIT 1
                """,
                [rel, digest],
            ).fetchone()
            if existing:
                report.band_days_skipped += 1
                continue

            payload = json.loads(path.read_text())
            samples: dict[datetime, int] = {}
            for row in payload.get("data") or []:
                if not isinstance(row, dict):
                    continue
                day_text = row.get("date_time")
                encoded = row.get("data_hr")
                if not day_text or not encoded:
                    continue
                for recorded_at, bpm in decode_data_hr_b64(
                    encoded, date.fromisoformat(str(day_text))
                ):
                    samples[recorded_at] = bpm

            conn.execute("DELETE FROM heart_rate_samples WHERE raw_file = ?", [rel])
            for recorded_at, bpm in sorted(samples.items()):
                conn.execute(
                    """
                    INSERT INTO heart_rate_samples
                      (recorded_at, hr_bpm, source, raw_file, content_sha256)
                    VALUES (?, ?, 'band', ?, ?)
                    """,
                    [recorded_at, bpm, rel, digest],
                )
            report.band_days_upserted += 1
            report.band_samples_written += len(samples)
        except Exception as exc:
            report.errors.append(f"{type(exc).__name__} on band {_rel(raw_dir, path)}")
