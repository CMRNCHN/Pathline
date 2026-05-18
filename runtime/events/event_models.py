from __future__ import annotations
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

@dataclass(frozen=True)
class EventMetadata:
    """Lineage and context for an operational event."""
    session_id: Optional[str] = None
    workspace_origin: Optional[str] = None
    state_id: Optional[str] = None
    path_id: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_component: Optional[str] = None
    replay_reference: Optional[str] = None
    unresolved_reference: Optional[str] = None
    escalation_reference: Optional[str] = None
    confidence: Optional[float] = None

    def as_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None}

@dataclass(frozen=True)
class OperationalEvent:
    """Base model for all operational telemetry in Pathline."""
    type: str
    payload: dict[str, Any] = field(default_factory=dict)
    meta: EventMetadata = field(default_factory=EventMetadata)

    def as_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "payload": self.payload,
            "meta": self.meta.as_dict()
        }