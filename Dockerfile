# Dockerfile (repo root)
FROM python:3.12-slim

WORKDIR /app
RUN pip install --no-cache-dir uv

COPY services/zepp-importer /app/services/zepp-importer
COPY services/api /app/services/api

WORKDIR /app/services/api
RUN uv sync --no-dev

ENV DUCKDB_PATH=/data/zepp.duckdb \
    PROFILE_PATH=/data/profile.json \
    ZEPP_ENV_PATH=/data/zepp.env \
    DATA_RAW_DIR=/data/raw \
    SYNC_JOB_PATH=/data/_meta/sync_job.json \
    API_CORS_ORIGIN=https://training.xbonell.com

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "fitness_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
