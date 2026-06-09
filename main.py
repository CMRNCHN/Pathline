from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from runtime.api import app_state
from runtime.api.control import router as control_router
from runtime.api.live_broadcast import LiveBroadcaster
from runtime.api.live_ws import router as live_ws_router
from runtime.api.static import mount_static
from runtime.api.suites import router as suites_router
from runtime.api.transcription_ws import router as transcription_router
from runtime.dtmf.generator import DTMFGenerator
from runtime.kernel.startup_runtime import configure_logging
from runtime.sessions.session import SessionManager
from runtime.transcription.storage import TranscriptStorage
from runtime.transcription.streaming_whisper import StreamingWhisperTranscriber
from runtime.voice.synthesizer import VoiceSynthesizer

log = structlog.get_logger()


def _load_suites() -> dict:
    suites_path = Path(os.environ.get("PATHLINE_SUITES", "suites.json"))
    if suites_path.exists():
        try:
            return json.loads(suites_path.read_text())
        except Exception as exc:
            log.warning("suites_load_failed", path=str(suites_path), error=str(exc))
    return {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    log.info("pathline_startup")

    # Core services
    app_state.session_manager = SessionManager()
    app_state.broadcaster = LiveBroadcaster()
    app_state.storage = TranscriptStorage()
    app_state.transcriber = StreamingWhisperTranscriber(
        initial_prompt="IVR phone menu: press 1, press 2, amount, dollars, cents."
    )

    from runtime.telephony import build_telephony
    app_state.twilio_client = build_telephony()
    app_state.dtmf_generator = DTMFGenerator(app_state.twilio_client)
    app_state.voice_synthesizer = VoiceSynthesizer(app_state.twilio_client)
    log.info("telephony_client_ready", mode=os.getenv("TELEPHONY_MODE", "mock"))

    app_state.SUITES = _load_suites()
    log.info("suites_loaded", count=len(app_state.SUITES))

    yield

    log.info("pathline_shutdown")


def create_app() -> FastAPI:
    app = FastAPI(title="Pathline", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(control_router)
    app.include_router(suites_router)
    app.include_router(transcription_router)
    app.include_router(live_ws_router)

    mount_static(app)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        reload=True,
    )
