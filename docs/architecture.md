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

## Handoff

- **M2 — persistence:** begins after live raw payloads exist. Validate the
  provisional schema, normalize into DuckDB, and retain raw-file provenance.
- **M3 — application:** expose DuckDB through FastAPI and build activity,
  detail, heart-rate, and zone visualizations in React.
- **M4 — HR intelligence:** implement configurable zone models, observed HRmax,
  resting-HR estimation, and trends. Keep Zepp-provided load distinct from
  locally calculated metrics.

The governing principle is: measure first, model second. Unknown source fields
remain raw rather than receiving inferred meanings.
