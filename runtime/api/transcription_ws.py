from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import structlog

from runtime.transcription.streaming_whisper import StreamingWhisperTranscriber
from runtime.transcription.storage import TranscriptStorage
from runtime.telephony.media_handler import TwilioMediaReceiver

log = structlog.get_logger()
router = APIRouter()

transcriber = StreamingWhisperTranscriber(
    initial_prompt="IVR phone menu: press 1, press 2, amount, dollars, cents."
)
storage = TranscriptStorage()


@router.websocket("/transcribe/{call_sid}")
async def transcribe_ws(websocket: WebSocket, call_sid: str):
    """
    Twilio Media Stream WebSocket endpoint.
    Receives audio, transcribes in real-time, stores locally.
    """
    await websocket.accept()
    log.info("transcribe_ws_accepted", call_sid=call_sid)

    audio_chunks = []
    segments = []

    try:
        async def chunk_generator():
            async for chunk in TwilioMediaReceiver.handle_media_stream(websocket):
                audio_chunks.append(chunk)
                yield chunk

        async for segment in transcriber.stream_transcribe(chunk_generator()):
            segments.append(
                {
                    "text": segment.text,
                    "raw_text": segment.raw_text,
                    "start": segment.start_time,
                    "end": segment.end_time,
                    "confidence": segment.confidence,
                    "final": segment.is_final,
                    "metadata": segment.metadata,
                }
            )

            await websocket.send_json(
                {
                    "event": "transcript",
                    "segment": {
                        "text": segment.text,
                        "start": segment.start_time,
                        "end": segment.end_time,
                        "confidence": segment.confidence,
                        "metadata": segment.metadata,
                    },
                }
            )

            log.info(
                "segment_transcribed",
                call_sid=call_sid,
                text=segment.text[:80],
                confidence=segment.confidence,
                final=segment.is_final,
            )

    except WebSocketDisconnect:
        log.info("transcribe_ws_disconnected", call_sid=call_sid)

    except Exception as e:
        log.error("transcribe_ws_error", call_sid=call_sid, error=str(e))
        raise

    finally:
        paths = storage.save_call(call_sid, audio_chunks, segments)
        log.info("call_complete", call_sid=call_sid, segments=len(segments), call_id=paths["call_id"])
