# Milestone 3 — Training Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a local FastAPI + React dashboard over DuckDB with OTF-style 5-zone analytics, activity overview/list/detail, and light/dark/system themes.

**Architecture:** Read-only FastAPI (`services/api`) queries `data/zepp.duckdb`, computes zones in-process, stores athlete profile in gitignored `data/profile.json`. React/Vite app (`apps/web`) consumes `/api/*`. No Zepp network calls from M3.

**Tech Stack:** Python 3.12+, `uv`, FastAPI, uvicorn, duckdb, pydantic, pydantic-settings; React 19 + TypeScript + Vite; CSS variables for themes

## Global Constraints

- Spec: `docs/superpowers/specs/2026-08-26-m3-dashboard-design.md`
- OTF bands: Z1 50–60, Z2 61–70, Z3 71–83, Z4 84–91, Z5 92–100 (% MaxHR)
- Colors: gray, blue, green, orange, red (fixed across themes)
- HRmax: override else 99th percentile of `activity_samples.hr_bpm > 0`
- `<50%` → `below`; `≥92%` (incl. >100%) → Z5
- Splat estimate = minutes in Z4+Z5; label as local estimate
- Display TZ Europe/Madrid; DB stays UTC
- Never commit `data/profile.json`, DuckDB, or raw health payloads
- No live Zepp in tests; TDD for zone math + API
- UI: functional / futuristic / minimal — avoid purple SaaS / cream-serif clichés

---

## File map

| Path | Responsibility |
|---|---|
| `services/api/pyproject.toml` | API package + deps |
| `services/api/src/fitness_api/` | FastAPI app package |
| `fitness_api/zones.py` | Pure zone math |
| `fitness_api/profile.py` | Load/save profile.json |
| `fitness_api/db.py` | DuckDB read-only helper |
| `fitness_api/queries.py` | SQL + aggregation |
| `fitness_api/main.py` | Routes |
| `services/api/tests/` | Zone + API tests |
| `apps/web/` | Vite React TS app |
| `apps/web/src/styles/theme.css` | Light/dark/system tokens + zone colors |
| `apps/web/src/pages/*` | Overview, Activities, Detail, Zones |
| `docs/architecture.md`, `docs/hr-zone-models.md`, `README.md` | M3 docs |
| `.env.example` | `DUCKDB_PATH`, `PROFILE_PATH`, `API_CORS_ORIGIN` |

---

### Task 1: Zone engine (pure functions)

**Files:**
- Create: `services/api/pyproject.toml` (minimal package first)
- Create: `services/api/src/fitness_api/__init__.py`
- Create: `services/api/src/fitness_api/zones.py`
- Test: `services/api/tests/test_zones.py`

**Interfaces:**
- `ZoneId = Literal["below","z1","z2","z3","z4","z5"]`
- `OTF_BANDS: list[tuple[ZoneId, int, int, str]]` — (id, pct_lo, pct_hi, color) for z1–z5; below separate
- `assign_zone(hr: int, hrmax: float) -> ZoneId`
- `bpm_boundaries(hrmax: float) -> dict[ZoneId, tuple[float, float]]`
- `suggest_hrmax(samples: list[int], percentile: float = 0.99) -> float | None`
- `time_in_zones(series: list[tuple[int, int]], hrmax: float) -> dict[ZoneId, float]`  
  series = `(elapsed_s, hr_bpm)` sorted; duration for point i = `elapsed[i+1]-elapsed[i]` seconds; last point contributes **0**
- `splat_minutes(time_by_zone: dict[ZoneId, float]) -> float` — `(z4+z5)/60`

- [ ] **Step 1: Scaffold api package + failing tests**

`pyproject.toml`:

```toml
[project]
name = "fitness-api"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "fastapi>=0.115",
  "uvicorn[standard]>=0.30",
  "duckdb>=1.1",
  "pytz>=2024.1",
  "pydantic>=2.7",
  "pydantic-settings>=2.3",
]

[project.optional-dependencies]
dev = ["pytest>=8.2", "httpx>=0.27"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/fitness_api"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

```python
# tests/test_zones.py
from fitness_api.zones import assign_zone, suggest_hrmax, time_in_zones, splat_minutes

