# CLI progress for sync & normalize — Design

**Date:** 2026-08-26  
**Status:** Approved (brainstorming)  
**Scope:** Terminal progress feedback for long-running `fitness sync` and `fitness normalize`

## 1. Goal

Show live progress during initial (and incremental) sync/normalize so long runs
do not look hung. Keep core sync/normalize logic free of terminal I/O.

**Success criteria**

- Interactive TTY runs show Rich progress (phase label + bar when total known)
- Non-TTY / piped / CI runs stay silent until the existing final report
- `run_sync` / `run_normalize` accept an optional progress callback; default `None`
- Existing unit tests keep passing without changes to assertions about stdout
- New unit tests assert emitted progress events (phase order and totals)

## 2. Decisions locked in brainstorming

| Decision | Choice |
|---|---|
| UX | **A** — Rich progress bars (not plain status lines / tqdm) |
| Core API | Optional `on_progress` callback; no terminal I/O in library |
| Non-TTY | No progress UI; final report unchanged |
| Skipped work | Still advances the bar (avoids freeze on skip-heavy re-runs) |

## 3. Out of scope

- Progress for `fitness status`
- Changing sync/normalize business logic, skip rules, or report fields
- Logging to files or structured progress protocols
- Web/dashboard progress

## 4. Progress API

```python
@dataclass(frozen=True)
class ProgressEvent:
    phase: str           # e.g. "history", "details", "band_hr", "lists", "band"
    current: int         # completed units in this phase so far (1..total after each tick)
    total: int | None    # None when unknown (history pages)
    message: str = ""    # optional short label (e.g. track id / date)
```

- `ProgressCallback = Callable[[ProgressEvent], None]`
- `run_sync(..., on_progress: ProgressCallback | None = None)`
- `run_normalize(..., on_progress: ProgressCallback | None = None)`
- Helper: `_emit(on_progress, event)` no-ops when callback is `None`

Emit only after each unit completes (no separate “phase started” event).
When `total` is known, `current` runs `1..total`.

## 5. Phases

### Sync

| Phase | When | `total` | Tick |
|---|---|---|---|
| `history` | Each history page archived | `None` | After each page |
| `details` | After activity list filtered for this run | Count of activities that will be considered (fetch or skip) | Per activity |
| `band_hr` | Before day loop | Number of days in range | Per day (fetch or skip) |

### Normalize

| Phase | When | `total` | Tick |
|---|---|---|---|
| `lists` | After items gathered by activity id | `len(items_by_id)` | Per activity upsert/skip |
| `details` | Before file loop | Count of `activity-details/*.json` | Per file |
| `band` | Before file loop | Count of `band-data/*.json` | Per file |

Empty phases emit nothing (no events).

## 6. CLI wiring

In `fitness.cli`:

1. If `sys.stderr.isatty()`, build a Rich `Progress` listener that maps phases to
   tasks (update description + completed/total).
2. Else pass `on_progress=None`.
3. Always print the existing report string after the run.
4. Declare `rich` as an explicit package dependency in `zepp-importer`.

Suggested display: one active task at a time (or one task per phase created when
the first event for that phase arrives). Description like
`Syncing activity details` / `Normalizing band HR`.

## 7. Testing

- Append-callback tests: sync and normalize emit expected phase sequence and
  matching totals on fixture/raw fixtures (extend existing test modules).
- Do not assert Rich rendering in unit tests.
- Default `on_progress=None` preserves current CLI/test silence of core functions.

## 8. Docs

- One-line note in root `README.md` setup section that sync/normalize show
  progress on an interactive terminal.
