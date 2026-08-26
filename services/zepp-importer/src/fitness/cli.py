import typer

app = typer.Typer(add_completion=False, no_args_is_help=True)


@app.callback()
def main() -> None:
    """Zepp training analytics CLI."""


@app.command("status")
def status_cmd() -> None:
    typer.echo("fitness status: package OK (CLI incomplete)")
