# Provisional Zepp data model

This document records the request shape implemented in M1 plus **live Global-EU
evidence** from an Amazfit T-Rex Pro account (`bind_device` prefix
`0:MILI:200:…`, host `api-mifit-us3.zepp.com`, first sync 2026-08-26).

Rows labeled **live** were observed in archived responses under `data/raw/`.
Rows labeled **candidate** come from OSS / Zepp OS docs and are not confirmed
for this cloud API. Unknowns stay explicit.

## Request model

The client sends these headers on every GET:

| Header | Value |
|---|---|
| `apptoken` | `ZEPP_APP_TOKEN` |
| `appPlatform` | `web` |
| `appname` | `com.xiaomi.hm.health` |

`ZEPP_USER_ID` is inserted into user-scoped paths. The regional base host is
configurable through `ZEPP_HOST`; the live account used
`api-mifit-us3.zepp.com` successfully.

### Implemented endpoints

| Client method | Request | Live status |
|---|---|---|
| history | `GET /v1/sport/run/history.json` | **live** — `code=1`, `message=success` |
| next history page | same path with `?trackid=<data.next>` | **live** — first page returned `next=-1` (no further pages for this pull) |
| activity detail | `GET /v1/sport/run/detail.json?trackid=<id>&source=<source>` | **live** — indoor fitness details archived |
| continuous HR (hollow) | `GET /users/<ZEPP_USER_ID>/heartRate?startTime=<ms>&endTime=<ms>&type=2` | **live** — HTTP 200 with `{"items":[]}`; not used by sync |
| all-day band data / HR | `GET /v1/data/band_data.json?query_type=detail&from_date=&to_date=&userid=&device_type=0` | **live** — `code=1` with `data[].data_hr` present |

Sync requests one `band_data` detail day per UTC calendar date and archives the
raw body under `band-data/YYYY-MM-DD.json`. On this account, `data_hr` is base64
of **1440 uint8** values (one per minute); `254` (`0xFE`) is the empty sentinel
and in-range BPM appears as raw bytes (e.g. 54–172 on a sampled day). OSS often
describes Java `short` pairs — treat that as **candidate** for other devices /
API versions; do not assume 2-byte decoding here. M1 does not decode the blob.
`device_type=0` is verified on this account; other device_type strings may also
work.

Future-only OSS evidence from `m4ary/zepp-health-cli` identifies
`GET /v2/watch/users/{id}/WatchSportStatistics/SPORT_LOAD`. M1 does not call it.

## History pagination and timestamps

History responses contain `data.summary[]` and `data.next` (**live**).

- `trackid` is the activity start as a **Unix seconds** string (**live**).
- `end_time` is Unix seconds as a string; `int(end_time) - int(trackid)` matches
  `run_time` for sampled rows (**live**).
- `run_time` is duration in **seconds** as a string (**live**).
- M1 uses `trackid` for `--from` filtering and does not rewrite timestamps.
- Display timezone for the product remains Europe/Madrid; archives keep source
  epochs as-is.

## History summary fields

Observed JSON types on this account (489 activities in one list page):

| Field | Live JSON type | Notes |
|---|---|---|
| `trackid`, `source`, `dis`, `calorie`, `end_time`, `run_time` | string | present on all 489 |
| `avg_pace`, `avg_frequency`, `avg_heart_rate` | string | present on all 489 |
| `type` | integer | sport discriminator; see below |
| `max_heart_rate`, `min_heart_rate` | integer | present on all 489 |
| `te` | integer | present on 485/489 |
| `exercise_load` | integer | present on 481/489; Zepp proprietary load |
| `bind_device`, `app_name`, `location` | string | all 489; device id `0:MILI:200:…` |
| `total_step` | integer | 353/489 non-sentinel; often `-1` when N/A |
| `city` | string | 51/489 |
| `syncedTimezone` | string | 17/489 |
| `sport_title`, `model` | — | empty / absent on this pull |

Many other keys appear with sentinels (`-1`, `0`, `""`). Treat absence and
sentinel as null for M2. The synthetic test fixture is not live evidence.

### Sport `type` values (this account)

Confirmed labels (matched in Zepp app, 2026-08-26):

| `type` | Label | Count (approx) |
|---|---|---|
| 1 | Outdoor Running | 22 |
| 6 | Walking | 8 |
| 9 | Outdoor Cycling | 37 |
| 10 | Indoor Cycling | 1 |
| 16 | Freestyle | 22 |
| 22 | Hiking | 12 |
| 24 | Indoor Fitness | 386 |
| 40 | Indoor Walk | 1 |

Dashboard maps these in `fitness_api.sports.SPORT_LABELS`; unknown ids render as `Sport {n}`.

| `type` | Count | Empirical traits (live) | Notes |
|---|---|---|---|
| 24 | 386 | `dis=0`, workout HR in details | Indoor Fitness |
| 9 | 37 | large `dis`, altitude | Outdoor Cycling |
| 1 | 22 | `dis` ~5–10 km, step counts | Outdoor Running |
| 16 | 22 | `dis=0` | Freestyle |
| 22 | 12 | `dis` + steps + altitude, slow | Hiking |
| 6 | 8 | `dis` + steps, walk pace | Walking |
| 10 | 1 | `dis=0` | Indoor Cycling |
| 40 | 1 | `dis` + steps | Indoor Walk |

Keep raw `type` integers in storage. Display labels are a local confirmed map,
not inventing analytical categories beyond Zepp app names.

