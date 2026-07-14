from __future__ import annotations

from collections import deque
from datetime import UTC, datetime

from fastapi import FastAPI

from pathline_shared.logging_config import configure_logging, get_logger
from pathline_shared.models import NotificationPayload

configure_logging("notifications")
logger = get_logger("notifications")

app = FastAPI(title="Pathline Notifications", version="0.1.0")

# In-memory store for dev — production would use webhook/email/push
_notifications: deque[dict] = deque(maxlen=100)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "notifications", "queued": len(_notifications)}


@app.post("/v1/notify")
async def notify(payload: NotificationPayload):
    entry = {
        **payload.model_dump(),
        "received_at": datetime.now(UTC).isoformat(),
    }
    _notifications.appendleft(entry)
    logger.info(
        "notification_sent",
        event=payload.event,
        severity=payload.severity,
        session_id=payload.session_id,
    )
    return {"delivered": True}


@app.get("/v1/notifications")
async def list_notifications(limit: int = 20):
    return list(_notifications)[:limit]
