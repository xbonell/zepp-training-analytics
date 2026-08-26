# M3 final fix report

## Important findings resolved
- `scripts/dev.sh` uses Bash 3.2-compatible plain `wait`.
- Missing DuckDB returns actionable 503 responses from overview, activities, and activity detail; zones remain available with `source: none`.
- DuckDB `quantile_cont` HRmax and resolved API HRmax values are rounded to one decimal.
- Zone settings swatches use shared `zone-z*` CSS classes instead of API color keywords.
- Activity timestamps use the profile `display_timezone`, defaulting to `Europe/Madrid`.
- The purple favicon was replaced with a teal `Z` mark matching `--accent`.
- Production SQL suggested-HRmax behavior has DuckDB-backed regression coverage.

## Optional minors included
- `--zone-below` is visually distinct from `--zone-z1`.
- Activity detail uses settled requests and remains available when zones fail.

## Verification
- API: `uv run pytest -q` — 28 passed.
- Web: `npm test` — 28 passed, 8 files.
- Web build: `npm run build` — passed.
- Web lint: `./node_modules/.bin/oxlint` — passed with no findings.
- Script syntax: `/bin/bash -n scripts/dev.sh` — passed.