## Detail series

Detail envelope (**live**): `{ "code", "message", "data" }`.

For the nine archived type-24 details:

| Series key | Live observation |
|---|---|
| `heart_rate` | Non-empty on all nine; semicolon-separated `dt,dv` pairs |
| `source` | e.g. `run.200.huami.com` |
| `provider` | `gps` even when GPS series empty |
| `longitude_latitude`, `altitude`, `pace`, … | empty strings on these indoor sessions |
| `pause`, `lap` | occasionally present |

### Workout `heart_rate` encoding (**live**)

Format: `dt,dv;dt,dv;…` where

1. `dt` is seconds since the previous sample (cumulative time ≈ `run_time`);
2. the first `dv` is absolute BPM;
3. later `dv` values are signed deltas from the previous BPM.

Sample-mean BPM tracks summary `avg_heart_rate`; min/max track summary
`min_heart_rate` / `max_heart_rate` (sentinel `0` can appear at the tail).

M1 still archives bytes without decoding. M2 decodes this stream into
`activity_samples` (implemented by `fitness normalize`). Workout HR does not
populate `heart_rate_samples`; that table is band-only in this cut.

## Continuous heart rate / band data

`/users/.../heartRate` is a known hollow endpoint on this account (and in OSS
reports): correct query shape still yields empty `items`.

All-day continuous HR is carried in `band_data` detail responses as `data_hr`.
Synced days archive under `band-data/`; older empty `heart-rate/` files from the
hollow endpoint may remain on disk as historical evidence and are not deleted.

Implications:

- M2 decodes `data_hr` into `heart_rate_samples` (UTC midnight + minute index;
  omit sentinel `254`; keep BPM in 30–220). Workout detail HR stays in
  `activity_samples`.
- Deduplication between band and workout HR remains **unknown**.
- Prefer workout detail HR for in-session analytics; use band HR for all-day
  continuous coverage.

## Units

| Field group | Status |
|---|---|
| `run_time`, detail HR `dt` | seconds (**live**) |
| `trackid`, `end_time` | Unix seconds (**live**) |
| continuous HR bounds (`/heartRate`) | Unix **milliseconds** (**live**, hollow) |
| `band_data` `from_date` / `to_date` | calendar `YYYY-MM-DD` (**live**) |
| heart-rate values (workout) | BPM (**live**, matches summary) |
| `data_hr` blob | base64; **live** 1440×uint8 BPM/min, sentinel `254`; OSS short pairs **candidate** elsewhere |
| `dis`, climb distances | numeric strings; meters **candidate** / **unverified** |
| `calorie` | numeric string; unit **unverified** |
| `avg_pace`, cadence/frequency | **unverified** |
| `te`, `exercise_load` | Zepp proprietary; keep separate from local load |

## Missing data and limitations

- `/heartRate` returns empty `items` with the web `appname` token used in M1;
  sync uses `band_data` instead.
- Indoor activities omit GPS series; all sample columns must be nullable.
- History mixes strings, ints, and sentinels (`-1`, `0`, `""`).
- Only nine activity details were pulled (`--from 2026-07-01`); most history
  rows are summary-only until a wider detail sync.
- Sleep, steps (daily), stress, SpO2, and daily band summaries are not fetched
  by M1.
- Zepp OS `subType` labels do not safely map to every live `type` on this
  account.

## Provisional normalized schema for M2

Refine from live evidence; unknowns stay nullable and retain `raw_file`.

**Implemented (this cut):** `activities` and `activity_samples` are loaded by
`fitness normalize` from `activity-lists/` and `activity-details/`. Band-data
continuous HR (`data_hr` → `heart_rate_samples`) is loaded from `band-data/`.

### `activities` *(implemented)*

`activity_id` (`trackid`), raw `sport_type` (`type`), start (`trackid` epoch),
end (`end_time`), duration (`run_time`), distance (`dis`), calories, HR summary
(`avg`/`max`/`min`), pace/cadence when present, elevation fields when present,
`te` / `exercise_load` as Zepp-provided load, `source`, `bind_device`,
`raw_file`.

### `activity_samples` *(implemented)*

`activity_id`, elapsed seconds, HR (decoded from detail `heart_rate`), optional
lat/lon/altitude/pace/cadence when those series are non-empty, `raw_file`.

### `heart_rate_samples` *(implemented — band only)*

`recorded_at` (UTC), `hr_bpm`, `source` (`'band'`), `raw_file`, `content_sha256`.
Populated from `band-data/YYYY-MM-DD.json` via base64 `data_hr` decode (1440
uint8/min; omit `254`; 30–220 BPM). Unchanged files skipped by SHA-256;
changed files replace rows for that `raw_file`. Workout HR is not stored here.

### `daily_metrics`

Defer until a daily raw source with non-empty payloads exists.

## Evidence

- Live archives: `data/raw/activity-lists/`, `activity-details/`, `band-data/`
  (and legacy empty `heart-rate/`; gitignored; local only)
- [Zepp OS workout `subType` table](https://docs.zepp.com/docs/guides/workout-extension/quick-start/)
  (candidate labels only)
- [Roland Szabó exporter notes](https://rolandszabo.com/posts/export-mi-fit-and-zepp-workout-data/)
- [`m4ary/zepp-health-cli` endpoint inventory](https://github.com/m4ary/zepp-health-cli)
- Implementation: `services/zepp-importer/src/fitness/endpoints.py`, `client.py`
