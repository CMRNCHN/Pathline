from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any
from urllib.request import urlopen

from runtime.state.models import CallEvent
from replay.replay_mode import replay_trace

_TEXT_PREVIEW_LIMIT = 96


def build_session_snapshot(
    *,
    target: str,
    started_at: float | None,
    ended_at: float,
    manual_mode: bool,
    events: Sequence[CallEvent | Mapping[str, object]],
    graph: Mapping[str, object],
    queue_metrics: Mapping[str, object] | None,
    error: str | None,
) -> dict[str, Any]:
    event_dicts = [_coerce_event_dict(event, seq=index + 1) for index, event in enumerate(events)]
    action_events = [event for event in event_dicts if event["kind"] == "action"]
    first_event = event_dicts[0] if event_dicts else None
    last_event = event_dicts[-1] if event_dicts else None
    duration_ms = None
    if started_at is not None:
        duration_ms = max(0, int((ended_at - started_at) * 1000))
    return {
        "target": target,
        "started_at": started_at,
        "ended_at": ended_at,
        "duration_ms": duration_ms,
        "manual_mode": manual_mode,
        "event_count": len(event_dicts),
        "events": event_dicts,
        "graph_node_count": len(graph),
        "last_action": action_events[-1]["text"] if action_events else None,
        "first_event_t_ms": first_event["t_ms"] if first_event else None,
        "last_event_t_ms": last_event["t_ms"] if last_event else None,
        "queue": dict(queue_metrics) if queue_metrics is not None else None,
        "error": error,
    }


def inspect_replay_artifact(
    trace_source: str | Path | Sequence[Mapping[str, object] | CallEvent],
) -> dict[str, Any]:
    result = replay_trace(trace_source)
    chronology = build_event_chronology(result.events)
    timestamps = [event.t_ms for event in result.events]
    prompt_texts = [event.text for event in result.events if event.kind == "prompt"]
    action_texts = [event.text for event in result.events if event.kind == "action"]
    gap_values = [entry["delta_ms"] for entry in chronology[1:]]
    notes: list[str] = []
    if timestamps != sorted(timestamps):
        notes.append("non_monotonic_event_timeline")
    return {
        "source": _trace_source_payload(trace_source),
        "summary": {
            "event_count": result.summary["event_count"],
            "prompt_count": result.summary["prompt_count"],
            "action_count": result.summary["action_count"],
            "node_count": result.summary["node_count"],
            "root_prompts": list(result.summary["root_prompts"]),
            "duration_ms": max(timestamps) if timestamps else 0,
            "first_prompt": prompt_texts[0] if prompt_texts else None,
            "last_prompt": prompt_texts[-1] if prompt_texts else None,
            "unique_actions": sorted(set(action_texts)),
            "dtmf_path": [
                action.split(":", 1)[1]
                for action in action_texts
                if action.startswith("dtmf:")
            ],
            "largest_gap_ms": max(gap_values, default=0),
            "notes": notes,
        },
        "chronology": chronology,
        "report_preview": result.report.text.splitlines()[:12],
    }


def build_event_chronology(
    events: Sequence[CallEvent | Mapping[str, object]],
) -> list[dict[str, Any]]:
    chronology: list[dict[str, Any]] = []
    previous_t_ms: int | None = None
    for index, event in enumerate(events, start=1):
        payload = _coerce_event_dict(event, seq=index)
        delta_ms = 0 if previous_t_ms is None else payload["t_ms"] - previous_t_ms
        chronology.append(
            {
                "seq": index,
                "kind": payload["kind"],
                "t_ms": payload["t_ms"],
                "delta_ms": delta_ms,
                "text": payload["text"],
                "text_preview": _safe_preview(payload["text"]),
            }
        )
        previous_t_ms = payload["t_ms"]
    return chronology


