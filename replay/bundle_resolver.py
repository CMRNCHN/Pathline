from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from replay.inspection_models import ArtifactAvailabilityEntry, ArtifactAvailabilitySection
from replay.snapshots.replay_snapshot import ReplaySnapshot
from replay.snapshots.snapshot_service import SnapshotService
from replay.timelines.replay_service import ReplayService
from replay.media_sync.media_replay_service import MediaReplayService
from runtime.state.replay_state import ReplayState
from runtime.events.bookmark_service import BookmarkService
from runtime.events.annotation_service import AnnotationService
from runtime.events.replay_bookmark import ReplayBookmark
from runtime.events.replay_annotation import ReplayAnnotation

@dataclass(frozen=True)
class ReplayBundle:
    """Resolved replay artifacts and their availability status."""
    session_id: str
    events: list[dict[str, Any]] = field(default_factory=list)
    state: Optional[ReplayState] = None
    latest_snapshot: Optional[ReplaySnapshot] = None
    media_metadata: dict[str, Any] = field(default_factory=dict)
    waveform_metadata: Optional[dict[str, Any]] = None
    bookmarks: list[ReplayBookmark] = field(default_factory=list)
    annotations: list[ReplayAnnotation] = field(default_factory=list)
    availability: ArtifactAvailabilitySection = field(default_factory=ArtifactAvailabilitySection)

