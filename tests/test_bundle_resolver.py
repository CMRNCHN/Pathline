from __future__ import annotations

import json
from pathlib import Path

from replay.bundle_resolver import BundleResolver
from replay.media_sync.media_replay_service import MediaReplayService
from replay.snapshots.snapshot_service import SnapshotService
from replay.timelines.replay_service import ReplayService
from runtime.events.annotation_service import AnnotationService
from runtime.events.bookmark_service import BookmarkService
from runtime.events.replay_annotation import AnnotationSeverity, ReplayAnnotation
from runtime.events.replay_bookmark import BookmarkCategory, ReplayBookmark


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


def _build_resolver(
    tmp_path: Path,
    monkeypatch,
    *,
    session_id: str,
    with_snapshot: bool,
    with_recording: bool,
    with_waveform: bool,
    with_bookmarks: bool,
    with_annotations: bool,
) -> BundleResolver:
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


def test_bundle_resolver_reports_full_artifact_availability(tmp_path, monkeypatch) -> None:
    session_id = "resolver-full"
    resolver = _build_resolver(
        tmp_path,
        monkeypatch,
        session_id=session_id,
        with_snapshot=True,
        with_recording=True,
        with_waveform=True,
        with_bookmarks=True,
        with_annotations=True,
    )

    bundle = resolver.resolve(session_id)
    entries = {entry.artifact: entry for entry in bundle.artifact_availability.entries}

    assert bundle.session_listing is not None
    assert len(bundle.raw_events) == 7
    assert bundle.replay_state is not None
    assert bundle.latest_snapshot is not None
    assert bundle.runtime_diagnostics["call_status"] == "completed"
    assert bundle.waveform_metadata is not None
    assert bundle.verification_event_index
    assert bundle.artifact_availability.missing == []
    assert all(entry.available for entry in entries.values())
    assert entries["event_log"].file_count == 1
    assert entries["snapshots"].file_count == 1
    assert entries["recording"].location is not None
    assert entries["waveform"].location is not None
    assert entries["bookmarks"].file_count == 1
    assert entries["annotations"].file_count == 1


def test_bundle_resolver_reports_partial_availability_without_raising(
    tmp_path,
    monkeypatch,
) -> None:
    session_id = "resolver-partial"
    resolver = _build_resolver(
        tmp_path,
        monkeypatch,
        session_id=session_id,
        with_snapshot=False,
        with_recording=False,
        with_waveform=False,
        with_bookmarks=False,
        with_annotations=True,
    )

    bundle = resolver.resolve(session_id)
    entries = {entry.artifact: entry for entry in bundle.artifact_availability.entries}

    assert len(bundle.raw_events) == 7
    assert bundle.replay_state is not None
    assert bundle.latest_snapshot is None
    assert bundle.waveform_metadata is None
    assert entries["event_log"].available is True
    assert entries["runtime_diagnostics"].available is True
    assert entries["annotations"].available is True
    assert entries["snapshots"].available is False
    assert entries["recording"].available is False
    assert entries["waveform"].available is False
    assert entries["bookmarks"].available is False
    assert bundle.artifact_availability.missing == [
        "snapshots",
        "recording",
        "waveform",
        "bookmarks",
    ]


def test_bundle_resolver_handles_unknown_session_as_missing_artifacts(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "replay.media_sync.media_replay_service.RECORDINGS_DIR",
        tmp_path / "recordings",
    )
    monkeypatch.setattr(
        "replay.media_sync.waveform_metadata.RECORDINGS_DIR",
        tmp_path / "recordings",
    )
    monkeypatch.setattr("replay.media_sync.waveform_metadata.WAVEFORMS_DIR", tmp_path / "waveforms")

    resolver = BundleResolver(
        replay_service=ReplayService(events_dir=tmp_path / "events"),
        snapshot_service=SnapshotService(snapshots_dir=tmp_path / "snapshots"),
        media_replay_service=MediaReplayService(),
        bookmark_service=BookmarkService(base_dir=tmp_path / "annotations"),
        annotation_service=AnnotationService(base_dir=tmp_path / "annotations"),
    )

    bundle = resolver.resolve("missing-session")

    assert bundle.raw_events == []
    assert bundle.replay_state is None
    assert bundle.latest_snapshot is None
    assert bundle.artifact_availability.missing == [
        "event_log",
        "snapshots",
        "runtime_diagnostics",
        "recording",
        "waveform",
        "bookmarks",
        "annotations",
    ]
