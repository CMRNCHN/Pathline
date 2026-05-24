from __future__ import annotations

import asyncio
from typing import Any

import structlog
from fastapi import WebSocket

log = structlog.get_logger()


class LiveBroadcaster:
    """WebSocket pub/sub hub: one connection per call_sid, fan-out to all subscribers."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[WebSocket]] = {}

    def subscribe(self, call_sid: str, ws: WebSocket) -> None:
        self._subscribers.setdefault(call_sid, []).append(ws)

    def unsubscribe(self, call_sid: str, ws: WebSocket) -> None:
        subs = self._subscribers.get(call_sid, [])
        if ws in subs:
            subs.remove(ws)

    async def _send(self, call_sid: str, payload: dict) -> None:
        subs = list(self._subscribers.get(call_sid, []))
        dead: list[WebSocket] = []
        for ws in subs:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.unsubscribe(call_sid, ws)

    async def broadcast_transcript(self, call_sid: str, segment: Any) -> None:
        # Map ConfidentSegment field names to what the dashboard expects.
        await self._send(
            call_sid,
            {
                "event": "transcript",
                "data": {
                    "text": segment.text,
                    "start": segment.start_time,
                    "end": segment.end_time,
                    "confidence": segment.confidence,
                    "final": segment.is_final,
                },
            },
        )

    async def broadcast_map_update(self, call_sid: str, cytoscape_data: dict) -> None:
        await self._send(call_sid, {"event": "map_update", "data": cytoscape_data})

    async def broadcast_dtmf(self, call_sid: str, dtmf: str) -> None:
        await self._send(call_sid, {"event": "dtmf", "data": {"dtmf": dtmf}})

    async def broadcast_voice(self, call_sid: str, text: str) -> None:
        await self._send(call_sid, {"event": "voice", "data": {"text": text}})
