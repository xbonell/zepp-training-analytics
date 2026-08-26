# Sanitized payload examples

Live sync archives exist locally under `data/raw/` (gitignored). This directory
still has **no** committed examples. Synthetic test fixtures are not live
evidence. Schema notes from the live pull live in `docs/zepp-data-model.md`.

Examples may be added only after removing or replacing:

- `apptoken`, user IDs, device identifiers, and account/profile data;
- GPS coordinates, location names, routes, and source URLs containing IDs;
- exact timestamps and any identifiers derived from timestamps;
- free text and other values that could identify a person.

Keep field names, nesting, JSON types, nulls, and representative array shapes
when safe. Clearly label whether an example is synthetic or sanitized live data,
which endpoint produced it, and which values were altered. Never copy raw
archives directly into this directory.
