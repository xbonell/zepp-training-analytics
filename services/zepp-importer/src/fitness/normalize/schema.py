from __future__ import annotations

import duckdb

ACTIVITIES_DDL = """
CREATE TABLE IF NOT EXISTS activities (
  activity_id VARCHAR PRIMARY KEY,
  sport_type INTEGER,
  source VARCHAR,
  bind_device VARCHAR,
  started_at TIMESTAMPTZ,
  ended_at TIMESTAMPTZ,
  duration_s INTEGER,
  distance_m DOUBLE,
  calories DOUBLE,
  avg_hr DOUBLE,
  max_hr INTEGER,
  min_hr INTEGER,
  te INTEGER,
  exercise_load INTEGER,
  list_raw_file VARCHAR,
  detail_raw_file VARCHAR,
  list_content_sha256 VARCHAR,
  detail_content_sha256 VARCHAR
);
"""

SAMPLES_DDL = """
CREATE TABLE IF NOT EXISTS activity_samples (
  activity_id VARCHAR,
  elapsed_s INTEGER,
  hr_bpm INTEGER,
  detail_raw_file VARCHAR,
  detail_content_sha256 VARCHAR,
  PRIMARY KEY (activity_id, elapsed_s)
);
"""

HEART_RATE_SAMPLES_DDL = """
CREATE TABLE IF NOT EXISTS heart_rate_samples (
  recorded_at TIMESTAMPTZ,
  hr_bpm INTEGER,
  source VARCHAR,
  raw_file VARCHAR,
  content_sha256 VARCHAR,
  PRIMARY KEY (recorded_at, source)
);
"""


def ensure_schema(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(ACTIVITIES_DDL)
    conn.execute(SAMPLES_DDL)
    conn.execute(HEART_RATE_SAMPLES_DDL)
