from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime

@dataclass
class ReplayState:
    """Deterministic runtime state reconstructed from events."""
    session_id: str
    call_sid: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    nodes: Dict[str, Any] = field(default_factory=dict)
    edges: List[Any] = field(default_factory=list)
    transcripts: List[Dict[str, Any]] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    active_path: List[str] = field(default_factory=list)
    visited_nodes: List[str] = field(default_factory=list)
    dtmf_history: List[str] = field(default_factory=list)
    call_status: str = "unknown"
    
    # Media Metadata
    recording_reference: Optional[str] = None
    media_duration_ms: Optional[int] = None
    replay_anchor_timestamp: Optional[str] = None
    waveform_reference: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        """Serializable representation of the replay state."""
        return {
            "session_id": self.session_id,
            "call_sid": self.call_sid,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "nodes": self.nodes,
            "edges": self.edges,
            "transcripts": self.transcripts,
            "events": self.events,
            "metrics": self.metrics,
            "active_path": self.active_path,
            "visited_nodes": self.visited_nodes,
            "dtmf_history": self.dtmf_history,
            "call_status": self.call_status,
            "recording_reference": self.recording_reference,
            "media_duration_ms": self.media_duration_ms,
            "replay_anchor_timestamp": self.replay_anchor_timestamp,
            "waveform_reference": self.waveform_reference
        }

@dataclass
class ReplayCursor:
    """Pure, serializable replay position."""
    event_index: int
    event_id: str
    media_time_ms: int
    snapshot_anchor_offset: int = 0

    def as_dict(self) -> Dict[str, Any]:
        return {
            "event_index": self.event_index,
            "event_id": self.event_id,
            "media_time_ms": self.media_time_ms,
            "snapshot_anchor_offset": self.snapshot_anchor_offset
        }
