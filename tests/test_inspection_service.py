"""Tests for replay/inspection_service.py.

These tests verify:
- Service produces a fully-populated report for a fixture session (resolver mocked).
- Service produces a sensible partial report when artifacts are missing.
- Stubbed anomaly/next-step calls return empty lists and never block report production.
- Identity, session_metadata, chronology, path, state_diagnostics, correlation,
  bookmarks_annotations, media_status, and artifact_availability sections are all
  populated from bundle data.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from replay.bundle_resolver import BundleResolver, ResolvedReplayBundle
from replay.inspection_models import (
    Anomaly,
    AnnotationSummary,
    ArtifactAvailabilityEntry,
    ArtifactAvailabilitySection,
    BookmarkSummary,
    Reference,
    ReplayInspectionReport,
)
from replay.inspection_service import inspect_session
from replay.media_sync.media_replay_service import MediaReplayService
from replay.snapshots.snapshot_service import SnapshotService
from replay.timelines.replay_service import ReplayService
from runtime.events.annotation_service import AnnotationService
from runtime.events.bookmark_service import BookmarkService
from runtime.events.replay_annotation import AnnotationSeverity, ReplayAnnotation
from runtime.events.replay_bookmark import BookmarkCategory, ReplayBookmark


# ---------------------------------------------------------------------------
# Helpers: write fixture event log and waveform metadata
# ---------------------------------------------------------------------------

def _write_event_log(path: Path) -> None:
    events = [
        {
            "type": "CALL_STARTED",
            "meta": {"timestamp": 1700000000.0, "event_id": "evt-1"},
            "payload": {
                "call_sid": "CA123",
                "recording_url": "https://example.test/recordings/RE123.wav",
            },
        },
        {
            "type": "CALL_CONNECTED",
            "meta": {"timestamp": 1700000000.5, "event_id": "evt-2"},
            "payload": {},
        },
        {
            "type": "STATE_DISCOVERED",
            "meta": {"timestamp": 1700000001.0, "event_id": "evt-3"},
            "payload": {"id": "node-root", "label": "Root menu"},
        },
        {
            "type": "TRANSCRIPT_FINAL",
            "meta": {"timestamp": 1700000002.0, "event_id": "evt-4"},
            "payload": {"text": "Press 1 for billing", "speech_start_offset": 1.5},
        },
        {
            "type": "DTMF_SENT",
            "meta": {"timestamp": 1700000003.0, "event_id": "evt-5"},
            "payload": {"digits": "1"},
        },
        {
            "type": "PATH_ADVANCED",
            "meta": {"timestamp": 1700000004.0, "event_id": "evt-6"},
            "payload": {"node_id": "node-billing"},
        },
        {
            "type": "CALL_COMPLETED",
            "meta": {"timestamp": 1700000005.0, "event_id": "evt-7"},
            "payload": {},
        },
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event) + "\n")


def _write_waveform_metadata(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "peaks": [0.1, 0.3, 0.2],
                "rms_buckets": [0.05, 0.15, 0.1],
                "bucket_size_ms": 100,
                "duration_ms": 5000,
            }
        ),
        encoding="utf-8",
    )


def _build_real_resolver(
    tmp_path: Path,
    monkeypatch,
    *,
    session_id: str,
    with_snapshot: bool = True,
    with_recording: bool = True,
    with_waveform: bool = True,
    with_bookmarks: bool = True,
    with_annotations: bool = True,
) -> BundleResolver:
    """Build a BundleResolver backed by temp-dir fixtures."""
    events_dir = tmp_path / "events"
    snapshots_dir = tmp_path / "snapshots"
    annotations_dir = tmp_path / "annotations"
    recordings_dir = tmp_path / "recordings"
    waveforms_dir = tmp_path / "waveforms"

    event_log = events_dir / "2024-01-01" / f"session_{session_id}.jsonl"
    _write_event_log(event_log)

    replay_service = ReplayService(events_dir=events_dir)
    snapshot_service = SnapshotService(snapshots_dir=snapshots_dir)

    monkeypatch.setattr("replay.media_sync.media_replay_service.RECORDINGS_DIR", recordings_dir)
    monkeypatch.setattr("replay.media_sync.waveform_metadata.RECORDINGS_DIR", recordings_dir)
    monkeypatch.setattr("replay.media_sync.waveform_metadata.WAVEFORMS_DIR", waveforms_dir)
    media_replay_service = MediaReplayService()

    bookmark_service = BookmarkService(base_dir=annotations_dir)
    annotation_service = AnnotationService(base_dir=annotations_dir)

    if with_snapshot:
        replay_state = replay_service.load_replay(session_id)
        assert replay_state is not None
        snapshot = snapshot_service.create_snapshot(
            replay_state,
            event_offset=len(replay_state.events),
        )
        snapshot_service.persist_snapshot(snapshot)

    if with_recording:
        recording_path = recordings_dir / "2024-01-01" / f"session_{session_id}.wav"
        recording_path.parent.mkdir(parents=True, exist_ok=True)
        recording_path.write_bytes(b"RIFFtest")

    if with_waveform:
        _write_waveform_metadata(waveforms_dir / f"session_{session_id}.json")

    if with_bookmarks:
        bookmark_service.add_bookmark(
            ReplayBookmark(
                session_id=session_id,
                event_id="evt-4",
                event_index=3,
                media_time_ms=1500.0,
                label="Prompt mismatch",
                category=BookmarkCategory.PROMPT_MISMATCH,
                note="Billing prompt worth review",
            )
        )

    if with_annotations:
        annotation_service.add_annotation(
            ReplayAnnotation(
                session_id=session_id,
                event_id="evt-5",
                event_index=4,
                media_time_ms=3000.0,
                type="operator-note",
                text="Operator confirmed DTMF branch",
                severity=AnnotationSeverity.INFO,
            )
        )

    return BundleResolver(
        replay_service=replay_service,
        snapshot_service=snapshot_service,
        media_replay_service=media_replay_service,
        bookmark_service=bookmark_service,
        annotation_service=annotation_service,
    )


# ---------------------------------------------------------------------------
# Tests: full fixture session
# ---------------------------------------------------------------------------

def test_service_produces_report_with_all_sections_populated(
    tmp_path, monkeypatch
) -> None:
    """Service returns a ReplayInspectionReport with expected sections populated."""
    session_id = "svc-full"
    resolver = _build_real_resolver(
        tmp_path,
        monkeypatch,
        session_id=session_id,
        with_snapshot=True,
        with_recording=True,
        with_waveform=True,
        with_bookmarks=True,
        with_annotations=True,
    )

    report = inspect_session(session_id, resolver=resolver)

    assert isinstance(report, ReplayInspectionReport)
    assert report.schema_version == "1.0"

    # Identity
    assert report.identity.session_id == session_id
    assert report.identity.call_sid == "CA123"
    assert report.identity.source_kind == "event_log"

    # Artifact availability
    artifact_names = [e.artifact for e in report.artifact_availability.entries]
    assert "event_log" in artifact_names
    assert "snapshots" in artifact_names
    assert "recording" in artifact_names
    assert "waveform" in artifact_names
    assert "bookmarks" in artifact_names
    assert "annotations" in artifact_names
    assert report.artifact_availability.missing == []

    # Session metadata
    assert report.session_metadata.started_at is not None
    assert report.session_metadata.ended_at is not None
    assert report.session_metadata.duration_ms is not None
    assert report.session_metadata.duration_ms >= 0

    # Summary
    assert report.summary.event_count == 7
    # The session has one TRANSCRIPT_FINAL (prompt) and one DTMF_SENT (action)
    assert report.summary.prompt_count >= 1
    assert report.summary.action_count >= 1
    assert report.summary.first_prompt is not None

    # Chronology
    assert len(report.chronology.entries) == 7
    kinds = [e.kind for e in report.chronology.entries]
    assert "prompt" in kinds
    assert "action" in kinds
    assert "call_started" in kinds
    assert "call_completed" in kinds

    # Path
    assert "1" in report.path.dtmf_path

    # State diagnostics
    assert report.state_diagnostics.call_status is not None
    assert report.state_diagnostics.graph_node_count >= 0

    # Correlation
    assert report.correlation.session_duration_ms is not None
    assert report.correlation.session_start_to_first_prompt_ms is not None

    # Bookmarks and annotations
    assert len(report.bookmarks_annotations.bookmarks) == 1
    assert report.bookmarks_annotations.bookmarks[0].label == "Prompt mismatch"
    assert len(report.bookmarks_annotations.annotations) == 1
    assert report.bookmarks_annotations.annotations[0].text == "Operator confirmed DTMF branch"

    # Media status
    assert report.media_status.recording_available is True
    assert report.media_status.waveform_available is True

    # Anomalies and next_steps are empty (stubs)
    assert report.anomalies == []
    assert report.next_steps == []


def test_service_chronology_has_correct_sequence_and_event_ids(
    tmp_path, monkeypatch
) -> None:
    """Chronology entries have sequential seq numbers and event_ids from the log."""
    session_id = "svc-chron"
    resolver = _build_real_resolver(
        tmp_path,
        monkeypatch,
        session_id=session_id,
        with_snapshot=False,
        with_recording=False,
        with_waveform=False,
        with_bookmarks=False,
        with_annotations=False,
    )

    report = inspect_session(session_id, resolver=resolver)

    seqs = [e.seq for e in report.chronology.entries]
    assert seqs == list(range(1, len(seqs) + 1)), "seq must be monotonically increasing from 1"

    event_ids = [e.event_id for e in report.chronology.entries if e.event_id]
    assert "evt-1" in event_ids
    assert "evt-4" in event_ids  # TRANSCRIPT_FINAL
    assert "evt-5" in event_ids  # DTMF_SENT


# ---------------------------------------------------------------------------
# Tests: partial artifact session
# ---------------------------------------------------------------------------

def test_service_produces_partial_report_without_raising(
    tmp_path, monkeypatch
) -> None:
    """Service returns a coherent partial report when most artifacts are absent."""
    session_id = "svc-partial"
    resolver = _build_real_resolver(
        tmp_path,
        monkeypatch,
        session_id=session_id,
        with_snapshot=False,
        with_recording=False,
        with_waveform=False,
        with_bookmarks=False,
        with_annotations=False,
    )

    report = inspect_session(session_id, resolver=resolver)

    assert isinstance(report, ReplayInspectionReport)
    # Event log is still present
    assert report.summary.event_count == 7
    # Missing artifacts listed
    assert "snapshots" in report.artifact_availability.missing
    assert "recording" in report.artifact_availability.missing
    assert "waveform" in report.artifact_availability.missing
    assert "bookmarks" in report.artifact_availability.missing
    assert "annotations" in report.artifact_availability.missing
    # Media flags reflect absence
    assert report.media_status.recording_available is False
    assert report.media_status.waveform_available is False
    # Bookmarks/annotations are empty
    assert report.bookmarks_annotations.bookmarks == []
    assert report.bookmarks_annotations.annotations == []
    # Anomalies and next_steps still empty (stubs)
    assert report.anomalies == []
    assert report.next_steps == []


def test_service_handles_completely_missing_session(
    tmp_path, monkeypatch
) -> None:
    """Service returns a safe empty-ish report for an unknown session id."""
    monkeypatch.setattr(
        "replay.media_sync.media_replay_service.RECORDINGS_DIR",
        tmp_path / "recordings",
    )
    monkeypatch.setattr(
        "replay.media_sync.waveform_metadata.RECORDINGS_DIR",
        tmp_path / "recordings",
    )
    monkeypatch.setattr(
        "replay.media_sync.waveform_metadata.WAVEFORMS_DIR",
        tmp_path / "waveforms",
    )
    resolver = BundleResolver(
        replay_service=ReplayService(events_dir=tmp_path / "events"),
        snapshot_service=SnapshotService(snapshots_dir=tmp_path / "snapshots"),
        media_replay_service=MediaReplayService(),
        bookmark_service=BookmarkService(base_dir=tmp_path / "annotations"),
        annotation_service=AnnotationService(base_dir=tmp_path / "annotations"),
    )

    report = inspect_session("no-such-session", resolver=resolver)

    assert isinstance(report, ReplayInspectionReport)
    assert report.identity.session_id == "no-such-session"
    assert report.summary.event_count == 0
    assert report.chronology.entries == []
    assert report.anomalies == []
    assert report.next_steps == []
    # All artifacts missing
    assert set(report.artifact_availability.missing) == {
        "event_log",
        "snapshots",
        "runtime_diagnostics",
        "recording",
        "waveform",
        "bookmarks",
        "annotations",
    }


# ---------------------------------------------------------------------------
# Tests: stubbed anomaly/next-step calls
# ---------------------------------------------------------------------------

def test_stubbed_anomaly_detection_returns_empty_and_does_not_block(
    tmp_path, monkeypatch
) -> None:
    """Stub anomaly/next-step calls return [] and report is still produced."""
    session_id = "svc-stub"
    resolver = _build_real_resolver(
        tmp_path,
        monkeypatch,
        session_id=session_id,
        with_snapshot=False,
        with_recording=False,
        with_waveform=False,
        with_bookmarks=False,
        with_annotations=False,
    )

    report = inspect_session(session_id, resolver=resolver)

    # Anomaly detection and next-step generation are stubbed with lambdas
    # that return [].  The report must still be fully formed.
    assert report.anomalies == []
    assert report.next_steps == []
    assert isinstance(report, ReplayInspectionReport)
    # Other sections should still be populated normally
    assert report.summary.event_count > 0


def test_real_anomaly_detection_module_wired_in_when_present(
    monkeypatch,
) -> None:
    """When anomaly_detection module exists, its results appear in the report.

    This test simulates what happens after Agent 3 delivers the real module.
    It monkeypatches the service's module-level callables to verify the wiring.
    """
    fake_anomaly = Anomaly(
        code="TEST_ANOMALY",
        severity="warn",
        explanation="Synthetic anomaly for wiring test",
        references=[
            Reference(
                kind="report_field",
                label="summary.event_count",
                field_path="summary.event_count",
            )
        ],
    )

    # Patch both references inside inspection_service
    import replay.inspection_service as svc_module

    monkeypatch.setattr(svc_module, "_detect_anomalies", lambda report: [fake_anomaly])
    monkeypatch.setattr(svc_module, "_generate_next_steps", lambda report: [])

    # Use a mock resolver so we don't need disk fixtures
    bundle = ResolvedReplayBundle(
        session_id="wiring-test",
        raw_events=[],
        artifact_availability=ArtifactAvailabilitySection(
            entries=[
                ArtifactAvailabilityEntry(
                    artifact="event_log",
                    available=False,
                    detail="event log not found",
                )
            ],
            missing=["event_log"],
        ),
    )
    mock_resolver = MagicMock(spec=BundleResolver)
    mock_resolver.resolve.return_value = bundle

    report = inspect_session("wiring-test", resolver=mock_resolver)

    assert len(report.anomalies) == 1
    assert report.anomalies[0].code == "TEST_ANOMALY"
    assert report.next_steps == []


# ---------------------------------------------------------------------------
# Tests: mock-resolver fast path
# ---------------------------------------------------------------------------

def test_service_with_mock_resolver_full_bundle() -> None:
    """Service populates all sections correctly given a mock resolver."""
    from unittest.mock import MagicMock

    from replay.snapshots.replay_snapshot import ReplaySnapshot
    from runtime.state.replay_state import ReplayState

    session_id = "mock-full"

    # Minimal ReplayState
    state = ReplayState(session_id=session_id)
    state.call_sid = "CA-MOCK"
    state.call_status = "completed"
    state.nodes = {"node-root": {"id": "node-root", "label": "Root"}}
    state.transcripts = [{"text": "Hello world", "speaker": "system"}]
    state.dtmf_history = ["2", "3"]
    state.visited_nodes = ["node-root"]
    state.active_path = ["node-root"]
    state.metrics = {
        "reconstructed_from_snapshot": False,
        "snapshot_offset": 0,
        "target_offset": 3,
        "total_event_count": 3,
    }
    state.recording_reference = "RE-MOCK"
    state.waveform_reference = "WV-MOCK"

    raw_events = [
        {
            "type": "TRANSCRIPT_FINAL",
            "meta": {"timestamp": 1700000001.0, "event_id": "evt-m1"},
            "payload": {"text": "Hello world"},
            "media_offset_ms": 0,
        },
        {
            "type": "DTMF_SENT",
            "meta": {"timestamp": 1700000002.0, "event_id": "evt-m2"},
            "payload": {"digits": "2"},
            "media_offset_ms": 1000,
        },
        {
            "type": "DTMF_SENT",
            "meta": {"timestamp": 1700000003.0, "event_id": "evt-m3"},
            "payload": {"digits": "3"},
            "media_offset_ms": 2000,
        },
    ]

    availability = ArtifactAvailabilitySection(
        entries=[
            ArtifactAvailabilityEntry(artifact="event_log", available=True, detail="3 events loaded"),
            ArtifactAvailabilityEntry(artifact="snapshots", available=False, detail="no snapshots"),
            ArtifactAvailabilityEntry(artifact="runtime_diagnostics", available=True, detail="ok"),
            ArtifactAvailabilityEntry(artifact="recording", available=False, detail="not found"),
            ArtifactAvailabilityEntry(artifact="waveform", available=False, detail="not found"),
            ArtifactAvailabilityEntry(artifact="bookmarks", available=False, detail="none"),
            ArtifactAvailabilityEntry(artifact="annotations", available=False, detail="none"),
        ],
        missing=["snapshots", "recording", "waveform", "bookmarks", "annotations"],
    )

    bundle = ResolvedReplayBundle(
        session_id=session_id,
        raw_events=raw_events,
        replay_state=state,
        latest_snapshot=None,
        session_listing={"session_id": session_id, "event_count": 3},
        runtime_diagnostics={
            "session_id": session_id,
            "call_sid": "CA-MOCK",
            "call_status": "completed",
            "graph_node_count": 1,
            "transcript_count": 1,
            "visited_node_count": 1,
            "active_path_length": 1,
            "metrics": state.metrics,
            "recording_reference": "RE-MOCK",
            "waveform_reference": "WV-MOCK",
            "media_duration_ms": None,
            "replay_anchor_timestamp": None,
        },
        media_metadata={"recording_exists": False},
        waveform_metadata=None,
        bookmarks=[],
        annotations=[],
        artifact_availability=availability,
    )

    mock_resolver = MagicMock(spec=BundleResolver)
    mock_resolver.resolve.return_value = bundle

    report = inspect_session(session_id, resolver=mock_resolver)

    # Identity
    assert report.identity.session_id == session_id
    assert report.identity.call_sid == "CA-MOCK"

    # Chronology
    assert len(report.chronology.entries) == 3
    assert report.chronology.entries[0].kind == "prompt"
    assert report.chronology.entries[1].kind == "action"
    assert report.chronology.entries[2].kind == "action"
    assert report.chronology.entries[1].delta_ms == 1000
    assert report.chronology.entries[2].delta_ms == 1000

    # Summary
    assert report.summary.event_count == 3
    assert report.summary.prompt_count == 1
    assert report.summary.action_count == 2
    assert report.summary.first_prompt == "Hello world"
    assert report.summary.node_count == 1

    # Path
    assert report.path.dtmf_path == ["2", "3"]
    assert report.path.unique_actions == ["2", "3"]

    # State diagnostics
    assert report.state_diagnostics.call_status == "completed"
    assert report.state_diagnostics.graph_node_count == 1
    assert report.state_diagnostics.total_event_count == 3

    # Correlation
    assert report.correlation.session_start_to_first_prompt_ms == 0
    assert report.correlation.session_start_to_first_action_ms == 1000

    # Stubs
    assert report.anomalies == []
    assert report.next_steps == []
