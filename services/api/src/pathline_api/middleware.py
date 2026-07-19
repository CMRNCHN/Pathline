from __future__ import annotations

import asyncio
import time
import uuid
from collections import defaultdict, deque

import structlog
from fastapi import HTTPException, Request, status
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class RequestSizeLimitMiddleware:
    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        content_length = headers.get(b"content-length")
        if content_length:
            try:
                if int(content_length) > self.max_bytes:
                    await self._reject(send)
                    return
            except ValueError:
                await self._reject(send)
                return

        received = 0
        rejected = False

        async def limited_receive() -> Message:
            nonlocal received, rejected
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    rejected = True
                    return {"type": "http.disconnect"}
            return message

        async def guarded_send(message: Message) -> None:
            if not rejected:
                await send(message)

        try:
            await self.app(scope, limited_receive, guarded_send)
        except Exception:
            if rejected:
                await self._reject(send)
                return
            raise
        if rejected:
            await self._reject(send)

    @staticmethod
    async def _reject(send: Send) -> None:
        body = b'{"detail":"Request body too large"}'
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})


class CorrelationIdMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_headers = dict(scope.get("headers", []))
        supplied = request_headers.get(b"x-request-id", b"").decode(errors="ignore")
        correlation_id = supplied if _valid_correlation_id(supplied) else str(uuid.uuid4())
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)

        async def add_header(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["X-Request-ID"] = correlation_id
            await send(message)

        try:
            await self.app(scope, receive, add_header)
        finally:
            structlog.contextvars.clear_contextvars()


def _valid_correlation_id(value: str) -> bool:
    return bool(value) and len(value) <= 64 and all(character.isalnum() or character in "-_." for character in value)


class RateLimiter:
    """Bounded per-process protection; production should also enforce limits at the edge."""

    def __init__(self, window_seconds: int, max_keys: int = 10_000) -> None:
        self.window_seconds = window_seconds
        self.max_keys = max_keys
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def check(self, key: str, limit: int) -> None:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        async with self._lock:
            bucket = self._requests[key]
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= limit:
                raise HTTPException(
                    status.HTTP_429_TOO_MANY_REQUESTS,
                    "Rate limit exceeded",
                    headers={"Retry-After": str(self.window_seconds)},
                )
            bucket.append(now)
            if len(self._requests) > self.max_keys:
                stale = [candidate for candidate, values in self._requests.items() if not values or values[-1] <= cutoff]
                for candidate in stale[: len(self._requests) - self.max_keys]:
                    self._requests.pop(candidate, None)


async def enforce_token_rate_limit(request: Request) -> None:
    client = request.client.host if request.client else "unknown"
    settings = request.app.state.settings
    await request.app.state.rate_limiter.check(f"token:{client}", settings.token_rate_limit)


async def enforce_authenticated_rate_limit(request: Request, owner: str) -> None:
    settings = request.app.state.settings
    await request.app.state.rate_limiter.check(f"owner:{owner}", settings.authenticated_rate_limit)
