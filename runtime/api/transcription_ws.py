from __future__ import annotations

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from runtime.api import app_state
from runtime.telephony.media_handler import TwilioMediaReceiver

log = structlog.get_logger()
router = APIRouter()


@router.websocket("/transcribe/{call_sid}")
async def transcribe_ws(websocket: WebSocket, call_sid: str) -> None:
    """
    Twilio Media Stream endpoint.
    Receives mulaw audio, transcribes it, stores segments, and fans them out
    to all dashboard subscribers via LiveBroadcaster.
    """
    await websocket.accept()
    log.info("transcribe_ws_accepted", call_sid=call_sid)

    session_mgr = app_state.session_manager
    broadcaster = app_state.broadcaster
    transcriber = app_state.transcriber
    storage = app_state.storage

    session = session_mgr.get_or_create(call_sid)
    audio_chunks: list[bytes] = []
    segments: list[dict] = []

    try:
        async def chunk_generator():
            async for chunk in TwilioMediaReceiver.handle_media_stream(websocket):
                audio_chunks.append(chunk)
                yield chunk

        async for seg in transcriber.stream_transcribe(chunk_generator()):
            segment_dict = {
                "text": seg.text,
                "raw_text": seg.raw_text,
                "start": seg.start_time,
                "end": seg.end_time,
                "confidence": seg.confidence,
                "final": seg.is_final,
            }
            segments.append(segment_dict)
            session_mgr.add_transcript_segment(call_sid, segment_dict)

            await broadcaster.broadcast_transcript(call_sid, seg)

            # Re-broadcast updated map after each new node.
            cyto = session.flow_map.to_cytoscape()
            await broadcaster.broadcast_map_update(call_sid, cyto)

            log.info(
                "segment_transcribed",
                call_sid=call_sid,
                text=seg.text[:80],
                confidence=seg.confidence,
            )

    except WebSocketDisconnect:
        log.info("transcribe_ws_disconnected", call_sid=call_sid)

    except Exception as exc:
        log.error("transcribe_ws_error", call_sid=call_sid, error=str(exc))
        raise

    finally:
        session_mgr.close_session(call_sid)
        if storage and segments:
            paths = storage.save_call(call_sid, audio_chunks, segments)
            log.info("call_saved", call_sid=call_sid, **paths)
