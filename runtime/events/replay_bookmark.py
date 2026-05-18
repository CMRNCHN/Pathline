from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid

class BookmarkCategory(Enum):
    LOOP_START = "LOOP_START"
    PROMPT_MISMATCH = "PROMPT_MISMATCH"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    TRANSFER_POINT = "TRANSFER_POINT"
    DEAD_END = "DEAD_END"
    OPERATOR_NOTE = "OPERATOR_NOTE"
    AUDIO_GAP = "AUDIO_GAP"
    ROUTING_DRIFT = "ROUTING_DRIFT"
    RUNTIME_FAILURE = "RUNTIME_FAILURE"
    REVIEW_FINDING = "REVIEW_FINDING"

@dataclass
class ReplayBookmark:
    session_id: str
    event_id: str
    event_index: int
    media_time_ms: float
    label: str
    category: BookmarkCategory
    note: str
    source: str = "operator" # operator | system
    bookmark_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: datetime.isoformat(datetime.now()))

    def to_dict(self) -> dict:
        return {
            "bookmark_id": self.bookmark_id,
            "session_id": self.session_id,
            "event_id": self.event_id,
            "event_index": self.event_index,
            "media_time_ms": self.media_time_ms,
            "label": self.label,
            "category": self.category.value,
            "note": self.note,
            "created_at": self.created_at,
            "source": self.source
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ReplayBookmark":
        return cls(
            bookmark_id=data["bookmark_id"],
            session_id=data["session_id"],
            event_id=data["event_id"],
            event_index=data["event_index"],
            media_time_ms=data["media_time_ms"],
            label=data["label"],
            category=BookmarkCategory(data["category"]),
            note=data["note"],
            created_at=data["created_at"],
            source=data.get("source", "operator")
        )