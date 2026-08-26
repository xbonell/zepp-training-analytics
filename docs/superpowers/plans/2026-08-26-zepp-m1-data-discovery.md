# Milestone 1 — Zepp Data Discovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scaffold a Python `fitness` CLI that investigates/documents Global-EU Zepp Cloud access and archives immutable raw API responses under `data/raw/`, failing clearly until credentials exist.

**Architecture:** Independent thin HTTP client (learn from OSS, do not vendor). Config from env → client GETs with `apptoken` → every response body written via immutable archive → sync orchestrates list/detail/HR. Docs capture provisional endpoints and schema; no DuckDB/web in M1.

**Tech Stack:** Python 3.12+, `uv`, `httpx`, `pydantic`, `typer`, `python-dotenv`, `pytest`

## Global Constraints

- Python 3.12+; package managed with `uv` under `services/zepp-importer/`
- CLI entry point name: `fitness`
- Auth: `ZEPP_APP_TOKEN` + `ZEPP_USER_ID` only — no password login
- Default host: `api-mifit-us3.zepp.com` (overridable via `ZEPP_HOST`)
- Region context: Global / EU (`ZEPP_REGION=eu` informational)
- Raw archive: one file per HTTP response body; never overwrite differing content
- No DuckDB, FastAPI, React, Docker, or analytics engines in M1
- No live Zepp calls in tests — mocks/fixtures only
- Never commit `.env`, tokens, user IDs, or `data/raw/**` payloads
- Display timezone later is Europe/Madrid; do not reinterpret Zepp timestamps in M1 beyond archival
- Spec: `docs/superpowers/specs/2026-08-26-zepp-m1-data-discovery-design.md`

---

## File map

| Path | Responsibility |
|---|---|
| `.gitignore` | Secrets, raw data, captures, venv, DuckDB placeholders |
| `.env.example` | Documented env vars |
| `data/raw/.gitkeep` | Preserve empty archive tree |
| `README.md` | Setup + commands |
| `docs/architecture.md` | Full target + M1 slice |
| `docs/zepp-auth.md` | Cookie + MITM auth |
| `docs/zepp-data-model.md` | Provisional endpoints/fields |
| `docs/hr-zone-models.md` | Stub for later |
| `docs/examples/README.md` | How sanitized examples will be added |
| `services/zepp-importer/pyproject.toml` | Package + scripts + deps |
| `services/zepp-importer/src/fitness/__init__.py` | Package version |
| `services/zepp-importer/src/fitness/config.py` | Load/validate settings |
| `services/zepp-importer/src/fitness/archive.py` | Immutable raw writer |
| `services/zepp-importer/src/fitness/endpoints.py` | Path/query builders |
| `services/zepp-importer/src/fitness/client.py` | HTTP client |
| `services/zepp-importer/src/fitness/sync.py` | Sync orchestration |
| `services/zepp-importer/src/fitness/cli.py` | Typer CLI |
| `services/zepp-importer/tests/...` | Unit tests |

---

### Task 1: Repository bootstrap

**Files:**
- Create: `.gitignore`
- Create: `.env.example`
- Create: `data/raw/.gitkeep`
- Create: `README.md` (minimal stub; expanded in Task 8)
- Modify: (none — init git)

**Interfaces:**
- Consumes: none
- Produces: git repo root; ignored paths for secrets/raw data

- [ ] **Step 1: Create `.gitignore`**

```gitignore
.env
.env.*
!.env.example

data/raw/**
!data/raw/.gitkeep
data/parquet/
data/*.duckdb
data/**/*.duckdb

*.har
*.chlsj
*.saz
capture*.json

__pycache__/
*.py[cod]
.pytest_cache/
.mypy_cache/
.ruff_cache/
.venv/
venv/
dist/
*.egg-info/
uv.lock

.DS_Store
```

- [ ] **Step 2: Create `.env.example`**

```env
ZEPP_APP_TOKEN=
ZEPP_USER_ID=
ZEPP_HOST=api-mifit-us3.zepp.com
ZEPP_REGION=eu
# Optional. Defaults to <repo-root>/data/raw
# DATA_RAW_DIR=
```

- [ ] **Step 3: Create `data/raw/.gitkeep` and stub root `README.md`**

