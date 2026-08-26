# Milestone 2 — Persistence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add offline `fitness normalize` that upserts activities and workout HR samples from `data/raw/` into DuckDB with raw-file provenance and SHA-256 skip logic.

**Architecture:** Extend `services/zepp-importer` (`fitness` package). Sync stays HTTP/archive-only. Normalize opens local DuckDB, ensures schema, scans list/detail JSON, decodes workout `heart_rate`, upserts incrementally. No network; no band-data decode in this cut.

**Tech Stack:** Python 3.12+, `uv`, existing `typer`/`pydantic-settings`, new `duckdb`, `pytest`

## Global Constraints

- Spec: `docs/superpowers/specs/2026-08-26-zepp-m2-persistence-design.md`
- Package: `services/zepp-importer/`; CLI entry `fitness`
- Default DB: `<repo-root>/data/zepp.duckdb` (overridable via `DUCKDB_PATH`)
- Raw root: existing `DATA_RAW_DIR` / `Settings.data_raw_dir`
- Timestamps: UTC only (`TIMESTAMPTZ` from Unix seconds)
- Sentinels `-1`, `""` → SQL NULL for metric columns
- No live Zepp calls in tests; fixtures only; never commit `data/raw/**` or `*.duckdb`
- No band-data / daily metrics / GPS series / sport labels in this cut
- TDD: failing test → implement → pass → commit per task

---

## File map

| Path | Responsibility |
|---|---|
| `services/zepp-importer/pyproject.toml` | Add `duckdb` dependency |
| `services/zepp-importer/src/fitness/config.py` | `duckdb_path` setting |
| `services/zepp-importer/src/fitness/normalize/__init__.py` | Package export |
| `services/zepp-importer/src/fitness/normalize/decode.py` | Workout HR string decode |
| `services/zepp-importer/src/fitness/normalize/schema.py` | DDL + `ensure_schema` |
| `services/zepp-importer/src/fitness/normalize/load.py` | Scan/upsert orchestration + report |
| `services/zepp-importer/src/fitness/cli.py` | `normalize` command |
| `services/zepp-importer/tests/test_decode.py` | HR decode tests |
| `services/zepp-importer/tests/test_normalize_schema.py` | Schema creation |
| `services/zepp-importer/tests/test_normalize_load.py` | Loader behavior |
| `services/zepp-importer/tests/test_cli.py` | CLI normalize smoke |
| `services/zepp-importer/tests/fixtures/normalize_list.json` | Synthetic list page |
| `services/zepp-importer/tests/fixtures/normalize_detail.json` | Synthetic detail |
| `.env.example` | Optional `DUCKDB_PATH` |
| `README.md`, `docs/architecture.md`, `docs/zepp-data-model.md` | M2 usage notes |

---

### Task 1: Config + DuckDB dependency

**Files:**
- Modify: `services/zepp-importer/pyproject.toml`
- Modify: `services/zepp-importer/src/fitness/config.py`
- Modify: `.env.example`
- Test: `services/zepp-importer/tests/test_config.py`

**Interfaces:**
- Consumes: existing `Settings`, `_repo_root()`
- Produces: `Settings.duckdb_path: Path` (default `<repo>/data/zepp.duckdb`)

- [ ] **Step 1: Extend failing config test**

Add to `tests/test_config.py`:

```python
def test_duckdb_path_default(tmp_path, monkeypatch):
    monkeypatch.delenv("DUCKDB_PATH", raising=False)
    monkeypatch.delenv("DATA_RAW_DIR", raising=False)
    settings = load_settings()
    assert settings.duckdb_path.name == "zepp.duckdb"
    assert settings.duckdb_path.parent.name == "data"


def test_duckdb_path_from_env(tmp_path, monkeypatch):
    target = tmp_path / "custom.duckdb"
    monkeypatch.setenv("DUCKDB_PATH", str(target))
    settings = load_settings()
    assert settings.duckdb_path == target
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd services/zepp-importer && uv run pytest tests/test_config.py::test_duckdb_path_default tests/test_config.py::test_duckdb_path_from_env -v`

Expected: FAIL — `Settings` has no `duckdb_path`

- [ ] **Step 3: Add dependency and setting**

In `pyproject.toml` dependencies, add `"duckdb>=1.1"`.

In `config.py`:

