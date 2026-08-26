from __future__ import annotations

from datetime import datetime
from typing import Optional

import typer

from fitness.archive import RawArchive
from fitness.client import ZeppAuthError, ZeppClient
from fitness.config import ConfigError, credentials_ready, load_settings, require_credentials
from fitness.normalize.load import run_normalize
from fitness.sync import SyncOptions, run_sync

app = typer.Typer(add_completion=False, no_args_is_help=True)


@app.callback()
def main() -> None:
    """Local-first Zepp data importer."""


@app.command("status")
def status_cmd() -> None:
    settings = load_settings()
    archive = RawArchive(settings.data_raw_dir)
    typer.echo(f"host: {settings.zepp_host}")
    typer.echo(f"region: {settings.zepp_region}")
    typer.echo(f"raw_dir: {settings.data_raw_dir}")
    typer.echo(
        f"duckdb: {settings.duckdb_path} ({'yes' if settings.duckdb_path.exists() else 'missing'})"
    )
    typer.echo(f"credentials: {'ok' if credentials_ready(settings) else 'missing'}")
    typer.echo(f"raw_files: {archive.count_files()}")
    meta = archive.read_meta()
    finished = None
    if meta:
        finished = meta.get("finished_at") or meta.get("completed_at")
    typer.echo(f"last_sync: {finished if finished else 'never'}")


def _run_sync_cmd(from_: Optional[str], activity: Optional[str]) -> None:
    settings = load_settings()
    try:
        require_credentials(settings)
    except ConfigError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    from_date = datetime.strptime(from_, "%Y-%m-%d").date() if from_ else None
    archive = RawArchive(settings.data_raw_dir)
    assert settings.zepp_app_token and settings.zepp_user_id
    client = ZeppClient(settings.zepp_host, settings.zepp_app_token, settings.zepp_user_id)
    try:
        report = run_sync(
            settings,
            client,
            archive,
            SyncOptions(from_date=from_date, activity_id=activity),
        )
    except ZeppAuthError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc
    finally:
        client.close()
    typer.echo(report)
    if report.errors:
        raise typer.Exit(code=1)


@app.command("sync")
def sync_cmd(
    from_: Optional[str] = typer.Option(None, "--from", help="YYYY-MM-DD"),
    activity: Optional[str] = typer.Option(None, "--activity", help="Zepp track id"),
) -> None:
    _run_sync_cmd(from_, activity)


@app.command("import")
def import_cmd(
    from_: Optional[str] = typer.Option(None, "--from"),
    activity: Optional[str] = typer.Option(None, "--activity"),
) -> None:
    """Alias of sync for Milestone 1."""
    _run_sync_cmd(from_, activity)


@app.command("normalize")
def normalize_cmd() -> None:
    """Load raw archives into local DuckDB (offline)."""
    settings = load_settings()
    report = run_normalize(settings.data_raw_dir, settings.duckdb_path)
    typer.echo(report)
    if report.errors:
        raise typer.Exit(code=1)
