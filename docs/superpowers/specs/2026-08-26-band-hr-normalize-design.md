# Band-data continuous HR — Normalize Design

**Date:** 2026-08-26  
**Status:** Approved (brainstorming)  
**Scope:** Extend `fitness normalize` to load continuous HR from `band-data/` into DuckDB

## 1. Goal

Decode archived `band-data/*/data_hr` blobs into queryable continuous heart-rate
samples without changing workout `activity_samples` or requiring network access.

**Success criteria**

- `fitness normalize` loads band days into `heart_rate_samples`
- Sentinel `254` minutes are omitted; only plausible BPM rows stored
- Timestamps are UTC (`date_time` midnight UTC + minute index)
- Unchanged band files are skipped by SHA-256; changed files replace their rows
- Unit tests cover decode/skip/replace with fixtures only
- Docs state workout vs band split

## 2. Decisions locked in brainstorming

| Decision | Choice |
|---|---|
| Storage | **C** — new `heart_rate_samples`; leave `activity_samples` for workout only |
| Day origin | **A** — `date_time` midnight **UTC** |
| Sentinel `254` | **A** — omit (no row) |
| CLI | **A** — extend existing `fitness normalize` |
| Package layout | **2** — `normalize/band.py` + call from `run_normalize` |

## 3. Out of scope

- Decoding band `summary` daily metrics (steps/sleep)
- Merging/deduping band vs workout HR
- Europe/Madrid storage (display later)
- New CLI command or `--band` flag
- OSS 2-byte `short` decoding (this account is 1440×uint8)

## 4. Schema

```sql
CREATE TABLE IF NOT EXISTS heart_rate_samples (
  recorded_at TIMESTAMPTZ,
  hr_bpm INTEGER,
  source VARCHAR,
  raw_file VARCHAR,
  content_sha256 VARCHAR,
  PRIMARY KEY (recorded_at, source)
);
```

- `source` is always `'band'` in this cut
- Skip: if rows already exist for `raw_file` with matching `content_sha256`, skip the file
- On change: `DELETE FROM heart_rate_samples WHERE raw_file = ?` then insert

## 5. Decode & load

For each `band-data/YYYY-MM-DD.json`:

1. Compute file SHA-256; skip if unchanged for that `raw_file`
2. Parse JSON `data` array; for each element with non-empty `data_hr`:
   - Base64-decode; expect length **1440** (record error if not)
   - For minute `i` in `0..1439`: if byte ≠ `254` and `30 ≤ value ≤ 220`,
     emit `recorded_at = UTC midnight(date_time) + i minutes`, `hr_bpm = value`
3. Multiple `data[]` entries in one file: last write wins per `recorded_at` within the file load
4. Per-file errors collected; processing continues
5. Report adds: `band_days_upserted`, `band_days_skipped`, `band_samples_written`

## 6. Modules

| Path | Role |
|---|---|
| `fitness/normalize/band.py` | `decode_data_hr`, band-day helpers |
| `fitness/normalize/schema.py` | add `heart_rate_samples` DDL |
| `fitness/normalize/load.py` | call band load after details; extend report |
| tests + tiny fixture with synthetic base64 `data_hr` | |

## 7. Testing

- Decode: omit 254; keep in-range BPM; reject/flag wrong length
- Load: skip unchanged hash; replace on change; CLI normalize still exits 0 on happy path
- No real `data/raw` in tests

## 8. Docs

- `docs/architecture.md` — `heart_rate_samples` in DuckDB slice
- `docs/zepp-data-model.md` — band path implemented; workout vs band tables

## 9. Handoff

| Next | When |
|---|---|
| Daily metrics from band `summary` | After this ships |
| Dedup band ↔ workout | Product rule defined |
| M3 FastAPI/React | When DB coverage is enough for UI |
