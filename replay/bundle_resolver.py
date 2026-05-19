from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from replay.inspection_models import (
    ArtifactAvailabilityEntry,
    ArtifactAvailabilitySection,
    Reference,
)
from replay.media_sync.media_replay_service import MediaReplayService
from replay.snapshots.replay_snapshot import ReplaySnapshot
from replay.snapshots.snapshot_service import SnapshotService
from replay.timelines.replay_service import ReplayService
from replay.verification.replay_search import ReplaySearch
from runtime.events.annotation_service import (
    AnnotationService,
    annotation_service as default_annotation_service,
)
from runtime.events.bookmark_service import (
    BookmarkService,
    bookmark_service as default_bookmark_service,
)
from runtime.events.replay_annotation import ReplayAnnotation
from runtime.events.replay_bookmark import ReplayBookmark
from runtime.state.replay_state import ReplayState


@dataclass(frozen=True)
class ResolvedReplayBundle:
    """Internal bundle of replay artifacts used to construct the canonical report."""

    session_id: str
    raw_events: list[dict[str, Any]] = field(default_factory=list)
    replay_state: ReplayState | None = None
    latest_snapshot: ReplaySnapshot | None = None
    session_listing: dict[str, Any] | None = None
    runtime_diagnostics: dict[str, Any] = field(default_factory=dict)
    media_metadata: dict[str, Any] = field(default_factory=dict)
    waveform_metadata: dict[str, Any] | None = None
    verification_event_index: list[dict[str, Any]] = field(default_factory=list)
    bookmarks: list[ReplayBookmark] = field(default_factory=list)
    annotations: list[ReplayAnnotation] = field(default_factory=list)
    artifact_availability: ArtifactAvailabilitySection = field(
        default_factory=ArtifactAvailabilitySection
    )


