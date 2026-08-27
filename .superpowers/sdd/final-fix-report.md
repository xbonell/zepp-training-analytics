# M3 final fix report

## Important findings resolved
- `scripts/dev.sh` uses Bash 3.2-compatible plain `wait`.
- Missing DuckDB returns actionable 503 responses from overview, activities, and activity detail; zones remain available with `source: none`.
- DuckDB `quantile_cont` HRmax and resolved API HRmax values are rounded to one decimal.
- Zone settings swatches use shared `zone-z*` CSS classes instead of API color keywords.
- Activity timestamps use the profile `display_timezone`, defaulting to `Europe/Madrid`.
- The purple favicon was replaced with a teal `Z` mark matching `--accent`.
- Production SQL suggested-HRmax behavior has DuckDB-backed regression coverage.

## Optional minors included
- `--zone-below` is visually distinct from `--zone-z1`.
- Activity detail uses settled requests and remains available when zones fail.

## Verification
- API: `uv run pytest -q` — 28 passed.
- Web: `npm test` — 28 passed, 8 files.
- Web build: `npm run build` — passed.
- Web lint: `./node_modules/.bin/oxlint` — passed with no findings.
- Script syntax: `/bin/bash -n scripts/dev.sh` — passed.

---

# Whole-branch review fixes — feature/self-hosted-settings

## Critical 1 — DuckDB read/write collision

Confirmed the bug is real: opening a `read_only=True` DuckDB connection while
another connection to the same file is open read-write in the same process
raises `duckdb.Error: Connection Error: Can't open a connection to same
database file with a different configuration than existing connections`.

Fix: added a process-wide `fitness_api.db.DUCKDB_LOCK` (`threading.Lock`).
- `queries.py`'s `_connect` is now a context manager that acquires the lock
  for the full lifetime of the read-only connection (open → use → close).
- `sync_job.py`'s `_run_job` acquires the same lock around the
  `run_normalize_fn(**job_kwargs)` call, so the read-write normalize
  connection never overlaps with an API read connection.
- Documented the rationale as a comment in `db.py` and at each call site.

This serializes rather than blocks-only-during-normalize; simplest fix that
satisfies "normalize never overlaps with API reads."

Regression test: `services/api/tests/test_duckdb_lock.py`
- `test_mixed_read_only_and_read_write_connections_raise_without_lock`
  reproduces the underlying DuckDB error directly (grounds the bug).
- `test_duckdb_lock_serializes_normalize_writes_and_api_reads` runs a
  simulated normalize (real read-write connection, held for 80ms under
  `DUCKDB_LOCK`) concurrently with a real `queries.list_activities` read
  call in separate threads, and asserts their connection-open windows
  never overlap in wall-clock time.

## Important 2 — Stale `running` status

`create_app()` now calls `_recover_interrupted_sync_job(settings)` before
building the FastAPI app. If the persisted sync job status is `running` at
startup (only possible if a previous process died mid-sync), it's rewritten
to `status=error`, `error="Interrupted by process restart; run Sync again"`,
preserving the original `started_at` and setting `finished_at=now`. Any
other status (including missing file) is left untouched.

Tests: `services/api/tests/test_main_startup.py` (rewrites stale running;
leaves ok/idle/missing untouched).

## Important 3 — ZEPP_HOST ignored

Added `Settings.zepp_host: str` (`fitness_api/config.py`), reading
`ZEPP_HOST` env var, default `api-mifit-us3.zepp.com` — matching
`start_sync_job`'s existing default so nothing changes for deployments that
don't set the env var. `main.py`'s `POST /api/settings/sync` handler now
passes `zepp_host=app_settings.zepp_host` into `start_sync_job`.

Test: `test_start_sync_job_passes_configured_zepp_host` in
`test_sync_job.py` asserts the configured host reaches the sync settings.

## Important 4 — Soft sync errors block normalize

`_run_job` no longer short-circuits on `report.errors` from a successful
(non-raising) `run_sync_fn` call. It now always proceeds to normalize in
that case, and:
- If normalize succeeds: final status `ok`, with
  `message="Sync completed with warnings: ..."` summarizing the sync
  warnings.
- If normalize also reports errors: final status `error`, with both the
  sync warning and normalize error joined into `error`.
- If `run_sync_fn` *raises* (e.g. `ZeppAuthError` or any other exception),
  behavior is unchanged: normalize is skipped and status is `error`.

Tests added to `test_sync_job.py`:
- `test_soft_sync_errors_still_run_normalize_and_report_ok_with_message`
- `test_soft_sync_errors_with_normalize_failure_reports_error`
- `test_sync_raising_skips_normalize` (locks in the "raise skips normalize"
  behavior explicitly)

## Important 5 — Show sync timestamps in Settings UI

`Settings.tsx` now renders a second line under the sync status showing
`Started: <local time>` / `Finished: <local time>` (via
`Date#toLocaleString()`), derived from `syncJob.started_at` /
`syncJob.finished_at`. The line is omitted entirely when neither timestamp
is set (e.g. `idle`).

Tests added to `Settings.test.tsx`:
- `shows sync started and finished timestamps`
- `omits the timestamp line when neither is set`

## Important 6 — Healthcheck without wget

`docs/deploy-outer-rim.md`'s compose healthcheck no longer shells out to
`wget` (not installed on `python:3.12-slim`). It now runs:

```yaml
healthcheck:
  test:
    [
      "CMD",
      "python3",
      "-c",
      "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=5).status == 200 else 1)",
    ]
```

Checked the repo-root `Dockerfile`: it has no `HEALTHCHECK` directive, so
the compose doc remains the single source of truth here; nothing else to
update.

## Minor — Zones.tsx loading copy

Loading state copy changed from "Reading your local training profile…" to
"Reading your heart-rate zones…" since this page only loads zone data, not
the training profile.

## Tests

```
cd services/api && uv run pytest -q
# 55 passed

cd apps/web && npm test -- --run
# Test Files  9 passed (9)
# Tests  32 passed (32)
```

Additional sanity checks:
- `cd apps/web && npm run build` — passed (tsc -b && vite build).
- `cd apps/web && ./node_modules/.bin/oxlint` — same single pre-existing
  warning in `ProfileForm.tsx` (unrelated to this change set), no new
  findings.

## Residual concerns

- `DUCKDB_LOCK` is a simple mutual-exclusion lock: it serializes *all*
  DuckDB access (reads included) rather than allowing concurrent readers.
  This trades some read concurrency for simplicity/correctness, which
  matches the review's suggested fix approaches. If read throughput during
  large sync/normalize runs becomes a problem, a proper single-writer/
  multi-reader lock would be a follow-up.
- The lock in `sync_job._run_job` wraps the whole `run_normalize_fn` call
  (including non-DB file parsing work), not just the DuckDB write itself,
  so API reads are blocked slightly longer than strictly necessary during
  a sync. Acceptable given normalize runs are infrequent and manually
  triggered.
