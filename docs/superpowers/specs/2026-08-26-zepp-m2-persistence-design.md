# Milestone 2 — Persistence Design

**Date:** 2026-08-26  
**Status:** Approved (brainstorming)  
**Scope:** Milestone 2 first cut — DuckDB normalization for activities + workout HR

## 1. Goal

Turn immutable M1 raw archives into a queryable local DuckDB database without
requiring network access, while preserving raw-file provenance.

**Success criteria**

- `uv run fitness normalize` creates/updates `data/zepp.duckdb` from `data/raw/`
- `activities` rows exist for history summaries even when detail files are missing
- Workout HR samples are loaded from detail `heart_rate` when a detail archive exists
- Re-runs are incremental: unchanged raw content (by SHA-256) is skipped
- Timestamps stored as UTC only
- Unit tests cover decode, sentinels, skip/upsert, and CLI smoke with temp DB
- No live Zepp calls; no committed health payloads

## 2. Decisions locked in brainstorming

| Decision | Choice |
|---|---|
| First-cut scope | **B** — activities + workout HR samples (not band-data / daily metrics) |
| CLI shape | **A** — separate `fitness normalize`; sync stays archive-only |
| Re-run behavior | **B** — incremental upsert by `activity_id`; skip unchanged raw hashes |
| Missing details | **A** — still load summary; samples empty until detail exists |
| Timestamps | **A** — UTC only in DuckDB; Europe/Madrid later in UI/API |
| Package layout | **1** — extend `services/zepp-importer` / `fitness` package |

## 3. Out of scope (explicit)

- Continuous/`band-data` `data_hr` decoding (follow-up)
- Daily metrics from band `summary` (steps/sleep/etc.)
- GPS, pace, cadence, and other detail series beyond workout HR
- Sport-type label mapping (store raw `type` integer only)
- FastAPI / React (M3)
- HR zone engines, HRmax/RHR (M4)
- Mixing fetch into normalize (no network in this command)
- Overwriting or deleting raw archives

## 4. Architecture

```text
data/raw/
  activity-lists/*.json
  activity-details/<trackid>.json
        │
        ▼
  fitness normalize   (local only)
        │
        ▼
  data/zepp.duckdb
    ├── activities
    └── activity_samples
```

Sync (`fitness sync`) remains responsible for HTTP + immutable archival.
Normalize is a pure offline transform.

## 5. Schema

Database file: `DUCKDB_PATH` or default `<repo-root>/data/zepp.duckdb` (gitignored).

### `activities`

| Column | Type | Notes |
|---|---|---|
| `activity_id` | VARCHAR PK | Zepp `trackid` string |
| `sport_type` | INTEGER | raw `type` |
| `source` | VARCHAR | |
| `bind_device` | VARCHAR | nullable |
| `started_at` | TIMESTAMPTZ | from `trackid` Unix seconds, UTC |
| `ended_at` | TIMESTAMPTZ | from `end_time` Unix seconds, UTC; nullable if missing |
| `duration_s` | INTEGER | from `run_time`; nullable |
| `distance_m` | DOUBLE | from `dis` numeric string; nullable / sentinel → NULL |
| `calories` | DOUBLE | from `calorie`; nullable |
| `avg_hr` | DOUBLE | from `avg_heart_rate`; nullable |
| `max_hr` | INTEGER | nullable |
| `min_hr` | INTEGER | nullable |
| `te` | INTEGER | Zepp proprietary; nullable |
| `exercise_load` | INTEGER | Zepp proprietary; nullable |
| `list_raw_file` | VARCHAR | path relative to raw root |
| `detail_raw_file` | VARCHAR | nullable until detail exists |
| `list_content_sha256` | VARCHAR | of contributing list file bytes |
| `detail_content_sha256` | VARCHAR | nullable |

Sentinels such as `-1`, `""`, and empty strings become SQL NULL for metric columns.

### `activity_samples`

| Column | Type | Notes |
|---|---|---|
| `activity_id` | VARCHAR | FK logical to `activities` |
| `elapsed_s` | INTEGER | cumulative seconds from HR decode |
| `hr_bpm` | INTEGER | nullable |
| `detail_raw_file` | VARCHAR | |
| `detail_content_sha256` | VARCHAR | |

Primary key: `(activity_id, elapsed_s)`.

No continuous-HR sample table in this cut.

## 6. Loader behavior

1. Open/create DuckDB; `CREATE TABLE IF NOT EXISTS` for both tables (additive
   alters only if a later revision needs them).
2. Scan `activity-lists/*.json`. For each `data.summary[]` item:
   - Compute SHA-256 of the list file.
   - If activity exists and `list_content_sha256` matches → skip summary upsert.
   - Else upsert summary-derived columns and set `list_raw_file` / list hash.
3. Scan `activity-details/<trackid>.json`. For each file:
   - Compute SHA-256. If matches `activities.detail_content_sha256` → skip.
   - Else decode `data.heart_rate`, delete existing samples for that
     `activity_id`, insert new sample rows, update `detail_*` on `activities`.
4. Summary-only activities remain with null `detail_*` and no samples.
5. Per-file errors are collected; processing continues. Exit non-zero if any
   errors occurred. Successful upserts are kept.

### Workout `heart_rate` decode

Format `dt,dv;dt,dv;…` (**live**-verified in M1):

1. `dt` = seconds since previous sample (cumulative elapsed ≈ `run_time`)
2. First `dv` = absolute BPM
3. Later `dv` = signed delta from previous BPM

Trailing/sentinel BPM values of `0` may appear; store as-is unless clearly
outside decode (do not invent filtering rules beyond what tests specify).

## 7. CLI & config

| Item | Value |
|---|---|
| Command | `fitness normalize` |
| Network | none |
| `DATA_RAW_DIR` | existing setting |
| `DUCKDB_PATH` | optional; default `<repo>/data/zepp.duckdb` |
| Dependency | add `duckdb` to `services/zepp-importer` |

Report to stdout: activities upserted/skipped, samples written, errors count.
No tokens or user IDs in output.

Suggested module layout inside `fitness/`:

- `normalize/schema.py` — DDL
- `normalize/decode.py` — HR string decode
- `normalize/load.py` — scan/upsert orchestration
- `cli.py` — `normalize` command

Exact file split may vary in the implementation plan as long as boundaries stay clear.

## 8. Testing

- Fixtures only (synthetic list + detail with short `heart_rate` string)
- Cases: HR decode; sentinel → NULL; skip on unchanged hash; detail sample
  replace; summary without detail; CLI smoke against temp DuckDB
- No reads from real `data/raw/**`; no live API

## 9. Docs updates (with implementation)

- `docs/architecture.md` — M2 slice + DuckDB path
- `docs/zepp-data-model.md` — mark normalized tables as implemented for this cut
- Root `README.md` — `fitness normalize` usage
- `.env.example` — `DUCKDB_PATH=` optional

## 10. Handoff after this cut

| Next | Starts when |
|---|---|
| Band-data continuous HR into samples | This normalize path ships |
| Daily metrics from band `summary` | Non-empty band archives + schema proposal |
| M3 FastAPI/React | DuckDB populated for activities + workout HR |

## 11. Evidence / priors

- Live findings: `docs/zepp-data-model.md`
- M1 design: `docs/superpowers/specs/2026-08-26-zepp-m1-data-discovery-design.md`
- Raw archives remain source of truth; DuckDB is derived and regenerable
