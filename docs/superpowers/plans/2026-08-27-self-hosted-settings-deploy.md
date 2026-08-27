# Self-Hosted Settings + Deploy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Settings admin surface (Zepp connection, manual sync→normalize, training profile) and package the app for `training.xbonell.com` behind Cloudflare Access via `outer-rim`.

**Architecture:** Extend FastAPI with connection secrets + in-process sync jobs writing under `data/`. React Settings page consumes new endpoints; profile editing moves off Zones. Ship an API Docker image (importer as path dependency) and static Vite build; `outer-rim` adds an nginx site (SPA + `/api` proxy) and an internal API service with a writable data volume.

**Tech Stack:** Python 3.12+, `uv`, FastAPI, uvicorn, existing `fitness` importer, React 19 + TypeScript + Vite, Docker, nginx-proxy (`outer-rim`), Cloudflare Access

## Global Constraints

- Spec: `docs/superpowers/specs/2026-08-27-self-hosted-settings-deploy-design.md`
- Single user; no in-app auth (Cloudflare Access is the gate)
- Hostname: `training.xbonell.com` — one public host; `/api` same-origin
- Sync v1: manual only; always chain normalize after successful sync
- Never return full `ZEPP_APP_TOKEN` from GET; never log the token
- Secrets file: `data/zepp.env`; job status: `data/_meta/sync_job.json`
- `ZEPP_HOST` / region: env defaults only (not editable in Settings UI)
- Never commit `data/zepp.env`, DuckDB, raw archives, or `profile.json`
- TDD for connection mask, sync status machine, and Settings UI behavior
- Preserve `outer-rim` security defaults (no-new-privileges, resource limits, API not on `VIRTUAL_HOST`)

---

## File map

| Path | Responsibility |
|---|---|
| `services/api/src/fitness_api/connection.py` | Load/save/mask `zepp.env` |
| `services/api/src/fitness_api/sync_job.py` | Status file + run sync→normalize under lock |
| `services/api/src/fitness_api/config.py` | Paths for secrets, raw dir, sync job file |
| `services/api/src/fitness_api/schemas.py` | Connection + SyncJob response models |
| `services/api/src/fitness_api/main.py` | New `/api/settings/connection` and `/sync` routes |
| `services/api/pyproject.toml` | Path dependency on `fitness` (zepp-importer) |
| `services/api/tests/test_connection.py` | Mask + round-trip secrets |
| `services/api/tests/test_sync_job.py` | Status machine, 409 busy, auth error mapping |
| `apps/web/src/api/client.ts` | Connection + sync client helpers |
| `apps/web/src/pages/Settings.tsx` | Settings page (connection, sync, profile) |
| `apps/web/src/components/ProfileForm.tsx` | Shared profile form extracted from Zones |
| `apps/web/src/pages/Zones.tsx` | Analytics only (remove profile editor) |
| `apps/web/src/App.tsx` | `#settings` route + nav |
| `Dockerfile` | API image (repo root context) |
| `.dockerignore` | Exclude data, venvs, node_modules |
| `docs/deploy-outer-rim.md` | Exact compose/nginx/Access checklist for `outer-rim` |
| `.gitignore`, `.env.example`, `docs/architecture.md`, `README.md` | Ignore secrets; document Settings + deploy |

**Cross-repo:** Task 8 produces drop-in snippets applied in `xbonell/outer-rim` (not committed here).

---

### Task 1: Connection secrets module

**Files:**
- Create: `services/api/src/fitness_api/connection.py`
- Modify: `services/api/src/fitness_api/config.py`
- Modify: `.gitignore`
- Test: `services/api/tests/test_connection.py`

**Interfaces:**
- Consumes: `Path` for secrets file
- Produces:
  - `class ConnectionSecrets(BaseModel): user_id: str | None; app_token: str | None`
  - `def load_connection(path: Path) -> ConnectionSecrets`
  - `def save_connection(path: Path, *, user_id: str | None, app_token: str | None, replace_token: bool) -> ConnectionSecrets` — if `replace_token` is False, keep existing token when `app_token` is None/empty
  - `def connection_public_view(secrets: ConnectionSecrets) -> dict` → `{ "user_id", "token_set": bool, "token_hint": str | None }` where hint is last 4 chars of token or `None`
  - `Settings.zepp_env_path: Path` default `<repo>/data/zepp.env`
  - `Settings.data_raw_dir: Path` default `<repo>/data/raw`
  - `Settings.sync_job_path: Path` default `<repo>/data/_meta/sync_job.json`

