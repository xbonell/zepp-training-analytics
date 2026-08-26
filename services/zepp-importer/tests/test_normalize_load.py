import json
import shutil
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
