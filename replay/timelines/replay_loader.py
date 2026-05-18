import json
import logging
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

class ReplayLoader:
    """
    Loads JSONL event streams for operational replay and session reconstruction.
    """
    def __init__(self, file_path: Path):
        self.file_path = file_path

    def load_events(self) -> List[dict]:
        """Load all events from the JSONL file in order."""
        events = []
        if not self.file_path.exists():
            logger.error(f"Event log file not found: {self.file_path}")
            return events

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            events.append(json.loads(line))
                        except json.JSONDecodeError:
                            logger.warning(f"Skipping malformed JSON line in {self.file_path}")
        except Exception:
            logger.exception(f"Error reading event log {self.file_path}")
        
        return events

    def get_session_id(self) -> Optional[str]:
        """Extract session_id from the first event."""
        events = self.load_events()
        if events:
            return events[0].get("session_id")
        return None

    def get_timeline(self) -> List[dict]:
        """Return events sorted by timestamp."""
        events = self.load_events()
        # Prefer meta.timestamp for sorting if available
        return sorted(events, key=lambda x: x.get("meta", {}).get("timestamp") or x.get("ts", 0))