```python
def _default_duckdb_path() -> Path:
    return _repo_root() / "data" / "zepp.duckdb"


class Settings(BaseSettings):
    # ... existing fields ...
    duckdb_path: Path = Field(default_factory=_default_duckdb_path)
```

Append to `.env.example`:

```env
# Optional. Defaults to <repo-root>/data/zepp.duckdb
# DUCKDB_PATH=
```

- [ ] **Step 4: Sync and pass tests**

Run: `cd services/zepp-importer && uv sync --extra dev && uv run pytest tests/test_config.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add services/zepp-importer/pyproject.toml services/zepp-importer/src/fitness/config.py services/zepp-importer/tests/test_config.py .env.example
git commit -m "$(cat <<'EOF'
feat(config): add DUCKDB_PATH for normalize

EOF
)"
```

---

### Task 2: Workout HR decode

**Files:**
- Create: `services/zepp-importer/src/fitness/normalize/__init__.py`
- Create: `services/zepp-importer/src/fitness/normalize/decode.py`
- Test: `services/zepp-importer/tests/test_decode.py`

**Interfaces:**
- Consumes: none
- Produces: `decode_heart_rate(series: str) -> list[tuple[int, int]]`  
  Each tuple is `(elapsed_s, hr_bpm)`. Empty string → `[]`. Invalid segment → raise `ValueError`.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_decode.py
import pytest

from fitness.normalize.decode import decode_heart_rate


def test_decode_absolute_then_deltas():
    # 15s @ 98, +5s Δ0 → 98, +2s Δ-1 → 97
    assert decode_heart_rate("15,98;5,0;2,-1") == [(15, 98), (20, 98), (22, 97)]


def test_decode_empty():
    assert decode_heart_rate("") == []


def test_decode_keeps_zero_bpm():
    assert decode_heart_rate("1,80;1,-80") == [(1, 80), (2, 0)]


def test_decode_rejects_bad_segment():
    with pytest.raises(ValueError):
        decode_heart_rate("15,98;nope")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_decode.py -v`

Expected: FAIL — module missing

- [ ] **Step 3: Implement decode**

```python
# src/fitness/normalize/__init__.py
"""Offline normalization of raw Zepp archives into DuckDB."""

# src/fitness/normalize/decode.py
from __future__ import annotations


def decode_heart_rate(series: str) -> list[tuple[int, int]]:
    if not series or not series.strip():
        return []
    points: list[tuple[int, int]] = []
    elapsed = 0
    hr: int | None = None
    for raw in series.split(";"):
        seg = raw.strip()
        if not seg:
            continue
        parts = seg.split(",")
        if len(parts) != 2:
            raise ValueError(f"invalid heart_rate segment: {seg!r}")
        try:
            dt = int(parts[0])
            dv = int(parts[1])
        except ValueError as exc:
            raise ValueError(f"invalid heart_rate segment: {seg!r}") from exc
        elapsed += dt
        hr = dv if hr is None else hr + dv
        points.append((elapsed, hr))
    return points
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_decode.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add services/zepp-importer/src/fitness/normalize services/zepp-importer/tests/test_decode.py
git commit -m "$(cat <<'EOF'
feat(normalize): decode workout heart_rate delta series

EOF
)"
```

---

### Task 3: DuckDB schema

**Files:**
- Create: `services/zepp-importer/src/fitness/normalize/schema.py`
- Test: `services/zepp-importer/tests/test_normalize_schema.py`

**Interfaces:**
- Consumes: `duckdb.DuckDBPyConnection`
- Produces: `ensure_schema(conn) -> None` creating `activities` and `activity_samples`

- [ ] **Step 1: Write failing test**

```python
# tests/test_normalize_schema.py
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
    cols = {
        r[1]
        for r in conn.execute(
            "SELECT * FROM information_schema.columns WHERE table_name = 'activities'"
        ).fetchall()
    }
    assert "activity_id" in cols
    assert "list_content_sha256" in cols
    ensure_schema(conn)  # idempotent
    conn.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_normalize_schema.py -v`

Expected: FAIL — `ensure_schema` missing

- [ ] **Step 3: Implement schema**

```python
# src/fitness/normalize/schema.py
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


