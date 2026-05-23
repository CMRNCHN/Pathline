"""
replay/inspection_service.py — Orchestrates bundle resolution and report construction.

Public entry point: ``inspect_session(session_id)`` returns a fully-populated
``ReplayInspectionReport``.

**Anomaly detection stub**
``detect_anomalies`` and ``generate_next_steps`` are imported from
``replay/anomaly_detection.py``.  That module is owned by Agent 3 and does not
exist yet.  Until Agent 3 wires in the real implementation, both calls are
replaced with the no-op lambda ``lambda report: []`` defined immediately below the
import block.  Search for "STUB" in this file to find the two call sites that
Agent 3 must update.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from replay.bundle_resolver import BundleResolver, ResolvedReplayBundle
from replay.inspection_models import (
    Anomaly,
    AnnotationSummary,
    ArtifactAvailabilitySection,
    BookmarkSummary,
    BookmarksAnnotationsSection,
    ChronologyEntry,
    ChronologySection,
    CorrelationSection,
    IdentitySection,
    MediaStatusSection,
    NextStep,
    PathSection,
    PathStep,
    ReplayInspectionReport,
    SessionMetadataSection,
    StateDiagnosticsSection,
    SummarySection,
)

if TYPE_CHECKING:
    from replay.bundle_resolver import BundleResolver as _BundleResolverT

# ---------------------------------------------------------------------------
# Anomaly-detection stub (Agent 3 wires in the real module here)
# ---------------------------------------------------------------------------
# STUB: replace the lambdas below once replay/anomaly_detection.py is merged.
# Agent 3 should import the real implementations and remove these overrides.
try:
    from replay.anomaly_detection import (  # type: ignore[import-not-found]
        detect_anomalies as _detect_anomalies,
        generate_next_steps as _generate_next_steps,
    )
except ImportError:  # pragma: no cover — removed once Agent 3 lands
    # STUB — anomaly_detection.py does not exist yet (owned by Agent 3).
    # Both stubs return empty lists so report construction is never blocked.
    _detect_anomalies: Callable[[ReplayInspectionReport], list[Anomaly]] = (  # type: ignore[no-redef]
        lambda report: []
    )
    _generate_next_steps: Callable[[ReplayInspectionReport], list[NextStep]] = (  # type: ignore[no-redef]
        lambda report: []
    )

# ---------------------------------------------------------------------------
# Event-type → chronology-kind mapping
# ---------------------------------------------------------------------------
# Maps the raw ``type`` field in replay events to the human-readable ``kind``
# used in ``ChronologyEntry``.  Unmapped types fall back to the raw type string.
_EVENT_KIND_MAP: dict[str, str] = {
    "TRANSCRIPT_FINAL": "prompt",
    "PROMPT_DETECTED": "prompt",
    "DTMF_SENT": "action",
    "SPEECH_SENT": "action",
    "CALL_STARTED": "call_started",
    "CALL_CONNECTED": "call_connected",
    "CALL_ENDED": "call_ended",
    "CALL_COMPLETED": "call_completed",
    "STATE_DISCOVERED": "state_discovered",
    "NODE_DISCOVERED": "node_discovered",
    "EDGE_DISCOVERED": "edge_discovered",
    "PATH_ADVANCED": "path_advanced",
    "ERROR_RAISED": "error",
}

_TEXT_PREVIEW_LIMIT = 96


def _safe_preview(text: str) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= _TEXT_PREVIEW_LIMIT:
        return normalized
    return normalized[: _TEXT_PREVIEW_LIMIT - 1].rstrip() + "…"


def _extract_event_text(raw_event: dict[str, Any]) -> str:
    """Return the most human-readable text snippet from a raw replay event."""
    payload = raw_event.get("payload") or {}
    event_type = raw_event.get("type", "")
    if event_type in ("TRANSCRIPT_FINAL", "PROMPT_DETECTED"):
        return str(payload.get("text") or "")
    if event_type == "DTMF_SENT":
        digits = payload.get("digits", "")
        return f"dtmf:{digits}" if digits else ""
    if event_type == "SPEECH_SENT":
        return str(payload.get("text") or payload.get("utterance") or "")
    if event_type in ("STATE_DISCOVERED", "NODE_DISCOVERED"):
        return str(payload.get("label") or payload.get("id") or "")
    if event_type == "PATH_ADVANCED":
        return str(payload.get("node_id") or "")
    if event_type == "ERROR_RAISED":
        return str(payload.get("message") or payload.get("error") or "")
    # Fallback: stringify first non-empty payload value
    for value in payload.values():
        if value:
            return str(value)
    return ""


def _build_chronology(raw_events: list[dict[str, Any]]) -> ChronologySection:
    """Build a ``ChronologySection`` from the ordered raw replay event stream."""
    entries: list[ChronologyEntry] = []
    previous_t_ms: int | None = None

    for seq, raw_event in enumerate(raw_events, start=1):
        # media_offset_ms is set by apply_event when an anchor timestamp exists;
        # relative_time_ms is a synonym; fall back to 0.
        t_ms = int(
            raw_event.get("media_offset_ms")
            or raw_event.get("relative_time_ms")
            or 0
        )
        delta_ms = 0 if previous_t_ms is None else t_ms - previous_t_ms
        event_type = raw_event.get("type", "")
        kind = _EVENT_KIND_MAP.get(event_type, event_type.lower())
        text = _extract_event_text(raw_event)
        meta = raw_event.get("meta") or {}
        payload = raw_event.get("payload") or {}
        entries.append(
            ChronologyEntry(
                seq=seq,
                kind=kind,
                t_ms=t_ms,
                delta_ms=delta_ms,
                text=text or None,
                text_preview=_safe_preview(text) if text else None,
                event_id=str(meta.get("event_id")) if meta.get("event_id") else None,
                node_id=str(payload.get("node_id") or payload.get("id")) if (
                    payload.get("node_id") or payload.get("id")
                ) else None,
                dtmf=str(payload.get("digits")) if payload.get("digits") else None,
            )
        )
        previous_t_ms = t_ms

    return ChronologySection(entries=entries)


def _build_summary(
    bundle: ResolvedReplayBundle,
    chronology: ChronologySection,
) -> SummarySection:
    """Build the high-signal ``SummarySection`` from bundle artifacts."""
    prompt_entries = [e for e in chronology.entries if e.kind == "prompt"]
    action_entries = [e for e in chronology.entries if e.kind == "action"]
    gap_values = [e.delta_ms for e in chronology.entries[1:]]
    notes: list[str] = []

    # Non-monotonic timeline check
    t_values = [e.t_ms for e in chronology.entries]
    if t_values != sorted(t_values):
        notes.append("non_monotonic_event_timeline")

    # Node count: prefer replay_state, fall back to runtime_diagnostics
    node_count = 0
    if bundle.replay_state is not None:
        node_count = len(bundle.replay_state.nodes)
    else:
        node_count = int(bundle.runtime_diagnostics.get("graph_node_count") or 0)

    return SummarySection(
        event_count=len(chronology.entries),
        prompt_count=len(prompt_entries),
        action_count=len(action_entries),
        node_count=node_count,
        first_prompt=prompt_entries[0].text if prompt_entries else None,
        last_prompt=prompt_entries[-1].text if prompt_entries else None,
        last_action=action_entries[-1].text if action_entries else None,
        largest_gap_ms=max(gap_values, default=None),
        notes=notes,
    )


def _build_session_metadata(bundle: ResolvedReplayBundle) -> SessionMetadataSection:
    """Populate ``SessionMetadataSection`` from the session listing and runtime diagnostics."""
    listing = bundle.session_listing or {}
    diag = bundle.runtime_diagnostics

    started_at: float | None = None
    ended_at: float | None = None

    raw_events = bundle.raw_events
    if raw_events:
        first_ts = (raw_events[0].get("meta") or {}).get("timestamp")
        last_ts = (raw_events[-1].get("meta") or {}).get("timestamp")
        if isinstance(first_ts, (int, float)):
            started_at = float(first_ts)
        if isinstance(last_ts, (int, float)):
            ended_at = float(last_ts)

    duration_ms: int | None = None
    if started_at is not None and ended_at is not None:
        duration_ms = max(0, int((ended_at - started_at) * 1000))

    return SessionMetadataSection(
        target=diag.get("call_sid") or None,
        started_at=started_at,
        ended_at=ended_at,
        duration_ms=duration_ms,
        manual_mode=None,
        created_at=str(diag["created_at"]) if diag.get("created_at") else listing.get("created_at"),
        updated_at=str(diag["updated_at"]) if diag.get("updated_at") else listing.get("updated_at"),
    )


def _build_path(bundle: ResolvedReplayBundle) -> PathSection:
    """Populate ``PathSection`` from replay state traversal data."""
    state = bundle.replay_state
    if state is None:
        return PathSection()

    # Build path steps from raw events (prompts and actions in order)
    steps: list[PathStep] = []
    for seq, raw_event in enumerate(bundle.raw_events):
        event_type = raw_event.get("type", "")
        kind = _EVENT_KIND_MAP.get(event_type)
        if kind not in ("prompt", "action"):
            continue
        payload = raw_event.get("payload") or {}
        meta = raw_event.get("meta") or {}
        t_ms = int(
            raw_event.get("media_offset_ms")
            or raw_event.get("relative_time_ms")
            or 0
        )
        text = _extract_event_text(raw_event)
        steps.append(
            PathStep(
                event_index=seq,
                kind=kind,
                value=text or None,
                t_ms=t_ms,
                node_id=str(payload.get("node_id") or payload.get("id")) if (
                    payload.get("node_id") or payload.get("id")
                ) else None,
            )
        )

    prompt_texts = [
        str(t.get("text") or "") for t in state.transcripts if t.get("text")
    ]
    action_dtmf = [d for d in state.dtmf_history if d]

    return PathSection(
        root_prompts=prompt_texts[:1],
        dtmf_path=action_dtmf,
        unique_actions=sorted(set(action_dtmf)),
        visited_nodes=list(state.visited_nodes),
        active_path=list(state.active_path),
        steps=steps,
    )


def _build_state_diagnostics(bundle: ResolvedReplayBundle) -> StateDiagnosticsSection:
    """Populate ``StateDiagnosticsSection`` from runtime diagnostics."""
    diag = bundle.runtime_diagnostics
    state = bundle.replay_state
    snapshot = bundle.latest_snapshot

    metrics = dict(diag.get("metrics") or {})

    return StateDiagnosticsSection(
        graph_node_count=int(diag.get("graph_node_count") or 0),
        transcript_count=int(diag.get("transcript_count") or 0),
        visited_node_count=int(diag.get("visited_node_count") or 0),
        call_status=str(diag["call_status"]) if diag.get("call_status") else None,
        snapshot_offset=int(metrics["snapshot_offset"]) if "snapshot_offset" in metrics else (
            snapshot.event_offset if snapshot is not None else None
        ),
        target_offset=int(metrics["target_offset"]) if "target_offset" in metrics else None,
        total_event_count=int(metrics["total_event_count"]) if "total_event_count" in metrics else (
            len(bundle.raw_events) or None
        ),
        queue={},
        metrics=metrics,
        error=None,
    )


def _build_correlation(
    bundle: ResolvedReplayBundle,
    chronology: ChronologySection,
) -> CorrelationSection:
    """Populate ``CorrelationSection`` from timing data across the bundle."""
    raw_events = bundle.raw_events
    listing = bundle.session_listing or {}

    session_start_ts: float | None = None
    session_end_ts: float | None = None
    if raw_events:
        first_ts = (raw_events[0].get("meta") or {}).get("timestamp")
        last_ts = (raw_events[-1].get("meta") or {}).get("timestamp")
        if isinstance(first_ts, (int, float)):
            session_start_ts = float(first_ts)
        if isinstance(last_ts, (int, float)):
            session_end_ts = float(last_ts)

    session_duration_ms: int | None = None
    if session_start_ts is not None and session_end_ts is not None:
        session_duration_ms = max(0, int((session_end_ts - session_start_ts) * 1000))

    # Time from session start to first prompt/action (using chronology t_ms offsets)
    prompt_entries = [e for e in chronology.entries if e.kind == "prompt"]
    action_entries = [e for e in chronology.entries if e.kind == "action"]

    session_start_to_first_prompt_ms: int | None = (
        prompt_entries[0].t_ms if prompt_entries else None
    )
    session_start_to_first_action_ms: int | None = (
        action_entries[0].t_ms if action_entries else None
    )

    return CorrelationSection(
        startup_to_gui_ready_ms=None,
        session_start_to_first_prompt_ms=session_start_to_first_prompt_ms,
        session_start_to_first_action_ms=session_start_to_first_action_ms,
        stream_connect_to_first_prompt_ms=None,
        session_duration_ms=session_duration_ms,
        last_activity_at=session_end_ts,
        idle_for_s=None,
    )


def _build_bookmarks_annotations(bundle: ResolvedReplayBundle) -> BookmarksAnnotationsSection:
    """Project bookmarks and annotations from bundle into the report section."""
    bookmark_summaries = [
        BookmarkSummary(
            bookmark_id=bm.bookmark_id,
            session_id=bm.session_id,
            event_id=bm.event_id,
            event_index=bm.event_index,
            media_time_ms=bm.media_time_ms,
            label=bm.label,
            category=bm.category.value if hasattr(bm.category, "value") else str(bm.category),
            note=bm.note,
            created_at=bm.created_at if hasattr(bm, "created_at") else None,
            source=bm.source if hasattr(bm, "source") else "operator",
        )
        for bm in bundle.bookmarks
    ]
    annotation_summaries = [
        AnnotationSummary(
            annotation_id=ann.annotation_id,
            session_id=ann.session_id,
            event_id=ann.event_id,
            event_index=ann.event_index,
            media_time_ms=ann.media_time_ms,
            type=ann.type,
            text=ann.text,
            severity=ann.severity.value if hasattr(ann.severity, "value") else str(ann.severity),
            created_at=ann.created_at if hasattr(ann, "created_at") else None,
            revision_of=ann.revision_of if hasattr(ann, "revision_of") else None,
        )
        for ann in bundle.annotations
    ]
    return BookmarksAnnotationsSection(
        bookmarks=bookmark_summaries,
        annotations=annotation_summaries,
    )


def _build_media_status(bundle: ResolvedReplayBundle) -> MediaStatusSection:
    """Populate ``MediaStatusSection`` from media metadata and runtime diagnostics."""
    diag = bundle.runtime_diagnostics
    media = bundle.media_metadata

    recording_reference = diag.get("recording_reference")
    recording_path = media.get("recording_path")
    recording_available = bool(media.get("recording_exists"))

    waveform_reference = diag.get("waveform_reference")
    waveform_available = bundle.waveform_metadata is not None
    waveform_path: str | None = None
    if bundle.waveform_metadata is not None:
        # The waveform path is exposed via the artifact_availability entry when available.
        for entry in bundle.artifact_availability.entries:
            if entry.artifact == "waveform":
                waveform_path = entry.location
                break

    return MediaStatusSection(
        recording_reference=str(recording_reference) if recording_reference else None,
        recording_path=str(recording_path) if recording_path else None,
        recording_available=recording_available,
        waveform_reference=str(waveform_reference) if waveform_reference else None,
        waveform_path=waveform_path,
        waveform_available=waveform_available,
        media_duration_ms=int(diag["media_duration_ms"]) if diag.get("media_duration_ms") else None,
        replay_anchor_timestamp=(
            str(diag["replay_anchor_timestamp"]) if diag.get("replay_anchor_timestamp") else None
        ),
    )


def _build_identity(bundle: ResolvedReplayBundle) -> IdentitySection:
    """Populate ``IdentitySection`` from bundle artifacts."""
    diag = bundle.runtime_diagnostics
    listing = bundle.session_listing or {}
    return IdentitySection(
        session_id=bundle.session_id,
        call_sid=str(diag["call_sid"]) if diag.get("call_sid") else None,
        source_kind="event_log",
        source_path=None,  # caller may override if needed
    )


# ---------------------------------------------------------------------------
# Public service entry point
# ---------------------------------------------------------------------------

def inspect_session(
    session_id: str,
    *,
    resolver: BundleResolver | None = None,
) -> ReplayInspectionReport:
    """Return a fully-populated ``ReplayInspectionReport`` for *session_id*.

    All sections that can be derived from the resolved artifact bundle are
    populated.  Sections that require anomaly detection (``anomalies``,
    ``next_steps``) are populated via the stubbed lambdas until Agent 3
    delivers ``replay/anomaly_detection.py``.

    Parameters
    ----------
    session_id:
        Identifier for the replay session to inspect.
    resolver:
        Optional ``BundleResolver`` instance.  When *None*, a default resolver
        is constructed.  Pass a custom resolver in tests to inject mocks.
    """
    if resolver is None:
        resolver = BundleResolver()

    bundle = resolver.resolve(session_id)
    return _build_report(bundle)


def _build_report(bundle: ResolvedReplayBundle) -> ReplayInspectionReport:
    """Internal: map a resolved bundle onto a ``ReplayInspectionReport``."""
    identity = _build_identity(bundle)
    chronology = _build_chronology(bundle.raw_events)
    summary = _build_summary(bundle, chronology)
    session_metadata = _build_session_metadata(bundle)
    path = _build_path(bundle)
    state_diagnostics = _build_state_diagnostics(bundle)
    correlation = _build_correlation(bundle, chronology)
    bookmarks_annotations = _build_bookmarks_annotations(bundle)
    media_status = _build_media_status(bundle)

    # Partial report (no anomalies/next_steps yet) fed into the stubs.
    partial_report = ReplayInspectionReport(
        identity=identity,
        artifact_availability=bundle.artifact_availability,
        session_metadata=session_metadata,
        summary=summary,
        chronology=chronology,
        path=path,
        state_diagnostics=state_diagnostics,
        correlation=correlation,
        anomalies=[],
        bookmarks_annotations=bookmarks_annotations,
        media_status=media_status,
        next_steps=[],
    )

    # STUB call sites — Agent 3 wires in real implementations here.
    anomalies: list[Anomaly] = _detect_anomalies(partial_report)       # STUB
    next_steps: list[NextStep] = _generate_next_steps(partial_report)  # STUB

    return ReplayInspectionReport(
        identity=identity,
        artifact_availability=bundle.artifact_availability,
        session_metadata=session_metadata,
        summary=summary,
        chronology=chronology,
        path=path,
        state_diagnostics=state_diagnostics,
        correlation=correlation,
        anomalies=anomalies,
        bookmarks_annotations=bookmarks_annotations,
        media_status=media_status,
        next_steps=next_steps,
    )


__all__ = ["inspect_session"]