def build_runtime_diagnostics(
    runtime_metrics: Mapping[str, object],
    *,
    active_session_snapshot: Mapping[str, object] | None = None,
) -> dict[str, Any]:
    startup = _mapping(runtime_metrics.get("startup"))
    runtime = _mapping(runtime_metrics.get("runtime"))
    session = _mapping(runtime_metrics.get("session"))
    stream_server = _mapping(runtime_metrics.get("stream_server"))
    replay_visibility = _mapping(runtime_metrics.get("replay_visibility"))
    staleness = _mapping(runtime_metrics.get("staleness"))
    last_session = _mapping(runtime_metrics.get("last_session"))
    session_snapshot = _mapping(active_session_snapshot) if active_session_snapshot else last_session

    lifecycle_events = [_mapping(item) for item in _list(stream_server.get("lifecycle_events"))]
    lifecycle_counts = Counter(
        f"{event.get('endpoint')}:{event.get('phase')}" for event in lifecycle_events
    )
    first_prompt = _first_session_event(session_snapshot, kind="prompt")
    first_action = _first_session_event(session_snapshot, kind="action")
    session_started_at = _float_or_none(session_snapshot.get("started_at"))
    stream_connected_at = _float_or_none(stream_server.get("last_stream_connected_at"))

    return {
        "summary": {
            "session_active": bool(session.get("is_running")),
            "session_target": session.get("target") or session_snapshot.get("target"),
            "session_event_count": session_snapshot.get("event_count", 0),
            "runtime_checkpoint_count": runtime.get("checkpoint_count", 0),
            "cleanup_count": runtime.get("cleanup_count", 0),
            "lifecycle_event_count": len(lifecycle_events),
            "stale_runtime": bool(staleness.get("is_stale")),
        },
        "queue_visibility": {
            "session_queue": session.get("queue") or session_snapshot.get("queue"),
            "last_checkpoint": runtime.get("last_checkpoint"),
        },
        "websocket_lifecycle": {
            "counts": dict(sorted(lifecycle_counts.items())),
            "last_stream_disconnect_reason": stream_server.get("last_stream_disconnect_reason"),
            "last_stream_close_code": stream_server.get("last_stream_close_code"),
            "last_listen_disconnect_reason": stream_server.get("last_listen_disconnect_reason"),
            "last_listen_close_code": stream_server.get("last_listen_close_code"),
            "recent": lifecycle_events[-10:],
        },
        "replay_diagnostics": {
            "artifact_summary": {
                "reports": replay_visibility.get("reports"),
                "recordings": replay_visibility.get("recordings"),
                "replays": replay_visibility.get("replays"),
                "snapshots": replay_visibility.get("snapshots"),
                "recording_artifacts": replay_visibility.get("recording_artifacts"),
            },
            "session": _session_diagnostics_payload(session_snapshot),
        },
        "correlation": {
            "startup_to_gui_ready_ms": _startup_stage_t_ms(startup, "gui.ready"),
            "session_start_to_first_prompt_ms": _event_t_ms(first_prompt),
            "session_start_to_first_action_ms": _event_t_ms(first_action),
            "stream_connect_to_first_prompt_ms": _absolute_delta_ms(
                session_started_at=session_started_at,
                event_t_ms=_event_t_ms(first_prompt),
                reference_ts=stream_connected_at,
            ),
            "session_duration_ms": session_snapshot.get("duration_ms"),
            "last_activity_at": staleness.get("last_activity_at"),
            "idle_for_s": staleness.get("idle_for_s"),
        },
        "timeline": _merged_runtime_timeline(
            startup_events=_list(startup.get("events")),
            runtime_checkpoints=_list(runtime.get("checkpoints")),
            lifecycle_events=lifecycle_events,
            session_snapshot=session_snapshot,
        ),
    }


def load_runtime_payload(
    *,
    metrics_path: Path | None = None,
    runtime_url: str | None = None,
) -> dict[str, Any]:
    if metrics_path is not None:
        return json.loads(metrics_path.read_text(encoding="utf-8"))
    if runtime_url is not None:
        with urlopen(runtime_url) as response:  # noqa: S310
            return json.loads(response.read().decode("utf-8"))
    raise ValueError("either metrics_path or runtime_url is required")


def format_replay_inspection_text(payload: Mapping[str, object]) -> str:
    summary = _mapping(payload.get("summary"))
    chronology = _list(payload.get("chronology"))
    lines = [
        "Replay inspection",
        f"- events: {summary.get('event_count', 0)}",
        f"- prompts: {summary.get('prompt_count', 0)}",
        f"- actions: {summary.get('action_count', 0)}",
        f"- nodes: {summary.get('node_count', 0)}",
        f"- duration_ms: {summary.get('duration_ms', 0)}",
    ]
    if summary.get("dtmf_path"):
        lines.append(f"- dtmf_path: {','.join(_list(summary.get('dtmf_path')))}")
    if summary.get("first_prompt"):
        lines.append(f"- first_prompt: {_safe_preview(str(summary['first_prompt']))}")
    if summary.get("last_prompt"):
        lines.append(f"- last_prompt: {_safe_preview(str(summary['last_prompt']))}")
    if chronology:
        lines.append("- chronology:")
        for entry in chronology[:10]:
            payload_entry = _mapping(entry)
            lines.append(
                "  "
                + f"{int(payload_entry.get('seq', 0)):02d} "
                + f"{int(payload_entry.get('t_ms', 0)):>5}ms "
                + f"Δ{int(payload_entry.get('delta_ms', 0)):>4} "
                + f"{payload_entry.get('kind')}: {payload_entry.get('text_preview')}"
            )
    return "\n".join(lines)