def ensure_schema(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(ACTIVITIES_DDL)
    conn.execute(SAMPLES_DDL)
```

If `information_schema` query shape differs on the installed DuckDB version, assert via `DESCRIBE activities` column names instead — keep the test aligned with the runtime.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_normalize_schema.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add services/zepp-importer/src/fitness/normalize/schema.py services/zepp-importer/tests/test_normalize_schema.py
git commit -m "$(cat <<'EOF'
feat(normalize): create activities and sample DuckDB tables

EOF
)"
```

---

### Task 4: Normalize loader

**Files:**
- Create: `services/zepp-importer/src/fitness/normalize/load.py`
- Create: `services/zepp-importer/tests/fixtures/normalize_list.json`
- Create: `services/zepp-importer/tests/fixtures/normalize_detail.json`
- Test: `services/zepp-importer/tests/test_normalize_load.py`

**Interfaces:**
- Consumes: `ensure_schema`, `decode_heart_rate`, raw dir `Path`, duckdb path `Path`
- Produces:
  - `@dataclass NormalizeReport` with `activities_upserted: int`, `activities_skipped: int`, `samples_written: int`, `errors: list[str]` and `__str__`
  - `run_normalize(raw_dir: Path, duckdb_path: Path) -> NormalizeReport`

**Parsing helpers (same module):**
- `sha256_file(path: Path) -> str`
- `null_sentinel(value) -> None | value` — treat `None`, `""`, `-1`, `"-1"` as NULL for metrics
- `unix_to_utc(ts: str | int) -> datetime` with `tzinfo=timezone.utc`

- [ ] **Step 1: Add fixtures**

`tests/fixtures/normalize_list.json`:

```json
{
  "code": 1,
  "message": "success",
  "data": {
    "next": -1,
    "summary": [
      {
        "trackid": "1700000100",
        "source": "run.200.huami.com",
        "type": 24,
        "end_time": "1700000400",
        "run_time": "300",
        "dis": "0.0",
        "calorie": "50.0",
        "avg_heart_rate": "120.0",
        "max_heart_rate": 150,
        "min_heart_rate": 80,
        "te": 20,
        "exercise_load": 100,
        "bind_device": "0:MILI:200:test",
        "total_step": -1
      },
      {
        "trackid": "1700001000",
        "source": "run.200.huami.com",
        "type": 1,
        "end_time": "1700001900",
        "run_time": "900",
        "dis": "5000.0",
        "calorie": "400.0",
        "avg_heart_rate": "150.0",
        "max_heart_rate": 180,
        "min_heart_rate": 100,
        "te": -1,
        "exercise_load": -1,
        "bind_device": "0:MILI:200:test"
      }
    ]
  }
}
```

`tests/fixtures/normalize_detail.json`:

```json
{
  "code": 1,
  "message": "success",
  "data": {
    "trackid": 1700000100,
    "source": "run.200.huami.com",
    "heart_rate": "15,98;5,0;2,-1"
  }
}
```

- [ ] **Step 2: Write failing loader tests**

```python
# tests/test_normalize_load.py
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
    n = conn.execute("SELECT COUNT(*) FROM activities").fetchone()[0]
    assert n == 2
    orphan = conn.execute(
        "SELECT detail_raw_file FROM activities WHERE activity_id = '1700001000'"
    ).fetchone()[0]
    assert orphan is None
    samples = conn.execute(
        "SELECT elapsed_s, hr_bpm FROM activity_samples WHERE activity_id = '1700000100' ORDER BY elapsed_s"
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
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_normalize_load.py -v`

Expected: FAIL — `run_normalize` missing

- [ ] **Step 4: Implement `load.py`**

Implement approximately:

```python
# src/fitness/normalize/load.py
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb

from fitness.normalize.decode import decode_heart_rate
from fitness.normalize.schema import ensure_schema


@dataclass
class NormalizeReport:
    activities_upserted: int = 0
    activities_skipped: int = 0
    samples_written: int = 0
    errors: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        return (
            f"activities_upserted={self.activities_upserted}, "
            f"activities_skipped={self.activities_skipped}, "
            f"samples_written={self.samples_written}, "
            f"errors={len(self.errors)}"
        )


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def null_sentinel(value: Any) -> Any:
    if value is None or value == "" or value == -1 or value == "-1":
        return None
    return value


def unix_to_utc(ts: str | int) -> datetime:
    return datetime.fromtimestamp(int(ts), tz=timezone.utc)


def run_normalize(raw_dir: Path, duckdb_path: Path) -> NormalizeReport:
    report = NormalizeReport()
    duckdb_path.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(duckdb_path))
    try:
        ensure_schema(conn)
        _load_lists(conn, raw_dir, report)
        _load_details(conn, raw_dir, report)
    finally:
        conn.close()
    return report


def _rel(raw_dir: Path, path: Path) -> str:
    return path.relative_to(raw_dir).as_posix()


def _load_lists(conn, raw_dir: Path, report: NormalizeReport) -> None:
    for path in sorted((raw_dir / "activity-lists").glob("*.json")):
        try:
            digest = sha256_file(path)
            payload = json.loads(path.read_text())
            summary = (payload.get("data") or {}).get("summary") or []
            for item in summary:
                if not isinstance(item, dict):
                    continue
                activity_id = str(item.get("trackid", ""))
                if not activity_id:
                    report.errors.append(f"list missing trackid in {_rel(raw_dir, path)}")
                    continue
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
                        unix_to_utc(item["end_time"]) if item.get("end_time") not in (None, "") else None,
                        int(item["run_time"]) if null_sentinel(item.get("run_time")) is not None else None,
                        float(item["dis"]) if null_sentinel(item.get("dis")) is not None else None,
                        float(item["calorie"]) if null_sentinel(item.get("calorie")) is not None else None,
                        float(item["avg_heart_rate"]) if null_sentinel(item.get("avg_heart_rate")) is not None else None,
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
            report.errors.append(f"{type(exc).__name__} on list {_rel(raw_dir, path)}")


def _load_details(conn, raw_dir: Path, report: NormalizeReport) -> None:
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
                report.activities_skipped += 1
                continue
            payload = json.loads(path.read_text())
            data = payload.get("data") or {}
            points = decode_heart_rate(data.get("heart_rate") or "")
            # Ensure parent row exists (detail-only edge case)
            if existing is None:
                started = unix_to_utc(activity_id)
                conn.execute(
                    """
                    INSERT INTO activities (activity_id, source, started_at, detail_raw_file, detail_content_sha256)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT (activity_id) DO NOTHING
                    """,
                    [activity_id, data.get("source"), started, _rel(raw_dir, path), digest],
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
            if existing is None or existing[0] != digest:
                # detail change is not a summary upsert; do not bump activities_upserted
                pass
        except Exception as exc:
            report.errors.append(f"{type(exc).__name__} on detail {_rel(raw_dir, path)}")
```

Notes for implementer:
- Preserve `detail_*` columns when list upsert runs (`ON CONFLICT` must not null out `detail_raw_file` / `detail_content_sha256`).
- Skip counting: list skip increments `activities_skipped`; detail skip also increments `activities_skipped` (acceptable for M2 report) — or only skip-count lists if tests require; **align report with tests above**.
- For `test_normalize_skips_unchanged_on_second_run`, second run must report `activities_skipped == 2` from the two list rows; detail skip should not break that assertion (either don't count detail skips separately, or ensure list skips alone equal 2 and detail skip is omitted from that field). Prefer: **list skip → `activities_skipped`; detail skip → silent / separate counter not asserted**. Update implementation so second run: list skips 2, detail skip does not add to `activities_skipped`.

- [ ] **Step 5: Run loader tests**

Run: `uv run pytest tests/test_normalize_load.py -v`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add services/zepp-importer/src/fitness/normalize/load.py services/zepp-importer/tests/test_normalize_load.py services/zepp-importer/tests/fixtures/normalize_list.json services/zepp-importer/tests/fixtures/normalize_detail.json
git commit -m "$(cat <<'EOF'
feat(normalize): upsert activities and workout HR samples

EOF
)"
```

---

### Task 5: CLI `fitness normalize`

**Files:**
- Modify: `services/zepp-importer/src/fitness/cli.py`
- Modify: `services/zepp-importer/tests/test_cli.py`

**Interfaces:**
- Consumes: `load_settings`, `run_normalize`
- Produces: Typer command `normalize` — no credentials required; exit 1 if `report.errors`

- [ ] **Step 1: Write failing CLI test**

```python
def test_normalize_cli_writes_duckdb(tmp_path, monkeypatch):
    raw = tmp_path / "raw"
    (raw / "activity-lists").mkdir(parents=True)
    (raw / "activity-details").mkdir(parents=True)
    list_src = Path(__file__).parent / "fixtures" / "normalize_list.json"
    detail_src = Path(__file__).parent / "fixtures" / "normalize_detail.json"
    (raw / "activity-lists" / "trackid-start.json").write_bytes(list_src.read_bytes())
    (raw / "activity-details" / "1700000100.json").write_bytes(detail_src.read_bytes())
    db = tmp_path / "out.duckdb"
    monkeypatch.setenv("DATA_RAW_DIR", str(raw))
    monkeypatch.setenv("DUCKDB_PATH", str(db))
    runner = CliRunner()
    result = runner.invoke(app, ["normalize"])
    assert result.exit_code == 0, result.output
    assert db.exists()
    assert "activities_upserted=" in result.output
```

Add necessary imports (`CliRunner`, `app`, `Path`) matching existing `test_cli.py` style.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cli.py::test_normalize_cli_writes_duckdb -v`

Expected: FAIL — no `normalize` command

- [ ] **Step 3: Implement command**

```python
from fitness.normalize.load import run_normalize

@app.command("normalize")
def normalize_cmd() -> None:
    """Load raw archives into local DuckDB (offline)."""
    settings = load_settings()
    report = run_normalize(settings.data_raw_dir, settings.duckdb_path)
    typer.echo(report)
    if report.errors:
        raise typer.Exit(code=1)
```

- [ ] **Step 4: Run CLI tests**

Run: `uv run pytest tests/test_cli.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add services/zepp-importer/src/fitness/cli.py services/zepp-importer/tests/test_cli.py
git commit -m "$(cat <<'EOF'
feat(cli): add fitness normalize command

EOF
)"
```

---

### Task 6: Docs + status polish

**Files:**
- Modify: `README.md`
- Modify: `docs/architecture.md`
- Modify: `docs/zepp-data-model.md` (mark M2 tables implemented for this cut)
- Modify: `services/zepp-importer/src/fitness/cli.py` (`status` may print `duckdb: <path>` and whether file exists)

**Interfaces:**
- Consumes: none new
- Produces: user-facing docs for normalize

- [ ] **Step 1: Update README setup block**

After sync example, add:

```bash
uv run fitness normalize
```

Note: requires local raw archives; writes `data/zepp.duckdb` by default.

- [ ] **Step 2: Update architecture M2 handoff / slice**

Document:

```text
data/raw/** ──► fitness normalize ──► data/zepp.duckdb
```

- [ ] **Step 3: Update data model provisional schema section**

State `activities` + `activity_samples` are implemented by `fitness normalize`; band-data continuous HR still deferred.

- [ ] **Step 4: Optional status line**

```python
typer.echo(f"duckdb: {settings.duckdb_path} ({'yes' if settings.duckdb_path.exists() else 'missing'})")
```

- [ ] **Step 5: Run full test suite**

Run: `cd services/zepp-importer && uv run pytest -v`

Expected: all PASS

- [ ] **Step 6: Manual smoke (local raw only; do not commit DB)**

```bash
uv run fitness normalize
uv run fitness status
```

Expected: report with upserts; `data/zepp.duckdb` created; status shows duckdb present.

- [ ] **Step 7: Commit**

```bash
git add README.md docs/architecture.md docs/zepp-data-model.md services/zepp-importer/src/fitness/cli.py
git commit -m "$(cat <<'EOF'
docs: document fitness normalize and DuckDB slice

EOF
)"
```

---

## Spec coverage checklist

| Spec requirement | Task |
|---|---|
| `fitness normalize` offline CLI | 5 |
| `activities` from list summaries | 4 |
| Summary without detail still loaded | 4 (fixture activity `1700001000`) |
| Workout HR samples from detail | 2 + 4 |
| SHA-256 skip / incremental upsert | 4 |
| UTC timestamps | 4 (`unix_to_utc`) |
| Sentinels → NULL | 4 |
| DuckDB path config | 1 |
| Unit tests / fixtures only | 2–5 |
| Docs + `.env.example` | 1 + 6 |
| No band-data decode | omitted (out of scope) |

## Placeholder / consistency notes

- Detail skip must **not** inflate `activities_skipped` in a way that breaks Task 4’s second-run assertion (`activities_skipped == 2`).
- List `ON CONFLICT` must not clear `detail_*` columns.
- Prefer `DESCRIBE activities` if DuckDB `information_schema` column indexes differ.

---

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-08-26-zepp-m2-persistence.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks  
2. **Inline Execution** — execute tasks in this session with checkpoints  

Which approach?
