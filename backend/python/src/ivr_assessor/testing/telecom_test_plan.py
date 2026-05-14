from dataclasses import dataclass, field
from typing import Optional

@dataclass
class TelecomTestPlan:
    test_id: str
    name: str
    target_label: str
    target_number_ref: str  # Config/user input ref, not hardcoded number
    max_duration_seconds: int
    max_depth: int
    max_dtmf_actions: int
    allow_speech_injection: bool = False
    allow_human_transfer: bool = False
    recording_required: bool = True
    transcript_required: bool = True
    stop_on_transfer: bool = True
    stop_on_low_confidence: bool = True
    expected_initial_prompt: Optional[str] = None
    notes: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "test_id": self.test_id,
            "name": self.name,
            "target_label": self.target_label,
            "target_number_ref": self.target_number_ref,
            "max_duration_seconds": self.max_duration_seconds,
            "max_depth": self.max_depth,
            "max_dtmf_actions": self.max_dtmf_actions,
            "allow_speech_injection": self.allow_speech_injection,
            "allow_human_transfer": self.allow_human_transfer,
            "recording_required": self.recording_required,
            "transcript_required": self.transcript_required,
            "stop_on_transfer": self.stop_on_transfer,
            "stop_on_low_confidence": self.stop_on_low_confidence,
            "expected_initial_prompt": self.expected_initial_prompt,
            "notes": self.notes
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TelecomTestPlan":
        return cls(**data)
