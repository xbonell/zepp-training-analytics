# Zepp Training Analytics

Local-first fitness analytics for Amazfit T-Rex Pro / Zepp (Global/EU).

Milestone 1: data discovery importer. See `docs/` after Task 8 completes setup docs.

```bash
cd services/zepp-importer
uv sync
cp ../../.env.example ../../.env
# fill ZEPP_APP_TOKEN and ZEPP_USER_ID — see docs/zepp-auth.md
uv run fitness status
```
