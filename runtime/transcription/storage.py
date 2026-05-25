from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime

import numpy as np
import soundfile as sf
import structlog

from runtime.transcription.db import TranscriptDB

log = structlog.get_logger()


class TranscriptStorage:
    """
    Local file + SQLite storage. Audio → WAV, metadata → DB.
    Lives in Pathline/data/transcripts/
    """

    def __init__(
        self,
        audio_dir: str | Path = None,
        db_path: str | Path = None,
    ):
        if audio_dir is None:
            audio_dir = Path(__file__).parent.parent.parent / "data" / "transcripts"

        self.audio_dir = Path(audio_dir)
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.db = TranscriptDB(db_path)

    def save_call(
        self,
        call_sid: str,
        audio_pcm16: list[bytes],
        segments: list[dict],
        customer_id: str | None = None,
        invoice_id: str | None = None,
    ) -> dict:
        """
        Save audio + transcript to local storage + SQLite.
        Returns paths + call_id.
        """
        call_dir = self.audio_dir / call_sid
        call_dir.mkdir(exist_ok=True)

        if audio_pcm16:
            audio = np.concatenate(
                [np.frombuffer(chunk, dtype=np.int16) for chunk in audio_pcm16]
            )
            audio_path = call_dir / "audio.wav"
            sf.write(audio_path, audio, 16000, subtype="PCM_16")
            duration_seconds = len(audio) / 16000.0
        else:
            audio_path = None
            duration_seconds = None

        transcript_data = {
            "call_sid": call_sid,
            "timestamp": datetime.utcnow().isoformat(),
            "segments": segments,
        }
        transcript_path = call_dir / "transcript.json"
        with open(transcript_path, "w") as f:
            json.dump(transcript_data, f, indent=2)

        amounts = []
        dtmf = []
        min_confidence = 1.0
        for seg in segments:
            meta = seg.get("metadata", {})
            amounts.extend(meta.get("amounts", []))
            dtmf.extend(meta.get("dtmf", []))
            if "confidence" in seg:
                min_confidence = min(min_confidence, seg["confidence"])

        call_id = self.db.log_call(
            call_sid=call_sid,
            transcript_path=str(transcript_path),
            audio_path=str(audio_path),
            duration_seconds=duration_seconds,
            segments=segments,
            customer_id=customer_id,
            invoice_id=invoice_id,
            metadata={
                "amounts": amounts,
                "dtmf": dtmf,
                "min_confidence": min_confidence,
            },
        )

        log.info(
            "call_saved",
            call_sid=call_sid,
            call_id=call_id,
            audio_path=str(audio_path),
            transcript_path=str(transcript_path),
        )
        return {
            "call_id": call_id,
            "call_sid": call_sid,
            "audio_path": str(audio_path),
            "transcript_path": str(transcript_path),
        }