```markdown
# Zepp Training Analytics

Local-first fitness analytics for Amazfit T-Rex Pro / Zepp (Global/EU).

Milestone 1: data discovery importer. See `docs/` after Task 8 completes setup docs.

```bash
cd services/zepp-importer
uv sync
cp ../../.env.example ../../.env
# fill ZEPP_APP_TOKEN and ZEPP_USER_ID — see docs/zepp-auth.md
uv run fitness status
```
```

- [ ] **Step 4: Initialize git and commit bootstrap + existing design/plan docs**

```bash
cd /home/xbonell/Developer/00.personal/zepp-training-analytics
git init
git add .gitignore .env.example data/raw/.gitkeep README.md docs/
git status
git commit -m "$(cat <<'EOF'
chore: bootstrap M1 repo layout and design docs

EOF
)"
```

Expected: commit succeeds; `git status` clean for tracked files.

---

### Task 2: Python package scaffold

**Files:**
- Create: `services/zepp-importer/pyproject.toml`
- Create: `services/zepp-importer/src/fitness/__init__.py`
- Create: `services/zepp-importer/tests/test_smoke.py`

**Interfaces:**
- Consumes: none
- Produces: installable package `fitness` with console script `fitness` (CLI wired in Task 7; placeholder module OK)

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[project]
name = "fitness"
version = "0.1.0"
description = "Zepp raw-data importer for local fitness analytics"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
  "httpx>=0.27",
  "pydantic>=2.7",
  "pydantic-settings>=2.3",
  "python-dotenv>=1.0",
  "typer>=0.12",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.2",
  "pytest-httpx>=0.30",
]

[project.scripts]
fitness = "fitness.cli:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/fitness"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

Also create a short `services/zepp-importer/README.md` pointing to repo root docs.

- [ ] **Step 2: Create package init and temporary CLI stub**

`src/fitness/__init__.py`:

```python
__version__ = "0.1.0"
```

`src/fitness/cli.py` (temporary until Task 7):

```python
import typer

app = typer.Typer(add_completion=False, no_args_is_help=True)

@app.callback()
def main() -> None:
    """Zepp training analytics CLI."""


@app.command("status")
def status_cmd() -> None:
    typer.echo("fitness status: package OK (CLI incomplete)")
```

- [ ] **Step 3: Write smoke test**

`tests/test_smoke.py`:

```python
from fitness import __version__


def test_version():
    assert __version__ == "0.1.0"
```

- [ ] **Step 4: Install and run tests**

```bash
cd services/zepp-importer
uv sync --extra dev
uv run pytest -v
uv run fitness status
```

Expected: tests pass; CLI prints package OK message.

- [ ] **Step 5: Commit**

```bash
git add services/zepp-importer
git commit -m "$(cat <<'EOF'
chore: scaffold fitness Python package with uv

EOF
)"
```

---

### Task 3: Config loading

**Files:**
- Create: `services/zepp-importer/src/fitness/config.py`
- Create: `services/zepp-importer/tests/test_config.py`

**Interfaces:**
- Consumes: env vars / optional `.env` at repo root
- Produces:
  - `class Settings(BaseSettings)` with fields: `zepp_app_token: str | None`, `zepp_user_id: str | None`, `zepp_host: str`, `zepp_region: str`, `data_raw_dir: Path`
  - `def load_settings() -> Settings`
  - `def credentials_ready(settings: Settings) -> bool` → True iff token and user_id both non-empty
  - `def require_credentials(settings: Settings) -> None` → raises `ConfigError` if not ready
  - `class ConfigError(Exception)`

- [ ] **Step 1: Write failing tests**

```python
import os
from pathlib import Path

import pytest

from fitness.config import ConfigError, credentials_ready, load_settings, require_credentials


def test_defaults_without_credentials(monkeypatch, tmp_path):
    monkeypatch.delenv("ZEPP_APP_TOKEN", raising=False)
    monkeypatch.delenv("ZEPP_USER_ID", raising=False)
    monkeypatch.setenv("DATA_RAW_DIR", str(tmp_path / "raw"))
    s = load_settings()
    assert s.zepp_host == "api-mifit-us3.zepp.com"
    assert s.zepp_region == "eu"
    assert credentials_ready(s) is False


def test_credentials_ready_when_both_set(monkeypatch, tmp_path):
    monkeypatch.setenv("ZEPP_APP_TOKEN", "tok")
    monkeypatch.setenv("ZEPP_USER_ID", "uid")
    monkeypatch.setenv("DATA_RAW_DIR", str(tmp_path / "raw"))
    s = load_settings()
    assert credentials_ready(s) is True
    require_credentials(s)  # does not raise


def test_require_credentials_raises(monkeypatch, tmp_path):
    monkeypatch.delenv("ZEPP_APP_TOKEN", raising=False)
    monkeypatch.setenv("ZEPP_USER_ID", "uid")
    monkeypatch.setenv("DATA_RAW_DIR", str(tmp_path / "raw"))
    s = load_settings()
    with pytest.raises(ConfigError):
        require_credentials(s)
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
cd services/zepp-importer && uv run pytest tests/test_config.py -v
```