def test_assign_zone_otf_bands():
    assert assign_zone(80, 160) == "below"   # 50%
    assert assign_zone(81, 160) == "z1"      # >50%
    assert assign_zone(112, 160) == "z3"     # 70% is still z2 (61-70); 71% = 113.6
    assert assign_zone(114, 160) == "z3"
    assert assign_zone(147, 160) == "z5"     # 91.875% → z4 is 84-91; 92% = 147.2
    assert assign_zone(200, 160) == "z5"

def test_suggest_hrmax_percentile():
    samples = list(range(100, 181))  # 100..180
    assert suggest_hrmax(samples, 0.99) == 180

def test_time_in_zones_and_splat():
    # 0@100, 60@140, 120@150 with hrmax 160 → durations 60s, 60s
    series = [(0, 100), (60, 140), (120, 150)]
    t = time_in_zones(series, 160.0)
    assert t["z2"] == 60.0   # 100/160=62.5% → z2
    assert t["z4"] == 60.0   # 140/160=87.5% → z4
    assert splat_minutes(t) == 1.0
```

Adjust exact assertions carefully when implementing so they match inclusive OTF cutovers:
- z1 if `50 ≤ pct ≤ 60`
- z2 if `61 ≤ pct ≤ 70`
- … use integer percent via `floor` or round? Spec: `pct = 100 * hr / hrmax` then compare. Use continuous float compares: `50 <= pct < 61` for z1, etc., with z5 `pct >= 92`. **Lock this in code:**

```python
def assign_zone(hr: int, hrmax: float) -> ZoneId:
    if hrmax <= 0:
        raise ValueError("hrmax must be positive")
    pct = 100.0 * hr / hrmax
    if pct < 50:
        return "below"
    if pct < 61:
        return "z1"
    if pct < 71:
        return "z2"
    if pct < 84:
        return "z3"
    if pct < 92:
        return "z4"
    return "z5"
```

Rewrite the sample assertions to match this half-open style (document as implementing OTF published ranges).

- [ ] **Step 2: Run tests — expect FAIL**

`cd services/api && uv sync --extra dev && uv run pytest tests/test_zones.py -v`

- [ ] **Step 3: Implement `zones.py`**

- [ ] **Step 4: PASS + commit**

```bash
git add services/api
git commit -m "feat(api): add OTF zone math helpers"
```

---

### Task 2: Profile store + API health

**Files:**
- Create: `fitness_api/config.py`, `profile.py`, `db.py`, `main.py`
- Test: `tests/test_profile.py`, `tests/test_health.py`
- Modify: `.env.example`, root `README.md` (run API note stub)

**Interfaces:**
- `Settings`: `duckdb_path`, `profile_path` (default `<repo>/data/profile.json`), `cors_origin` default `http://localhost:5173`
- `Profile` pydantic model with fields from spec
- `load_profile() / save_profile()`
- App factory `create_app()` with CORS + `GET /api/health`

- [ ] **Step 1: Failing tests for profile round-trip + health with missing/present duckdb**

- [ ] **Step 2: Implement**

```python
# health returns {"status":"ok","duckdb": true/false}
```

- [ ] **Step 3: PASS + commit**

```bash
git commit -m "feat(api): profile store and health endpoint"
```

---

### Task 3: Activities, overview, zones API

**Files:**
- Create: `fitness_api/queries.py`, `fitness_api/schemas.py`
- Extend: `main.py`
- Test: `tests/test_api_queries.py` with **temp DuckDB** seeded with tiny `activities` + `activity_samples`

**Interfaces:**
- Seed helper in tests creates schema compatible with importer tables (minimal columns used)
- `GET /api/zones` — resolved hrmax, source (`override`|`suggested`|`none`), boundaries, colors, age refs if birth_date set
- `GET /api/activities` — query params `from`, `to` (ISO date), optional `sport_type`
- `GET /api/activities/{id}` — 404 if missing; includes `hr_series: [{elapsed_s, hr_bpm, zone}]`, `time_in_zone`, `splat_minutes_estimate`
- `GET /api/overview` — counts, duration_s, zone_mix seconds, splat estimate, `recent: []` (limit 10)
- `GET/PUT /api/settings/profile`

