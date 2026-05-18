from pathlib import Path
from typing import Optional, Dict, Any

from infrastructure.config.paths import RECORDINGS_DIR
from replay.media_sync.waveform_metadata import WaveformService

class MediaReplayService:
    """
    Responsibilities:
    * Resolve recording references
    * Serve media metadata
    * Serve waveform metadata
    * Provide timestamp -> byte/time lookup (future-facing)
    * Provide event_index ↔ media_offset lookup (via replay state)
    """
    
    def __init__(self, waveform_service: Optional[WaveformService] = None):
        self._waveform_service = waveform_service or WaveformService()

    def get_media_metadata(self, session_id: str) -> Dict[str, Any]:
        """
        Returns metadata about the recording for a session.
        """
        recording_path = self.resolve_recording_path(session_id)
        exists = recording_path.exists() if recording_path else False
        
        return {
            "session_id": session_id,
            "recording_exists": exists,
            "recording_path": str(recording_path) if exists else None,
            "media_url": f"/api/replays/{session_id}/media/stream" if exists else None,
            "content_type": "audio/wav" # Default for Twilio recordings we save
        }

    def resolve_recording_path(self, session_id: str) -> Optional[Path]:
        """
        Locates the recording file on disk for a given session.
        Matches recordings stored in RECORDINGS_DIR/YYYY-MM-DD/session_{session_id}.wav
        """
        # Search recursively in RECORDINGS_DIR as they are partitioned by date
        for path in RECORDINGS_DIR.rglob(f"session_{session_id}.wav"):
            return path
        return None

    def get_waveform_metadata(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Returns waveform visualization metadata.
        """
        metadata = self._waveform_service.get_waveform_for_session(session_id)
        if metadata:
            return metadata.as_dict()
        return None

    def get_replay_cursor_at_time(self, session_id: str, media_time_ms: int) -> Optional[Dict[str, Any]]:
        """
        Calculates the replay cursor (active event, etc.) for a specific media time.
        This usually requires loading the replay state.
        """
        # This will be called by the API layer which has access to ReplayService
        return None
