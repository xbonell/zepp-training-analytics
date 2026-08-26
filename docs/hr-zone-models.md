# Heart-rate zone models

M1 only archives raw Zepp responses; zone math was deferred until the dashboard
could compute from normalized workout HR samples.

## Implemented for dashboard (M3)

### Percentage of maximum heart rate — OTF-style (primary)

The M3 dashboard uses Orangetheory-style % MaxHR bands as the primary zone
model. Implementation lives in `services/api/src/fitness_api/zones.py`.

| Zone | Color | Published % MaxHR | Assignment (half-open) |
|---|---|---|---|
| below | gray | &lt; 50 | `pct < 50` |
| 1 | gray | 50–60 | `50 <= pct < 61` |
| 2 | blue | 61–70 | `61 <= pct < 71` |
| 3 | green | 71–83 | `71 <= pct < 84` |
| 4 | orange | 84–91 | `84 <= pct < 92` |
| 5 | red | 92–100 | `pct >= 92` (includes &gt;100%) |

OTF publishes inclusive ranges; the API uses half-open float cutovers so ties
at 61/71/84/92 land unambiguously in the higher zone.

**HRmax resolution:** manual `hrmax_override` in `data/profile.json` if set;
otherwise suggested from the 99th percentile of positive `activity_samples.hr_bpm`.
Age formulas (220 − age, Tanaka) are reference-only on the Zones page.

**Time-in-zone:** each sample contributes duration until the next sample; the
last sample contributes zero seconds.

**Splat:** minutes in zones 4 + 5 (orange + red).

Resting HR is stored in profile but not used for OTF % math in M3.

## Future models (M4+)

### Heart-rate reserve (HRR / Karvonen)

Boundaries use:

```text
target HR = resting HR + intensity × (HRmax − resting HR)
```

Requires trustworthy resting-HR and HRmax values. Estimation windows, missing-data
behavior, and provenance must be documented when implemented.

### Manual zones

Users provide ordered BPM boundaries directly. Validation should reject gaps,
overlaps, and non-increasing boundaries while preserving the user's labels.

## Deferred decisions

M4 will define additional zone counts, default percentages beyond OTF, richer
HRmax and resting-HR estimators, rounding, per-sport overrides, and historical
recalculation. Zepp proprietary training load must remain distinct from metrics
calculated from local zones.
