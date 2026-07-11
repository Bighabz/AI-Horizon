"""Feed ingestion CLI.

Examples:
    python -m src.ingestion.run --dry-run
    python -m src.ingestion.run --dry-run --limit 5
    python -m src.ingestion.run --limit 10          # real: classifies + stores
"""

import logging
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from src.ingestion.pipeline import ingest_candidate, run_ingestion

app = typer.Typer(
    name="ingest",
    help="Pull articles from configured RSS/Atom feeds into the AI Horizon evidence pipeline.",
    add_completion=False,
)
console = Console()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@app.command()
def ingest(
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Fetch, normalize, and dedupe only. Prints what WOULD be ingested. "
        "Never calls Gemini and never writes to the database.",
    ),
    limit: Optional[int] = typer.Option(
        None, "--limit", "-n", help="Max number of NEW articles to process this run."
    ),
    feeds_file: Optional[Path] = typer.Option(
        None, "--feeds", help="Path to a feeds.json (defaults to src/ingestion/feeds.json)."
    ),
    no_db: bool = typer.Option(
        False, "--no-db", help="Skip PostgreSQL when loading existing URLs (dedupe against evidence_store.json only)."
    ),
):
    """Fetch configured feeds and ingest new articles into the evidence pipeline."""
    result = run_ingestion(feeds_path=feeds_file, limit=limit, include_db=not no_db)
    stats = result["stats"]
    new = result["new"]
    duplicates = result["duplicates"]

    console.print(
        f"\n[bold]Feeds:[/bold] {stats.feeds_fetched}/{stats.feeds_configured} fetched "
        f"({stats.feeds_failed} failed) | "
        f"[bold]Entries:[/bold] {stats.entries_fetched} fetched, {stats.entries_normalized} normalized | "
        f"[bold]Known URLs:[/bold] {result['existing_url_count']} | "
        f"[bold]Duplicates skipped:[/bold] {len(duplicates)} | "
        f"[bold]New:[/bold] {len(new)}"
        + (f" (capped by --limit {limit})" if limit is not None else "")
    )
    for error in stats.errors:
        console.print(f"[red]Feed error:[/red] {error}")

    if not new:
        console.print("[yellow]Nothing new to ingest.[/yellow]")
        raise typer.Exit(0)

    table = Table(title="New articles" + (" (dry run - not ingested)" if dry_run else ""))
    table.add_column("Feed", style="cyan", no_wrap=True)
    table.add_column("Title", style="bold", max_width=50)
    table.add_column("URL", max_width=60)
    table.add_column("Published", no_wrap=True)
    table.add_column("Content chars", justify="right")
    for candidate in new:
        table.add_row(
            candidate.feed_name,
            candidate.title[:120],
            candidate.source_url,
            candidate.published or "-",
            str(len(candidate.content)),
        )
    console.print(table)

    if dry_run:
        console.print(
            f"[green]Dry run:[/green] would ingest {len(new)} article(s). "
            "No Gemini calls made, no database writes."
        )
        raise typer.Exit(0)

    stored = 0
    skipped = 0
    for candidate in new:
        try:
            outcome = ingest_candidate(candidate)
        except Exception as e:
            skipped += 1
            console.print(f"[red]Failed:[/red] {candidate.source_url}: {e}")
            continue
        if outcome.get("stored"):
            stored += 1
            console.print(
                f"[green]Stored[/green] {outcome['artifact_id']} "
                f"({outcome.get('classification')}, confidence {outcome.get('confidence')}): "
                f"{candidate.title[:60]}"
            )
        else:
            skipped += 1
            console.print(
                f"[yellow]Skipped[/yellow] (not relevant): {candidate.source_url} - "
                f"{outcome.get('reason', '')}"
            )

    console.print(f"\n[bold]Done.[/bold] Stored {stored}, skipped {skipped}.")


if __name__ == "__main__":
    app()