Expected: import/collection failure for `fitness.config`.

- [ ] **Step 3: Implement `config.py`**

```python
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigError(Exception):
    pass


def _default_raw_dir() -> Path:
    # services/zepp-importer/src/fitness/config.py → repo root is parents[4]
    return Path(__file__).resolve().parents[4] / "data" / "raw"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    zepp_app_token: str | None = None
    zepp_user_id: str | None = None
    zepp_host: str = "api-mifit-us3.zepp.com"
    zepp_region: str = "eu"
    data_raw_dir: Path = Field(default_factory=_default_raw_dir)


def load_settings() -> Settings:
    return Settings()


def credentials_ready(settings: Settings) -> bool:
    return bool(settings.zepp_app_token) and bool(settings.zepp_user_id)


def require_credentials(settings: Settings) -> None:
    if not credentials_ready(settings):
        raise ConfigError(
            "Missing ZEPP_APP_TOKEN and/or ZEPP_USER_ID. "
            "See docs/zepp-auth.md"
        )
```

Resolve `env_file` path carefully: prefer loading dotenv from repo-root `.env` explicitly in `load_settings` if pydantic relative paths are awkward — implementer may use:

```python
from dotenv import load_dotenv

def load_settings() -> Settings:
    repo_env = Path(__file__).resolve().parents[4] / ".env"
    if repo_env.exists():
        load_dotenv(repo_env)
    return Settings()
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
uv run pytest tests/test_config.py -v
```

- [ ] **Step 5: Commit**

```bash
git add services/zepp-importer/src/fitness/config.py services/zepp-importer/tests/test_config.py
git commit -m "$(cat <<'EOF'
feat: add Zepp settings and credential checks

EOF
)"
```

---

### Task 4: Immutable raw archive

**Files:**
- Create: `services/zepp-importer/src/fitness/archive.py`
- Create: `services/zepp-importer/tests/test_archive.py`

**Interfaces:**
- Consumes: `Path` root directory
- Produces:
  - `class ArchiveResult` with `path: Path`, `status: Literal["written","skipped","conflict"]`
  - `class RawArchive` with:
    - `__init__(self, root: Path)`
    - `write_bytes(self, relative: str, data: bytes) -> ArchiveResult`
    - `write_json_bytes(self, relative: str, data: bytes) -> ArchiveResult` (alias of write_bytes)
    - `count_files(self, subdir: str | None = None) -> int`
    - `read_meta(self) -> dict | None` / `write_meta(self, payload: dict) -> Path` for `_meta/last_sync.json` (overwrite allowed **only** for `_meta/`; document this exception)

- [ ] **Step 1: Write failing tests**

```python
from pathlib import Path

from fitness.archive import RawArchive


def test_write_new_file(tmp_path: Path):
    arc = RawArchive(tmp_path)
    r = arc.write_bytes("heart-rate/2026-01-01.json", b'{"ok":true}')
    assert r.status == "written"
    assert r.path.read_bytes() == b'{"ok":true}'


def test_skip_identical(tmp_path: Path):
    arc = RawArchive(tmp_path)
    payload = b'{"a":1}'
    arc.write_bytes("activity-details/1.json", payload)
    r = arc.write_bytes("activity-details/1.json", payload)
    assert r.status == "skipped"


def test_conflict_sibling(tmp_path: Path):
    arc = RawArchive(tmp_path)
    arc.write_bytes("activity-details/1.json", b'{"a":1}')
    r = arc.write_bytes("activity-details/1.json", b'{"a":2}')
    assert r.status == "conflict"
    assert r.path.name.startswith("1.")
    assert r.path.suffix == ".json"
    assert (tmp_path / "activity-details" / "1.json").read_bytes() == b'{"a":1}'
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
uv run pytest tests/test_archive.py -v
```

