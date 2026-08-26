# CLI Progress for Sync & Normalize — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show Rich progress bars during `fitness sync` and `fitness normalize` on interactive terminals, via an optional callback so core logic stays free of terminal I/O.

**Architecture:** Introduce `ProgressEvent` + `ProgressCallback` in a small `fitness.progress` module. `run_sync` / `run_normalize` emit events after each unit of work. The CLI attaches a Rich Progress listener only when `sys.stderr.isatty()`; otherwise `on_progress=None`. Final report printing is unchanged.

**Tech Stack:** Python 3.12+, Typer, Rich, pytest (existing FakeClient / normalize fixtures)

## Global Constraints

- Spec: `docs/superpowers/specs/2026-08-26-cli-progress-design.md`
- Package: `services/zepp-importer/`
- Core must not import Rich or write to the terminal
- `on_progress` default `None`; skipped work still advances the bar
- Empty phases emit nothing
- Emit only after each unit completes (`current` is `1..total` when total known)
- Do not change sync/normalize business logic, skip rules, or report fields
- TDD per task; no Rich rendering assertions in unit tests
- Never commit health payloads / `.env`

---

## File map

| Path | Responsibility |
|---|---|
| `src/fitness/progress.py` | `ProgressEvent`, `ProgressCallback`, `emit`, Rich CLI helper |
| `src/fitness/sync.py` | Emit progress in history / details / band_hr |
| `src/fitness/normalize/load.py` | Emit progress in lists / details / band |
| `src/fitness/cli.py` | Wire TTY progress into sync & normalize |
| `pyproject.toml` | Explicit `rich` dependency |
| `tests/test_progress_sync.py` | Sync progress event sequence |
| `tests/test_progress_normalize.py` | Normalize progress event sequence |
| `tests/test_cli.py` | Non-TTY path still works (existing + small wiring check) |
| `README.md` | One-line note about interactive progress |

---

### Task 1: Progress types + emit helper

**Files:**
- Create: `services/zepp-importer/src/fitness/progress.py`
- Test: `services/zepp-importer/tests/test_progress.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) class ProgressEvent` with fields `phase: str`, `current: int`, `total: int | None`, `message: str = ""`
  - `ProgressCallback = Callable[[ProgressEvent], None]`
  - `def emit(on_progress: ProgressCallback | None, event: ProgressEvent) -> None` — no-op if callback is `None`

- [ ] **Step 1: Write failing tests**

```python
# services/zepp-importer/tests/test_progress.py
from fitness.progress import ProgressEvent, emit


def test_emit_invokes_callback():
    seen: list[ProgressEvent] = []
    event = ProgressEvent(phase="history", current=1, total=None, message="start")
    emit(seen.append, event)
    assert seen == [event]


def test_emit_none_is_noop():
    event = ProgressEvent(phase="history", current=1, total=None)
    emit(None, event)  # must not raise
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd services/zepp-importer && uv run pytest tests/test_progress.py -v`

Expected: FAIL with `ModuleNotFoundError` / import error for `fitness.progress`

- [ ] **Step 3: Minimal implementation**

```python
# services/zepp-importer/src/fitness/progress.py
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class ProgressEvent:
    phase: str
    current: int
    total: int | None
    message: str = ""


ProgressCallback = Callable[[ProgressEvent], None]


def emit(on_progress: ProgressCallback | None, event: ProgressEvent) -> None:
    if on_progress is not None:
        on_progress(event)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd services/zepp-importer && uv run pytest tests/test_progress.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add services/zepp-importer/src/fitness/progress.py \
  services/zepp-importer/tests/test_progress.py
git commit -m "$(cat <<'EOF'
feat: add ProgressEvent callback helper

EOF
)"
```

---

### Task 2: Emit progress from `run_sync`

**Files:**
- Modify: `services/zepp-importer/src/fitness/sync.py`
- Test: `services/zepp-importer/tests/test_progress_sync.py`

**Interfaces:**
- Consumes: `ProgressEvent`, `ProgressCallback`, `emit` from `fitness.progress`
- Produces: `run_sync(..., on_progress: ProgressCallback | None = None) -> SyncReport`
- Thread `on_progress` into `_history_activities`, `_sync_details`, `_sync_heart_rate`

