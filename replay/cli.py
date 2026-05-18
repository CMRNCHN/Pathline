from __future__ import annotations

import json
from pathlib import Path

import typer

from replay.inspection import (
    build_runtime_diagnostics,
    format_replay_inspection_text,
    format_runtime_diagnostics_text,
    inspect_replay_artifact,
    load_runtime_payload,
)
from replay.replay_mode import replay_trace

app = typer.Typer(help="Replay and diagnostics commands")


@app.command()
def replay(
    trace_path: Path = typer.Option(..., "--trace-path"),
) -> None:
    result = replay_trace(trace_path)
    typer.echo(f"Replayed {result.summary['event_count']} events")
    typer.echo(f"Mapped {result.summary['node_count']} IVR nodes")
    typer.echo(result.report.text)


@app.command("inspect-replay")
def inspect_replay(
    trace_path: Path = typer.Option(..., "--trace-path"),
    output_format: str = typer.Option("text", "--format"),
) -> None:
    if not trace_path.exists():
        typer.echo(f"Trace file not found: {trace_path}")
        raise typer.Exit(code=2)

    payload = inspect_replay_artifact(trace_path)
    if output_format == "json":
        typer.echo(json.dumps(payload, indent=2, sort_keys=True))
        return
    if output_format != "text":
        typer.echo(f"Unsupported format: {output_format}")
        raise typer.Exit(code=2)
    typer.echo(format_replay_inspection_text(payload))


@app.command("inspect-runtime")
def inspect_runtime(
    metrics_path: Path | None = typer.Option(None, "--metrics-path"),
    runtime_url: str | None = typer.Option(None, "--runtime-url"),
    output_format: str = typer.Option("text", "--format"),
) -> None:
    if metrics_path is not None and runtime_url is not None:
        typer.echo("Choose either --metrics-path or --runtime-url, not both.")
        raise typer.Exit(code=2)
    if metrics_path is None and runtime_url is None:
        runtime_url = "http://127.0.0.1:8080/api/runtime-diagnostics"
    if metrics_path is not None and not metrics_path.exists():
        typer.echo(f"Metrics file not found: {metrics_path}")
        raise typer.Exit(code=2)

    try:
        payload = load_runtime_payload(metrics_path=metrics_path, runtime_url=runtime_url)
    except Exception as exc:
        typer.echo(f"Unable to load runtime payload: {exc}")
        raise typer.Exit(code=1)

    diagnostics = payload
    if "summary" not in payload or "timeline" not in payload:
        diagnostics = build_runtime_diagnostics(payload)

    if output_format == "json":
        typer.echo(json.dumps(diagnostics, indent=2, sort_keys=True))
        return
    if output_format != "text":
        typer.echo(f"Unsupported format: {output_format}")
        raise typer.Exit(code=2)
    typer.echo(format_runtime_diagnostics_text(diagnostics))
