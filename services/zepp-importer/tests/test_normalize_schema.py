from pathlib import Path

import duckdb

from fitness.normalize.schema import ensure_schema


def test_ensure_schema_creates_tables(tmp_path: Path):
    db = tmp_path / "t.duckdb"
    conn = duckdb.connect(str(db))
    ensure_schema(conn)
    tables = {r[0] for r in conn.execute("SHOW TABLES").fetchall()}
    assert "activities" in tables
    assert "activity_samples" in tables
    assert "heart_rate_samples" in tables
    hr_cols = {row[0] for row in conn.execute("DESCRIBE heart_rate_samples").fetchall()}
    assert {"recorded_at", "hr_bpm", "source", "raw_file", "content_sha256"} <= hr_cols
    cols = {r[0] for r in conn.execute("DESCRIBE activities").fetchall()}
    assert "activity_id" in cols
    assert "list_content_sha256" in cols
    ensure_schema(conn)  # idempotent
    conn.close()