def format_runtime_diagnostics_text(payload: Mapping[str, object]) -> str:
    summary = _mapping(payload.get("summary"))
    queue_visibility = _mapping(payload.get("queue_visibility"))
    websocket_lifecycle = _mapping(payload.get("websocket_lifecycle"))
    correlation = _mapping(payload.get("correlation"))
    replay_diagnostics = _mapping(payload.get("replay_diagnostics"))
    session_payload = _mapping(replay_diagnostics.get("session"))
    lines = [
        "Runtime diagnostics",
        f"- session_active: {summary.get('session_active')}",
        f"- session_target: {summary.get('session_target') or '<none>'}",
        f"- session_events: {summary.get('session_event_count', 0)}",
        f"- runtime_checkpoints: {summary.get('runtime_checkpoint_count', 0)}",
        f"- cleanup_count: {summary.get('cleanup_count', 0)}",
        f"- stale_runtime: {summary.get('stale_runtime')}",
        f"- idle_for_s: {correlation.get('idle_for_s')}",
    ]
    queue = _mapping(queue_visibility.get("session_queue"))
    if queue:
        lines.append(
            "- queue: "
            + f"depth={queue.get('current_depth')} max={queue.get('max_depth_seen')} "
            + f"puts={queue.get('puts_total')} gets={queue.get('gets_total')}"
        )
    lifecycle_counts = _mapping(websocket_lifecycle.get("counts"))
    if lifecycle_counts:
        lines.append("- websocket_counts:")
        for key in sorted(lifecycle_counts):
            lines.append(f"  {key}={lifecycle_counts[key]}")
    if session_payload:
        lines.append(
            "- session: "
            + f"duration_ms={session_payload.get('duration_ms')} "
            + f"graph_nodes={session_payload.get('graph_node_count')} "
            + f"error={session_payload.get('error') or '<none>'}"
        )
    timeline = _list(payload.get("timeline"))
    if timeline:
        lines.append("- timeline:")
        for entry in timeline[:12]:
            payload_entry = _mapping(entry)
            marker = (
                payload_entry.get("marker")
                or payload_entry.get("stage")
                or payload_entry.get("phase")
                or payload_entry.get("kind")
            )
            detail = payload_entry.get("detail") or payload_entry.get("text_preview") or ""
            lines.append(f"  {payload_entry.get('source', 'event'):>18} {marker}: {detail}".rstrip())
    return "\n".join(lines)


def _merged_runtime_timeline(
    *,
    startup_events: Sequence[object],
    runtime_checkpoints: Sequence[object],
    lifecycle_events: Sequence[Mapping[str, object]],
    session_snapshot: Mapping[str, object],
) -> list[dict[str, Any]]:
    timeline: list[dict[str, Any]] = []
    for event in startup_events:
        payload = _mapping(event)
        timeline.append(
            {
                "source": "startup",
                "ts": payload.get("ts"),
                "marker": payload.get("stage"),
                "detail": payload.get("detail", ""),
                "t_ms": payload.get("t_ms"),
            }
        )
    for checkpoint in runtime_checkpoints:
        payload = _mapping(checkpoint)
        timeline.append(
            {
                "source": "checkpoint",
                "ts": payload.get("ts"),
                "marker": payload.get("stage"),
                "detail": payload.get("detail", ""),
                "category": payload.get("category"),
                "t_ms": payload.get("t_ms"),
            }
        )
    for event in lifecycle_events:
        timeline.append(
            {
                "source": "websocket",
                "ts": event.get("ts"),
                "marker": f"{event.get('endpoint')}:{event.get('phase')}",
                "detail": "",
                "t_ms": event.get("uptime_ms"),
            }
        )
    session_started_at = _float_or_none(session_snapshot.get("started_at"))
    for event in _list(session_snapshot.get("events")):
        payload = _mapping(event)
        event_t_ms = _event_t_ms(payload)
        event_ts = None
        if session_started_at is not None and event_t_ms is not None:
            event_ts = session_started_at + (event_t_ms / 1000.0)
        timeline.append(
            {
                "source": "session_event",
                "ts": event_ts,
                "marker": payload.get("kind"),
                "detail": _safe_preview(str(payload.get("text", ""))),
                "t_ms": event_t_ms,
            }
        )
    return sorted(
        timeline,
        key=lambda item: (
            item.get("ts") is None,
            float(item.get("ts") or 0.0),
            str(item.get("source")),
            str(item.get("marker")),
        ),
    )


