# Band-data continuous HR — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend `fitness normalize` so archived `band-data/*.json` `data_hr` blobs become rows in DuckDB `heart_rate_samples` (workout `activity_samples` unchanged).

**Architecture:** Add `normalize/band.py` for uint8 decode; extend schema DDL; call band load from `run_normalize` after details. Skip unchanged files by SHA-256; replace rows for a `raw_file` on change. Sentinel `254` omitted; timestamps = UTC midnight(`date_time`) + minute index.

**Tech Stack:** Existing `fitness` package, DuckDB, pytest, base64 stdlib

## Global Constraints

- Spec: `docs/superpowers/specs/2026-08-26-band-hr-normalize-design.md`
- Package: `services/zepp-importer/`; CLI `fitness normalize` (no new flags)
- Blob: 1440×uint8; omit `254`; keep BPM only if `30 ≤ v ≤ 220`
- Day origin: `date_time` midnight **UTC**
- PK: `(recorded_at, source)` with `source='band'`
- No network; fixtures only in tests; never commit health payloads
- TDD per task; do not modify workout decode/`activity_samples` semantics

---

## File map

| Path | Responsibility |
|---|---|
| `src/fitness/normalize/band.py` | `decode_data_hr`, helpers |
| `src/fitness/normalize/schema.py` | `heart_rate_samples` DDL |
| `src/fitness/normalize/load.py` | report fields + `_load_band_data` |
| `tests/test_band_decode.py` | decode unit tests |
| `tests/test_normalize_schema.py` | assert new table |
| `tests/test_normalize_band_load.py` | skip/replace load tests |
| `tests/fixtures/normalize_band_day.json` | synthetic band day |
| `docs/architecture.md`, `docs/zepp-data-model.md` | document table |

---

### Task 1: Decode `data_hr`

**Files:**
- Create: `services/zepp-importer/src/fitness/normalize/band.py`
- Test: `services/zepp-importer/tests/test_band_decode.py`

**Interfaces:**
- Produces:
  - `BAND_HR_SENTINEL = 254`
  - `BAND_HR_MINUTES = 1440`
  - `decode_data_hr(blob: bytes, day: date) -> list[tuple[datetime, int]]`  
    Raises `ValueError` if `len(blob) != 1440`.
  - `decode_data_hr_b64(b64: str, day: date) -> list[tuple[datetime, int]]`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_band_decode.py
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
```

- [ ] **Step 2: Run tests — expect FAIL**

Run: `cd services/zepp-importer && uv run pytest tests/test_band_decode.py -v`

- [ ] **Step 3: Implement `band.py`**

```python
from __future__ import annotations

import base64
from datetime import date, datetime, timedelta, timezone

BAND_HR_SENTINEL = 254
BAND_HR_MINUTES = 1440
BAND_HR_BPM_MIN = 30
BAND_HR_BPM_MAX = 220


def decode_data_hr(blob: bytes, day: date) -> list[tuple[datetime, int]]:
    if len(blob) != BAND_HR_MINUTES:
        raise ValueError(f"data_hr length must be {BAND_HR_MINUTES}, got {len(blob)}")
    start = datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc)
    points: list[tuple[datetime, int]] = []
    for i, value in enumerate(blob):
        if value == BAND_HR_SENTINEL:
            continue
        if value < BAND_HR_BPM_MIN or value > BAND_HR_BPM_MAX:
            continue
        points.append((start + timedelta(minutes=i), int(value)))
    return points


def decode_data_hr_b64(b64: str, day: date) -> list[tuple[datetime, int]]:
    return decode_data_hr(base64.b64decode(b64), day)
```

- [ ] **Step 4: Run tests — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add services/zepp-importer/src/fitness/normalize/band.py services/zepp-importer/tests/test_band_decode.py
git commit -m "feat(normalize): decode band_data data_hr uint8 series"
```

---

### Task 2: Schema `heart_rate_samples`

**Files:**
- Modify: `services/zepp-importer/src/fitness/normalize/schema.py`
- Modify: `services/zepp-importer/tests/test_normalize_schema.py`

**Interfaces:**
- Produces: `ensure_schema` also creates `heart_rate_samples`

- [ ] **Step 1: Extend failing schema test**

```python
def test_ensure_schema_creates_tables(tmp_path: Path):
    # ... existing assertions ...
    assert "heart_rate_samples" in tables
    hr_cols = {row[0] for row in conn.execute("DESCRIBE heart_rate_samples").fetchall()}
    assert {"recorded_at", "hr_bpm", "source", "raw_file", "content_sha256"} <= hr_cols
```

- [ ] **Step 2: Run test — expect FAIL**

- [ ] **Step 3: Add DDL**

```python
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
```

- [ ] **Step 4: Run test — expect PASS**

- [ ] **Step 5: Commit**

```bash
git commit -am "feat(normalize): add heart_rate_samples DuckDB table"
```

---

### Task 3: Load band-data in `run_normalize`

**Files:**
- Modify: `services/zepp-importer/src/fitness/normalize/load.py`
- Create: `services/zepp-importer/tests/fixtures/normalize_band_day.json`
- Create: `services/zepp-importer/tests/test_normalize_band_load.py`

