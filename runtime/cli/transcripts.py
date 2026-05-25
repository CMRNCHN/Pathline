from __future__ import annotations

import typer
import json
from tabulate import tabulate

from runtime.transcription.db import TranscriptDB

app = typer.Typer()


@app.command()
def search(
    query: str = typer.Option(..., help="Keyword to search in transcripts"),
    limit: int = typer.Option(20, help="Max results"),
):
    """Search call transcripts by keyword."""
    db = TranscriptDB()
    results = db.search_transcript(query, limit=limit)

    if not results:
        typer.echo("No results found.")
        return

    table_data = [
        [
            r["call_sid"][:12],
            r["customer_id"] or "—",
            r["segment_count"],
            f"{r['min_confidence']:.2f}",
            "✓" if r["requires_confirmation"] else "—",
            r["created_at"][:10],
        ]
        for r in results
    ]

    typer.echo(
        tabulate(
            table_data,
            headers=["Call SID", "Customer", "Segments", "Conf", "Review?", "Date"],
            tablefmt="simple",
        )
    )


@app.command()
def get(call_sid: str = typer.Argument(..., help="Call SID")):
    """Fetch full call details."""
    db = TranscriptDB()
    call = db.get_call(call_sid)

    if not call:
        typer.echo(f"Call {call_sid} not found.")
        return

    typer.echo(json.dumps(call, indent=2))


@app.command()
def recent(
    limit: int = typer.Option(10, help="Number of recent calls"),
    requires_review: bool = typer.Option(False, help="Only calls needing confirmation"),
):
    """List recent calls."""
    db = TranscriptDB()
    results = db.search_calls(
        requires_confirmation=requires_review if requires_review else None,
        limit=limit,
    )

    if not results:
        typer.echo("No calls found.")
        return

    table_data = [
        [
            r["call_sid"][:12],
            r["customer_id"] or "—",
            r["segment_count"],
            f"{r['min_confidence']:.2f}",
            "✓" if r["requires_confirmation"] else "—",
            r["created_at"][:19],
        ]
        for r in results
    ]

    typer.echo(
        tabulate(
            table_data,
            headers=["Call SID", "Customer", "Segments", "Conf", "Review?", "Created"],
            tablefmt="simple",
        )
    )


if __name__ == "__main__":
    app()
