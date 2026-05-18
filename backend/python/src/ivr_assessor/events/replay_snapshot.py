from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass(frozen=True)
class ReplaySnapshot:
    """
    Immutable operational checkpoint of a ReplayState.
    """
    session_id: str
    snapshot_id: str
    created_at: Optional[str]
    event_offset: int
    nodes: Dict[str, Any]
    edges: List[Any]
    transcripts: List[Dict[str, Any]]
    metrics: Dict[str, Any]
    visited_nodes: List[str]
    dtmf_history: List[str]
    active_path: List[str]
    call_status: str
    events: List[Dict[str, Any]] = field(default_factory=list)
    updated_at: Optional[str] = None
    call_sid: Optional[str] = None
    recording_reference: Optional[str] = None
    media_duration_ms: Optional[int] = None
    replay_anchor_timestamp: Optional[str] = None
    waveform_reference: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert snapshot to a serializable dictionary."""
        return {
            "session_id": self.session_id,
            "snapshot_id": self.snapshot_id,
            "created_at": self.created_at,
            "event_offset": self.event_offset,
            "nodes": self.nodes,
            "edges": self.edges,
            "transcripts": self.transcripts,
            "metrics": self.metrics,
            "visited_nodes": self.visited_nodes,
            "dtmf_history": self.dtmf_history,
            "active_path": self.active_path,
            "call_status": self.call_status,
            "events": self.events,
            "updated_at": self.updated_at,
            "call_sid": self.call_sid,
            "recording_reference": self.recording_reference,
            "media_duration_ms": self.media_duration_ms,
            "replay_anchor_timestamp": self.replay_anchor_timestamp,
            "waveform_reference": self.waveform_reference
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReplaySnapshot":
        """Create a snapshot from a dictionary."""
        return cls(
            session_id=data["session_id"],
            snapshot_id=data["snapshot_id"],
            created_at=data["created_at"],
            event_offset=data["event_offset"],
            nodes=data["nodes"],
            edges=data["edges"],
            transcripts=data["transcripts"],
            metrics=data["metrics"],
            visited_nodes=data["visited_nodes"],
            dtmf_history=data["dtmf_history"],
            active_path=data["active_path"],
            call_status=data["call_status"],
            events=data.get("events", []),
            updated_at=data.get("updated_at"),
            call_sid=data.get("call_sid"),
            recording_reference=data.get("recording_reference"),
            media_duration_ms=data.get("media_duration_ms"),
            replay_anchor_timestamp=data.get("replay_anchor_timestamp"),
            waveform_reference=data.get("waveform_reference")
        )
