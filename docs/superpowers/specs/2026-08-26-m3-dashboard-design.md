# Milestone 3 — Training Dashboard Design

**Date:** 2026-08-26  
**Status:** Approved (brainstorming)  
**Scope:** Local FastAPI + React dashboard over DuckDB; OTF-style 5-zone analytics

## 1. Goal

Give a global view of trainings/activities, activity detail with HR, and
visualization of heart-rate training zones computed from recorded workout data —
with a functional, futuristic, minimal UI (light / dark / system).

**Success criteria**

- Overview: period volume, zone mix, local splat estimate, recent activities
- Activities list → detail with zone-colored HR chart and time-in-zone
- Zones page: OTF % bands, suggested HRmax, manual override, BPM preview
- Themes: light, dark, system
- Read-only API over existing DuckDB; no Zepp network calls
- Local profile/settings (gitignored); zone math unit-tested

## 2. Decisions locked in brainstorming

| Decision | Choice |
|---|---|
| Look & feel | Functional, futuristic, minimal; light / dark / system |
| Zone franchise alignment | Orangetheory % MaxHR bands + colors |
| Zone boundary mode | % of HRmax (not manual BPM table as primary) |
| Default HRmax | **C** — suggested from workout HR distribution (99th percentile); manual override |
| OTF app MaxHR | Not default (user reports it keeps them in gray–blue–green) |
| Splat-like metric | **B** — orange+red minutes, labeled as local estimate (not official Splat) |
| Architecture | **1** — FastAPI (`services/api`) + React/Vite (`apps/web`) |
| Below 50% MaxHR | Separate “below zones” bucket (not forced into gray) |
| ≥100% MaxHR | Zone 5 (red) |
| Resting HR / DOB / sex | Stored in local profile; RHR not used for OTF % math in v1 |
| Display timezone | Europe/Madrid; DuckDB timestamps remain UTC |

## 3. Out of scope (this cut)

- Official Orangetheory / OTBeat API sync
- Karvonen / HRR as primary zone model
- Band continuous-HR chart on overview (workout zones first)
- GPS maps, pace charts, social/auth
- Recalculating/writing zones back into DuckDB tables (compute in API)
- Docker requirement (optional later)

## 4. Information architecture

### Shell
Minimal nav: Overview · Activities · Zones · theme control.

### Overview
- Period: 7d / 30d / 90d / YTD / all
- Volume: sessions, total duration
- Zone mix (stacked bar): below + Z1–Z5 colors
- Local splat estimate (Z4+Z5 minutes), clearly labeled
- Recent activities → detail

### Activities
- Dense list: date, sport type, duration, avg/max HR, dominant zone chip, splat estimate
- Filters: period, sport type
- Navigate to detail

### Activity detail
- Header metrics
- HR timeline with zone-colored bands
- Time-in-zone + splat estimate for session

### Zones
- OTF % table (defaults fixed; editable percentages deferred unless trivial)
- HRmax: suggested value + provenance; manual override; age-formula references
- Resting HR field (stored)
- BPM boundary preview for current HRmax

## 5. Zone engine

### OTF defaults (% MaxHR)

| Zone | Color | % MaxHR |
|---|---|---|
| 1 | gray | 50–60 |
| 2 | blue | 61–70 |
| 3 | green | 71–83 |
| 4 | orange | 84–91 |
| 5 | red | 92–100 |

### HRmax resolution
1. `hrmax_override` if set in profile  
2. Else suggested = **99th percentile** of `activity_samples.hr_bpm` where `hr_bpm > 0`  
3. Age formulas (`220 − age`, Tanaka `208 − 0.7×age`) shown as reference only  

### Sample assignment
Given `hr` and resolved `hrmax`:
- `pct = 100 * hr / hrmax`
- `pct < 50` → `below`
- else map into Z1–Z5 by inclusive OTF ranges; `pct ≥ 92` → Z5 (including &gt;100)

### Time-in-zone
For an ordered workout series `(elapsed_s, hr_bpm)`, attribute each sample’s zone for duration until next sample (last sample: repeat previous Δ or 1s minimum — document choice in implementation: **use Δ to next sample; final point contributes 0 or 1s — prefer Δ to next only, drop trailing zero**).

Splat estimate = seconds in Z4 + Z5, reported as minutes.

### Profile (`data/profile.json`, gitignored)
Fields: `sex`, `birth_date`, `resting_hr`, `hrmax_override` (nullable), `theme_preference` (`light`|`dark`|`system`), `display_timezone` default `Europe/Madrid`.

## 6. API (`services/api`)

| Method | Path | Role |
|---|---|---|
| GET | `/api/health` | liveness + duckdb reachable |
| GET | `/api/overview` | period aggregates |
| GET | `/api/activities` | list + summary zone chips |
| GET | `/api/activities/{id}` | detail + HR series + zones |
| GET/PUT | `/api/settings/profile` | profile CRUD |
| GET | `/api/zones` | resolved HRmax, boundaries, colors |

DuckDB path from env (`DUCKDB_PATH`), same convention as importer. Read-only connections preferred.

## 7. Web (`apps/web`)

- React + TypeScript + Vite
- CSS variables for themes; zone colors constant across themes
- Futuristic minimal: sparse chrome, strong hierarchy, subtle atmosphere (not generic purple SaaS)
- Motions: chart draw-in, theme cross-fade, list/route transition (2–3 total)

## 8. Testing

- Zone math: assignment, suggestion percentile, splat estimate, below-bucket
- API: happy-path with temp DuckDB fixture
- No live Zepp; no committed `profile.json` with personal data

## 9. Repo layout (additive)

```text
services/api/          # FastAPI
apps/web/              # React UI
data/profile.json      # gitignored
docs/hr-zone-models.md # update OTF defaults as implemented model
```

## 10. Handoff

| Later | Notes |
|---|---|
| Tune HRmax UX | Compare suggested vs override vs age on Zones page |
| Band HR on overview | Optional day strip from `heart_rate_samples` |
| Karvonen mode | Uses stored resting HR |
| M4 depth | Trends, richer estimators, historical recalculation |
