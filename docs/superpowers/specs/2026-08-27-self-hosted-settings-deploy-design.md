# Self-Hosted Settings + Deploy Design

**Date:** 2026-08-27  
**Status:** Approved (brainstorming)  
**Scope:** Single-user public deploy of the existing dashboard behind Cloudflare
Access, with a Settings admin surface for Zepp connection, manual sync, and
training profile — wired through the `outer-rim` VPS stack.

## 1. Goal

Run Zepp Training Analytics at a subdomain of `xbonell.com` so the owner can use
the dashboard from anywhere, manage Zepp credentials and training profile in the
UI, and trigger sync→normalize without SSH/CLI.

**Success criteria**

- `training.xbonell.com` serves the React dashboard and proxies `/api` to the API
- Cloudflare Access is the only login gate (no in-app user accounts)
- Settings page: connection (token/user id), Sync now + status, training profile
- Sync job archives raw data then normalizes into DuckDB on a persistent volume
- Deploy fits `outer-rim`: static site mount + internal API container
- Tokens never returned in full from the API; never logged

## 2. Decisions locked in brainstorming

| Decision | Choice |
|---|---|
| Audience | Single user (owner only) |
| Exposure | Public internet subdomain |
| Hostname | `training.xbonell.com` (subdomain of personal site already on Cloudflare) |
| Access gate | Cloudflare Access on the whole hostname |
| Compute | Small VPS already running `outer-rim` |
| Orchestration | Extend `xbonell/outer-rim` Docker Compose |
| Routing | One subdomain; nginx proxies `/api/` → internal API (not a public `api.` host) |
| Sync mode (v1) | Manual “Sync now” only; schedule later |
| Settings scope (v1) | Connection + sync status + training profile (fold from Zones) |
| Normalize | Auto-chained after successful sync; no separate rebuild UI in v1 |
| App auth | None beyond Access |
| Architecture | Extend this monorepo’s FastAPI + React; image + static build published for `outer-rim` |

## 3. Out of scope (this cut)

- Multi-user / SaaS accounts
- Scheduled/cron sync
- Separate rebuild/normalize controls or raw-archive browser
- In-app login, sessions, or API keys (Access is the gate)
- Moving off DuckDB to a hosted database
- Public `api.training.xbonell.com` hostname
- Changing `outer-rim` security defaults beyond adding the new services

## 4. Deploy topology

```text
Browser
  → training.xbonell.com
  → Cloudflare (DNS + Access)
  → outer-rim VPS :443 (nginx-proxy + Let's Encrypt)
  → training.xbonell.com nginx container
       ├─ /          static Vite build (sites/training.xbonell.com/)
       └─ /api/*     proxy_pass → zepp-training-api:8000
                          └─ writable volume: data/
                             (zepp.duckdb, raw/, profile.json,
                              zepp.env secrets, sync job status)
```

### `outer-rim` responsibilities

- Service `training.xbonell.com`: `nginx:alpine`, `VIRTUAL_HOST` /
  `LETSENCRYPT_HOST` / `LETSENCRYPT_EMAIL`, read-only mount of
  `./sites/training.xbonell.com` plus site `nginx.conf`
- Site nginx: SPA `try_files` for `/`; `location /api/` proxies to
  `http://zepp-training-api:8000`
- Service `zepp-training-api`: image from this repo; **no** `VIRTUAL_HOST`
  (internal on `web` network only); healthcheck on `/api/health`; writable
  host volume for application `data/`
- Document that Cloudflare Access must protect the hostname before broad use

### This repo responsibilities

- API Docker image including importer sync/normalize entrypoints used by jobs
- Vite production build for the dashboard
- CI: publish API image; deploy static build into the VPS site folder (same drop
  pattern as other `outer-rim` static sites)
- Settings UI + connection/sync API endpoints

### Local development

Unchanged: `services/api` + `apps/web` Vite `/api` proxy against local `data/`.
Settings uses the same paths/layout as the production volume.

## 5. Settings surface

New **Settings** nav item in `apps/web`.