- [ ] **Step 3: Implement `archive.py`**

```python
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal


@dataclass(frozen=True)
class ArchiveResult:
    path: Path
    status: Literal["written", "skipped", "conflict"]


class RawArchive:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def write_bytes(self, relative: str, data: bytes) -> ArchiveResult:
        target = self.root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if target.read_bytes() == data:
                return ArchiveResult(path=target, status="skipped")
            stem = target.stem
            suffix = target.suffix
            ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            conflict = target.with_name(f"{stem}.{ts}{suffix}")
            conflict.write_bytes(data)
            return ArchiveResult(path=conflict, status="conflict")
        target.write_bytes(data)
        return ArchiveResult(path=target, status="written")

    def count_files(self, subdir: str | None = None) -> int:
        base = self.root if subdir is None else self.root / subdir
        if not base.exists():
            return 0
        return sum(1 for p in base.rglob("*") if p.is_file() and p.name != ".gitkeep")

    def write_meta(self, payload: dict[str, Any]) -> Path:
        path = self.root / "_meta" / "last_sync.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return path

    def read_meta(self) -> dict[str, Any] | None:
        path = self.root / "_meta" / "last_sync.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
uv run pytest tests/test_archive.py -v
```

- [ ] **Step 5: Commit**

```bash
git add services/zepp-importer/src/fitness/archive.py services/zepp-importer/tests/test_archive.py
git commit -m "$(cat <<'EOF'
feat: immutable raw archive writer with conflict siblings

EOF
)"
```

---

### Task 5: Endpoints + HTTP client

**Files:**
- Create: `services/zepp-importer/src/fitness/endpoints.py`
- Create: `services/zepp-importer/src/fitness/client.py`
- Create: `services/zepp-importer/tests/test_client.py`
- Create: `services/zepp-importer/tests/fixtures/history_page.json` (minimal synthetic)

**Interfaces:**
- Consumes: `Settings` host/token/user_id
- Produces:
  - `endpoints.history_path() -> str` → `"/v1/sport/run/history.json"`
  - `endpoints.detail_path() -> str` → `"/v1/sport/run/detail.json"`
  - `endpoints.heart_rate_path(user_id: str) -> str` → `f"/users/{user_id}/heartRate"`
  - `endpoints.history_params(from_track_id: int | None) -> dict`
  - `endpoints.detail_params(track_id: str, source: str) -> dict`
  - `endpoints.heart_rate_params(start: str, end: str) -> dict` — provisional query keys `start`/`end` as ISO dates; document as unverified
  - `class ZeppAuthError(Exception)`
  - `class ZeppClient`:
    - `__init__(self, host: str, app_token: str, user_id: str, transport: httpx.BaseTransport | None = None)`
    - `get_raw(self, path: str, params: dict | None = None) -> bytes` — returns response **body bytes**; raises `ZeppAuthError` on 401/403; retries once on 429/5xx with short sleep
    - `get_history(self, from_track_id: int | None = None) -> bytes`
    - `get_detail(self, track_id: str, source: str) -> bytes`
    - `get_heart_rate(self, start: str, end: str) -> bytes`

**Provisional endpoint evidence (OSS, unverified on T-Rex Pro):**
- History: `GET /v1/sport/run/history.json` (rolandsz uses `trackid` for pagination cursor)
- Detail: `GET /v1/sport/run/detail.json?trackid=&source=`
- HR: `GET /users/{id}/heartRate` (m4ary/zepp-health-cli)
- Headers: `apptoken`, `appPlatform: web`, `appname: com.xiaomi.hm.health`

- [ ] **Step 1: Write fixture + failing client tests**

`tests/fixtures/history_page.json`:

```json
{
  "code": 1,
  "message": "success",
  "data": {
    "next": 0,
    "summary": [
      {
        "trackid": "1700000000",
        "source": "run.mifit.huami.com",
        "type": 8,
        "run_time": "3600",
        "avg_heart_rate": "120",
        "max_heart_rate": 150,
        "app_name": "com.xiaomi.hm.health"
      }
    ]
  }
}
```

`tests/test_client.py`:

```python
from pathlib import Path

import httpx
import pytest

from fitness.client import ZeppAuthError, ZeppClient


FIXTURE = Path(__file__).parent / "fixtures" / "history_page.json"


def test_get_history_sends_auth_headers():
    body = FIXTURE.read_bytes()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["apptoken"] == "tok"
        assert request.headers["appPlatform"] == "web"
        assert request.headers["appname"] == "com.xiaomi.hm.health"
        assert request.url.path == "/v1/sport/run/history.json"
        return httpx.Response(200, content=body)

    transport = httpx.MockTransport(handler)
    client = ZeppClient("api-mifit-us3.zepp.com", "tok", "uid", transport=transport)
    assert client.get_history() == body


def test_401_raises_auth_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, content=b"nope")

    client = ZeppClient("api-mifit-us3.zepp.com", "tok", "uid", transport=httpx.MockTransport(handler))
    with pytest.raises(ZeppAuthError):
        client.get_history()
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
uv run pytest tests/test_client.py -v
```

- [ ] **Step 3: Implement `endpoints.py` and `client.py`**

`endpoints.py`:

```python
APP_NAME = "com.xiaomi.hm.health"
APP_PLATFORM = "web"


def history_path() -> str:
    return "/v1/sport/run/history.json"


def detail_path() -> str:
    return "/v1/sport/run/detail.json"


def heart_rate_path(user_id: str) -> str:
    return f"/users/{user_id}/heartRate"


def history_params(from_track_id: int | None = None) -> dict[str, str | int]:
    if from_track_id is None:
        return {}
    return {"trackid": from_track_id}


def detail_params(track_id: str, source: str) -> dict[str, str]:
    return {"trackid": track_id, "source": source}


def heart_rate_params(start: str, end: str) -> dict[str, str]:
    # Unverified query param names — confirm on first live sync.
    return {"start": start, "end": end}
```

`client.py` (outline — implement retries with `time.sleep(0.5)` once):

```python
from __future__ import annotations

import time

import httpx

from fitness import endpoints


class ZeppAuthError(Exception):
    pass


class ZeppClient:
    def __init__(
        self,
        host: str,
        app_token: str,
        user_id: str,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.user_id = user_id
        base = host if host.startswith("http") else f"https://{host}"
        self._client = httpx.Client(
            base_url=base.rstrip("/"),
            headers={
                "apptoken": app_token,
                "appPlatform": endpoints.APP_PLATFORM,
                "appname": endpoints.APP_NAME,
            },
            transport=transport,
            timeout=60.0,
        )

    def close(self) -> None:
        self._client.close()

    def get_raw(self, path: str, params: dict | None = None) -> bytes:
        last_exc: Exception | None = None
        for attempt in range(2):
            response = self._client.get(path, params=params or {})
            if response.status_code in (401, 403):
                raise ZeppAuthError(
                    f"Zepp auth failed ({response.status_code}). Re-extract apptoken — see docs/zepp-auth.md"
                )
            if response.status_code in (429, 500, 502, 503, 504) and attempt == 0:
                time.sleep(0.5)
                last_exc = httpx.HTTPStatusError(
                    "retryable", request=response.request, response=response
                )
                continue
            response.raise_for_status()
            return response.content
        assert last_exc is not None
        raise last_exc

    def get_history(self, from_track_id: int | None = None) -> bytes:
        return self.get_raw(endpoints.history_path(), endpoints.history_params(from_track_id))

    def get_detail(self, track_id: str, source: str) -> bytes:
        return self.get_raw(endpoints.detail_path(), endpoints.detail_params(track_id, source))

    def get_heart_rate(self, start: str, end: str) -> bytes:
        return self.get_raw(
            endpoints.heart_rate_path(self.user_id),
            endpoints.heart_rate_params(start, end),
        )
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
uv run pytest tests/test_client.py -v
```

- [ ] **Step 5: Commit**

```bash
git add services/zepp-importer/src/fitness/endpoints.py services/zepp-importer/src/fitness/client.py services/zepp-importer/tests/test_client.py services/zepp-importer/tests/fixtures
git commit -m "$(cat <<'EOF'
feat: add Zepp HTTP client for history, detail, HR

EOF
)"
```

---

### Task 6: Sync orchestration

**Files:**
- Create: `services/zepp-importer/src/fitness/sync.py`
- Create: `services/zepp-importer/tests/test_sync.py`