- [ ] **Step 1: Write the failing tests**

```python
# services/api/tests/test_connection.py
from fitness_api.connection import (
    connection_public_view,
    load_connection,
    save_connection,
)


def test_load_missing_file_returns_empty(tmp_path):
    assert load_connection(tmp_path / "zepp.env").model_dump() == {
        "user_id": None,
        "app_token": None,
    }


def test_save_and_load_round_trip(tmp_path):
    path = tmp_path / "nested" / "zepp.env"
    save_connection(path, user_id="42", app_token="secret-token-9999", replace_token=True)
    loaded = load_connection(path)
    assert loaded.user_id == "42"
    assert loaded.app_token == "secret-token-9999"
    assert path.read_text(encoding="utf-8").startswith("ZEPP_")


def test_save_without_replace_keeps_existing_token(tmp_path):
    path = tmp_path / "zepp.env"
    save_connection(path, user_id="1", app_token="keep-me-1234", replace_token=True)
    save_connection(path, user_id="2", app_token=None, replace_token=False)
    loaded = load_connection(path)
    assert loaded.user_id == "2"
    assert loaded.app_token == "keep-me-1234"


def test_public_view_masks_token():
    from fitness_api.connection import ConnectionSecrets

    view = connection_public_view(
        ConnectionSecrets(user_id="9", app_token="abcdefghijklmnop")
    )
    assert view == {
        "user_id": "9",
        "token_set": True,
        "token_hint": "mnop",
    }
    assert "abcdef" not in str(view)


def test_public_view_when_token_missing():
    from fitness_api.connection import ConnectionSecrets

    assert connection_public_view(ConnectionSecrets()) == {
        "user_id": None,
        "token_set": False,
        "token_hint": None,
    }
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd services/api && uv run pytest tests/test_connection.py -v`

Expected: FAIL (module/import not found)

- [ ] **Step 3: Implement connection module + config paths**

```python
# services/api/src/fitness_api/connection.py
from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel


class ConnectionSecrets(BaseModel):
    user_id: str | None = None
    app_token: str | None = None


def load_connection(path: Path) -> ConnectionSecrets:
    if not path.exists():
        return ConnectionSecrets()
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return ConnectionSecrets(
        user_id=values.get("ZEPP_USER_ID") or None,
        app_token=values.get("ZEPP_APP_TOKEN") or None,
    )


def save_connection(
    path: Path,
    *,
    user_id: str | None,
    app_token: str | None,
    replace_token: bool,
) -> ConnectionSecrets:
    current = load_connection(path)
    token = app_token if replace_token and app_token else current.app_token
    if replace_token and app_token == "":
        token = None
    secrets = ConnectionSecrets(user_id=user_id or None, app_token=token)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = (
        f"ZEPP_USER_ID={secrets.user_id or ''}\n"
        f"ZEPP_APP_TOKEN={secrets.app_token or ''}\n"
    )
    path.write_text(body, encoding="utf-8")
    path.chmod(0o600)
    return secrets


def connection_public_view(secrets: ConnectionSecrets) -> dict:
    token = secrets.app_token
    token_set = bool(token)
    hint = token[-4:] if token and len(token) >= 4 else (token if token else None)
    return {
        "user_id": secrets.user_id,
        "token_set": token_set,
        "token_hint": hint if token_set else None,
    }
```

Add to `config.py` defaults:

```python
def _default_zepp_env_path() -> Path:
    return _repo_root() / "data" / "zepp.env"

def _default_data_raw_dir() -> Path:
    return _repo_root() / "data" / "raw"

def _default_sync_job_path() -> Path:
    return _repo_root() / "data" / "_meta" / "sync_job.json"
```

Fields on `Settings`: `zepp_env_path`, `data_raw_dir`, `sync_job_path` (env aliases `ZEPP_ENV_PATH`, `DATA_RAW_DIR`, `SYNC_JOB_PATH`).

Add to `.gitignore`:

```
data/zepp.env
data/_meta/sync_job.json
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd services/api && uv run pytest tests/test_connection.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add services/api/src/fitness_api/connection.py services/api/src/fitness_api/config.py services/api/tests/test_connection.py .gitignore
git commit -m "$(cat <<'EOF'
feat(api): add masked Zepp connection secrets helper

Persist credentials in data/zepp.env for Settings without exposing full tokens.
EOF
)"
```

---

### Task 2: Connection HTTP endpoints

