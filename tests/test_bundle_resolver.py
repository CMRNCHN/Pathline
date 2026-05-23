import unittest
from unittest.mock import MagicMock
from pathlib import Path

from replay.bundle_resolver import BundleResolver, ReplayBundle
from replay.inspection_models import ArtifactAvailabilitySection
from runtime.state.replay_state import ReplayState
from replay.snapshots.replay_snapshot import ReplaySnapshot

class TestBundleResolver(unittest.TestCase):
    def setUp(self):
        self.replay_service = MagicMock()
        self.snapshot_service = MagicMock()
        self.media_service = MagicMock()
        self.bookmark_service = MagicMock()
        self.annotation_service = MagicMock()
        self.resolver = BundleResolver(
            replay_service=self.replay_service,
            snapshot_service=self.snapshot_service,
            media_service=self.media_service,
            bookmark_service=self.bookmark_service,
            annotation_service=self.annotation_service
        )

    def test_resolve_bundle_full_availability(self):
        session_id = "test_session_123"
        
        # Mocking ReplayService
        events = [{"kind": "prompt", "text": "Hello", "t_ms": 100}]
        self.replay_service.get_raw_events.return_value = events
        self.replay_service._find_session_file.return_value = Path("/tmp/session_test_session_123.jsonl")
        
        state = ReplayState(session_id=session_id)
        self.replay_service.load_replay.return_value = state
        
        # Mocking SnapshotService
        snapshot = ReplaySnapshot(
            session_id=session_id,
            snapshot_id="snap_1",
            created_at="2023-01-01T00:00:00",
            event_offset=1,
            nodes={},
            edges=[],
            transcripts=[],
            metrics={},
            visited_nodes=[],
            dtmf_history=[],
            active_path=[],
            call_status="completed"
        )
        self.snapshot_service.get_latest_snapshot.return_value = snapshot
        snapshot_dir = MagicMock(spec=Path)
        snapshot_dir.exists.return_value = True
        snapshot_dir.glob.return_value = [Path("snapshot_1.json")]
        self.snapshot_service._find_session_dir.return_value = snapshot_dir
        
        # Mocking MediaReplayService
        media_metadata = {
            "recording_exists": True,
            "recording_path": "/tmp/recording.wav"
        }
        self.media_service.get_media_metadata.return_value = media_metadata
        waveform_metadata = {"data": [0.1, 0.2]}
        self.media_service.get_waveform_metadata.return_value = waveform_metadata

        # Mocking Bookmarks & Annotations
        bookmarks = [MagicMock()]
        annotations = [MagicMock()]
        self.bookmark_service.get_bookmarks.return_value = bookmarks
        self.annotation_service.get_annotations.return_value = annotations
        
        bundle = self.resolver.resolve_bundle(session_id)
        
        self.assertIsInstance(bundle, ReplayBundle)
        self.assertEqual(bundle.session_id, session_id)
        self.assertEqual(bundle.events, events)
        self.assertEqual(bundle.state, state)
        self.assertEqual(bundle.latest_snapshot, snapshot)
        self.assertEqual(bundle.media_metadata, media_metadata)
        self.assertEqual(bundle.waveform_metadata, waveform_metadata)
        self.assertEqual(bundle.bookmarks, bookmarks)
        self.assertEqual(bundle.annotations, annotations)
        
        # Verify availability
        availability = bundle.availability
        self.assertIsInstance(availability, ArtifactAvailabilitySection)
        self.assertEqual(len(availability.missing), 0)
        
        available_artifacts = [entry.artifact for entry in availability.entries if entry.available]
        self.assertIn("events", available_artifacts)
        self.assertIn("reconstructed_state", available_artifacts)
        self.assertIn("snapshots", available_artifacts)
        self.assertIn("recording", available_artifacts)
        self.assertIn("waveform", available_artifacts)
        self.assertIn("bookmarks", available_artifacts)
        self.assertIn("annotations", available_artifacts)

    def test_resolve_bundle_partial_availability(self):
        session_id = "test_session_456"
        
        # Mocking ReplayService (only events available)
        events = [{"kind": "prompt", "text": "Hello", "t_ms": 100}]
        self.replay_service.get_raw_events.return_value = events
        self.replay_service._find_session_file.return_value = Path("/tmp/session_test_session_456.jsonl")
        self.replay_service.load_replay.return_value = None
        
        # Mocking SnapshotService (none available)
        self.snapshot_service.get_latest_snapshot.return_value = None
        self.snapshot_service._find_session_dir.return_value = None
        
        # Mocking MediaReplayService (none available)
        self.media_service.get_media_metadata.return_value = {"recording_exists": False}
        self.media_service.get_waveform_metadata.return_value = None

        # Mocking Bookmarks & Annotations (none available)
        self.bookmark_service.get_bookmarks.return_value = []
        self.annotation_service.get_annotations.return_value = []
        
        bundle = self.resolver.resolve_bundle(session_id)
        
        availability = bundle.availability
        missing_artifacts = set(availability.missing)
        self.assertIn("reconstructed_state", missing_artifacts)
        self.assertIn("snapshots", missing_artifacts)
        self.assertIn("recording", missing_artifacts)
        self.assertIn("waveform", missing_artifacts)
        self.assertNotIn("events", missing_artifacts)
        
        # Bookmarks/Annotations are not considered "required" in the same way (not in missing list usually)
        # but their available flag should be false
        entries_dict = {e.artifact: e.available for e in availability.entries}
        self.assertFalse(entries_dict["bookmarks"])
        self.assertFalse(entries_dict["annotations"])

    def test_resolve_bundle_handles_service_exceptions(self):
        session_id = "error_session"
        self.replay_service.get_raw_events.side_effect = FileNotFoundError("Missing file")
        
        bundle = self.resolver.resolve_bundle(session_id)
        
        availability = bundle.availability
        self.assertIn("events", availability.missing)
        
        # Verify detail contains error message
        events_entry = next(e for e in availability.entries if e.artifact == "events")
        self.assertFalse(events_entry.available)
        self.assertIn("Missing file", events_entry.detail)

    def test_resolve_bundle_handles_none_media_metadata(self):
        session_id = "none_media_session"
        self.media_service.get_media_metadata.return_value = None
        
        bundle = self.resolver.resolve_bundle(session_id)
        
        availability = bundle.availability
        self.assertIn("recording", availability.missing)
        self.assertIn("waveform", availability.missing)
        
        recording_entry = next(e for e in availability.entries if e.artifact == "recording")
        self.assertFalse(recording_entry.available)
        self.assertEqual(recording_entry.detail, "Media service returned no metadata")



if __name__ == "__main__":
    unittest.main()
