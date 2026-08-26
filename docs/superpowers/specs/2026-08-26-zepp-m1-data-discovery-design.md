# Milestone 1 — Zepp Data Discovery Design

**Date:** 2026-08-26  
**Status:** Approved  
**Scope:** Milestone 1 only (data discovery + scaffolded importer)

## 1. Goal

Build the foundation of a local-first fitness analytics app for Amazfit T-Rex Pro data synchronized via Zepp (Global/EU), without inventing a schema before real payloads exist.

Milestone 1 establishes:

1. Current Zepp Cloud authentication and endpoint knowledge (from maintained OSS, then live validation later)
2. A scaffolded Python importer that archives raw API responses immutably
3. Clear docs so credentials can be plugged in later and sync can proceed safely
4. A *provisional* normalized schema proposal in documentation only

**Success criteria for M1**

- User can install the importer with `uv`
- `fitness status` works without credentials
- `fitness sync` fails clearly until `ZEPP_APP_TOKEN` / `ZEPP_USER_ID` are set
- With credentials (later), sync archives activity history, activity details, and continuous HR under `data/raw/`
- Docs cover auth extraction, architecture, provisional data model, and HR zone models (stub)

## 2. Decisions locked in brainstorming

| Decision | Choice |
|---|---|
| Scope | Milestone 1 only |
| Credentials | Not available yet — research + scaffolded importer |
| Zepp region | Global / EU |
| Monorepo width | Importer-only (`services/zepp-importer/`); web/API later |
| CLI | Python via `uv run fitness …` |
| Implementation approach | Own thin HTTP client; learn from OSS; do not vendor/copy exporters |

## 3. Out of scope (explicit)

- DuckDB schema and normalization pipeline (Milestone 2)
- FastAPI / React web app (Milestone 3)
- Observed HRmax, resting HR estimators, zone engines (Milestone 4)
- Email/password Zepp login
- PostgreSQL, Redis, queues, cloud services
- Docker (welcome later; not required for M1)
- Blind copying of old exporter code

## 4. Target architecture (context) vs M1 slice

**Full target (later milestones):**

```text
Amazfit T-Rex Pro → Zepp → Zepp Cloud
  → Python importer → raw immutable files → DuckDB
  → FastAPI → React + TypeScript web app
```

**Milestone 1 implements only:**

```text
Zepp Cloud ──(when credentials present)──► zepp-importer
                                              │
                                              ▼
                                         data/raw/**
                                              │
                                         docs (provisional schema)
```

## 5. Repository layout (M1)

```text
/
├── services/
│   └── zepp-importer/
│       ├── pyproject.toml
│       ├── README.md
│       ├── src/
│       │   └── fitness/          # CLI package name: fitness
│       │       ├── __init__.py
│       │       ├── cli.py
│       │       ├── config.py
│       │       ├── client.py     # Zepp HTTP client
│       │       ├── archive.py    # immutable raw writer
│       │       ├── sync.py       # orchestration
│       │       └── endpoints.py  # named endpoint paths / builders
│       └── tests/
├── data/
│   └── raw/                      # gitignored contents; keep .gitkeep
├── docs/
│   ├── architecture.md
│   ├── zepp-auth.md
│   ├── zepp-data-model.md
│   ├── hr-zone-models.md
│   ├── examples/
│   └── superpowers/specs/        # this design
├── .env.example
├── .gitignore
└── README.md
```

Root README documents: clone → `cd services/zepp-importer && uv sync` → copy `.env.example` → auth guide → `uv run fitness status`.

## 6. Authentication & configuration

### 6.1 Environment variables

```text
ZEPP_APP_TOKEN=          # required for sync
ZEPP_USER_ID=            # required for sync
ZEPP_HOST=api-mifit-us3.zepp.com   # default Global/EU guess; overridable
ZEPP_REGION=eu           # informational
DATA_RAW_DIR=            # optional; default <repo>/data/raw
```

Secrets never committed. `.gitignore` must include `.env`, `data/raw/**` (except `.gitkeep`), HAR/captures, and future DuckDB files.

### 6.2 Auth model

- Authentication is the `apptoken` request header on GETs to the regional host.
- No password login in M1 (current OSS consensus: unreliable / rate-limited).
- Primary extraction path (documented in `docs/zepp-auth.md`):
  1. Open Huami privacy / export page in a desktop browser
  2. Sign in
  3. DevTools → Application → Cookies → copy `apptoken` and `userid`
- Fallback: MITM/HAR capture of Zepp app traffic to obtain token, user id, and confirmed regional host.
- Tokens are treated like passwords; ~30-day expiry is expected; `401`/`403`/empty critical payloads → instruct re-extraction.

### 6.3 Behavior without credentials

| Command | Behavior |
|---|---|
| `fitness status` | Exit 0; report missing creds, archive counts, last sync meta if any |
| `fitness sync` / `fitness import` | Exit non-zero; short message + pointer to `docs/zepp-auth.md` |
| Live HTTP | Never called without both token and user id |

No synthetic/fake Zepp payloads are written to `data/raw/`.

## 7. CLI

Package entry point: `fitness`.

| Command | M1 behavior |
|---|---|
| `fitness status` | Config presence, host, raw archive inventory, last sync stamp |
| `fitness sync` | Incremental sync when credentials present |
| `fitness sync --from YYYY-MM-DD` | Restrict discovery window |
| `fitness sync --activity <id>` | Fetch one activity list entry (if needed) + detail |
| `fitness import` | Alias of `sync` in M1 |

`rebuild` is documented as Milestone 2 (requires DuckDB normalization).