**Files:**
- Modify: `services/api/src/fitness_api/schemas.py`
- Modify: `services/api/src/fitness_api/main.py`
- Test: `services/api/tests/test_connection_api.py`

**Interfaces:**
- Consumes: `load_connection`, `save_connection`, `connection_public_view`, `Settings.zepp_env_path`
- Produces:
  - `ConnectionView` — `user_id: str | None`, `token_set: bool`, `token_hint: str | None`
  - `ConnectionUpdate` — `user_id: str | None = None`, `app_token: str | None = None` (`app_token` omitted/null → keep existing)
  - `GET /api/settings/connection` → `ConnectionView`
  - `PUT /api/settings/connection` → `ConnectionView`

- [ ] **Step 1: Write the failing API tests**

```python
# services/api/tests/test_connection_api.py
from fastapi.testclient import TestClient

from fitness_api.config import Settings
from fitness_api.main import create_app


def _client(tmp_path):
    settings = Settings(
        duckdb_path=tmp_path / "zepp.duckdb",
        profile_path=tmp_path / "profile.json",
        zepp_env_path=tmp_path / "zepp.env",
        data_raw_dir=tmp_path / "raw",
        sync_job_path=tmp_path / "_meta" / "sync_job.json",
        cors_origin="http://localhost:5173",
    )
    return TestClient(create_app(settings))


def test_connection_put_get_masks_token(tmp_path):
    client = _client(tmp_path)
    put = client.put(
        "/api/settings/connection",
        json={"user_id": "99", "app_token": "super-secret-token"},
    )
    assert put.status_code == 200
    body = put.json()
    assert body["user_id"] == "99"
    assert body["token_set"] is True
    assert body["token_hint"] == "oken"
    assert "super-secret" not in put.text

    got = client.get("/api/settings/connection")
    assert got.json() == body


def test_connection_put_without_token_keeps_existing(tmp_path):
    client = _client(tmp_path)
    client.put(
        "/api/settings/connection",
        json={"user_id": "1", "app_token": "abcdefgh"},
    )
    response = client.put("/api/settings/connection", json={"user_id": "2"})
    assert response.json()["user_id"] == "2"
    assert response.json()["token_set"] is True
    assert response.json()["token_hint"] == "efgh"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd services/api && uv run pytest tests/test_connection_api.py -v`

Expected: FAIL (404 or missing routes)

- [ ] **Step 3: Add schemas + routes**

```python
# schemas.py additions
class ConnectionView(BaseModel):
    user_id: str | None = None
    token_set: bool = False
    token_hint: str | None = None


class ConnectionUpdate(BaseModel):
    user_id: str | None = None
    app_token: str | None = None
```

In `create_app`:

```python
@app.get("/api/settings/connection", response_model=ConnectionView)
def get_connection() -> ConnectionView:
    secrets = load_connection(app_settings.zepp_env_path)
    return ConnectionView.model_validate(connection_public_view(secrets))


@app.put("/api/settings/connection", response_model=ConnectionView)
def put_connection(body: ConnectionUpdate) -> ConnectionView:
    replace_token = body.app_token is not None
    secrets = save_connection(
        app_settings.zepp_env_path,
        user_id=body.user_id,
        app_token=body.app_token,
        replace_token=replace_token,
    )
    return ConnectionView.model_validate(connection_public_view(secrets))
```

Update existing test helpers that construct `Settings(...)` to pass the new path fields (or rely on defaults pointing at repo — prefer explicit `tmp_path` in new tests; fix any `Settings(...)` constructors that break if new fields are required — they should have defaults).

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd services/api && uv run pytest tests/test_connection_api.py tests/test_connection.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add services/api/src/fitness_api/schemas.py services/api/src/fitness_api/main.py services/api/tests/test_connection_api.py
git commit -m "$(cat <<'EOF'
feat(api): expose connection settings endpoints

