# Overview Peak HR (period) — Design

## Goal

Show the highest recorded workout heart rate for the Overview’s selected period, without conflating it with MaxHR.

## Decision

- **Source:** `max(activity_samples.hr_bpm)` where `hr_bpm > 0`, joined to `activities`, filtered by the same `started_at` period as overview (`from`/`to`, Europe/Madrid inclusive).
- **Not used:** band `heart_rate_samples`, activity summary `max_hr`, MaxHR override/suggestion.
- **API:** `GET /api/overview` adds `peak_hr_bpm: int | null` (`null` when no positive samples in period).
- **UI:** Overview metrics row — label **Peak HR**, value `{n} bpm` or `—`, supporting text **Highest workout sample**.

## Out of scope

Activities column, promoting peak into MaxHR, band continuous HR.
