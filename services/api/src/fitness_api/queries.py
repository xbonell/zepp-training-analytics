from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Any, Iterator

import duckdb

from fitness_api.db import DUCKDB_LOCK

ACTIVITY_COLUMNS = """
activity_id, sport_type, source, started_at, ended_at, duration_s,
distance_m, calories, avg_hr, max_hr, min_hr, te, exercise_load
"""


@contextmanager
def _connect(path: Path) -> Iterator[duckdb.DuckDBPyConnection]:
    # Held for the lifetime of the connection so it can never overlap with
    # the sync job's read-write normalize connection. See fitness_api.db.
    with DUCKDB_LOCK:
        connection = duckdb.connect(str(path), read_only=True)
        try:
            connection.execute("SET TimeZone = 'Europe/Madrid'")
            yield connection
        finally:
            connection.close()


def _rows(cursor: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
    columns = [item[0] for item in cursor.description]
    return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


def suggested_hrmax(path: Path) -> float | None:
    with _connect(path) as conn:
        row = conn.execute(
            """
            SELECT quantile_cont(hr_bpm, 0.99)
            FROM activity_samples
            WHERE hr_bpm > 0
            """
        ).fetchone()
    return round(float(row[0]), 1) if row and row[0] is not None else None


def list_activities(
    path: Path,
    from_date: date | None = None,
    to_date: date | None = None,
    sport_type: int | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    conditions: list[str] = []
    parameters: list[Any] = []
    if from_date is not None:
        conditions.append("started_at >= CAST(? AS DATE)")
        parameters.append(from_date)
    if to_date is not None:
        conditions.append("started_at < CAST(? AS DATE) + INTERVAL 1 DAY")
        parameters.append(to_date)
    if sport_type is not None:
        conditions.append("sport_type = ?")
        parameters.append(sport_type)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    limit_clause = "LIMIT ?" if limit is not None else ""
    if limit is not None:
        parameters.append(limit)
    with _connect(path) as conn:
        cursor = conn.execute(
            f"""
            SELECT {ACTIVITY_COLUMNS}
            FROM activities
            {where}
            ORDER BY started_at DESC
            {limit_clause}
            """,
            parameters,
        )
        return _rows(cursor)


def get_activity(path: Path, activity_id: str) -> dict[str, Any] | None:
    with _connect(path) as conn:
        cursor = conn.execute(
            f"""
            SELECT {ACTIVITY_COLUMNS}
            FROM activities
            WHERE activity_id = ?
            """,
            [activity_id],
        )
        rows = _rows(cursor)
    return rows[0] if rows else None


def get_activity_samples(path: Path, activity_id: str) -> list[tuple[int, int]]:
    with _connect(path) as conn:
        rows = conn.execute(
            """
            SELECT elapsed_s, hr_bpm
            FROM activity_samples
            WHERE activity_id = ? AND hr_bpm > 0
            ORDER BY elapsed_s
            """,
            [activity_id],
        ).fetchall()
    return [(int(elapsed_s), int(hr_bpm)) for elapsed_s, hr_bpm in rows]


def all_activity_samples(
    path: Path,
    from_date: date | None = None,
    to_date: date | None = None,
) -> dict[str, list[tuple[int, int]]]:
    conditions = ["samples.hr_bpm > 0"]
    parameters: list[Any] = []
    if from_date is not None:
        conditions.append("activities.started_at >= CAST(? AS DATE)")
        parameters.append(from_date)
    if to_date is not None:
        conditions.append(
            "activities.started_at < CAST(? AS DATE) + INTERVAL 1 DAY"
        )
        parameters.append(to_date)

    with _connect(path) as conn:
        rows = conn.execute(
            f"""
            SELECT samples.activity_id, samples.elapsed_s, samples.hr_bpm
            FROM activity_samples AS samples
            JOIN activities USING (activity_id)
            WHERE {" AND ".join(conditions)}
            ORDER BY samples.activity_id, samples.elapsed_s
            """,
            parameters,
        ).fetchall()
    result: dict[str, list[tuple[int, int]]] = {}
    for activity_id, elapsed_s, hr_bpm in rows:
        result.setdefault(str(activity_id), []).append((int(elapsed_s), int(hr_bpm)))
    return result


def overview_totals(
    path: Path,
    from_date: date | None = None,
    to_date: date | None = None,
) -> tuple[int, int]:
    conditions: list[str] = []
    parameters: list[Any] = []
    if from_date is not None:
        conditions.append("started_at >= CAST(? AS DATE)")
        parameters.append(from_date)
    if to_date is not None:
        conditions.append("started_at < CAST(? AS DATE) + INTERVAL 1 DAY")
        parameters.append(to_date)
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    with _connect(path) as conn:
        count, duration = conn.execute(
            f"""
            SELECT count(*), coalesce(sum(duration_s), 0)
            FROM activities
            {where}
            """,
            parameters,
        ).fetchone()
    return int(count), int(duration)


def overview_peak_hr(
    path: Path,
    from_date: date | None = None,
    to_date: date | None = None,
) -> int | None:
    conditions = ["samples.hr_bpm > 0"]
    parameters: list[Any] = []
    if from_date is not None:
        conditions.append("activities.started_at >= CAST(? AS DATE)")
        parameters.append(from_date)
    if to_date is not None:
        conditions.append(
            "activities.started_at < CAST(? AS DATE) + INTERVAL 1 DAY"
        )
        parameters.append(to_date)

    with _connect(path) as conn:
        row = conn.execute(
            f"""
            SELECT max(samples.hr_bpm)
            FROM activity_samples AS samples
            JOIN activities USING (activity_id)
            WHERE {" AND ".join(conditions)}
            """,
            parameters,
        ).fetchone()
    if row is None or row[0] is None:
        return None
    return int(row[0])


def list_sport_types(path: Path) -> list[int]:
    with _connect(path) as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT sport_type
            FROM activities
            WHERE sport_type IS NOT NULL
            ORDER BY sport_type
            """
        ).fetchall()
    return [int(sport_type) for (sport_type,) in rows]