Allow Settings UI to store Zepp user id and token with masked reads.
EOF
)"
```

---

### Task 3: Sync job runner (status + orchestration)

**Files:**
- Create: `services/api/src/fitness_api/sync_job.py`
- Modify: `services/api/pyproject.toml` (path dep on `fitness`)
- Test: `services/api/tests/test_sync_job.py`

**Interfaces:**
- Consumes: `fitness.sync.run_sync`, `fitness.normalize.load.run_normalize`, `fitness.client.ZeppAuthError`, `fitness.config.Settings` as `ImporterSettings`, `load_connection`
- Produces:
  - `class SyncJobBusy(Exception)`
  - `class SyncJobState(BaseModel): status: Literal["idle","running","ok","error"]; started_at: datetime | None; finished_at: datetime | None; error: str | None; message: str | None = None`
  - `def read_sync_job(path: Path) -> SyncJobState` — missing file → `idle`
  - `def write_sync_job(path: Path, state: SyncJobState) -> None`
  - `def start_sync_job(*, sync_job_path, zepp_env_path, data_raw_dir, duckdb_path, zepp_host: str = "api-mifit-us3.zepp.com", run_sync_fn=..., run_normalize_fn=...) -> SyncJobState` — raises `SyncJobBusy` if status is `running`; sets `running` then executes in a daemon thread; maps `ZeppAuthError` to error message `"Zepp token expired or rejected; update Connection settings"`

- [ ] **Step 1: Add path dependency and failing tests**

In `services/api/pyproject.toml` add dependency `"fitness"` and:

```toml
[tool.uv.sources]
fitness = { path = "../zepp-importer", editable = true }
```

Then `cd services/api && uv sync --extra dev`

```python
# services/api/tests/test_sync_job.py
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from fitness_api.connection import save_connection
from fitness_api.sync_job import (
    SyncJobBusy,
    SyncJobState,
    read_sync_job,
    start_sync_job,
    write_sync_job,
)


def test_read_missing_job_is_idle(tmp_path):
    assert read_sync_job(tmp_path / "sync_job.json").status == "idle"


def test_start_rejects_when_running(tmp_path):
    path = tmp_path / "sync_job.json"
    write_sync_job(
        path,
        SyncJobState(
            status="running",
            started_at=datetime.now(timezone.utc),
            finished_at=None,
            error=None,
        ),
    )
    with pytest.raises(SyncJobBusy):
        start_sync_job(
            sync_job_path=path,
            zepp_env_path=tmp_path / "zepp.env",
            data_raw_dir=tmp_path / "raw",
            duckdb_path=tmp_path / "zepp.duckdb",
        )


def test_successful_sync_runs_normalize(tmp_path):
    env = tmp_path / "zepp.env"
    save_connection(env, user_id="1", app_token="tok", replace_token=True)
    calls: list[str] = []

    def fake_sync(**kwargs):
        calls.append("sync")
        return type("R", (), {"errors": []})()

    def fake_normalize(**kwargs):
        calls.append("normalize")
        return type("R", (), {"errors": []})()

    state = start_sync_job(
        sync_job_path=tmp_path / "job.json",
        zepp_env_path=env,
        data_raw_dir=tmp_path / "raw",
        duckdb_path=tmp_path / "db.duckdb",
        run_sync_fn=fake_sync,
        run_normalize_fn=fake_normalize,
        wait=True,
    )
    assert calls == ["sync", "normalize"]
    assert state.status == "ok"
    assert read_sync_job(tmp_path / "job.json").status == "ok"


def test_auth_error_message(tmp_path):
    from fitness.client import ZeppAuthError

    env = tmp_path / "zepp.env"
    save_connection(env, user_id="1", app_token="tok", replace_token=True)

    def boom(**kwargs):
        raise ZeppAuthError("nope")

    state = start_sync_job(
        sync_job_path=tmp_path / "job.json",
        zepp_env_path=env,
        data_raw_dir=tmp_path / "raw",
        duckdb_path=tmp_path / "db.duckdb",
        run_sync_fn=boom,
        run_normalize_fn=lambda **k: None,
        wait=True,
    )
    assert state.status == "error"
    assert "token expired" in (state.error or "").lower()
```

Implement `wait: bool = False` on `start_sync_job` for tests only (when True, run inline instead of thread).

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd services/api && uv run pytest tests/test_sync_job.py -v`

Expected: FAIL (import error)

- [ ] **Step 3: Implement `sync_job.py`**

Core behavior:

1. If `read_sync_job(...).status == "running"` → raise `SyncJobBusy`
2. If connection missing user_id or token → write `error` `"Missing Zepp credentials; update Connection settings"` and return (or raise before start — prefer immediate `error` state return without thread)
3. Write `running` with `started_at=now`
4. Build importer `Settings` with token/user/host/`data_raw_dir`/`duckdb_path`
5. Call `run_sync_fn` (default wraps real `run_sync` with `ZeppClient` + `RawArchive`); on auth error set message above; on other errors store short message
6. If sync ok (no exception; treat report.errors as failure if non-empty), call `run_normalize_fn(raw_dir, duckdb_path)`
7. Write final `ok` or `error` with `finished_at`

