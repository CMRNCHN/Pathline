from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Form

from .recording_pipeline import process_recording

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/webhooks/recording-complete")
async def recording_complete(
    background_tasks: BackgroundTasks,
    CallSid: str = Form(...),
    RecordingUrl: str = Form(...),
    RecordingSid: str = Form(...)
) -> dict[str, Any]:
    logger.info("Recording webhook received", extra={
        "call_sid": CallSid,
        "recording_sid": RecordingSid,
    })
    background_tasks.add_task(process_recording, RecordingUrl, CallSid, RecordingSid)
    return {"status": "received"}
