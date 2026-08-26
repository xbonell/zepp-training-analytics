# Provisional Zepp data model

This document records reverse-engineered OSS evidence and the request shape
implemented in M1. Every endpoint, field, encoding, unit, and T-Rex Pro behavior
below is **unverified** until the first successful live sync.

## Request model

The client sends these headers on every GET:

| Header | Value |
|---|---|
| `apptoken` | `ZEPP_APP_TOKEN` |
| `appPlatform` | `web` |
| `appname` | `com.xiaomi.hm.health` |

`ZEPP_USER_ID` is inserted into user-scoped paths. The regional base host is
configurable through `ZEPP_HOST`; the template default is
`api-mifit-us3.zepp.com`. Captured `api-mifit*.zepp.com` traffic is the authority
for an account's host. Host selection is **unverified** until first sync.

### Implemented endpoints

| Client method | Request |
|---|---|
| history | `GET /v1/sport/run/history.json` |
| next history page | same path with `?trackid=<data.next>` |
| activity detail | `GET /v1/sport/run/detail.json?trackid=<id>&source=<source>` |
| continuous HR | `GET /users/<ZEPP_USER_ID>/heartRate?start=YYYY-MM-DD&end=YYYY-MM-DD` |

The importer requests HR once per UTC calendar day with identical `start` and
`end` dates. Those parameter names and date semantics are **unverified**.

Future-only OSS evidence from `m4ary/zepp-health-cli` identifies
`GET /v2/watch/users/{id}/WatchSportStatistics/SPORT_LOAD`. M1 does not call it;
availability, parameters, payload, units, and T-Rex Pro support are
**unverified**.

## History pagination and timestamps

History responses are expected to contain `data.summary[]` and `data.next`.
The importer starts without a cursor, archives the response, and then uses a
positive integer `next` as the following request's `trackid`. It stops on a
missing/non-positive `next` or an empty summary.

OSS reports each summary `trackid` as the activity start time in Unix seconds.
M1 uses that claim to apply `--from` filtering to details; it does not rewrite
the source timestamp. Epoch unit, timezone behavior, uniqueness, ordering, and
T-Rex Pro semantics remain **unverified**.

## History summary fields

The following field names and JSON types are reported by the rolandsz exporter
model/example. Types describe the OSS payload, not a stable Zepp contract.
Every row is **unverified** on this device and account.

| Field | Reported JSON type |
|---|---|
| `trackid`, `source` | string |
| `dis`, `calorie`, `end_time`, `run_time` | string |
| `avg_pace`, `avg_frequency`, `avg_heart_rate` | string |
| `type` | integer |
| `location`, `city`, `forefoot_ratio`, `bind_device` | string |
| `max_pace`, `min_pace`, `version` | integer |
| `altitude_ascend`, `altitude_descend`, `total_step` | integer |
| `avg_stride_length`, `max_frequency` | integer |
| `max_altitude`, `min_altitude`, `lap_distance` | integer |
| `sync_to` | string |
| `distance_ascend`, `max_cadence`, `avg_cadence` | integer |
| `landing_time`, `flight_ratio` | integer |
| `climb_dis_descend`, `climb_dis_ascend_time`, `climb_dis_descend_time` | integer |
| `child_list` | string |
| `parent_trackid`, `max_heart_rate`, `min_heart_rate` | integer |
| `swolf`, `total_strokes`, `total_trips` | integer |
| `avg_stroke_speed`, `max_stroke_speed`, `avg_distance_per_stroke` | integer |
| `swim_pool_length`, `te`, `swim_style`, `unit` | integer |
| `add_info` | string |
| `sport_mode`, `downhill_num`, `downhill_max_altitude_desend` | integer |

Payloads may add, omit, null, or change the type of any field. The local
synthetic test fixture covers only `trackid`, `source`, `type`, `run_time`,
`avg_heart_rate`, `max_heart_rate`, and `app_name`; it is not live evidence.

The integer `type` and `sport_mode` mappings are unknown. No gym, run, cycling,
or other sport labels are assigned in M1.

## Detail series

OSS reports detail heart-rate and GPS series as compact strings or arrays where
the first value may be absolute and subsequent values delta-encoded. Field
spellings can vary (`heart_rate`/`heartrate` in reports). The importer preserves
the response bytes and performs no decoding.

**Investigate on live data:** exact keys, delimiters, sampling interval, reset
rules, signed deltas, coordinate scale/order, missing-value sentinels, alignment
between streams, and whether non-GPS activities still contain HR.

## Units

No unit is accepted as confirmed for the T-Rex Pro before live validation.

| Candidate field group | Unit/status |
|---|---|
| `dis`, `lap_distance`, climb distances | unknown / **unverified** |
| `run_time`, `end_time`, detail offsets | unknown / **unverified** |
| `calorie` | unknown / **unverified** |
| heart-rate values | unknown / **unverified** |
| pace, speed, cadence, frequency | unknown / **unverified** |
| altitude and ascent/descent | unknown / **unverified** |
| GPS coordinates | representation and scale unknown / **unverified** |
| `te`, `unit`, `sport_mode`, load | semantics unknown / **unverified** |

## Missing data and limitations

- No live credentials or T-Rex Pro payloads have validated this schema.
- Regional hosts and endpoint availability can differ by account.
- Indoor activities may omit GPS; all activity/sample columns must be nullable.
- History may omit fields or mix numeric strings, numbers, nulls, and empty
  strings.
- Continuous HR may overlap workout HR; a canonical deduplication rule is not
  yet known.
- M1 archives bytes but does not validate completeness or decode detail series.
- Training load, VO2 max, sleep, steps, stress, SpO2, and daily summaries are
  not fetched by M1.

## Provisional normalized schema for M2

This is a proposal only; unknowns stay nullable and retain a raw-file pointer.

### `activities`

`activity_id` (source `trackid`), raw `sport_type` integer, future analytical
category (**unknown**), start/end timestamps (**unverified**), duration,
distance, calories, HR summary, pace/cadence, elevation, optional Zepp-provided
training load, `source`, and `raw_file`.

### `activity_samples`

`activity_id`, sample index/time (**unknown**), HR, latitude, longitude,
altitude, speed/pace, cadence, cumulative distance, and `raw_file`. Every metric
is nullable because streams and sport capabilities vary.

### `heart_rate_samples`

Timestamp and HR value plus source (`continuous` or `workout`), activity ID when
known, and `raw_file`. Overlap priority and deduplication are **unknown**.

### `daily_metrics`

Date, timezone (**unknown**), and only daily measures supported by observed raw
data. Do not add sleep, steps, resting HR, stress, SpO2, or load columns merely
because other fitness platforms expose them.

## Evidence

- [Roland Szabó's exporter and payload discussion](https://rolandszabo.com/posts/export-mi-fit-and-zepp-workout-data/)
- [`m4ary/zepp-health-cli` endpoint inventory](https://github.com/m4ary/zepp-health-cli)
- The implementation in `services/zepp-importer/src/fitness/endpoints.py` and
  `client.py` is authoritative for what M1 actually requests.