Use `threading.Lock` around the running check + status write. Default `run_sync_fn`/`run_normalize_fn` call real importer functions.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd services/api && uv run pytest tests/test_sync_job.py tests/test_connection.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add services/api/pyproject.toml services/api/uv.lock services/api/src/fitness_api/sync_job.py services/api/tests/test_sync_job.py
git commit -m "$(cat <<'EOF'
feat(api): add sync-to-normalize job runner

Persist job status and chain importer sync with DuckDB normalize under a lock.
EOF
)"
```

---

### Task 4: Sync HTTP endpoints

**Files:**
- Modify: `services/api/src/fitness_api/schemas.py`
- Modify: `services/api/src/fitness_api/main.py`
- Test: `services/api/tests/test_sync_api.py`

**Interfaces:**
- Consumes: `start_sync_job`, `read_sync_job`, `SyncJobBusy`
- Produces:
  - `SyncJobView` matching `SyncJobState` fields
  - `GET /api/settings/sync` → current status
  - `POST /api/settings/sync` → starts job; `409` with detail `"Sync already running"` on busy

- [ ] **Step 1: Write failing API tests**

```python
# services/api/tests/test_sync_api.py
from unittest.mock import patch

from fastapi.testclient import TestClient

from fitness_api.config import Settings
from fitness_api.connection import save_connection
from fitness_api.main import create_app
from fitness_api.sync_job import SyncJobState, write_sync_job


def _client(tmp_path):
    settings = Settings(
        duckdb_path=tmp_path / "zepp.duckdb",
        profile_path=tmp_path / "profile.json",
        zepp_env_path=tmp_path / "zepp.env",
        data_raw_dir=tmp_path / "raw",
        sync_job_path=tmp_path / "sync_job.json",
        cors_origin="http://localhost:5173",
    )
    save_connection(
        settings.zepp_env_path,
        user_id="1",
        app_token="tok",
        replace_token=True,
    )
    return TestClient(create_app(settings)), settings


def test_get_sync_idle(tmp_path):
    client, _ = _client(tmp_path)
    assert client.get("/api/settings/sync").json()["status"] == "idle"


def test_post_sync_conflict_when_running(tmp_path):
    client, settings = _client(tmp_path)
    write_sync_job(
        settings.sync_job_path,
        SyncJobState(
            status="running",
            started_at=None,
            finished_at=None,
            error=None,
        ),
    )
    assert client.post("/api/settings/sync").status_code == 409


def test_post_sync_starts_job(tmp_path):
    client, settings = _client(tmp_path)

    def fake_start(**kwargs):
        state = SyncJobState(
            status="running",
            started_at=None,
            finished_at=None,
            error=None,
        )
        write_sync_job(settings.sync_job_path, state)
        return state

    with patch("fitness_api.main.start_sync_job", side_effect=fake_start):
        response = client.post("/api/settings/sync")
    assert response.status_code == 200
    assert response.json()["status"] == "running"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd services/api && uv run pytest tests/test_sync_api.py -v`

Expected: FAIL (404)

- [ ] **Step 3: Wire routes in `main.py`**

```python
@app.get("/api/settings/sync", response_model=SyncJobView)
def get_sync() -> SyncJobView:
    return SyncJobView.model_validate(
        read_sync_job(app_settings.sync_job_path).model_dump()
    )


@app.post("/api/settings/sync", response_model=SyncJobView)
def post_sync() -> SyncJobView:
    try:
        state = start_sync_job(
            sync_job_path=app_settings.sync_job_path,
            zepp_env_path=app_settings.zepp_env_path,
            data_raw_dir=app_settings.data_raw_dir,
            duckdb_path=app_settings.duckdb_path,
        )
    except SyncJobBusy as exc:
        raise HTTPException(status_code=409, detail="Sync already running") from exc
    return SyncJobView.model_validate(state.model_dump())
```

- [ ] **Step 4: Run API test suite subset**

Run: `cd services/api && uv run pytest tests/test_sync_api.py tests/test_sync_job.py tests/test_connection_api.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add services/api/src/fitness_api/main.py services/api/src/fitness_api/schemas.py services/api/tests/test_sync_api.py
git commit -m "$(cat <<'EOF'
feat(api): add sync job HTTP endpoints