class BundleResolver:
    """Resolve replay inspection artifacts through the repo's existing replay/runtime services."""

    def __init__(
        self,
        *,
        replay_service: ReplayService | None = None,
        snapshot_service: SnapshotService | None = None,
        media_replay_service: MediaReplayService | None = None,
        bookmark_service: BookmarkService | None = None,
        annotation_service: AnnotationService | None = None,
    ) -> None:
        self._replay_service = replay_service or ReplayService()
        self._snapshot_service = snapshot_service or SnapshotService()
        self._media_replay_service = media_replay_service or MediaReplayService()
        self._bookmark_service = bookmark_service or default_bookmark_service
        self._annotation_service = annotation_service or default_annotation_service

    def resolve(self, session_id: str) -> ResolvedReplayBundle:
        session_listing = self._find_session_listing(session_id)
        raw_events = self._replay_service.get_raw_events(session_id)
        replay_state = self._replay_service.load_replay(session_id) if raw_events else None
        latest_snapshot = self._snapshot_service.get_latest_snapshot(session_id)
        runtime_diagnostics = self._build_runtime_diagnostics(
            session_id=session_id,
            replay_state=replay_state,
            latest_snapshot=latest_snapshot,
        )
        media_metadata = self._media_replay_service.get_media_metadata(session_id)
        waveform_metadata = self._media_replay_service.get_waveform_metadata(session_id)
        verification_event_index = self._build_verification_event_index(replay_state)
        bookmarks = self._bookmark_service.get_bookmarks(session_id)
        annotations = self._annotation_service.get_annotations(session_id)
        artifact_availability = self._build_artifact_availability(
            session_id=session_id,
            raw_events=raw_events,
            replay_state=replay_state,
            latest_snapshot=latest_snapshot,
            runtime_diagnostics=runtime_diagnostics,
            media_metadata=media_metadata,
            waveform_metadata=waveform_metadata,
            bookmarks=bookmarks,
            annotations=annotations,
        )

        return ResolvedReplayBundle(
            session_id=session_id,
            raw_events=raw_events,
            replay_state=replay_state,
            latest_snapshot=latest_snapshot,
            session_listing=session_listing,
            runtime_diagnostics=runtime_diagnostics,
            media_metadata=media_metadata,
            waveform_metadata=waveform_metadata,
            verification_event_index=verification_event_index,
            bookmarks=bookmarks,
            annotations=annotations,
            artifact_availability=artifact_availability,
        )

    def _find_session_listing(self, session_id: str) -> dict[str, Any] | None:
        for replay_entry in self._replay_service.list_replays():
            if replay_entry.get("session_id") == session_id:
                return replay_entry
        return None

    def _build_runtime_diagnostics(
        self,
        *,
        session_id: str,
        replay_state: ReplayState | None,
        latest_snapshot: ReplaySnapshot | None,
    ) -> dict[str, Any]:
        if replay_state is not None:
            state_payload = replay_state.as_dict()
            return {
                "session_id": session_id,
                "call_sid": state_payload.get("call_sid"),
                "created_at": state_payload.get("created_at"),
                "updated_at": state_payload.get("updated_at"),
                "call_status": state_payload.get("call_status"),
                "graph_node_count": len(state_payload.get("nodes", {})),
                "transcript_count": len(state_payload.get("transcripts", [])),
                "visited_node_count": len(state_payload.get("visited_nodes", [])),
                "active_path_length": len(state_payload.get("active_path", [])),
                "metrics": dict(state_payload.get("metrics", {})),
                "recording_reference": state_payload.get("recording_reference"),
                "waveform_reference": state_payload.get("waveform_reference"),
                "media_duration_ms": state_payload.get("media_duration_ms"),
                "replay_anchor_timestamp": state_payload.get("replay_anchor_timestamp"),
            }

        if latest_snapshot is not None:
            return {
                "session_id": session_id,
                "call_sid": latest_snapshot.call_sid,
                "created_at": latest_snapshot.created_at,
                "updated_at": latest_snapshot.updated_at,
                "call_status": latest_snapshot.call_status,
                "graph_node_count": len(latest_snapshot.nodes),
                "transcript_count": len(latest_snapshot.transcripts),
                "visited_node_count": len(latest_snapshot.visited_nodes),
                "active_path_length": len(latest_snapshot.active_path),
                "metrics": dict(latest_snapshot.metrics),
                "recording_reference": latest_snapshot.recording_reference,
                "waveform_reference": latest_snapshot.waveform_reference,
                "media_duration_ms": latest_snapshot.media_duration_ms,
                "replay_anchor_timestamp": latest_snapshot.replay_anchor_timestamp,
                "snapshot_event_offset": latest_snapshot.event_offset,
            }

        return {"session_id": session_id, "metrics": {}}

    def _build_verification_event_index(
        self,
        replay_state: ReplayState | None,
    ) -> list[dict[str, Any]]:
        if replay_state is None:
            return []
        return ReplaySearch.format_results(ReplaySearch.search_events(replay_state))

    def _build_artifact_availability(
        self,
        *,
        session_id: str,
        raw_events: list[dict[str, Any]],
        replay_state: ReplayState | None,
        latest_snapshot: ReplaySnapshot | None,
        runtime_diagnostics: dict[str, Any],
        media_metadata: dict[str, Any],
        waveform_metadata: dict[str, Any] | None,
        bookmarks: list[ReplayBookmark],
        annotations: list[ReplayAnnotation],
    ) -> ArtifactAvailabilitySection:
        entries = [
            self._event_log_entry(session_id, raw_events),
            self._snapshot_entry(session_id, latest_snapshot),
            self._runtime_diagnostics_entry(runtime_diagnostics, replay_state),
            self._recording_entry(session_id, media_metadata, replay_state, latest_snapshot),
            self._waveform_entry(session_id, waveform_metadata, replay_state, latest_snapshot),
            self._bookmarks_entry(session_id, bookmarks),
            self._annotations_entry(session_id, annotations),
        ]
        missing = [entry.artifact for entry in entries if not entry.available]
        return ArtifactAvailabilitySection(entries=entries, missing=missing)

    def _event_log_entry(
        self,
        session_id: str,
        raw_events: list[dict[str, Any]],
    ) -> ArtifactAvailabilityEntry:
        session_file = self._replay_service._find_session_file(session_id)
        detail = f"{len(raw_events)} events loaded" if raw_events else "event log not found"
        references = [
            Reference(
                kind="artifact",
                label="event log",
                session_id=session_id,
                artifact_path=str(session_file),
                value=len(raw_events),
            )
        ] if session_file else []
        return ArtifactAvailabilityEntry(
            artifact="event_log",
            available=bool(raw_events),
            location=str(session_file) if session_file else None,
            detail=detail,
            file_count=1 if session_file else 0,
            references=references,
        )

    def _snapshot_entry(
        self,
        session_id: str,
        latest_snapshot: ReplaySnapshot | None,
    ) -> ArtifactAvailabilityEntry:
        session_dir = self._snapshot_service._find_session_dir(session_id)
        snapshot_paths = (
            sorted(session_dir.glob("snapshot_*.json")) if session_dir is not None else []
        )
        location = str(session_dir) if session_dir is not None else None
        detail = (
            f"latest snapshot offset {latest_snapshot.event_offset}"
            if latest_snapshot is not None
            else "no snapshots found"
        )
        references = [
            Reference(
                kind="snapshot",
                label="latest snapshot",
                session_id=session_id,
                snapshot_offset=latest_snapshot.event_offset,
                artifact_path=str(session_dir) if session_dir is not None else None,
                value=latest_snapshot.snapshot_id,
            )
        ] if latest_snapshot is not None else []
        return ArtifactAvailabilityEntry(
            artifact="snapshots",
            available=latest_snapshot is not None,
            location=location,
            detail=detail,
            file_count=len(snapshot_paths),
            references=references,
        )

    def _runtime_diagnostics_entry(
        self,
        runtime_diagnostics: dict[str, Any],
        replay_state: ReplayState | None,
    ) -> ArtifactAvailabilityEntry:
        has_runtime_payload = replay_state is not None or len(runtime_diagnostics) > 2
        detail = (
            f"call_status={runtime_diagnostics.get('call_status', 'unknown')}"
            if has_runtime_payload
            else "runtime diagnostics unavailable"
        )
        references = [
            Reference(
                kind="report_field",
                label="runtime diagnostics",
                field_path="state_diagnostics.metrics",
                session_id=runtime_diagnostics.get("session_id"),
                value=runtime_diagnostics.get("call_status"),
            )
        ] if has_runtime_payload else []
        return ArtifactAvailabilityEntry(
            artifact="runtime_diagnostics",
            available=has_runtime_payload,
            detail=detail,
            references=references,
        )

    def _recording_entry(
        self,
        session_id: str,
        media_metadata: dict[str, Any],
        replay_state: ReplayState | None,
        latest_snapshot: ReplaySnapshot | None,
    ) -> ArtifactAvailabilityEntry:
        recording_reference = (
            (replay_state.recording_reference if replay_state is not None else None)
            or (latest_snapshot.recording_reference if latest_snapshot is not None else None)
        )
        recording_path = media_metadata.get("recording_path")
        available = bool(media_metadata.get("recording_exists"))
        detail = recording_reference or "recording not found"
        references = [
            Reference(
                kind="media",
                label="recording",
                session_id=session_id,
                artifact_path=recording_path,
                value=recording_reference or recording_path,
            )
        ] if available or recording_reference else []
        return ArtifactAvailabilityEntry(
            artifact="recording",
            available=available,
            location=recording_path,
            detail=detail,
            file_count=1 if available else 0,
            references=references,
        )

    def _waveform_entry(
        self,
        session_id: str,
        waveform_metadata: dict[str, Any] | None,
        replay_state: ReplayState | None,
        latest_snapshot: ReplaySnapshot | None,
    ) -> ArtifactAvailabilityEntry:
        waveform_reference = (
            (replay_state.waveform_reference if replay_state is not None else None)
            or (latest_snapshot.waveform_reference if latest_snapshot is not None else None)
        )
        location = self._waveform_path(session_id) if waveform_metadata is not None else None
        detail = waveform_reference or "waveform metadata not found"
        references = [
            Reference(
                kind="media",
                label="waveform",
                session_id=session_id,
                artifact_path=location,
                value=waveform_reference or location,
            )
        ] if waveform_metadata is not None or waveform_reference else []
        return ArtifactAvailabilityEntry(
            artifact="waveform",
            available=waveform_metadata is not None,
            location=location,
            detail=detail,
            file_count=1 if waveform_metadata is not None else 0,
            references=references,
        )

    def _bookmarks_entry(
        self,
        session_id: str,
        bookmarks: list[ReplayBookmark],
    ) -> ArtifactAvailabilityEntry:
        references = [
            Reference(
                kind="event",
                label=bookmark.label,
                session_id=session_id,
                event_id=bookmark.event_id,
                event_index=bookmark.event_index,
                media_time_ms=bookmark.media_time_ms,
                value=bookmark.bookmark_id,
            )
            for bookmark in bookmarks[:5]
        ]
        detail = f"{len(bookmarks)} bookmarks found" if bookmarks else "no bookmarks found"
        return ArtifactAvailabilityEntry(
            artifact="bookmarks",
            available=bool(bookmarks),
            detail=detail,
            file_count=len(bookmarks),
            references=references,
        )

    def _annotations_entry(
        self,
        session_id: str,
        annotations: list[ReplayAnnotation],
    ) -> ArtifactAvailabilityEntry:
        references = [
            Reference(
                kind="event",
                label=annotation.type,
                session_id=session_id,
                event_id=annotation.event_id,
                event_index=annotation.event_index,
                media_time_ms=annotation.media_time_ms,
                value=annotation.annotation_id,
            )
            for annotation in annotations[:5]
        ]
        detail = (
            f"{len(annotations)} annotations found" if annotations else "no annotations found"
        )
        return ArtifactAvailabilityEntry(
            artifact="annotations",
            available=bool(annotations),
            detail=detail,
            file_count=len(annotations),
            references=references,
        )

    def _waveform_path(self, session_id: str) -> str | None:
        waveform_path = self._media_replay_service._waveform_service._get_waveform_path(
            session_id
        )
        return str(waveform_path) if isinstance(waveform_path, Path) else None


def resolve_replay_bundle(session_id: str) -> ResolvedReplayBundle:
    """Convenience entry point for service-layer callers."""

    return BundleResolver().resolve(session_id)


__all__ = ["BundleResolver", "ResolvedReplayBundle", "resolve_replay_bundle"]