def _session_diagnostics_payload(session_snapshot: Mapping[str, object]) -> dict[str, Any]:
    if not session_snapshot:
        return {}
    return {
        "target": session_snapshot.get("target"),
        "duration_ms": session_snapshot.get("duration_ms"),
        "manual_mode": session_snapshot.get("manual_mode"),
        "graph_node_count": session_snapshot.get("graph_node_count"),
        "queue": session_snapshot.get("queue"),
        "error": session_snapshot.get("error"),
        "event_count": session_snapshot.get("event_count"),
        "chronology": build_event_chronology(_list(session_snapshot.get("events"))),
    }


def _startup_stage_t_ms(startup: Mapping[str, object], stage: str) -> int | None:
    for event in _list(startup.get("events")):
        payload = _mapping(event)
        if payload.get("stage") == stage:
            return _event_t_ms(payload)
    return None


def _first_session_event(
    session_snapshot: Mapping[str, object],
    *,
    kind: str,
) -> Mapping[str, object] | None:
    for event in _list(session_snapshot.get("events")):
        payload = _mapping(event)
        if payload.get("kind") == kind:
            return payload
    return None


def _absolute_delta_ms(
    *,
    session_started_at: float | None,
    event_t_ms: int | None,
    reference_ts: float | None,
) -> int | None:
    if session_started_at is None or event_t_ms is None or reference_ts is None:
        return None
    return int(((session_started_at + (event_t_ms / 1000.0)) - reference_ts) * 1000)


def _event_t_ms(event: Mapping[str, object] | None) -> int | None:
    if event is None:
        return None
    value = event.get("t_ms")
    if isinstance(value, (int, float)):
        return int(value)
    return None


def _coerce_event_dict(
    event: CallEvent | Mapping[str, object],
    *,
    seq: int,
) -> dict[str, Any]:
    if isinstance(event, CallEvent):
        payload = {"kind": event.kind, "text": event.text, "t_ms": event.t_ms}
    else:
        payload = {
            "kind": str(event.get("kind", "")),
            "text": str(event.get("text", "")),
            "t_ms": int(event.get("t_ms", 0)),
        }
    payload["seq"] = seq
    return payload


def _trace_source_payload(
    trace_source: str | Path | Sequence[Mapping[str, object] | CallEvent],
) -> dict[str, Any]:
    if isinstance(trace_source, (str, Path)):
        path = Path(trace_source).expanduser()
        stat = path.stat()
        return {
            "path": str(path),
            "name": path.name,
            "size_bytes": stat.st_size,
            "updated_at": stat.st_mtime,
        }
    return {"path": None, "name": "in_memory_events", "size_bytes": None, "updated_at": None}


def _safe_preview(text: str) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= _TEXT_PREVIEW_LIMIT:
        return normalized
    return normalized[: _TEXT_PREVIEW_LIMIT - 1].rstrip() + "…"


def _float_or_none(value: object) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _list(value: object) -> list[object]:
    if isinstance(value, list):
        return value
    return []


def _mapping(value: object) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}


# New service API — also importable directly from replay.inspection_service.
# Legacy functions above remain unchanged for backwards compatibility.
try:  # noqa: E402
    from replay.inspection_service import (
        InspectionService,
        build_inspection_report,
    )
except ModuleNotFoundError:  # temporary recovery shim
    InspectionService = None

    def build_inspection_report(*args, **kwargs):
        raise NotImplementedError(
            "replay.inspection_service has not been restored yet"
        )

__all__ = [
    # legacy
    "build_event_chronology",
    "build_runtime_diagnostics",
    "build_session_snapshot",
    "format_replay_inspection_text",
    "format_runtime_diagnostics_text",
    "inspect_replay_artifact",
    "load_runtime_payload",
    # new service API
    "InspectionService",
    "build_inspection_report",
]