Expose manual Sync now with 409 when a job is already running.
EOF
)"
```

---

### Task 5: Web client + Settings page (connection & sync)

**Files:**
- Modify: `apps/web/src/api/client.ts`
- Create: `apps/web/src/pages/Settings.tsx`
- Create: `apps/web/src/pages/Settings.test.tsx`
- Modify: `apps/web/src/App.tsx`
- Modify: `apps/web/src/App.test.tsx` (nav assertion if present)

**Interfaces:**
- Consumes: `/api/settings/connection`, `/api/settings/sync`
- Produces:
  - `ConnectionView`, `fetchConnection`, `updateConnection({ user_id, app_token? })`
  - `SyncJobView`, `fetchSyncJob`, `startSyncJob`
  - Route `#settings` → `<Settings />`

- [ ] **Step 1: Write failing Settings tests**

```tsx
// apps/web/src/pages/Settings.test.tsx
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as api from '../api/client'
import { Settings } from './Settings'

vi.mock('../api/client')

describe('Settings', () => {
  beforeEach(() => {
    vi.mocked(api.fetchConnection).mockResolvedValue({
      user_id: '1',
      token_set: true,
      token_hint: 'oken',
    })
    vi.mocked(api.fetchSyncJob).mockResolvedValue({
      status: 'ok',
      started_at: null,
      finished_at: null,
      error: null,
      message: null,
    })
    vi.mocked(api.fetchProfile).mockResolvedValue({
      sex: null,
      birth_date: null,
      resting_hr: null,
      hrmax_override: null,
      theme_preference: 'system',
      display_timezone: 'Europe/Madrid',
    })
  })

  it('shows masked token and disables sync while running', async () => {
    vi.mocked(api.fetchSyncJob).mockResolvedValue({
      status: 'running',
      started_at: null,
      finished_at: null,
      error: null,
      message: null,
    })
    render(<Settings />)
    expect(await screen.findByText(/oken/i)).toBeVisible()
    expect(
      await screen.findByRole('button', { name: /sync now/i }),
    ).toBeDisabled()
  })

  it('saves connection with pasted token', async () => {
    vi.mocked(api.updateConnection).mockResolvedValue({
      user_id: '2',
      token_set: true,
      token_hint: 'zzzz',
    })
    const user = userEvent.setup()
    render(<Settings />)
    await screen.findByLabelText(/user id/i)
    await user.clear(screen.getByLabelText(/user id/i))
    await user.type(screen.getByLabelText(/user id/i), '2')
    await user.type(screen.getByLabelText(/app token/i), 'new-token-zzzz')
    await user.click(screen.getByRole('button', { name: /save connection/i }))
    await waitFor(() =>
      expect(api.updateConnection).toHaveBeenCalledWith({
        user_id: '2',
        app_token: 'new-token-zzzz',
      }),
    )
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/web && npm test -- --run src/pages/Settings.test.tsx`

Expected: FAIL (module not found)

- [ ] **Step 3: Implement client helpers + Settings page + nav**

Add to `client.ts`:

```typescript
export interface ConnectionView {
  user_id: string | null
  token_set: boolean
  token_hint: string | null
}

export interface SyncJobView {
  status: 'idle' | 'running' | 'ok' | 'error'
  started_at: string | null
  finished_at: string | null
  error: string | null
  message: string | null
}

export function fetchConnection(signal?: AbortSignal) {
  return getJson<ConnectionView>('/api/settings/connection', signal)
}

export async function updateConnection(body: {
  user_id: string | null
  app_token?: string | null
}): Promise<ConnectionView> {
  const response = await fetch('/api/settings/connection', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!response.ok) throw new Error(`API request failed (${response.status})`)
  return response.json()
}

export function fetchSyncJob(signal?: AbortSignal) {
  return getJson<SyncJobView>('/api/settings/sync', signal)
}

export async function startSyncJob(): Promise<SyncJobView> {
  const response = await fetch('/api/settings/sync', { method: 'POST' })
  if (response.status === 409) throw new Error('Sync already running')
  if (!response.ok) throw new Error(`API request failed (${response.status})`)
  return response.json()
}
```

`Settings.tsx` sections: Connection form (user id, token password input placeholder “leave blank to keep”), Sync card (status + Sync now), stub empty profile section for Task 6. Poll `fetchSyncJob` every 2s while `status === 'running'`.