**Interfaces:**
- Consumes: `Settings`, `ZeppClient`, `RawArchive`
- Produces:
  - `@dataclass SyncOptions`: `from_date: date | None`, `activity_id: str | None`
  - `@dataclass SyncReport`: counts written/skipped/conflict; errors list
  - `def run_sync(settings: Settings, client: ZeppClient, archive: RawArchive, options: SyncOptions) -> SyncReport`
  - Behavior:
    1. Fetch history pages; archive each page as `activity-lists/trackid-{cursor-or-start}.json` (use `start` for first page, else `trackid-{from_track_id}`)
    2. Parse JSON only **after** archival to discover `data.summary[]` with `trackid` + `source`
    3. Filter by `from_date` if set: `trackid` is unix seconds string — keep items with `int(trackid) >= from_date` midnight UTC
    4. If `activity_id` set: only that track id
    5. For each selected activity missing `activity-details/{trackid}.json` (or forced by `--activity`): fetch detail → archive
    6. For HR: if `from_date` else last 7 days through today UTC — call `get_heart_rate` per day or range; archive as `heart-rate/YYYY-MM-DD.json`. Prefer one request per day if API semantics unclear; if single range response, still write one file named by start date and note limitation in report. **M1 default: one GET per calendar day** writing `heart-rate/YYYY-MM-DD.json`
    7. `archive.write_meta({...})` with ISO timestamps and counts
  - Do **not** call network when used with a fake client in tests

- [ ] **Step 1: Write failing sync test with fake client**

```python
import json
from datetime import date
from pathlib import Path

from fitness.archive import RawArchive
from fitness.config import Settings
from fitness.sync import SyncOptions, run_sync


class FakeClient:
    def __init__(self):
        self.detail_calls: list[tuple[str, str]] = []
        self.hr_calls: list[tuple[str, str]] = []

    def get_history(self, from_track_id: int | None = None) -> bytes:
        assert from_track_id is None
        return json.dumps(
            {
                "code": 1,
                "message": "success",
                "data": {
                    "next": 0,
                    "summary": [
                        {
                            "trackid": "1700000000",
                            "source": "run.mifit.huami.com",
                            "type": 8,
                        }
                    ],
                },
            }
        ).encode()

    def get_detail(self, track_id: str, source: str) -> bytes:
        self.detail_calls.append((track_id, source))
        return json.dumps({"code": 1, "data": {"trackid": int(track_id)}}).encode()

    def get_heart_rate(self, start: str, end: str) -> bytes:
        self.hr_calls.append((start, end))
        return json.dumps({"date": start, "bpm": [60, 61]}).encode()


def test_sync_archives_list_detail_and_hr(tmp_path: Path):
    settings = Settings(
        zepp_app_token="tok",
        zepp_user_id="uid",
        data_raw_dir=tmp_path,
    )
    client = FakeClient()
    archive = RawArchive(tmp_path)
    report = run_sync(
        settings,
        client,  # type: ignore[arg-type]
        archive,
        SyncOptions(from_date=date(2023, 1, 1), activity_id=None),
    )
    assert (tmp_path / "activity-lists").exists()
    assert (tmp_path / "activity-details" / "1700000000.json").exists()
    assert client.detail_calls == [("1700000000", "run.mifit.huami.com")]
    assert archive.read_meta() is not None
    assert report.details_written >= 1
```

- [ ] **Step 2: Run — expect FAIL**

```bash
uv run pytest tests/test_sync.py -v
```

- [ ] **Step 3: Implement `sync.py`**

Implement pagination: while history `data.next` is a positive track id cursor, fetch next page with `get_history(from_track_id=next)` and archive each page. Stop when `next` is 0/missing or page has empty summary. Keep M1 simple but correct vs rolandsz (`next` field).

Idempotency: skip `get_detail` when `activity-details/{trackid}.json` already exists unless `options.activity_id` equals that id (then always refresh fetch + archive rules still apply — conflict sibling if changed).

- [ ] **Step 4: Run — expect PASS**

```bash
uv run pytest tests/test_sync.py -v
```

- [ ] **Step 5: Commit**

```bash
git add services/zepp-importer/src/fitness/sync.py services/zepp-importer/tests/test_sync.py
git commit -m "$(cat <<'EOF'
feat: idempotent sync orchestration for lists, details, HR

EOF
)"
```

---

### Task 7: CLI commands

**Files:**
- Modify: `services/zepp-importer/src/fitness/cli.py`
- Create: `services/zepp-importer/tests/test_cli.py`

