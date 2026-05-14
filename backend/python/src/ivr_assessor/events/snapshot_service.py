import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any

from .replay_snapshot import ReplaySnapshot
from .replay_state import ReplayState
from ..backend.ui.ui_state import SNAPSHOTS_DIR

logger = logging.getLogger(__name__)

class SnapshotService:
    """
    Handles snapshot creation, persistence, and discovery.
    """
    def __init__(self, snapshots_dir: Path = SNAPSHOTS_DIR):
        self.snapshots_dir = snapshots_dir

    def create_snapshot(self, state: ReplayState, event_offset: int) -> ReplaySnapshot:
        """Create a ReplaySnapshot from a ReplayState."""
        snapshot_id = f"snap_{event_offset}_{int(datetime.now().timestamp())}"
        return ReplaySnapshot(
            session_id=state.session_id,
            snapshot_id=snapshot_id,
            created_at=state.created_at,
            event_offset=event_offset,
            nodes=state.nodes.copy(),
            edges=state.edges.copy(),
            transcripts=state.transcripts.copy(),
            metrics=state.metrics.copy(),
            visited_nodes=state.visited_nodes.copy(),
            dtmf_history=state.dtmf_history.copy(),
            active_path=state.active_path.copy(),
            call_status=state.call_status,
            events=state.events.copy(),
            updated_at=state.updated_at,
            call_sid=state.call_sid,
            recording_reference=state.recording_reference,
            media_duration_ms=state.media_duration_ms,
            replay_anchor_timestamp=state.replay_anchor_timestamp,
            waveform_reference=state.waveform_reference
        )

    def persist_snapshot(self, snapshot: ReplaySnapshot) -> Path:
        """Save a snapshot to disk."""
        # Storage layout: ~/.ivr_assessor/snapshots/YYYY-MM-DD/session_<id>/snapshot_<offset>.json
        # Use current date for folder if created_at is not a valid ISO date
        try:
            date_str = datetime.fromisoformat(snapshot.created_at).strftime("%Y-%m-%d")
        except (TypeError, ValueError):
            date_str = datetime.now().strftime("%Y-%m-%d")
            
        session_dir = self.snapshots_dir / date_str / f"session_{snapshot.session_id}"
        session_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = session_dir / f"snapshot_{snapshot.event_offset}.json"
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(snapshot.to_dict(), f, indent=2)
            
        logger.info(f"Persisted snapshot to {file_path}")
        return file_path

    def load_snapshot(self, session_id: str, event_offset: int) -> Optional[ReplaySnapshot]:
        """Load a specific snapshot from disk."""
        session_dir = self._find_session_dir(session_id)
        if not session_dir:
            return None
            
        file_path = session_dir / f"snapshot_{event_offset}.json"
        if not file_path.exists():
            return None
            
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return ReplaySnapshot.from_dict(data)
        except Exception:
            logger.exception(f"Failed to load snapshot from {file_path}")
            return None

    def get_latest_snapshot(self, session_id: str) -> Optional[ReplaySnapshot]:
        """Find the snapshot with the largest event_offset for a session."""
        session_dir = self._find_session_dir(session_id)
        if not session_dir:
            return None
            
        snapshots = list(session_dir.glob("snapshot_*.json"))
        if not snapshots:
            return None
            
        # Extract offset from filename snapshot_<offset>.json
        def get_offset(path: Path) -> int:
            try:
                return int(path.stem.split("_")[1])
            except (IndexError, ValueError):
                return -1
        
        latest_snapshot_path = max(snapshots, key=get_offset)
        
        try:
            with open(latest_snapshot_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return ReplaySnapshot.from_dict(data)
        except Exception:
            logger.exception(f"Failed to load latest snapshot from {latest_snapshot_path}")
            return None

    def _find_session_dir(self, session_id: str) -> Optional[Path]:
        """Locate the session directory within the snapshots directory."""
        if not self.snapshots_dir.exists():
            return None
            
        for date_dir in self.snapshots_dir.iterdir():
            if date_dir.is_dir():
                session_dir = date_dir / f"session_{session_id}"
                if session_dir.exists():
                    return session_dir
        return None
