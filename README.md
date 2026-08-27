# Zepp Training Analytics

Local-first fitness analytics for Amazfit T-Rex Pro / Zepp (Global/EU).

Milestone 1 archives request-faithful Zepp Cloud responses locally. A first
Global-EU live sync against T-Rex Pro data is documented in
`docs/zepp-data-model.md`.

## Setup

```bash
git clone <repository-url>
cd zepp-training-analytics
cd services/zepp-importer
uv sync --extra dev
cp ../../.env.example ../../.env
# edit ../../.env — see ../../docs/zepp-auth.md
uv run fitness status
uv run fitness sync --from 2025-01-01
uv run fitness normalize
```

`fitness normalize` requires local raw archives; it writes `data/zepp.duckdb`
(activities, workout HR samples, and band continuous HR) by default.

On an interactive terminal, `fitness sync` and `fitness normalize` show progress bars.

`fitness status` works without credentials. `fitness sync` requires
`ZEPP_APP_TOKEN` and `ZEPP_USER_ID`; it writes raw responses under `data/raw/`
by default. Never commit `.env`, captures, or health data.

## Dashboard runbook

The M3 dashboard reads normalized DuckDB data through a local FastAPI service
and a React/Vite web app. No Zepp network calls are made at runtime.

**Prerequisites:** run `fitness normalize` so `data/zepp.duckdb` exists. Profile
and theme settings are stored in gitignored `data/profile.json`.

### Terminal 1 — API

```bash
cd services/api
uv sync --extra dev
uv run uvicorn fitness_api.main:app --reload --port 8000
```

Health check: `http://localhost:8000/api/health` (reports DuckDB reachability).

Optional env vars (see `.env.example`): `DUCKDB_PATH`, `PROFILE_PATH`,
`API_CORS_ORIGIN` (default `http://localhost:5173`).

### Terminal 2 — Web

```bash
cd apps/web
npm install
npm run dev
```

Open the URL Vite prints (default `http://localhost:5173`). The dev server
proxies `/api` to `http://127.0.0.1:8000`.

### Settings (local)

The **Settings** page (`/settings`) manages Zepp connection (masked token),
manual sync + normalize, and training profile (HRmax override). Data paths
match the API env vars above; see [architecture](docs/architecture.md).

For a self-hosted VPS deploy (Cloudflare Access, outer-rim compose, static drop),
see [Deploy on outer-rim](docs/deploy-outer-rim.md).

### Optional — both processes

```bash
./scripts/dev.sh
```

Starts the API and web dev servers together; stop with Ctrl+C.

## Documentation

- [Architecture and milestone boundaries](docs/architecture.md)
- [Self-hosted deploy (outer-rim)](docs/deploy-outer-rim.md)
- [Zepp authentication](docs/zepp-auth.md)
- [Provisional Zepp data model](docs/zepp-data-model.md)
- [Heart-rate zone models](docs/hr-zone-models.md)
- [Sanitized examples policy](docs/examples/README.md)
