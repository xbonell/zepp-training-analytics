# Deploy on outer-rim (training.xbonell.com)

Operator checklist for wiring this project into the [`xbonell/outer-rim`](https://github.com/xbonell/outer-rim) VPS stack. Copy the snippets below into that repo; do not commit outer-rim changes from this repository.

## Prerequisites

- [ ] DNS: `training` → VPS (Cloudflare proxy on)
- [ ] Cloudflare Access application for `training.xbonell.com` (create before exposing real tokens)
- [ ] SSL mode **Full (Strict)** once origin cert exists (nginx-proxy + Let's Encrypt)
- [ ] Data volume on VPS: `./data/zepp-training/` with DuckDB, profile, secrets, raw archives (see architecture doc)

## 1. Cloudflare

1. Add DNS record: `training` → VPS IP (proxied).
2. Create a Cloudflare Access application for `training.xbonell.com` (allow your identity only).
3. Set SSL/TLS mode to **Full (Strict)** after the origin certificate is issued.
4. **Do not** enable Access until HTTPS works end-to-end; enable Access **before** pasting a real Zepp token in Settings.

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
      test: ["CMD-SHELL", "wget -qO- http://127.0.0.1:8000/api/health >/dev/null 2>&1"]
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

- [ ] `https://training.xbonell.com` loads the SPA (Access gate active)
- [ ] `https://training.xbonell.com/api/health` returns OK
- [ ] Settings → connection test succeeds with masked token display
- [ ] Manual sync + normalize completes; dashboard shows data