**Emission rules (exact):**

1. **history** — after each page is archived (`_record` done):  
   `ProgressEvent("history", current=page_index, total=None, message=name)`  
   where `page_index` starts at 1 for the first page, and `name` is `"start"` or the cursor string used in the filename.

2. **details** — build `targets` first (same filters as today’s loop: require trackid+source string; honor `--activity`; honor `--from` earliest). If `targets` is empty, emit nothing for this phase. Else for each target activity in order, after fetch-or-skip completes:  
   `ProgressEvent("details", current=i, total=len(targets), message=track_id)` with `i` from 1..N.  
   Do **not** count activities that fail the filter (missing trackid, wrong activity_id, too old) toward `total`.

3. **band_hr** — compute `days = list of dates from start_day..today inclusive`. If empty, emit nothing. Else for each day after fetch-or-skip:  
   `ProgressEvent("band_hr", current=i, total=len(days), message=day.isoformat())`.

Do not change written/skipped/conflict counters or meta shape.

- [ ] **Step 1: Write failing test**

```python
# services/zepp-importer/tests/test_progress_sync.py
from datetime import date
from pathlib import Path

import json

from fitness.archive import RawArchive
from fitness.config import Settings
from fitness.progress import ProgressEvent
from fitness.sync import SyncOptions, run_sync


class FakeClient:
    def __init__(self) -> None:
        self.history_calls: list[int | None] = []
        self.detail_calls: list[tuple[str, str]] = []
        self.band_data_calls: list[str] = []

    def get_history(self, from_track_id: int | None = None) -> bytes:
        self.history_calls.append(from_track_id)
        assert from_track_id is None
        return json.dumps(
            {
                "code": 1,
                "message": "success",
                "data": {
                    "next": 0,
                    "summary": [
                        {
                            "trackid": "1700000000",
                            "source": "run.mifit.huami.com",
                            "type": 8,
                        }
                    ],
                },
            }
        ).encode()

    def get_detail(self, track_id: str, source: str) -> bytes:
        self.detail_calls.append((track_id, source))
        return json.dumps({"code": 1, "data": {"trackid": int(track_id)}}).encode()

    def get_band_data(self, day: str) -> bytes:
        self.band_data_calls.append(day)
        return json.dumps(
            {"code": 1, "message": "success", "data": [{"date_time": day, "data_hr": "QQ=="}]}
        ).encode()


def test_sync_emits_history_details_band_progress(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("fitness.sync._utc_today", lambda: date(2023, 1, 1))
    settings = Settings(
        zepp_app_token="tok",
        zepp_user_id="uid",
        data_raw_dir=tmp_path,
    )
    events: list[ProgressEvent] = []
    run_sync(
        settings,
        FakeClient(),  # type: ignore[arg-type]
        RawArchive(tmp_path),
        SyncOptions(from_date=date(2023, 1, 1)),
        on_progress=events.append,
    )

    assert events[0] == ProgressEvent("history", 1, None, "start")
    detail_events = [e for e in events if e.phase == "details"]
    assert detail_events == [
        ProgressEvent("details", 1, 1, "1700000000"),
    ]
    band_events = [e for e in events if e.phase == "band_hr"]
    assert len(band_events) == 1
    assert band_events[0] == ProgressEvent("band_hr", 1, 1, "2023-01-01")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd services/zepp-importer && uv run pytest tests/test_progress_sync.py::test_sync_emits_history_details_band_progress -v`

Expected: FAIL (`run_sync` unexpected keyword `on_progress` or events empty)

- [ ] **Step 3: Implement emissions in sync.py**

Sketch of required signature / threading:

```python
def run_sync(
    settings: Settings,
    client: ZeppClient,
    archive: RawArchive,
    options: SyncOptions,
    on_progress: ProgressCallback | None = None,
) -> SyncReport:
    ...
    activities = _history_activities(client, archive, report, options.from_date, on_progress)
    _sync_details(client, archive, options, report, activities, on_progress)
    _sync_heart_rate(client, archive, options, report, on_progress)
    ...
```

In `_sync_details`, precompute targets:

