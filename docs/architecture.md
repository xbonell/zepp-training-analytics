# Architecture

Zepp Training Analytics is local-first: credentials, raw health data, and future
derived data stay on the user's machine.

## Target pipeline

```text
Amazfit T-Rex Pro
        │ device sync
        ▼
      Zepp app ──► Zepp Cloud
                        │ HTTPS GET + apptoken
                        ▼
                 Python importer
                        │ request-faithful, immutable responses
                        ▼
                    data/raw/
                        │ M2 normalization
                        ▼
                     DuckDB
                        │ M3 query API
                        ▼
                     FastAPI
                        │
                        ▼
               React + TypeScript UI
                        │ M4 analytics
                        ▼
             HR zones, HRmax/RHR, trends
```

## Milestone 1 slice

M1 implements only the thin HTTP client, sync orchestration, immutable raw
archive, CLI, and provisional documentation:

```text
Zepp Cloud ──► services/zepp-importer ──► data/raw/**
                         │
                         └── fitness status / sync / import
```

The importer first archives each response body, then reads only enough JSON to
paginate history and request activity details. Existing identical files are
skipped; differing responses are written as conflict siblings rather than
overwriting prior bytes. Sync metadata contains no secrets.

Current archive categories are:

```text
data/raw/
├── activity-lists/trackid-*.json
├── activity-details/<trackid>.json
├── band-data/YYYY-MM-DD.json
├── heart-rate/YYYY-MM-DD.json   # legacy hollow /heartRate archives (optional)
└── _meta/last_sync.json
```

First live Global-EU sync succeeded (2026-08-26). Endpoint and field findings
are recorded in `docs/zepp-data-model.md`. M1 contains no DuckDB, API, web UI,
zone calculations, or proprietary training-load interpretation.

## Milestone 2 slice

M2 normalizes archived raw JSON into a local DuckDB database (offline; no live
Zepp calls):

```text
data/raw/** ──► fitness normalize ──► data/zepp.duckdb
```

`activities` and `activity_samples` are populated from activity-list summaries
and detail `heart_rate` series. `heart_rate_samples` holds all-day band HR from
`band-data/` (`data_hr`: 1440×uint8 per minute, omit sentinel `254`, UTC
midnight + minute index). Workout HR stays in `activity_samples` only.
Raw-file provenance is retained on each row.

## Milestone 3 slice

M3 exposes normalized DuckDB data through a read-only FastAPI service and a
React/Vite dashboard (no live Zepp calls):

```text
data/zepp.duckdb ──► services/api (FastAPI) ──► /api/*
                              │
data/profile.json ────────────┤ settings + HRmax override
                              │
                              ▼
                     apps/web (React + Vite)
                              │
                              └── Overview · Activities · Detail · Zones
```

Zone analytics use the OTF-style % MaxHR model (see `docs/hr-zone-models.md`).
HRmax resolves from profile override or a suggested 99th percentile of workout
HR samples. Time-in-zone and Splat (Z4+Z5 minutes) are computed in the API from
workout `activity_samples`; nothing is written back to DuckDB.

API defaults: `data/zepp.duckdb`, `data/profile.json`, CORS for
`http://localhost:5173`. Web dev proxies `/api` to port 8000.

### Self-hosted deploy

The M3+ **Settings** page (connection, masked token, manual sync, profile) also
targets a single-operator VPS deploy via [`outer-rim`](deploy-outer-rim.md):
nginx serves the static SPA on `training.xbonell.com`, proxies `/api/` to the
`zepp-training-api` container, and Cloudflare Access gates the origin. Credentials,
raw archives, DuckDB, and sync state remain on the operator's VPS data volume —
not a multi-tenant cloud service. Local-first dev paths (`fitness` CLI, local
API + Vite) are unchanged.

## Handoff

- **M2 — persistence:** implemented for activity summaries, workout HR samples
  (`activity_samples`), and band continuous HR (`heart_rate_samples`).
- **M3 — application:** implemented — FastAPI query layer plus React dashboard
  (overview, activities, detail, zones, Settings, light/dark/system themes).
- **M4 — HR intelligence:** additional zone models (HRR/Karvonen, manual BPM
  tables), richer HRmax/RHR estimators, and trends. Keep Zepp-provided load
  distinct from locally calculated metrics.

The governing principle is: measure first, model second. Unknown source fields
remain raw rather than receiving inferred meanings.
