from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fitness_api.config import Settings
from fitness_api.db import duckdb_available


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or Settings()
    app = FastAPI(title="Zepp Training Analytics API")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[app_settings.cors_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health() -> dict[str, str | bool]:
        return {
            "status": "ok",
            "duckdb": duckdb_available(app_settings.duckdb_path),
        }

    return app


app = create_app()
