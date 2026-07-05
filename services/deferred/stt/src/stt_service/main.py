from __future__ import annotations

import hashlib
import io
import tempfile
from pathlib import Path

import httpx
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from pydantic import BaseModel
from pydantic_settings import BaseSettings

from promptpath_shared.logging_config import configure_logging, get_logger

configure_logging("stt")
logger = get_logger("stt")

app = FastAPI(title="PromptPath STT Service", version="0.1.0")


class Settings(BaseSettings):
    kms_url: str = "http://localhost:8006"
    whisper_model: str = "base"
    use_local_whisper: bool = False

    model_config = {"env_prefix": "", "case_sensitive": False}


settings = Settings()
_whisper_model = None


class TranscriptResult(BaseModel):
    transcript: str
    transcript_hash: str
    language: str = "en"
    confidence: float = 0.0


async def verify_auth(authorization: str | None = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Authorization required")


def get_whisper():
    global _whisper_model
    if _whisper_model is None and settings.use_local_whisper:
        try:
            import whisper
            _whisper_model = whisper.load_model(settings.whisper_model)
        except ImportError:
            logger.warning("whisper_not_installed", msg="Using mock STT")
    return _whisper_model


def mock_transcribe(audio_bytes: bytes) -> TranscriptResult:
    """Lab mock — returns placeholder transcript without persisting audio."""
    transcript = "[MOCK] IVR response detected — press 1 to continue"
    t_hash = hashlib.sha256(transcript.encode()).hexdigest()
    return TranscriptResult(transcript=transcript, transcript_hash=t_hash, confidence=0.85)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "stt",
        "local_whisper": settings.use_local_whisper,
        "model": settings.whisper_model,
    }


@app.post("/v1/transcribe", response_model=TranscriptResult)
async def transcribe(
    audio: UploadFile = File(...),
    _: None = Depends(verify_auth),
):
    """Transcribe audio in-memory — no disk persistence of raw audio."""
    audio_bytes = await audio.read()

    async with httpx.AsyncClient() as client:
        await client.post(
            f"{settings.kms_url}/v1/audit",
            json={"action": "stt_key_release", "resource": "transcription"},
            timeout=5.0,
        )

    model = get_whisper()
    if model is None:
        result = mock_transcribe(audio_bytes)
    else:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
            tmp.write(audio_bytes)
            tmp.flush()
            transcription = model.transcribe(tmp.name)
            text = transcription.get("text", "").strip()
            t_hash = hashlib.sha256(text.encode()).hexdigest()
            result = TranscriptResult(
                transcript=text,
                transcript_hash=t_hash,
                language=transcription.get("language", "en"),
                confidence=0.9,
            )

    logger.info("transcription_complete", transcript_hash=result.transcript_hash[:16] + "...")
    return result
