"""Regression test for the read/write DuckDB collision.

DuckDB refuses to open a second connection to the same file with a
different configuration (e.g. read_only=True) while another connection is
already open in the process. API queries open read-only connections while
the sync job's normalize step opens a read-write connection. Both must
share `fitness_api.db.DUCKDB_LOCK` so they never overlap.
"""

import threading
import time

import duckdb

from fitness_api import queries
from fitness_api.db import DUCKDB_LOCK


def _create_schema(db_path):
    with duckdb.connect(str(db_path)) as conn:
        conn.execute(
            """
            CREATE TABLE activities (
              activity_id VARCHAR,
              sport_type INTEGER,
              source VARCHAR,
              started_at TIMESTAMPTZ,
              ended_at TIMESTAMPTZ,
              duration_s INTEGER,
              distance_m DOUBLE,
              calories DOUBLE,
              avg_hr DOUBLE,
              max_hr INTEGER,
              min_hr INTEGER,
              te INTEGER,
              exercise_load INTEGER
            )
            """
        )


def test_mixed_read_only_and_read_write_connections_raise_without_lock(tmp_path):
    """Establishes the bug: DuckDB rejects mixed configs on the same file."""
    db_path = tmp_path / "zepp.duckdb"
    _create_schema(db_path)

    writer = duckdb.connect(str(db_path))
    try:
        try:
            reader = duckdb.connect(str(db_path), read_only=True)
        except duckdb.Error as exc:
            assert "different configuration" in str(exc)
        else:
            reader.close()
            raise AssertionError(
                "expected DuckDB to reject a mixed read-only/read-write open"
            )
    finally:
        writer.close()


def test_duckdb_lock_serializes_normalize_writes_and_api_reads(tmp_path, monkeypatch):
    """Proves DUCKDB_LOCK keeps a simulated normalize write and an API
    read query from ever having open connections at the same time, so the
    real DuckDB exception above can't happen in practice."""
    db_path = tmp_path / "zepp.duckdb"
    _create_schema(db_path)

    intervals: dict[str, tuple[float, float]] = {}
    intervals_guard = threading.Lock()

    def record(label: str, start: float, end: float) -> None:
        with intervals_guard:
            intervals[label] = (start, end)

    real_connect = duckdb.connect

    class _TrackedConnection:
        """Thin proxy so we can time the read connection's real open
        window (past lock acquisition); DuckDBPyConnection.close is a
        read-only C attribute and can't be monkeypatched directly."""

        def __init__(self, conn, start: float) -> None:
            self._conn = conn
            self._start = start

        def close(self) -> None:
            self._conn.close()
            record("read", self._start, time.monotonic())

        def __getattr__(self, name):
            return getattr(self._conn, name)

    def tracking_connect(*args, **kwargs):
        start = time.monotonic()
        return _TrackedConnection(real_connect(*args, **kwargs), start)

    monkeypatch.setattr(queries.duckdb, "connect", tracking_connect)

    def fake_normalize() -> None:
        with DUCKDB_LOCK:
            start = time.monotonic()
            conn = real_connect(str(db_path))
            try:
                conn.execute(
                    "INSERT INTO activities (activity_id) VALUES ('a')"
                )
                time.sleep(0.08)
            finally:
                conn.close()
            record("normalize", start, time.monotonic())

    def do_read() -> None:
        queries.list_activities(db_path)

    writer = threading.Thread(target=fake_normalize)
    reader = threading.Thread(target=do_read)
    writer.start()
    time.sleep(0.02)  # give normalize a head start acquiring the lock
    reader.start()
    writer.join()
    reader.join()

    assert set(intervals) == {"normalize", "read"}
    n_start, n_end = intervals["normalize"]
    r_start, r_end = intervals["read"]
    assert r_start >= n_end or n_start >= r_end, (
        f"normalize {intervals['normalize']} and read {intervals['read']} "
        "overlapped; DUCKDB_LOCK failed to serialize access"
    )
