# Heart-rate zone models

Heart-rate zones are **not implemented in M1**. M1 only archives raw Zepp
responses; all T-Rex Pro heart-rate fields, timestamps, and units remain
**unverified** until first sync.

Future milestones may support three explicitly selected models:

## Percentage of maximum heart rate

Zones are boundaries expressed as percentages of a configured maximum heart
rate (`HRmax`). The source of HRmax must be visible: manual, observed, or an
explicit age-based estimate. No formula or default boundaries are selected yet.

## Heart-rate reserve (HRR / Karvonen)

Boundaries use:

```text
target HR = resting HR + intensity × (HRmax − resting HR)
```

This requires a trustworthy resting-HR value and HRmax. Future implementation
must document estimation windows, missing-data behavior, and value provenance.

## Manual zones

Users provide ordered BPM boundaries directly. Validation should reject gaps,
overlaps, and non-increasing boundaries while preserving the user's labels.

## Deferred decisions

M4 will define zone count, default percentages, HRmax and resting-HR estimators,
rounding, per-sport overrides, and historical recalculation. Zepp proprietary
training load must remain distinct from metrics calculated from local zones.
