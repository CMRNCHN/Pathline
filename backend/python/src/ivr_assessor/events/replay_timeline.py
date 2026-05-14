import logging
from typing import Any, Dict, List, Optional
from .replay_state import ReplayState

class ReplayTimeline:
    """
    Deterministic timeline controller for operational replay.
    Maintains a cursor and handles navigation through the event stream.
    """
    def __init__(self, session_id: str, events: List[Dict[str, Any]]):
        self.session_id = session_id
        self.events = events
        self.cursor_position = 0
        self.total_events = len(events)
        self.reconstructed_state: Optional[ReplayState] = None

    def step_forward(self) -> int:
        """Move cursor forward by one event."""
        if self.cursor_position < self.total_events:
            self.cursor_position += 1
        return self.cursor_position

    def step_backward(self) -> int:
        """Move cursor backward by one event."""
        if self.cursor_position > 0:
            self.cursor_position -= 1
        return self.cursor_position

    def seek(self, position: int) -> int:
        """Jump to a specific event offset."""
        if position < 0:
            self.cursor_position = 0
        elif position > self.total_events:
            self.cursor_position = self.total_events
        else:
            self.cursor_position = position
        return self.cursor_position

    def seek_to_timestamp(self, ts: str) -> int:
        """Seek to the event closest to but not exceeding the given timestamp."""
        # Events are assumed to be sorted by timestamp
        for i, event in enumerate(self.events):
            event_ts = event.get("meta", {}).get("timestamp")
            if event_ts and event_ts > ts:
                self.cursor_position = i
                return self.cursor_position
        
        self.cursor_position = self.total_events
        return self.cursor_position

    def current_event(self) -> Optional[Dict[str, Any]]:
        """Return the event at the current cursor position."""
        if 0 < self.cursor_position <= self.total_events:
            return self.events[self.cursor_position - 1]
        return None

    def get_summary(self) -> Dict[str, Any]:
        """Return a summary of the timeline state."""
        return {
            "session_id": self.session_id,
            "cursor_position": self.cursor_position,
            "total_events": self.total_events
        }
