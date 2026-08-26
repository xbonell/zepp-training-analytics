import json
import shutil
import time
from datetime import datetime
from pathlib import Path

import duckdb

from fitness.normalize.load import run_normalize

FIXTURES = Path(__file__).parent / "fixtures"


def _raw_tree(tmp_path: Path) -> Path:
    raw = tmp_path / "raw"
    (raw / "activity-lists").mkdir(parents=True)
    (raw / "activity-details").mkdir(parents=True)
    shutil.copy(FIXTURES / "normalize_list.json", raw / "activity-lists" / "trackid-start.json")
    shutil.copy(FIXTURES / "normalize_detail.json", raw / "activity-details" / "1700000100.json")
    return raw


def test_normalize_loads_summaries_and_samples(tmp_path: Path):
    raw = _raw_tree(tmp_path)
    db = tmp_path / "zepp.duckdb"

    report = run_normalize(raw, db)

    assert report.activities_upserted == 2
    assert report.samples_written == 3
    assert report.errors == []
    conn = duckdb.connect(str(db))
    assert conn.execute("SELECT COUNT(*) FROM activities").fetchone()[0] == 2
    orphan = conn.execute(
        "SELECT detail_raw_file FROM activities WHERE activity_id = '1700001000'"
    ).fetchone()[0]
    assert orphan is None
    samples = conn.execute(
        "SELECT elapsed_s, hr_bpm FROM activity_samples "
        "WHERE activity_id = '1700000100' ORDER BY elapsed_s"
    ).fetchall()
    assert samples == [(15, 98), (20, 98), (22, 97)]
    te_null = conn.execute(
        "SELECT te FROM activities WHERE activity_id = '1700001000'"
    ).fetchone()[0]
    assert te_null is None
    conn.close()


def test_normalize_large_detail_bulk_insert_is_fast(tmp_path: Path):
    # Regression: per-row INSERT was ~1.8k rows/s (~9+ min for real archives).
    # Bulk load must finish a 20k-sample detail well under that budget.
    n = 20_000
    raw = tmp_path / "raw"
    (raw / "activity-details").mkdir(parents=True)
    heart_rate = ";".join(["1,100"] + ["1,0"] * (n - 1))
    (raw / "activity-details" / "1700000100.json").write_text(
        json.dumps(
            {
                "code": 1,
                "data": {
                    "trackid": 1700000100,
                    "source": "run.200.huami.com",
                    "heart_rate": heart_rate,
                },
            }
        )
    )
    db = tmp_path / "zepp.duckdb"

    t0 = time.perf_counter()
    report = run_normalize(raw, db)
    elapsed = time.perf_counter() - t0

    assert report.samples_written == n
    assert report.errors == []
    assert elapsed < 2.0, f"bulk insert too slow: {elapsed:.2f}s for {n} samples"
    conn = duckdb.connect(str(db))
    count = conn.execute(
        "SELECT COUNT(*) FROM activity_samples WHERE activity_id = '1700000100'"
    ).fetchone()[0]
    conn.close()
    assert count == n


def test_normalize_skips_unchanged_on_second_run(tmp_path: Path):
    raw = _raw_tree(tmp_path)
    db = tmp_path / "zepp.duckdb"

    first = run_normalize(raw, db)
    second = run_normalize(raw, db)

    assert first.activities_upserted == 2
    assert second.activities_skipped == 2
    assert second.activities_upserted == 0
    assert second.samples_written == 0


def test_normalize_replaces_samples_when_detail_changes(tmp_path: Path):
    raw = _raw_tree(tmp_path)
    db = tmp_path / "zepp.duckdb"
    run_normalize(raw, db)
    detail = raw / "activity-details" / "1700000100.json"
    payload = json.loads(detail.read_text())
    payload["data"]["heart_rate"] = "10,100"
    detail.write_text(json.dumps(payload))

    report = run_normalize(raw, db)

    assert report.samples_written == 1
    conn = duckdb.connect(str(db))
    rows = conn.execute(
        "SELECT elapsed_s, hr_bpm FROM activity_samples WHERE activity_id = '1700000100'"
    ).fetchall()
    assert rows == [(10, 100)]
    conn.close()


