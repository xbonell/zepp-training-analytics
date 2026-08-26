# Zepp Training Analytics

Local-first fitness analytics for Amazfit T-Rex Pro / Zepp (Global/EU).

Milestone 1 archives request-faithful Zepp Cloud responses locally. Endpoint and
field behavior for the T-Rex Pro remains **unverified** until the first live sync.

## Setup

```bash
git clone <repository-url>
cd zepp-training-analytics
cd services/zepp-importer
uv sync --extra dev
cp ../../.env.example ../../.env
# edit ../../.env — see ../../docs/zepp-auth.md
uv run fitness status
uv run fitness sync --from 2025-01-01
```

`fitness status` works without credentials. `fitness sync` requires
`ZEPP_APP_TOKEN` and `ZEPP_USER_ID`; it writes raw responses under `data/raw/`
by default. Never commit `.env`, captures, or health data.

## Documentation

- [Architecture and milestone boundaries](docs/architecture.md)
- [Zepp authentication](docs/zepp-auth.md)
- [Provisional Zepp data model](docs/zepp-data-model.md)
- [Future heart-rate zone models](docs/hr-zone-models.md)
- [Sanitized examples policy](docs/examples/README.md)
