from __future__ import annotations

import json
import platform
import sqlite3
import time
from pathlib import Path
from typing import Annotated

import typer

from salvage import __version__
from salvage.audit.ledger import verify_ledger
from salvage.config import Settings
from salvage.demo import run_demo, save_evaluation, seed_demo
from salvage.evaluation.runner import write_artifacts
from salvage.execution.worker import process_all, process_next
from salvage.persistence.db import migrate as apply_migrations

app = typer.Typer(no_args_is_help=True, help="Salvage deterministic recovery prototype")


@app.command()
def doctor() -> None:
    """Validate the offline environment without external writes."""
    settings = Settings()
    settings.assert_safe()
    typer.echo(f"Salvage {__version__}")
    typer.echo(f"Python {platform.python_version()} · SQLite {sqlite3.sqlite_version}")
    typer.echo(f"Mode {settings.mode} · Advisor {settings.llm}")
    typer.echo(f"Database {settings.database_path}")
    typer.echo("Live mode: unavailable by design")


@app.command("migrate")
def migrate_command() -> None:
    """Apply checked SQLite migrations."""
    settings = Settings()
    applied = apply_migrations(settings.database_path)
    typer.echo("Applied: " + (", ".join(applied) if applied else "schema already current"))


@app.command()
def demo(reset: bool = typer.Option(True, help="Rebuild the deterministic demo database.")) -> None:
    """Run the complete provider-free demo and evaluation."""
    result = run_demo(Settings(), reset=reset)
    typer.echo(json.dumps(result, indent=2))


@app.command()
def seed() -> None:
    """Seed synthetic Test Mode-shaped events without network access."""
    count = seed_demo(Settings())
    typer.echo(f"Seeded {count} new synthetic events")


@app.command()
def work(
    loop: bool = typer.Option(False, help="Keep leasing jobs until interrupted."),
    interval: float = typer.Option(1.0, min=0.1, max=30.0),
) -> None:
    """Process durable jobs through Rulebook and Gatekeeper."""
    settings = Settings()
    if not loop:
        typer.echo(f"Processed {len(process_all(settings))} jobs")
        return
    while True:
        result = process_next(settings)
        if result is None:
            time.sleep(interval)


@app.command("eval")
def evaluate(seed: int = 20260829, count: int = 500) -> None:
    """Run the same-batch counterfactual evaluation."""
    result = save_evaluation(Settings(), seed=seed, count=count)
    typer.echo(json.dumps(result, indent=2))


@app.command()
def report(
    source: Annotated[Path, typer.Argument(exists=True, readable=True)] = Path(
        "reports/results.json"
    ),
) -> None:
    """Render the static report from an existing result object."""
    result = json.loads(source.read_text(encoding="utf-8"))
    _, html_path = write_artifacts(result, source.parent)
    typer.echo(str(html_path))


@app.command("verify-ledger")
def verify_ledger_command() -> None:
    """Verify the append-only-by-contract hash chain."""
    status = verify_ledger(Settings().database_path)
    typer.echo(
        json.dumps(
            {
                "valid": status.valid,
                "entry_count": status.entry_count,
                "final_hash": status.final_hash,
                "first_mismatch_sequence": status.first_mismatch_sequence,
            },
            indent=2,
        )
    )
    if not status.valid:
        raise typer.Exit(code=1)


@app.command()
def serve(host: str = "0.0.0.0", port: int = 8000) -> None:  # noqa: S104
    """Serve the API and built read-only console."""
    import uvicorn

    uvicorn.run("salvage.api.app:app", host=host, port=port)


if __name__ == "__main__":
    app()
