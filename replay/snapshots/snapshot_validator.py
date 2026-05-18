import logging
from replay.snapshots.replay_snapshot import ReplaySnapshot

logger = logging.getLogger(__name__)

class SnapshotValidator:
    """
    Validates snapshot integrity and consistency.
    """
    @staticmethod
    def validate_schema(snapshot: ReplaySnapshot) -> bool:
        """Basic schema validation."""
        required_fields = [
            "session_id", "snapshot_id", "created_at", "event_offset",
            "nodes", "edges", "transcripts", "metrics",
            "visited_nodes", "dtmf_history", "active_path", "call_status"
        ]
        for field in required_fields:
            if getattr(snapshot, field) is None:
                logger.warning(f"Snapshot {snapshot.snapshot_id} missing field {field}")
                return False
        return True

    @staticmethod
    def validate_consistency(snapshot: ReplaySnapshot) -> bool:
        """Validate chronological and logical consistency."""
        if snapshot.event_offset < 0:
            logger.warning(f"Snapshot {snapshot.snapshot_id} has negative offset")
            return False
            
        # Add more consistency checks if needed
        return True

    @classmethod
    def is_valid(cls, snapshot: ReplaySnapshot) -> bool:
        """Full validation check."""
        return cls.validate_schema(snapshot) and cls.validate_consistency(snapshot)