```python
targets: list[dict[str, Any]] = []
for activity in activities:
    # same validation/filter as today; append only when it would enter fetch/skip path
    targets.append(activity)

for index, activity in enumerate(targets, start=1):
    # existing fetch-or-skip body
    emit(on_progress, ProgressEvent("details", index, len(targets), track_id))
```

In `_sync_heart_rate`, precompute day list then tick after each day.

In `_history_activities`, maintain `page = 0` and after each successful archive write:

```python
page += 1
emit(on_progress, ProgressEvent("history", page, None, name))
```

- [ ] **Step 4: Run progress + existing sync tests**

Run: `cd services/zepp-importer && uv run pytest tests/test_progress_sync.py tests/test_sync.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add services/zepp-importer/src/fitness/sync.py \
  services/zepp-importer/tests/test_progress_sync.py
git commit -m "$(cat <<'EOF'
feat: emit progress events from fitness sync

EOF
)"
```

---

### Task 3: Emit progress from `run_normalize`

**Files:**
- Modify: `services/zepp-importer/src/fitness/normalize/load.py`
- Test: `services/zepp-importer/tests/test_progress_normalize.py`

**Interfaces:**
- Consumes: `ProgressEvent`, `ProgressCallback`, `emit` from `fitness.progress`
- Produces: `run_normalize(raw_dir, duckdb_path, on_progress: ProgressCallback | None = None) -> NormalizeReport`
- Thread callback into `_load_lists`, `_load_details`, `_load_band_data`

**Emission rules (exact):**

1. **lists** — after `items_by_id` is fully built, if empty emit nothing; else for each `(activity_id, …)` in sorted order, after upsert-or-skip:  
   `ProgressEvent("lists", i, len(items_by_id), activity_id)`

2. **details** — `paths = sorted(details_dir.glob("*.json"))`; if empty emit nothing; else after each file:  
   `ProgressEvent("details", i, len(paths), path.stem)`  
   (tick even when SHA skip continues early)

3. **band** — same pattern for `band-data/*.json` with phase `"band"` and `message=path.stem`

- [ ] **Step 1: Write failing test**

Reuse fixtures from `tests/fixtures/normalize_list.json` and `normalize_detail.json`.

```python
# services/zepp-importer/tests/test_progress_normalize.py
from pathlib import Path

from fitness.normalize.load import run_normalize
from fitness.progress import ProgressEvent


def test_normalize_emits_lists_and_details_progress(tmp_path: Path):
    raw = tmp_path / "raw"
    (raw / "activity-lists").mkdir(parents=True)
    (raw / "activity-details").mkdir(parents=True)
    fixtures = Path(__file__).parent / "fixtures"
    (raw / "activity-lists" / "trackid-start.json").write_bytes(
        (fixtures / "normalize_list.json").read_bytes()
    )
    (raw / "activity-details" / "1700000100.json").write_bytes(
        (fixtures / "normalize_detail.json").read_bytes()
    )
    events: list[ProgressEvent] = []
    run_normalize(raw, tmp_path / "out.duckdb", on_progress=events.append)

    list_events = [e for e in events if e.phase == "lists"]
    assert list_events  # at least one activity from fixture
    assert list_events[0].current == 1
    assert list_events[0].total == len(list_events)

    detail_events = [e for e in events if e.phase == "details"]
    assert detail_events == [
        ProgressEvent("details", 1, 1, "1700000100"),
    ]
    assert not any(e.phase == "band" for e in events)
```

Adjust `activity_id` / fixture counts to match the actual fixture contents (inspect `normalize_list.json` when implementing).

- [ ] **Step 2: Run test to verify it fails**

Run: `cd services/zepp-importer && uv run pytest tests/test_progress_normalize.py::test_normalize_emits_lists_and_details_progress -v`

Expected: FAIL (`on_progress` unexpected)

- [ ] **Step 3: Implement emissions in load.py**

```python
def run_normalize(
    raw_dir: Path,
    duckdb_path: Path,
    on_progress: ProgressCallback | None = None,
) -> NormalizeReport:
    ...
    _load_lists(conn, raw_dir, report, on_progress)
    _load_details(conn, raw_dir, report, on_progress)
    _load_band_data(conn, raw_dir, report, on_progress)
```

In each loader: materialize the work list, then `emit` after each unit (including skips).

- [ ] **Step 4: Run progress + existing normalize tests**