Update `App.tsx` route union + nav link **Settings**.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd apps/web && npm test -- --run src/pages/Settings.test.tsx src/App.test.tsx`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/api/client.ts apps/web/src/pages/Settings.tsx apps/web/src/pages/Settings.test.tsx apps/web/src/App.tsx apps/web/src/App.test.tsx
git commit -m "$(cat <<'EOF'
feat(web): add Settings page for connection and sync

Wire masked credential editing and Sync now against the new API.
EOF
)"
```

---

### Task 6: Move training profile editor to Settings

**Files:**
- Create: `apps/web/src/components/ProfileForm.tsx`
- Create: `apps/web/src/components/ProfileForm.test.tsx` (optional if Settings test covers save)
- Modify: `apps/web/src/pages/Settings.tsx`
- Modify: `apps/web/src/pages/Zones.tsx`
- Modify: `apps/web/src/pages/Zones.test.tsx` (remove save-profile expectations; keep analytics assertions)

**Interfaces:**
- Consumes: `fetchProfile`, `updateProfile`, existing `Profile` type
- Produces: `<ProfileForm profile={Profile} onSaved={(p) => void} />` reusable form UI

- [ ] **Step 1: Update Zones tests to expect no profile save controls; extend Settings test for profile save**

In `Zones.test.tsx`, remove the test that clicks **Save profile**. Assert zone table / HRmax copy still renders.

In `Settings.test.tsx`, add:

```tsx
it('saves training profile fields', async () => {
  vi.mocked(api.updateProfile).mockResolvedValue({
    sex: 'male',
    birth_date: '1971-11-03',
    resting_hr: 48,
    hrmax_override: 188,
    theme_preference: 'system',
    display_timezone: 'Europe/Madrid',
  })
  const user = userEvent.setup()
  render(<Settings />)
  await screen.findByLabelText(/hrmax override/i)
  await user.clear(screen.getByLabelText(/hrmax override/i))
  await user.type(screen.getByLabelText(/hrmax override/i), '188')
  await user.click(screen.getByRole('button', { name: /save profile/i }))
  await waitFor(() => expect(api.updateProfile).toHaveBeenCalled())
})
```

- [ ] **Step 2: Run tests to verify new expectations fail**

Run: `cd apps/web && npm test -- --run src/pages/Zones.test.tsx src/pages/Settings.test.tsx`

Expected: Settings profile test FAIL; Zones may FAIL if it still requires save button

- [ ] **Step 3: Extract `ProfileForm` from Zones markup; use it on Settings; strip form from Zones**

Keep Zones loading `fetchZones` (+ profile only if needed for display — currently profile drives form only; zones endpoint already returns HRmax source). Remove profile form section from Zones entirely.

- [ ] **Step 4: Run web tests**

Run: `cd apps/web && npm test -- --run`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/components/ProfileForm.tsx apps/web/src/pages/Settings.tsx apps/web/src/pages/Zones.tsx apps/web/src/pages/Settings.test.tsx apps/web/src/pages/Zones.test.tsx
git commit -m "$(cat <<'EOF'
feat(web): move training profile editor to Settings

Keep Zones focused on analytics; centralize admin fields on Settings.
EOF
)"
```

---

### Task 7: API Dockerfile

**Files:**
- Create: `Dockerfile`
- Create: `.dockerignore`
- Modify: `.env.example` (document `ZEPP_ENV_PATH`, `DATA_RAW_DIR`, `SYNC_JOB_PATH`, `API_CORS_ORIGIN` for prod)

**Interfaces:**
- Image runs `uvicorn fitness_api.main:app --host 0.0.0.0 --port 8000`
- Env: `DUCKDB_PATH=/data/zepp.duckdb`, `PROFILE_PATH=/data/profile.json`, `ZEPP_ENV_PATH=/data/zepp.env`, `DATA_RAW_DIR=/data/raw`, `SYNC_JOB_PATH=/data/_meta/sync_job.json`, `API_CORS_ORIGIN=https://training.xbonell.com`

- [ ] **Step 1: Add Dockerfile + dockerignore**

```dockerfile
# Dockerfile (repo root)
FROM python:3.12-slim

WORKDIR /app
RUN pip install --no-cache-dir uv

COPY services/zepp-importer /app/services/zepp-importer
COPY services/api /app/services/api

WORKDIR /app/services/api
RUN uv sync --no-dev

ENV DUCKDB_PATH=/data/zepp.duckdb \
    PROFILE_PATH=/data/profile.json \
    ZEPP_ENV_PATH=/data/zepp.env \
    DATA_RAW_DIR=/data/raw \
    SYNC_JOB_PATH=/data/_meta/sync_job.json \
    API_CORS_ORIGIN=https://training.xbonell.com

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "fitness_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```dockerignore
data/
**/.venv/
**/node_modules/
**/__pycache__/
**/.pytest_cache/
apps/web/
docs/
.worktrees/
.git/
```

Update `.env.example` with the new optional paths and a comment that production CORS should be `https://training.xbonell.com`.

