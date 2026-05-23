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


# ── inspect-session text formatter ───────────────────────────────────────────

def _format_inspection_text(report: "ReplayInspectionReport") -> str:  # noqa: F821
    """Render a ReplayInspectionReport as operator-friendly text."""
    lines: list[str] = []

    # Header
    lines.append("Replay inspection report")
    lines.append(f"  schema_version: {report.schema_version}")
    lines.append("")

    # Identity
    id_ = report.identity
    lines.append("Identity")
    lines.append(f"  session_id: {id_.session_id or '(none)'}")
    lines.append(f"  call_sid:   {id_.call_sid or '(none)'}")
    lines.append(f"  source:     {id_.source_kind or '(none)'}")
    if id_.source_path:
        lines.append(f"  source_path: {id_.source_path}")
    lines.append("")

    # Artifact availability
    avail = report.artifact_availability
    if avail.missing:
        lines.append(f"Missing artifacts: {', '.join(avail.missing)}")
    else:
        lines.append("All artifacts available")
    lines.append("")

    # Summary
    s = report.summary
    lines.append("Summary")
    lines.append(f"  event_count:   {s.event_count}")
    lines.append(f"  prompt_count:  {s.prompt_count}")
    lines.append(f"  action_count:  {s.action_count}")
    if s.first_prompt:
        lines.append(f"  first_prompt:  {s.first_prompt}")
    if s.last_action:
        lines.append(f"  last_action:   {s.last_action}")
    if s.largest_gap_ms is not None:
        lines.append(f"  largest_gap_ms: {s.largest_gap_ms}")
    lines.append("")

    # Path
    p = report.path
    if p.dtmf_path:
        lines.append(f"  dtmf_path: {' → '.join(p.dtmf_path)}")
    if p.visited_nodes:
        lines.append(f"  visited_nodes: {len(p.visited_nodes)}")
    lines.append("")

    # Anomalies
    if report.anomalies:
        lines.append(f"Anomalies ({len(report.anomalies)})")
        for a in report.anomalies:
            lines.append(f"  [{a.severity.upper()}] {a.code}: {a.explanation}")
        lines.append("")

    # Next steps
    if report.next_steps:
        lines.append(f"Next steps ({len(report.next_steps)})")
        for ns in report.next_steps:
            lines.append(f"  - {ns.action}")
            lines.append(f"    rationale: {ns.rationale}")
        lines.append("")

    return "\n".join(lines)


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


@app.command("inspect-session")
def inspect_session(
    session_id: str = typer.Option(..., "--session-id"),
    output_format: str = typer.Option("text", "--format"),
) -> None:
    """Inspect a replay session by session ID using the canonical inspection report."""
    from replay.inspection_service import build_inspection_report

    if output_format not in ("text", "json"):
        typer.echo(f"Unsupported format: {output_format}")
        raise typer.Exit(code=2)

    report = build_inspection_report(session_id)

    if output_format == "json":
        typer.echo(report.to_json(), nl=False)
        return

    typer.echo(_format_inspection_text(report))


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