Run: `cd services/zepp-importer && uv run pytest tests/test_progress_normalize.py tests/test_normalize_load.py tests/test_normalize_band_load.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add services/zepp-importer/src/fitness/normalize/load.py \
  services/zepp-importer/tests/test_progress_normalize.py
git commit -m "$(cat <<'EOF'
feat: emit progress events from fitness normalize

EOF
)"
```

---

### Task 4: CLI Rich progress + dependency + README

**Files:**
- Modify: `services/zepp-importer/src/fitness/progress.py` (add Rich helper)
- Modify: `services/zepp-importer/src/fitness/cli.py`
- Modify: `services/zepp-importer/pyproject.toml`
- Modify: `README.md`
- Test: `services/zepp-importer/tests/test_cli.py` (extend)

**Interfaces:**
- Produces:
  - `PHASE_LABELS_SYNC = {"history": "Syncing activity history", "details": "Syncing activity details", "band_hr": "Syncing band HR"}`
  - `PHASE_LABELS_NORMALIZE = {"lists": "Normalizing activities", "details": "Normalizing activity details", "band": "Normalizing band HR"}`
  - `@contextmanager def progress_callback(labels: dict[str, str]) -> Iterator[ProgressCallback | None]`  
    If not `sys.stderr.isatty()`, yield `None`. Else start Rich `Progress` on stderr, yield a callback that creates/updates one task per phase (first event for a phase adds the task with `total` or uses indeterminate when `total is None`), and stop Progress on exit.

**Rich behavior:**
- Use `Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), BarColumn(), TaskProgressColumn(), console=Console(stderr=True))`
- On event: if phase unseen, `add_task(labels.get(phase, phase), total=event.total)`; then `update(task_id, completed=event.current, total=event.total, description=labels.get(phase, phase))`
- For `total is None`, Rich treats as indeterminate — acceptable

**Note:** Spec says core must not import Rich. Keep Rich imports inside `progress_callback` only (lazy import inside the context manager), so `from fitness.progress import ProgressEvent` stays free of Rich for sync/normalize. Alternatively split `fitness/progress_cli.py` — prefer lazy import in `progress_callback` to keep one module if sync/normalize never call it.

- [ ] **Step 1: Add `rich` dependency and lock**

In `services/zepp-importer/pyproject.toml` dependencies list, add `"rich>=13.7"`.

Run: `cd services/zepp-importer && uv sync --extra dev`

- [ ] **Step 2: Write failing CLI test for callback wiring**

```python
# append to tests/test_cli.py
def test_normalize_passes_on_progress_kwarg(tmp_path, monkeypatch):
    raw = tmp_path / "raw"
    (raw / "activity-lists").mkdir(parents=True)
    (raw / "activity-details").mkdir(parents=True)
    fixtures = Path(__file__).parent / "fixtures"
    (raw / "activity-lists" / "trackid-start.json").write_bytes(
        (fixtures / "normalize_list.json").read_bytes()
    )
    (raw / "activity-details" / "1700000100.json").write_bytes(
        (fixtures / "normalize_detail.json").read_bytes()
    )
    db = tmp_path / "out.duckdb"
    monkeypatch.setenv("DATA_RAW_DIR", str(raw))
    monkeypatch.setenv("DUCKDB_PATH", str(db))
    monkeypatch.delenv("ZEPP_APP_TOKEN", raising=False)
    monkeypatch.delenv("ZEPP_USER_ID", raising=False)

    seen = {}

    def capture_normalize(raw_dir, duckdb_path, on_progress=None):
        seen["on_progress"] = on_progress
        from fitness.normalize.load import NormalizeReport
        return NormalizeReport(activities_upserted=1)

    monkeypatch.setattr("fitness.cli.run_normalize", capture_normalize)
    monkeypatch.setattr("sys.stderr", type("E", (), {"isatty": lambda self: False})())

    result = runner.invoke(app, ["normalize"])
    assert result.exit_code == 0
    assert seen["on_progress"] is None


def test_normalize_wires_callback_when_tty(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_RAW_DIR", str(tmp_path))
    monkeypatch.setenv("DUCKDB_PATH", str(tmp_path / "out.duckdb"))
    monkeypatch.delenv("ZEPP_APP_TOKEN", raising=False)
    monkeypatch.delenv("ZEPP_USER_ID", raising=False)

    seen = {}

    def capture_normalize(raw_dir, duckdb_path, on_progress=None):
        seen["on_progress"] = on_progress
        from fitness.normalize.load import NormalizeReport
        return NormalizeReport()

    monkeypatch.setattr("fitness.cli.run_normalize", capture_normalize)
    monkeypatch.setattr(
        "fitness.progress.sys.stderr",
        type("E", (), {"isatty": lambda self: True})(),
    )

    result = runner.invoke(app, ["normalize"])
    assert result.exit_code == 0
    assert callable(seen["on_progress"])
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd services/zepp-importer && uv run pytest tests/test_cli.py::test_normalize_passes_on_progress_kwarg tests/test_cli.py::test_normalize_wires_callback_when_tty -v`

