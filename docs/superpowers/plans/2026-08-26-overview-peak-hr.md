# Overview Peak HR Implementation Plan

> **For agentic workers:** Execute task-by-task with TDD.

**Goal:** Add period-scoped peak workout HR to Overview API + UI.

**Architecture:** Extend `overview` query/response; display fourth metric on Overview.

## Task 1: API `peak_hr_bpm`

**Files:** `queries.py`, `schemas.py`, `main.py`, `tests/test_api_queries.py`

- [ ] Add `overview_peak_hr(path, from_date, to_date) -> int | None`
- [ ] Add field on `OverviewResponse`
- [ ] Wire in overview route
- [ ] Assert all-time peak `160`, Aug 24 peak `150` on seeded fixtures
- [ ] Commit: `feat(api): expose period peak workout HR on overview`

## Task 2: Overview UI

**Files:** `apps/web/src/api/client.ts`, `pages/Overview.tsx`, `Overview.test.tsx` (+ App mocks if needed)

- [ ] Type + render Peak HR metric
- [ ] Tests for value and empty `—`
- [ ] Commit: `feat(web): show peak HR on overview metrics`
