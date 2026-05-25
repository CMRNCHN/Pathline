from __future__ import annotations

import asyncio

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from runtime.api import app_state

log = structlog.get_logger()
router = APIRouter()


@router.get("/api/suites")
async def list_suites():
    return {"suites": app_state.SUITES}


class SuiteExecuteRequest(BaseModel):
    call_sid: str
    suite_name: str


@router.post("/api/suites/execute")
async def execute_suite(req: SuiteExecuteRequest):
    suite = app_state.SUITES.get(req.suite_name)
    if suite is None:
        raise HTTPException(status_code=404, detail=f"Suite '{req.suite_name}' not found")

    steps = suite.get("steps", [])
    generator = app_state.dtmf_generator
    synth = app_state.voice_synthesizer

    for step in steps:
        kind = step.get("type")
        delay = step.get("delay_ms", 0) / 1000.0

        if kind == "dtmf" and generator:
            digits = step.get("digits", "")
            await generator.inject_into_call(req.call_sid, digits)
            await app_state.broadcaster.broadcast_dtmf(req.call_sid, digits)

        elif kind == "voice" and synth:
            text = step.get("text", "")
            await synth.inject_into_call(req.call_sid, text)
            await app_state.broadcaster.broadcast_voice(req.call_sid, text)

        if delay > 0:
            await asyncio.sleep(delay)

    return {"status": "ok", "steps_executed": len(steps)}
