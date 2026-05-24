from __future__ import annotations

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from runtime.api import app_state

log = structlog.get_logger()
router = APIRouter()


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


@router.get("/api/sessions/active")
async def get_active_sessions():
    sessions = app_state.session_manager.get_active_sessions()
    return {
        "sessions": [
            {
                "call_sid": s.call_sid,
                "phone_number": s.phone_number,
                "suite_name": s.suite_name,
                "started_at": s.started_at,
            }
            for s in sessions
        ]
    }


@router.get("/api/session/{call_sid}")
async def get_session(call_sid: str):
    session = app_state.session_manager.get_session(call_sid)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return app_state.session_manager.to_session_dict(session)


# ---------------------------------------------------------------------------
# Flow map
# ---------------------------------------------------------------------------


@router.get("/api/map/{call_sid}")
async def get_map(call_sid: str, format: str = "cytoscape"):
    session = app_state.session_manager.get_session(call_sid)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if format == "cytoscape":
        return session.flow_map.to_cytoscape()
    if format == "mermaid":
        return {"mermaid": session.flow_map.to_mermaid()}
    return session.flow_map.to_dict()


# ---------------------------------------------------------------------------
# DTMF injection
# ---------------------------------------------------------------------------


class DTMFRequest(BaseModel):
    call_sid: str
    dtmf: str


@router.post("/api/dtmf/send")
async def send_dtmf(req: DTMFRequest):
    generator = app_state.dtmf_generator
    if generator is None:
        raise HTTPException(status_code=503, detail="DTMF generator not initialised")
    await generator.inject_into_call(req.call_sid, req.dtmf)
    app_state.session_manager.record_dtmf_injection(req.call_sid, req.dtmf)
    await app_state.broadcaster.broadcast_dtmf(req.call_sid, req.dtmf)
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Voice injection
# ---------------------------------------------------------------------------


class VoiceRequest(BaseModel):
    call_sid: str
    text: str


@router.post("/api/voice/inject")
async def inject_voice(req: VoiceRequest):
    synth = app_state.voice_synthesizer
    if synth is None:
        raise HTTPException(status_code=503, detail="Voice synthesizer not initialised")
    await synth.inject_into_call(req.call_sid, req.text)
    app_state.session_manager.record_voice_injection(req.call_sid, req.text)
    await app_state.broadcaster.broadcast_voice(req.call_sid, req.text)
    return {"status": "ok"}