| Block | Behavior |
|---|---|
| Connection | Edit `ZEPP_USER_ID`; paste/replace `ZEPP_APP_TOKEN`. Read path returns masked hint only (`token_set`, optional last-4 hint). |
| Sync | “Sync now” starts sync→normalize. Show last/current run: timestamps, status (`idle` / `running` / `ok` / `error`), short error. Disable while running. |
| Training profile | Same fields as today’s Zones form via existing `GET/PUT /api/settings/profile`. Zones page remains analytics-focused (bands, suggested HRmax); profile editing lives on Settings. |

### API additions

| Method | Path | Behavior |
|---|---|---|
| `GET` | `/api/settings/connection` | `{ user_id, token_set, token_hint }` — never full token |
| `PUT` | `/api/settings/connection` | Persist user id + token to secrets file on data volume |
| `POST` | `/api/settings/sync` | Enqueue sync→normalize; `409` if already running |
| `GET` | `/api/settings/sync` | Current/last job status from status file |

Existing `/api/settings/profile` unchanged in contract.

No application-level auth middleware in v1; Cloudflare Access terminates at the
edge for the whole host (UI and `/api`).

## 6. Secrets, jobs, and failures

### Secrets

- Persist Zepp credentials on the API data volume as `data/zepp.env` (name may
  match existing importer env keys: `ZEPP_APP_TOKEN`, `ZEPP_USER_ID`, and host
  if needed)
- Not baked into the image; not committed; not stored long-term in `outer-rim`
  `.env` as the primary write path (Settings UI writes the volume file)
- Restrictive file permissions; API loads credentials when starting a sync
- Logs must never print `apptoken` / full token values

### Sync job (v1)

- Single API replica, in-process background task (no external queue)
- Flow: `POST` → status `running` → run existing importer sync against mounted
  `data/raw/` → on success run normalize into `data/zepp.duckdb` → `ok` or `error`
- Persist status to `data/_meta/sync_job.json` (`started_at`, `finished_at`,
  `status`, `error`, plus useful last-success fields when available)
- Concurrent `POST` while `running` → HTTP `409`
- Zepp `401` / `403` → job `error` with clear “token expired / update
  connection” message; no aggressive auto-retry
- Sync success + normalize failure → overall `error` with normalize reason; raw
  archives remain (immutable archive behavior unchanged)

### Explicitly deferred

- Cron/scheduled sync (add later on the same job API)
- Multi-worker job queue
- Raw archive browser / manual normalize-only controls

## 7. Testing

**API / importer orchestration**

- Connection PUT/GET mask and round-trip (full token never in GET body)
- Sync status machine: idle → running → ok/error; `409` when busy
- Normalize invoked after successful sync; skipped/failed paths covered with
  mocked importer

**Web**

- Settings: save connection, masked token display, Sync now disabled while
  running, status rendering
- Profile fields work after move/reuse from Zones
- Zones still loads profile-driven analytics without requiring edit form

**Deploy smoke (manual / ops)**

- `docker-compose config` in `outer-rim` after service add
- `/api/health` via the public host behind Access
- Static asset load + SPA deep link; `/api/settings/profile` same-origin

## 8. Repo change map

| Repo | Changes |
|---|---|
| `zepp-training-analytics` | Settings page; connection + sync endpoints; secrets/status files on `data/`; Dockerfile for API; CI for image + static deploy; tests above |
| `xbonell/outer-rim` | Compose services, `sites/training.xbonell.com/` (+ nginx.conf), data volume path, short ops note for Access |

## 9. Security notes

- Cloudflare Access is mandatory for a public hostname holding health data and a
  Zepp app token
- Same-origin `/api` avoids CORS and keeps one Access policy
- Token at rest only on the VPS data volume; masked in API responses
- Preserve `outer-rim` defaults: no-new-privileges, resource limits, least
  public surface (API not on `VIRTUAL_HOST`)

## 10. Open implementation details (non-blocking)

Resolved at plan/implementation time without changing this design:

- Exact static deploy mechanism (rsync/scp/action already used for other sites)
- API image registry/tagging convention
- Whether `ZEPP_HOST` is editable in Settings or fixed via env default
- Precise SPA `try_files` + cache headers mirroring other `outer-rim` sites