**HRmax suggestion query:**

```sql
SELECT quantile_cont(hr_bpm, 0.99)
FROM activity_samples
WHERE hr_bpm > 0
```

- [ ] **Step 1: Failing API tests with TestClient + tmp duckdb/profile**

- [ ] **Step 2: Implement queries + routes**

- [ ] **Step 3: Full api pytest PASS + commit**

```bash
git commit -m "feat(api): overview, activities, and zones endpoints"
```

---

### Task 4: Web app scaffold + theme shell

**Files:**
- Create: `apps/web/` via Vite React-TS template (or hand-rolled minimal)
- Create: `src/styles/theme.css`, `src/App.tsx`, layout/nav, theme provider (`light`|`dark`|`system`)
- Proxy `/api` → `http://127.0.0.1:8000` in `vite.config.ts`

**Visual constraints (hard):**
- Brand/product name “Zepp Training” or “Training Analytics” as clear header signal
- No card grid clutter; sparse layout; CSS variables
- Zone CSS vars: `--zone-below`, `--zone-z1` … `--zone-z5` with OTF-like gray/blue/green/orange/red
- Avoid purple-on-white and cream/terracotta AI defaults

- [ ] **Step 1: Scaffold app, theme toggle works offline (mock)**

- [ ] **Step 2: Commit**

```bash
git add apps/web
git commit -m "feat(web): scaffold Vite app with system theme support"
```

---

### Task 5: Overview + Activities pages

**Files:**
- `pages/Overview.tsx`, `pages/Activities.tsx`, `api/client.ts`
- Period selector shared component

- [ ] **Step 1: Wire `GET /api/overview` and `/api/activities`**
- [ ] **Step 2: Zone mix bar + recent list + activities table**
- [ ] **Step 3: Manual check with API running; commit**

```bash
git commit -m "feat(web): overview and activities views"
```

---

### Task 6: Activity detail + zone chart

**Files:**
- `pages/ActivityDetail.tsx`, `components/HrZoneChart.tsx`

- [ ] **Step 1: Fetch detail; render HR polyline with zone band background**
- [ ] **Step 2: Time-in-zone breakdown + splat estimate label**
- [ ] **Step 3: Commit**

```bash
git commit -m "feat(web): activity detail HR chart with zones"
```

---

### Task 7: Zones settings page

**Files:**
- `pages/Zones.tsx`

- [ ] **Step 1: Show OTF table, suggested vs override HRmax, age refs, BPM preview**
- [ ] **Step 2: PUT profile on save (hrmax_override, resting_hr, birth_date, sex)**
- [ ] **Step 3: Commit**

```bash
git commit -m "feat(web): zones settings and HRmax controls"
```

---

### Task 8: Docs + run scripts

**Files:**
- `README.md` — how to run importer normalize, API, web
- `docs/architecture.md` — M3 slice
- `docs/hr-zone-models.md` — mark OTF % model as implemented for dashboard
- Optional: `scripts/dev.sh` starting api+web

- [ ] **Step 1: Docs**
- [ ] **Step 2: Smoke**

```bash
# terminal 1
cd services/api && uv run uvicorn fitness_api.main:app --reload --port 8000
# terminal 2
cd apps/web && npm run dev
```

- [ ] **Step 3: Commit**

```bash
git commit -m "docs: document M3 dashboard runbook"
```

---

## Spec coverage checklist

| Spec item | Task |
|---|---|
| OTF zone math + below bucket | 1 |
| Suggested HRmax 99th + override | 1, 3, 7 |
| Splat estimate labeling | 3, 5, 6 |
| Profile local JSON | 2, 7 |
| API endpoints | 2–3 |
| Overview / Activities / Detail / Zones | 5–7 |
| Light/dark/system | 4 |
| Docs | 8 |

## Placeholder scan

- Half-open % cutovers must be documented in `zones.py` docstring (OTF inclusive tables approximated as half-open for ties at 61/71/84/92).
- Last HR sample duration = 0 (explicit).

---

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-08-26-m3-dashboard.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks  
2. **Inline Execution** — execute in this session with checkpoints  

Which approach?