- [ ] **Step 2: Build image locally**

Run: `docker build -t zepp-training-api:local .`

Expected: image builds successfully

- [ ] **Step 3: Smoke-run container with tmp data dir**

```bash
mkdir -p /tmp/zepp-data
docker run --rm -p 8000:8000 -v /tmp/zepp-data:/data zepp-training-api:local
```

In another shell: `curl -s http://127.0.0.1:8000/api/health`

Expected: JSON including `"duckdb": false` (empty volume) without crash

- [ ] **Step 4: Commit**

```bash
git add Dockerfile .dockerignore .env.example
git commit -m "$(cat <<'EOF'
build: add API Docker image for VPS deploy

Package FastAPI with the importer dependency and /data volume paths.
EOF
)"
```

---

### Task 8: `outer-rim` drop-in + project docs

**Files:**
- Create: `docs/deploy-outer-rim.md` (snippets to copy into `xbonell/outer-rim`)
- Modify: `docs/architecture.md` (M3+ Settings/deploy note; keep local-first principle with self-hosted exception)
- Modify: `README.md` (Settings + pointer to deploy doc)

**Interfaces:**
- Produces operator checklist: DNS, Cloudflare Access, compose services, site nginx, data volume, image pull/tag, static site drop path

- [ ] **Step 1: Write `docs/deploy-outer-rim.md` with exact snippets**

Include:

1. Cloudflare: DNS `training` → VPS; Access application for `training.xbonell.com`; SSL mode Full (Strict) once origin cert exists
2. Compose services (paste into `outer-rim/docker-compose.yml`):

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

3. `sites/training.xbonell.com/nginx.conf`:

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

4. Static deploy: build `apps/web` (`npm run build`) and publish `dist/` into `outer-rim/sites/training.xbonell.com/` (same GH Action mount pattern as other sites; keep `nginx.conf` on the VPS / in `outer-rim` git, not overwritten by the static drop)
5. API image: build/push `ghcr.io/xbonell/zepp-training-api` from this repo’s `Dockerfile`, then `docker-compose pull zepp-training-api && docker-compose up -d`
6. **Do not** expose Access until HTTPS works; enable Access before pasting a real Zepp token in Settings

- [ ] **Step 2: Update `docs/architecture.md` + `README.md`**

Architecture: add a short “Self-hosted deploy” subsection pointing at Settings + `docs/deploy-outer-rim.md`, clarifying data still lives on the operator’s VPS volume (not multi-tenant cloud).

README: link Settings (local) and deploy doc.

- [ ] **Step 3: Commit**

```bash
git add docs/deploy-outer-rim.md docs/architecture.md README.md
git commit -m "$(cat <<'EOF'
docs: add outer-rim deploy guide for training subdomain

Document Access-gated nginx+API wiring and Settings admin scope.
EOF
)"
```

---

## Plan self-review

| Spec requirement | Task |
|---|---|
| Settings: connection + sync + profile | 2, 4, 5, 6 |
| Masked token / no full GET | 1, 2 |
| Manual sync→normalize + status + 409 | 3, 4 |
| Secrets on data volume | 1, 7 |
| One subdomain `/api` proxy | 8 |
| Cloudflare Access gate | 8 (ops checklist) |
| API Docker image | 7 |
| Static site drop via outer-rim | 8 |
| Local-first paths still work | 1 config defaults + unchanged dev runbook |
| Tests for connection/sync/Settings | 1–6 |

**Deferred by spec (intentionally no task):** cron sync, multi-user auth, raw archive UI, public `api.` host.

**Open details resolved in plan:** `ZEPP_HOST` env-only; registry `ghcr.io/xbonell/zepp-training-api`; static deploy = existing site-folder drop; SPA `try_files` + `/api/` proxy as above.

---

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-08-27-self-hosted-settings-deploy.md`. Two execution options:

**1. Subagent-Driven (recommended)** — fresh subagent per task, review between tasks  
**2. Inline Execution** — execute tasks in this session with executing-plans checkpoints  

Which approach?