## 8. Sync orchestration

When credentials exist, `sync` is idempotent and resume-safe:

1. Validate config (token, user id, host, raw dir writable)
2. Discover activities via list/history endpoints (respect `--from` / `--activity`); archive each list page response under `activity-lists/`
3. For each activity missing a detail archive (or forced by `--activity`): fetch detail → archive under `activity-details/`
4. Fetch continuous heart-rate for the relevant date range → archive one file per day under `heart-rate/`
5. Optionally fetch profile and training-load / sport-statistics endpoints **only if** documented as available for this host
6. Update `data/raw/_meta/last_sync.json` (no secrets)

### 8.1 Raw archive layout

Prefer **one file per HTTP response body** (request-faithful), not derived splits:

```text
data/raw/
├── activity-lists/<query-key>.json      # original list/history page responses
├── activity-details/<zepp-id>.json      # original detail responses
├── heart-rate/YYYY-MM-DD.json           # original continuous-HR responses
├── profile/…                            # if retrieved
└── _meta/last_sync.json
```

`<query-key>` encodes the request window/page (e.g. `from-to-pageN`) so pagination is reproducible. If OSS reveals a stable per-activity summary endpoint, those responses may also be stored under `activities/<zepp-id>.json`. Do **not** invent per-id “activity” files by rewriting list items unless the bytes are exactly an API response body.

### 8.2 Immutability rules

- Every API response body used by the importer is written to raw storage **before** any interpretation beyond choosing the path.
- If the target path does not exist → write.
- If the target path exists and content is byte-identical → skip (idempotent).
- If the target path exists and content differs → do **not** overwrite; write a conflict sibling (`<stem>.<utc-timestamp>.json`) and log a warning.
- Raw files are never deleted by sync.

### 8.3 Endpoints (provisional)

Named client methods, paths taken from current OSS knowledge and marked unverified until live sync against T-Rex Pro / Global-EU:

- Activity / sport history (paginated if supported)
- Activity / workout detail (samples; GPS when present)
- Continuous / band heart rate by date range
- User/profile if available
- Training load / sport statistics only when confirmed

Exact URLs, query params, pagination, units, and field meanings live in `docs/zepp-data-model.md` and are updated after the first successful live sync.

### 8.4 Errors & retries

- Missing credentials → fail fast (sync/import)
- Auth failure → clear re-extract guidance
- Transient network / rate limit → limited retries with backoff, then fail loudly
- Partial progress is kept via archives; next sync resumes

## 9. Documentation deliverables

| Document | Purpose |
|---|---|
| `README.md` | Setup and command flow |
| `docs/architecture.md` | Full target architecture + M1 slice |
| `docs/zepp-auth.md` | Cookie + MITM auth extraction; secret handling |
| `docs/zepp-data-model.md` | Endpoints, fields, units, timestamps, sport IDs, nullability, gaps — **provisional from OSS**, labeled unverified until live sync |
| `docs/hr-zone-models.md` | Spec stub: %HRmax, HRR/Karvonen, manual; no implementation in M1 |
| `docs/examples/` | Sanitized example payload structure/notes; real sanitized examples after first live sync |
| `.env.example` | Required env vars |

### 9.1 Provisional normalized schema (docs only)

Conceptual starting point for Milestone 2, mapped to observed/expected Zepp fields with explicit unknown markers:

- `activities` — identity, sport type vs analytical category, times, duration, distance, calories, HR summaries, elevation, Zepp training load if present, `raw_file` pointer
- `activity_samples` — per-sample HR/GPS/speed/cadence/distance (nullable columns expected)
- `heart_rate_samples` — continuous monitoring; dedup strategy vs workout samples documented, not implemented
- `daily_metrics` — only fields supported by source data

Principle: **measure first, model second.** Unclear fields stay in raw JSON and are documented as unknown; meanings are not invented from Garmin/Strava/FIT assumptions.

## 10. Testing (M1)

Unit tests with mocks/fixtures only (no live Zepp calls):

- Config loading and missing-credential errors
- Archive idempotency (skip identical; conflict sibling on mismatch)
- HTTP client request shaping (headers, paths) against mocked responses
- Sync orchestration with fake client (which files would be written / skipped)

Analytics / zone / HRmax / resting-HR tests are deferred to later milestones.

## 11. OSS research stance

Investigate and cite current maintained projects (non-exhaustive): `m4ary/zepp-health-cli`, `rolandsz/Mi-Fit-and-Zepp-workout-exporter`, `bentasker/zepp_to_influxdb`, `H3llK33p3r/zepp-fit-extractor`, and related Global/EU notes. Use them as evidence for auth and endpoints; implement an independent client. Do not copy their code wholesale.

## 12. Privacy & safety

- Local-first; no third-party analytics/telemetry in M1
- Health data and secrets stay on disk under gitignored paths
- Never commit tokens, user IDs, raw activity files, or databases

## 13. Handoff to later milestones

| Milestone | Starts when |
|---|---|
| M2 Persistence | At least one successful live sync (or user-supplied raw archives) exists; schema proposal refined from real payloads |
| M3 Basic dashboard | DuckDB populated; overview + activities + detail + HR chart + zones |
| M4 HR intelligence | Configurable zone models, observed HRmax, resting HR, trends |

## 14. Implementation principles

1. Archive raw responses before interpreting them
2. Prefer UTC internally; display timezone Europe/Madrid later; never silently reinterpret Zepp timestamps
3. Label Zepp proprietary training-load fields separately from any future calculated load
4. YAGNI: no web/API/DuckDB scaffolding in M1
