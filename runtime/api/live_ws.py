from __future__ import annotations


import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from runtime.api import app_state

log = structlog.get_logger()
router = APIRouter()


@router.websocket("/live/{call_sid}")
async def live_ws(websocket: WebSocket, call_sid: str) -> None:
    """Dashboard connects here to receive live transcript + map events."""
    await websocket.accept()
    log.info("live_ws_connected", call_sid=call_sid)

    broadcaster = app_state.broadcaster
    broadcaster.subscribe(call_sid, websocket)

    # Send current session snapshot so the dashboard bootstraps without waiting.
    session_mgr = app_state.session_manager
    if session_mgr:
        session = session_mgr.get_session(call_sid)
        if session:
            for seg in session.transcript_segments:
                try:
                    await websocket.send_json({"event": "transcript", "data": seg})
                except Exception:
                    break
            cyto = session.flow_map.to_cytoscape()
            if cyto["elements"]:
                try:
                    await websocket.send_json({"event": "flow_map", "data": cyto})
                except Exception:
                    pass

    try:
        # Keep the connection alive until the client disconnects.
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        log.info("live_ws_disconnected", call_sid=call_sid)
    finally:
        broadcaster.unsubscribe(call_sid, websocket)