Expected: FAIL (normalize CLI does not pass `on_progress` / attribute missing)

- [ ] **Step 4: Implement Rich helper + CLI wiring**

```python
# in progress.py — add after emit(); lazy-import Rich inside the context manager
import sys
from contextlib import contextmanager
from typing import Iterator

PHASE_LABELS_SYNC = {
    "history": "Syncing activity history",
    "details": "Syncing activity details",
    "band_hr": "Syncing band HR",
}
PHASE_LABELS_NORMALIZE = {
    "lists": "Normalizing activities",
    "details": "Normalizing activity details",
    "band": "Normalizing band HR",
}

@contextmanager
def progress_callback(labels: dict[str, str]) -> Iterator[ProgressCallback | None]:
    if not sys.stderr.isatty():
        yield None
        return
    from rich.console import Console
    from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=Console(stderr=True),
    )
    task_ids: dict[str, int] = {}
    with progress:
        def _on_progress(event: ProgressEvent) -> None:
            label = labels.get(event.phase, event.phase)
            if event.phase not in task_ids:
                task_ids[event.phase] = progress.add_task(label, total=event.total)
            progress.update(
                task_ids[event.phase],
                completed=event.current,
                total=event.total,
                description=label,
            )
        yield _on_progress
```

CLI:

```python
from fitness.progress import PHASE_LABELS_NORMALIZE, PHASE_LABELS_SYNC, progress_callback

# in _run_sync_cmd:
with progress_callback(PHASE_LABELS_SYNC) as on_progress:
    report = run_sync(..., on_progress=on_progress)

# in normalize_cmd:
with progress_callback(PHASE_LABELS_NORMALIZE) as on_progress:
    report = run_normalize(..., on_progress=on_progress)
```

README (setup section, after normalize mention):

```markdown
On an interactive terminal, `fitness sync` and `fitness normalize` show progress bars.
```

- [ ] **Step 5: Run full importer test suite**

Run: `cd services/zepp-importer && uv run pytest -v`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add services/zepp-importer/src/fitness/progress.py \
  services/zepp-importer/src/fitness/cli.py \
  services/zepp-importer/pyproject.toml \
  services/zepp-importer/uv.lock \
  services/zepp-importer/tests/test_cli.py \
  README.md
git commit -m "$(cat <<'EOF'
feat: show Rich progress for sync and normalize

EOF
)"
```

---

## Spec coverage check

| Spec requirement | Task |
|---|---|
| `ProgressEvent` + optional callback | 1 |
| Sync phases history / details / band_hr | 2 |
| Normalize phases lists / details / band | 3 |
| Skips advance bar | 2, 3 |
| Empty phases emit nothing | 2, 3 |
| Rich on TTY only; silent otherwise | 4 |
| Explicit `rich` dependency | 4 |
| Final report unchanged | 4 (still `typer.echo(report)`) |
| Append-callback unit tests | 2, 3 |
| No Rich assertions in unit tests | 2, 3, 4 |
| README one-liner | 4 |

## Placeholder / consistency check

- Phase names match spec: `history`, `details`, `band_hr`, `lists`, `details`, `band`
- `emit` / `ProgressCallback` / `ProgressEvent` names consistent across tasks
- CLI labels distinguish sync vs normalize for shared `details` phase name
- Rich is lazy-imported inside `progress_callback` so core sync/normalize never load Rich
