# Sanitized payload examples

No live Zepp payload examples are included in M1. T-Rex Pro fields remain
**unverified** until first sync, and synthetic test fixtures are not evidence of
the live API schema.

After a successful sync, examples may be added only after removing or replacing:

- `apptoken`, user IDs, device identifiers, and account/profile data;
- GPS coordinates, location names, routes, and source URLs containing IDs;
- exact timestamps and any identifiers derived from timestamps;
- free text and other values that could identify a person.

Keep field names, nesting, JSON types, nulls, and representative array shapes
when safe. Clearly label whether an example is synthetic or sanitized live data,
which endpoint produced it, and which values were altered. Never copy raw
archives directly into this directory.