**Interfaces:**
- Extends `NormalizeReport` with `band_days_upserted`, `band_days_skipped`, `band_samples_written`
- `__str__` includes those fields
- `run_normalize` calls `_load_band_data` after details
- Skip when existing row for `raw_file` has matching `content_sha256`
- On load: delete by `raw_file`, insert rows with `source='band'`

- [ ] **Step 1: Build fixture**

Generate a 1440-byte blob (mostly 254, a few BPM values), base64 it, write:

```json
{
  "code": 1,
  "message": "success",
  "data": [
    {
      "date_time": "2026-08-18",
      "data_hr": "<base64>"
    }
  ]
}
```

Prefer creating the fixture in the test with `tmp_path` **or** a checked-in fixture built by a tiny script in the test module `conftest`/helper — if checked in, generate once in the test file setup comment. Simplest: **build the JSON file inside the test** under `tmp_path / "band-data" / "2026-08-18.json"` (no binary fixture commit). Skip a committed `normalize_band_day.json` unless you want a static file; plan default = **tmp_path-built payload**.

- [ ] **Step 2: Write failing load tests**

```python
# tests/test_normalize_band_load.py
import base64
import json
from pathlib import Path

import duckdb

from fitness.normalize.load import run_normalize


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
    assert len(rows) == 2
    assert rows[0][1] == 72 and rows[1][1] == 80
    assert rows[0][2] == "band"
    conn.close()


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
    path = _write_band_day(raw, "2026-08-18", {0: 72})
    db = tmp_path / "zepp.duckdb"
    run_normalize(raw, db)
    _write_band_day(raw, "2026-08-18", {0: 90})
    report = run_normalize(raw, db)
    assert report.band_samples_written == 1
    conn = duckdb.connect(str(db))
    bpm = conn.execute("SELECT hr_bpm FROM heart_rate_samples").fetchone()[0]
    assert bpm == 90
    conn.close()
```

- [ ] **Step 3: Run tests — expect FAIL**

- [ ] **Step 4: Implement load integration**

In `NormalizeReport` add the three band counters; extend `__str__`.

```python
from fitness.normalize.band import decode_data_hr_b64
from datetime import date

def run_normalize(...):
    ...
    _load_lists(...)
    _load_details(...)
    _load_band_data(conn, raw_dir, report)


def _load_band_data(conn, raw_dir: Path, report: NormalizeReport) -> None:
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
            rows = payload.get("data") or []
            merged: dict = {}
            for row in rows:
                if not isinstance(row, dict):
                    continue
                b64 = row.get("data_hr")
                day_text = row.get("date_time")
                if not b64 or not day_text:
                    continue
                day = date.fromisoformat(str(day_text))
                for recorded_at, bpm in decode_data_hr_b64(b64, day):
                    merged[recorded_at] = bpm
            conn.execute(
                "DELETE FROM heart_rate_samples WHERE raw_file = ?", [rel]
            )
            for recorded_at, bpm in sorted(merged.items()):
                conn.execute(
                    """
                    INSERT INTO heart_rate_samples
                      (recorded_at, hr_bpm, source, raw_file, content_sha256)
                    VALUES (?, ?, 'band', ?, ?)
                    """,
                    [recorded_at, bpm, rel, digest],
                )
            report.band_days_upserted += 1
            report.band_samples_written += len(merged)
        except Exception as exc:
            report.errors.append(f"{type(exc).__name__} on band {_rel(raw_dir, path)}")
```

- [ ] **Step 5: Run band load tests + full suite — expect PASS**

Run: `uv run pytest tests/test_normalize_band_load.py tests/test_cli.py tests/test_normalize_load.py -v`

- [ ] **Step 6: Commit**

```bash
git add services/zepp-importer/src/fitness/normalize/load.py services/zepp-importer/tests/test_normalize_band_load.py
git commit -m "feat(normalize): load band-data HR into heart_rate_samples"
```

---

### Task 4: Docs + manual smoke

**Files:**
- Modify: `docs/architecture.md`
- Modify: `docs/zepp-data-model.md`
- Optional: root `README.md` one-liner that normalize includes band HR

- [ ] **Step 1: Docs** — DuckDB now has `heart_rate_samples` (band); `activity_samples` remains workout-only; UTC midnight + omit 254.

- [ ] **Step 2: Full tests**

Run: `uv run pytest -v` → all PASS

- [ ] **Step 3: Manual smoke (local raw; do not commit DB)**

```bash
uv run fitness normalize
```

Expect `band_days_*` / `band_samples_written` nonzero given existing `data/raw/band-data/`.

- [ ] **Step 4: Commit docs**

```bash
git commit -am "docs: document band heart_rate_samples normalize"
```

---

## Spec coverage

| Requirement | Task |
|---|---|
| `heart_rate_samples` table | 2 |
| uint8 decode, omit 254, 30–220 | 1 |
| UTC midnight + minute | 1 |
| Extend `fitness normalize` | 3 |
| SHA-256 skip / replace | 3 |
| Module `band.py` | 1 |
| Docs | 4 |

---

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-08-26-band-hr-normalize.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks  
2. **Inline Execution** — execute in this session with checkpoints  

Which approach?