**Interfaces:**
- Consumes: `load_settings`, `credentials_ready`, `require_credentials`, `RawArchive`, `ZeppClient`, `run_sync`, `SyncOptions`
- Produces: Typer app with:
  - `fitness status`
  - `fitness sync [--from YYYY-MM-DD] [--activity ID]`
  - `fitness import` → same as sync

- [ ] **Step 1: Write CLI tests with Typer CliRunner**

```python
from typer.testing import CliRunner

from fitness.cli import app


runner = CliRunner()


def test_status_without_credentials(monkeypatch, tmp_path):
    monkeypatch.delenv("ZEPP_APP_TOKEN", raising=False)
    monkeypatch.delenv("ZEPP_USER_ID", raising=False)
    monkeypatch.setenv("DATA_RAW_DIR", str(tmp_path))
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "credentials" in result.stdout.lower() or "missing" in result.stdout.lower()


def test_sync_without_credentials(monkeypatch, tmp_path):
    monkeypatch.delenv("ZEPP_APP_TOKEN", raising=False)
    monkeypatch.delenv("ZEPP_USER_ID", raising=False)
    monkeypatch.setenv("DATA_RAW_DIR", str(tmp_path))
    result = runner.invoke(app, ["sync"])
    assert result.exit_code != 0
    assert "zepp-auth" in result.stdout.lower() or "zepp-auth" in (result.stderr or "").lower() or "ZEPP_" in result.stdout
```

- [ ] **Step 2: Run — expect FAIL/ partial until CLI implemented**

```bash
uv run pytest tests/test_cli.py -v
```

- [ ] **Step 3: Implement full `cli.py`**

```python
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

import typer

from fitness.archive import RawArchive
from fitness.client import ZeppAuthError, ZeppClient
from fitness.config import ConfigError, credentials_ready, load_settings, require_credentials
from fitness.sync import SyncOptions, run_sync

app = typer.Typer(add_completion=False, no_args_is_help=True)


@app.callback()
def main() -> None:
    """Local-first Zepp data importer."""


@app.command("status")
def status_cmd() -> None:
    settings = load_settings()
    archive = RawArchive(settings.data_raw_dir)
    typer.echo(f"host: {settings.zepp_host}")
    typer.echo(f"region: {settings.zepp_region}")
    typer.echo(f"raw_dir: {settings.data_raw_dir}")
    typer.echo(f"credentials: {'ok' if credentials_ready(settings) else 'missing'}")
    typer.echo(f"raw_files: {archive.count_files()}")
    meta = archive.read_meta()
    typer.echo(f"last_sync: {meta.get('finished_at') if meta else 'never'}")


def _run_sync_cmd(from_: Optional[str], activity: Optional[str]) -> None:
    settings = load_settings()
    try:
        require_credentials(settings)
    except ConfigError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    from_date = datetime.strptime(from_, "%Y-%m-%d").date() if from_ else None
    archive = RawArchive(settings.data_raw_dir)
    assert settings.zepp_app_token and settings.zepp_user_id
    client = ZeppClient(settings.zepp_host, settings.zepp_app_token, settings.zepp_user_id)
    try:
        report = run_sync(
            settings,
            client,
            archive,
            SyncOptions(from_date=from_date, activity_id=activity),
        )
    except ZeppAuthError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc
    finally:
        client.close()
    typer.echo(report)


@app.command("sync")
def sync_cmd(
    from_: Optional[str] = typer.Option(None, "--from", help="YYYY-MM-DD"),
    activity: Optional[str] = typer.Option(None, "--activity", help="Zepp track id"),
) -> None:
    _run_sync_cmd(from_, activity)


@app.command("import")
def import_cmd(
    from_: Optional[str] = typer.Option(None, "--from"),
    activity: Optional[str] = typer.Option(None, "--activity"),
) -> None:
    """Alias of sync for Milestone 1."""
    _run_sync_cmd(from_, activity)
```

Make `SyncReport` printable (`__str__` with counts).

- [ ] **Step 4: Run all tests**

```bash
uv run pytest -v
uv run fitness status
```

Expected: all pass; status works without credentials.

- [ ] **Step 5: Commit**

```bash
git add services/zepp-importer/src/fitness/cli.py services/zepp-importer/tests/test_cli.py
git commit -m "$(cat <<'EOF'
feat: add fitness status/sync/import CLI

EOF
)"
```

---

### Task 8: Documentation deliverables

