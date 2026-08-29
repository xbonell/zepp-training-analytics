# Deploy on outer-rim (training.xbonell.com)

Operator checklist for wiring this project into the [`xbonell/outer-rim`](https://github.com/xbonell/outer-rim) VPS stack. Copy the snippets below into that repo; do not commit outer-rim changes from this repository.

## Prerequisites

- [ ] DNS: `training` → VPS (Cloudflare proxy on)
- [ ] Cloudflare Access (OTP + owner email) for `training.xbonell.com` — enable after HTTPS, before real Zepp tokens
- [ ] SSL mode **Full (Strict)** once origin cert exists (nginx-proxy + Let's Encrypt)
- [ ] Data volume on VPS: `./data/zepp-training/` with DuckDB, profile, secrets, raw archives (see architecture doc)

## 1. Cloudflare

### 1.1 DNS and TLS (before Access)

1. Add DNS record: `training` → VPS IP (**proxied** / orange cloud).
2. Bring up the site containers so nginx-proxy can issue the certificate.
3. Set SSL/TLS mode to **Full (Strict)** after the origin certificate exists.
4. Confirm `https://training.xbonell.com` responds over HTTPS (Access still off is OK at this step).

### 1.2 Enable One-time PIN

In Cloudflare Zero Trust:

1. Open **Settings → Authentication** (login methods).
2. Add **One-time PIN** if it is not already enabled.
3. No other identity provider is required for this app.

If OTP emails are filtered, allowlist Cloudflare's notify sender using the
address listed in the current [One-time PIN docs](https://developers.cloudflare.com/cloudflare-one/identity/one-time-pin/).

### 1.3 Self-hosted Access application

1. Create an Access application:
   - **Type:** Self-hosted
   - **Application domain:** `training.xbonell.com` (whole hostname — covers `/` and `/api/*`)
   - **Session duration:** long enough for daily personal use (e.g. 1 month)
2. Attach an **Allow** policy:

| Rule type | Selector | Value |
|-----------|----------|-------|
| Include | Emails | Your personal email only (exact address) |
| Require | Login methods | One-time PIN |

3. Do **not**:
   - Use Include → **Everyone**
   - Use "emails ending in" a broad consumer domain (e.g. `@gmail.com`)
   - Use OTP as the only Include rule without an email restriction (anyone could request a PIN)

### 1.4 Order of operations (mandatory)

1. DNS proxied + HTTPS working end-to-end (§1.1).
2. Enable Access application + policy (§1.2–1.3).
3. Verify the gate (§7 Access checks).
4. Only then paste a real Zepp token in Settings.

**Origin reminder:** Keep `zepp-training-api` off the public internet (no
`VIRTUAL_HOST`, no published `:8000`). Access is edge-only; a publicly
reachable origin would bypass it.

## 2. Compose services

Paste into `outer-rim/docker-compose.yml` (alongside existing site services):

```yaml
  training.xbonell.com:
    image: nginx:alpine
    container_name: training.xbonell.com
    restart: unless-stopped
    environment:
      - VIRTUAL_HOST=training.xbonell.com
      - LETSENCRYPT_HOST=training.xbonell.com
      - LETSENCRYPT_EMAIL=${LETSENCRYPT_EMAIL:?LETSENCRYPT_EMAIL environment variable is required}
    volumes:
      - ./sites/training.xbonell.com:/usr/share/nginx/html:ro
      - ./sites/training.xbonell.com/nginx.conf:/etc/nginx/conf.d/default.conf:ro
    networks:
      - web
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
      - /var/cache/nginx
      - /var/run
    cpus: '0.2'
    mem_limit: 128M

  zepp-training-api:
    image: ghcr.io/xbonell/zepp-training-api:latest
    container_name: zepp-training-api
    restart: unless-stopped
    environment:
      - DUCKDB_PATH=/data/zepp.duckdb
      - PROFILE_PATH=/data/profile.json
      - ZEPP_ENV_PATH=/data/zepp.env
      - DATA_RAW_DIR=/data/raw
      - SYNC_JOB_PATH=/data/_meta/sync_job.json
      - API_CORS_ORIGIN=https://training.xbonell.com
    volumes:
      - ./data/zepp-training:/data
    networks:
      - web
    security_opt:
      - no-new-privileges:true
    cpus: '1.0'
    mem_limit: 1G
    healthcheck:
      test:
        [
          "CMD",
          "python3",
          "-c",
          "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=5).status == 200 else 1)",
        ]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 20s
```

## 3. Site nginx config

Create `outer-rim/sites/training.xbonell.com/nginx.conf`:

```nginx
server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    gzip on;
    gzip_types text/plain text/css application/javascript application/json image/svg+xml;

    location /api/ {
        proxy_pass http://zepp-training-api:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

## 4. Static site deploy

Build the web app from this repo and publish `dist/` into `outer-rim/sites/training.xbonell.com/`:

```bash
cd apps/web
npm install
npm run build
# rsync or copy dist/* to outer-rim/sites/training.xbonell.com/ on the VPS
```

Use the same GitHub Actions site-folder drop pattern as other outer-rim sites. Keep `nginx.conf` in outer-rim git (or on the VPS); the static deploy must **not** overwrite `nginx.conf`.

## 5. API image

Build and push from this repository:

```bash
docker build -t ghcr.io/xbonell/zepp-training-api:latest .
docker push ghcr.io/xbonell/zepp-training-api:latest
```

On the VPS (in `outer-rim`):

```bash
docker compose pull zepp-training-api
docker compose up -d
```

## 6. Data volume

Mount `./data/zepp-training:/data` in the API container. Populate with:

| Path | Purpose |
|------|---------|
| `zepp.duckdb` | Normalized analytics DB |
| `profile.json` | HRmax override, theme |
| `zepp.env` | `ZEPP_APP_TOKEN`, `ZEPP_USER_ID` (Settings writes here) |
| `raw/` | Immutable sync archives |
| `_meta/sync_job.json` | Sync job status |

Secrets never leave the VPS volume. Settings in the web UI manages connection and manual sync against this data.

## 7. Verification

### Access gate (do these first)

- [ ] Incognito → `https://training.xbonell.com` shows Access login / redirect, not the SPA
- [ ] Incognito → `https://training.xbonell.com/api/health` is gated the same way (not a public 200 without login)
- [ ] Owner email + OTP → SPA loads
- [ ] Owner session → `https://training.xbonell.com/api/health` returns OK
- [ ] Non-allowlisted email → no usable session

Revoke access later by removing the email from the Access policy or disabling the application.

### App smoke (after Access works)

- [ ] Settings → connection test succeeds with masked token display
- [ ] Manual sync + normalize completes; dashboard shows data
