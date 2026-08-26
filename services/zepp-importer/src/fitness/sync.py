from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from typing import Any

from fitness.archive import ArchiveResult, RawArchive
from fitness.client import ZeppClient
from fitness.config import Settings


@dataclass(frozen=True)
class SyncOptions:
    from_date: date | None = None
    activity_id: str | None = None


@dataclass
class SyncReport:
    lists_written: int = 0
    lists_skipped: int = 0
    lists_conflict: int = 0
    details_written: int = 0
    details_skipped: int = 0
    details_conflict: int = 0
    heart_rate_written: int = 0
    heart_rate_skipped: int = 0
    heart_rate_conflict: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def written(self) -> int:
        return self.lists_written + self.details_written + self.heart_rate_written

    @property
    def skipped(self) -> int:
        return self.lists_skipped + self.details_skipped + self.heart_rate_skipped

    @property
    def conflict(self) -> int:
        return self.lists_conflict + self.details_conflict + self.heart_rate_conflict

    def __str__(self) -> str:
        return (
            f"written={self.written}, skipped={self.skipped}, "
            f"conflict={self.conflict}, errors={len(self.errors)}"
        )


def _record(report: SyncReport, category: str, result: ArchiveResult) -> None:
    attribute = f"{category}_{result.status}"
    setattr(report, attribute, getattr(report, attribute) + 1)


def _utc_today() -> date:
    return datetime.now(timezone.utc).date()


def _history_start_timestamp(from_date: date | None) -> int | None:
    if from_date is None:
        return None
    return int(datetime.combine(from_date, time.min, tzinfo=timezone.utc).timestamp())


def _history_activities(
    client: ZeppClient,
    archive: RawArchive,
    report: SyncReport,
) -> list[dict[str, Any]]:
    activities: list[dict[str, Any]] = []
    cursor: int | None = None

    while True:
        try:
            body = client.get_history(from_track_id=cursor)
        except Exception as exc:
            report.errors.append(f"history fetch failed at {cursor or 'start'}: {exc}")
            break

        name = "start" if cursor is None else str(cursor)
        result = archive.write_bytes(f"activity-lists/trackid-{name}.json", body)
        _record(report, "lists", result)

        try:
            payload = json.loads(body)
            data = payload.get("data") or {}
            summary = data.get("summary") or []
        except (json.JSONDecodeError, AttributeError) as exc:
            report.errors.append(f"history parse failed at {name}: {exc}")
            break

        if not summary:
            break
        activities.extend(item for item in summary if isinstance(item, dict))

        next_cursor = data.get("next")
        try:
            next_cursor = int(next_cursor)
        except (TypeError, ValueError):
            next_cursor = 0
        if next_cursor <= 0:
            break
        cursor = next_cursor

    return activities


def _sync_details(
    client: ZeppClient,
    archive: RawArchive,
    options: SyncOptions,
    report: SyncReport,
    activities: list[dict[str, Any]],
) -> None:
    earliest = _history_start_timestamp(options.from_date)

    for activity in activities:
        track_id = str(activity.get("trackid", ""))
        source = activity.get("source")
        if not track_id or not isinstance(source, str):
            report.errors.append("history activity missing trackid or source")
            continue
        if options.activity_id is not None and track_id != options.activity_id:
            continue
        try:
            if earliest is not None and int(track_id) < earliest:
                continue
        except ValueError:
            report.errors.append(f"invalid activity trackid: {track_id}")
            continue

        relative = f"activity-details/{track_id}.json"
        forced = options.activity_id == track_id
        if (archive.root / relative).exists() and not forced:
            report.details_skipped += 1
            continue

        try:
            body = client.get_detail(track_id, source)
            _record(report, "details", archive.write_bytes(relative, body))
        except Exception as exc:
            report.errors.append(f"detail fetch failed for {track_id}: {exc}")


def _sync_heart_rate(
    client: ZeppClient,
    archive: RawArchive,
    options: SyncOptions,
    report: SyncReport,
) -> None:
    today = _utc_today()
    day = options.from_date or (today - timedelta(days=6))

    while day <= today:
        day_text = day.isoformat()
        try:
            body = client.get_heart_rate(day_text, day_text)
            result = archive.write_bytes(f"heart-rate/{day_text}.json", body)
            _record(report, "heart_rate", result)
        except Exception as exc:
            report.errors.append(f"heart-rate fetch failed for {day_text}: {exc}")
        day += timedelta(days=1)


def _report_counts(report: SyncReport) -> dict[str, int]:
    return {
        "written": report.written,
        "skipped": report.skipped,
        "conflict": report.conflict,
        "lists_written": report.lists_written,
        "lists_skipped": report.lists_skipped,
        "lists_conflict": report.lists_conflict,
        "details_written": report.details_written,
        "details_skipped": report.details_skipped,
        "details_conflict": report.details_conflict,
        "heart_rate_written": report.heart_rate_written,
        "heart_rate_skipped": report.heart_rate_skipped,
        "heart_rate_conflict": report.heart_rate_conflict,
    }


def run_sync(
    settings: Settings,
    client: ZeppClient,
    archive: RawArchive,
    options: SyncOptions,
) -> SyncReport:
    del settings
    started_at = datetime.now(timezone.utc)
    report = SyncReport()

    activities = _history_activities(client, archive, report)
    _sync_details(client, archive, options, report, activities)
    _sync_heart_rate(client, archive, options, report)

    archive.write_meta(
        {
            "started_at": started_at.isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "counts": _report_counts(report),
            "errors": report.errors,
        }
    )
    return report