**Files:**
- Modify: `README.md`
- Create: `docs/architecture.md`
- Create: `docs/zepp-auth.md`
- Create: `docs/zepp-data-model.md`
- Create: `docs/hr-zone-models.md`
- Create: `docs/examples/README.md`

**Interfaces:**
- Consumes: OSS endpoint knowledge + this plan’s provisional paths
- Produces: docs required by the design spec

- [ ] **Step 1: Write `docs/zepp-auth.md`**

Include:
1. Primary: `https://user.huami.com/privacy2/index.html` → login → DevTools → Application → Cookies → `apptoken`, `userid`
2. Fallback: MITM/HAR of Zepp app; extract host `api-mifit*.zepp.com`, `apptoken`, user id from path
3. Put values in repo-root `.env`
4. Token secrecy + ~30 day expiry
5. No password login in this project

- [ ] **Step 2: Write `docs/zepp-data-model.md`**

Sections (label all live-T-Rex-Pro fields **unverified** until first sync):
- Auth headers
- Hosts
- Endpoints: history, detail, heartRate (+ optional sport-load path from m4ary as future)
- Pagination (`trackid` / `next`)
- Known summary fields from rolandsz models (list with types)
- Detail delta-encoded series note (`heart_rate`, GPS strings) — meaning of encoding marked “investigate on live data”
- Timestamp semantics: `trackid` as unix start seconds (reported by OSS)
- Units: unknown/unverified table
- Sport `type` integers: unknown mapping — do not invent gym vs run labels yet
- Missing data / limitations
- Provisional normalized schema proposal (activities / samples / HR / daily_metrics) with unknown markers

- [ ] **Step 3: Write `docs/architecture.md`, `docs/hr-zone-models.md`, `docs/examples/README.md`, expand root `README.md`**

`hr-zone-models.md`: stub describing %HRmax, HRR/Karvonen, manual; note “not implemented in M1”.

`architecture.md`: full pipeline diagram + M1 slice + handoff to M2–M4.

Root README setup:

```bash
git clone …
cd zepp-training-analytics
cd services/zepp-importer && uv sync --extra dev
cp ../../.env.example ../../.env
# edit .env — see docs/zepp-auth.md
uv run fitness status
uv run fitness sync --from 2025-01-01
```

- [ ] **Step 4: Commit docs**

```bash
git add README.md docs/
git commit -m "$(cat <<'EOF'
docs: add M1 architecture, auth, and provisional Zepp data model

EOF
)"
```

---

### Task 9: Final verification gate

**Files:**
- Modify: none unless fixes required

- [ ] **Step 1: Run full test suite**

```bash
cd services/zepp-importer
uv run pytest -v
```

Expected: all green.

- [ ] **Step 2: Smoke CLI without credentials**

```bash
uv run fitness status
uv run fitness sync; echo exit:$?
```

Expected: status exit 0; sync non-zero with auth guidance.

- [ ] **Step 3: Confirm git hygiene**

```bash
git status
git check-ignore -v .env data/raw/foo.json || true
```

Expected: secrets/raw patterns ignored; working tree clean or only intentional leftovers.

- [ ] **Step 4: Spec coverage checklist (human/agent)**

Confirm each design success criterion:
1. `uv` install works
2. `fitness status` without creds
3. `fitness sync` fails clearly without creds
4. With creds (manual, later): can archive history/detail/HR — code paths exist
5. Docs present: README, architecture, zepp-auth, zepp-data-model, hr-zone-models, examples note, `.env.example`

- [ ] **Step 5: Final commit only if fixes were needed; otherwise done**

---

## Self-review (plan vs spec)

| Spec requirement | Task |
|---|---|
| Importer-only monorepo layout | 1–2 |
| Env auth, no password | 3, 7, 8 |
| `fitness status/sync/import` | 7 |
| `--from` / `--activity` | 6–7 |
| Immutable raw archive + conflict siblings | 4 |
| activity-lists / activity-details / heart-rate layout | 6 |
| Sync meta without secrets | 4, 6 |
| Provisional docs + schema proposal | 8 |
| HR zone stub doc | 8 |
| Tests: config, archive, client, sync, CLI | 3–7, 9 |
| No DuckDB/web | Global constraints |
| OSS-informed independent client | 5 |

No intentional placeholders remain. HR query param names are explicitly marked unverified in code comments and `zepp-data-model.md` — confirm on first live sync (post-M1 credential step), not during M1 offline work.
