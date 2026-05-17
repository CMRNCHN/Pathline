from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid

class AnnotationSeverity(Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

@dataclass
class ReplayAnnotation:
    session_id: str
    event_id: str
    event_index: int
    media_time_ms: float
    type: str
    text: str
    severity: AnnotationSeverity
    annotation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: datetime.isoformat(datetime.now()))
    revision_of: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "annotation_id": self.annotation_id,
            "session_id": self.session_id,
            "event_id": self.event_id,
            "event_index": self.event_index,
            "media_time_ms": self.media_time_ms,
            "type": self.type,
            "text": self.text,
            "severity": self.severity.value,
            "created_at": self.created_at,
            "revision_of": self.revision_of
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ReplayAnnotation":
        return cls(
            annotation_id=data["annotation_id"],
            session_id=data["session_id"],
            event_id=data["event_id"],
            event_index=data["event_index"],
            media_time_ms=data["media_time_ms"],
            type=data["type"],
            text=data["text"],
            severity=AnnotationSeverity(data["severity"]),
            created_at=data["created_at"],
            revision_of=data.get("revision_of")
        )