class BundleResolver:
    """Resolves and aggregates all artifacts associated with a replay session."""
    
    def __init__(
        self,
        replay_service: Optional[ReplayService] = None,
        snapshot_service: Optional[SnapshotService] = None,
        media_service: Optional[MediaReplayService] = None,
        bookmark_service: Optional[BookmarkService] = None,
        annotation_service: Optional[AnnotationService] = None,
    ):
        self.replay_service = replay_service or ReplayService()
        self.snapshot_service = snapshot_service or SnapshotService()
        self.media_service = media_service or MediaReplayService()
        self.bookmark_service = bookmark_service or BookmarkService()
        self.annotation_service = annotation_service or AnnotationService()

    def resolve_bundle(self, session_id: str) -> ReplayBundle:
        """
        Locates and loads all available artifacts for a session.
        Returns a ReplayBundle containing raw artifacts and an availability section.
        """
        events: list[dict[str, Any]] = []
        event_file: Optional[Path] = None
        state: Optional[ReplayState] = None
        latest_snapshot: Optional[ReplaySnapshot] = None
        snapshot_dir: Optional[Path] = None
        snapshot_count = 0
        media_metadata: dict[str, Any] = {}
        waveform_metadata: Optional[dict[str, Any]] = None
        bookmarks: list[ReplayBookmark] = []
        annotations: list[ReplayAnnotation] = []

        entries: list[ArtifactAvailabilityEntry] = []
        missing: list[str] = []

        # 1. Resolve Events
        try:
            events = self.replay_service.get_raw_events(session_id)
            event_file = self.replay_service._find_session_file(session_id)
            events_available = bool(events)
            entries.append(ArtifactAvailabilityEntry(
                artifact="events",
                available=events_available,
                location=str(event_file) if event_file else None,
                detail=f"{len(events)} events found" if events_available else "No events found"
            ))
            if not events_available:
                missing.append("events")
        except Exception as e:
            entries.append(ArtifactAvailabilityEntry(
                artifact="events",
                available=False,
                detail=f"Error resolving events: {e}"
            ))
            missing.append("events")

        # 2. Resolve Replay State (reconstructed)
        try:
            state = self.replay_service.load_replay(session_id)
            state_available = state is not None
            entries.append(ArtifactAvailabilityEntry(
                artifact="reconstructed_state",
                available=state_available,
                detail="State successfully reconstructed from events" if state_available else "Failed to reconstruct state"
            ))
            if not state_available:
                missing.append("reconstructed_state")
        except Exception as e:
            entries.append(ArtifactAvailabilityEntry(
                artifact="reconstructed_state",
                available=False,
                detail=f"Error reconstructing state: {e}"
            ))
            missing.append("reconstructed_state")

        # 3. Resolve Snapshots
        try:
            latest_snapshot = self.snapshot_service.get_latest_snapshot(session_id)
            snapshot_dir = self.snapshot_service._find_session_dir(session_id)
            if snapshot_dir and snapshot_dir.exists():
                snapshot_count = len(list(snapshot_dir.glob("snapshot_*.json")))
            
            snapshots_available = snapshot_count > 0
            entries.append(ArtifactAvailabilityEntry(
                artifact="snapshots",
                available=snapshots_available,
                location=str(snapshot_dir) if snapshot_dir else None,
                detail=f"{snapshot_count} snapshots found" if snapshots_available else "No snapshots found",
                file_count=snapshot_count
            ))
            if not snapshots_available:
                missing.append("snapshots")
        except Exception as e:
            entries.append(ArtifactAvailabilityEntry(
                artifact="snapshots",
                available=False,
                detail=f"Error resolving snapshots: {e}"
            ))
            missing.append("snapshots")

        # 4. Resolve Media
        try:
            raw_media_meta = self.media_service.get_media_metadata(session_id)
            if raw_media_meta is None:
                entries.append(ArtifactAvailabilityEntry(
                    artifact="recording",
                    available=False,
                    detail="Media service returned no metadata"
                ))
                missing.append("recording")
                entries.append(ArtifactAvailabilityEntry(
                    artifact="waveform",
                    available=False,
                    detail="Media service returned no metadata"
                ))
                missing.append("waveform")
            else:
                media_metadata = raw_media_meta
                waveform_metadata = self.media_service.get_waveform_metadata(session_id)
                
                recording_available = media_metadata.get("recording_exists", False)
                entries.append(ArtifactAvailabilityEntry(
                    artifact="recording",
                    available=recording_available,
                    location=media_metadata.get("recording_path"),
                    detail="Recording found" if recording_available else "Recording missing"
                ))
                if not recording_available:
                    missing.append("recording")
                
                waveform_available = waveform_metadata is not None
                entries.append(ArtifactAvailabilityEntry(
                    artifact="waveform",
                    available=waveform_available,
                    detail="Waveform metadata available" if waveform_available else "Waveform metadata missing"
                ))
                if not waveform_available:
                    missing.append("waveform")
        except Exception as e:
            entries.append(ArtifactAvailabilityEntry(artifact="recording", available=False, detail=f"Error: {e}"))
            missing.append("recording")
            entries.append(ArtifactAvailabilityEntry(artifact="waveform", available=False, detail=f"Error: {e}"))
            missing.append("waveform")

        # 5. Resolve Bookmarks & Annotations
        # NOTE: Bookmarks and Annotations are recorded with available=False when missing,
        # but are NOT appended to availability.missing. This is intentional to separate
        # core replay artifacts from optional operator metadata.
        try:
            bookmarks = self.bookmark_service.get_bookmarks(session_id)
            bookmarks_available = len(bookmarks) > 0
            entries.append(ArtifactAvailabilityEntry(
                artifact="bookmarks",
                available=bookmarks_available,
                detail=f"{len(bookmarks)} bookmarks found" if bookmarks_available else "No bookmarks found"
            ))
        except Exception as e:
            entries.append(ArtifactAvailabilityEntry(artifact="bookmarks", available=False, detail=f"Error: {e}"))

        try:
            annotations = self.annotation_service.get_annotations(session_id)
            annotations_available = len(annotations) > 0
            entries.append(ArtifactAvailabilityEntry(
                artifact="annotations",
                available=annotations_available,
                detail=f"{len(annotations)} annotations found" if annotations_available else "No annotations found"
            ))
        except Exception as e:
            entries.append(ArtifactAvailabilityEntry(artifact="annotations", available=False, detail=f"Error: {e}"))

        availability = ArtifactAvailabilitySection(entries=entries, missing=missing)

        return ReplayBundle(
            session_id=session_id,
            events=events,
            state=state,
            latest_snapshot=latest_snapshot,
            media_metadata=media_metadata,
            waveform_metadata=waveform_metadata,
            bookmarks=bookmarks,
            annotations=annotations,
            availability=availability
        )