def test_normalize_started_at_reads_back_as_datetime(tmp_path: Path):
    raw = _raw_tree(tmp_path)
    db = tmp_path / "zepp.duckdb"

    run_normalize(raw, db)

    conn = duckdb.connect(str(db))
    started_at = conn.execute(
        "SELECT started_at FROM activities WHERE activity_id = '1700000100'"
    ).fetchone()[0]
    conn.close()

    assert isinstance(started_at, datetime)


def _list_payload(items: list[dict]) -> str:
    return json.dumps({"code": 1, "message": "success", "data": {"next": -1, "summary": items}})


def test_normalize_converges_when_list_conflict_siblings_agree_after_first_run(
    tmp_path: Path,
):
    # Two list files describe the same activity_id with different calories,
    # simulating M1 "conflict siblings" from overlapping history pulls.
    raw = tmp_path / "raw"
    (raw / "activity-lists").mkdir(parents=True)
    item_a = {
        "trackid": "1700000100",
        "source": "run.200.huami.com",
        "type": 24,
        "end_time": "1700000400",
        "run_time": "300",
        "dis": "0.0",
        "calorie": "50.0",
        "avg_heart_rate": "120.0",
    }
    item_b = {**item_a, "calorie": "60.0"}
    (raw / "activity-lists" / "a-list.json").write_text(_list_payload([item_a]))
    (raw / "activity-lists" / "b-list.json").write_text(_list_payload([item_b]))
    db = tmp_path / "zepp.duckdb"

    first = run_normalize(raw, db)
    second = run_normalize(raw, db)

    # Deterministic pick (last file in sorted order wins) means both runs
    # settle on the same value without oscillating between files.
    conn = duckdb.connect(str(db))
    calorie = conn.execute(
        "SELECT calories FROM activities WHERE activity_id = '1700000100'"
    ).fetchone()[0]
    conn.close()

    assert calorie == 60.0
    assert first.activities_upserted == 1
    assert second.activities_upserted == 0
    assert second.activities_skipped == 1


def test_load_lists_isolates_bad_item_errors(tmp_path: Path):
    raw = tmp_path / "raw"
    (raw / "activity-lists").mkdir(parents=True)
    good_item = {
        "trackid": "1700000100",
        "source": "run.200.huami.com",
        "type": 24,
        "end_time": "1700000400",
        "run_time": "300",
        "dis": "0.0",
        "calorie": "50.0",
        "avg_heart_rate": "120.0",
    }
    bad_item = {**good_item, "trackid": "1700005000", "run_time": "not-a-number"}
    (raw / "activity-lists" / "mixed.json").write_text(_list_payload([good_item, bad_item]))
    db = tmp_path / "zepp.duckdb"

    report = run_normalize(raw, db)

    assert report.activities_upserted == 1
    assert report.errors != []
    conn = duckdb.connect(str(db))
    row = conn.execute(
        "SELECT calories FROM activities WHERE activity_id = '1700000100'"
    ).fetchone()
    missing = conn.execute(
        "SELECT COUNT(*) FROM activities WHERE activity_id = '1700005000'"
    ).fetchone()[0]
    conn.close()

    assert row is not None and row[0] == 50.0
    assert missing == 0


def test_list_reupsert_preserves_detail_and_samples(tmp_path: Path):
    raw = _raw_tree(tmp_path)
    db = tmp_path / "zepp.duckdb"
    run_normalize(raw, db)

    list_path = raw / "activity-lists" / "trackid-start.json"
    payload = json.loads(list_path.read_text())
    payload["data"]["summary"][0]["calorie"] = "999.0"
    list_path.write_text(json.dumps(payload))

    report = run_normalize(raw, db)

    assert report.activities_upserted == 1
    conn = duckdb.connect(str(db))
    row = conn.execute(
        "SELECT calories, detail_raw_file, detail_content_sha256 "
        "FROM activities WHERE activity_id = '1700000100'"
    ).fetchone()
    samples = conn.execute(
        "SELECT COUNT(*) FROM activity_samples WHERE activity_id = '1700000100'"
    ).fetchone()[0]
    conn.close()

    assert row[0] == 999.0
    assert row[1] is not None
    assert row[2] is not None
    assert samples == 3
