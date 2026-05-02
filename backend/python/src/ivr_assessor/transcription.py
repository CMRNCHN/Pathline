# cspell:ignore deepgram mulaw endpointing

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)

# Connect parameter variants tried in order. Different Deepgram SDK builds accept
# different shapes for boolean-style flags (some want native bools, some want the
# strings "true"/"false"). The autofix layer walks this list until one succeeds,
# then remembers the winning shape on the class for the next connection.
_CONNECT_PARAM_VARIANTS: list[dict[str, Any]] = [
    {"smart_format": "true", "interim_results": "true"},
    {"smart_format": True, "interim_results": True},
    {"smart_format": "true", "interim_results": True},
    {"smart_format": True, "interim_results": "true"},
]

_MODEL_FALLBACKS: list[str] = ["nova-3", "nova-2", "nova", "base"]


def _get(obj: Any, key: str, default: Any = None) -> Any:
    """Read a field from either an object (attr) or a mapping (key)."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _extract_transcript(message: Any) -> str:
    """Pull the first alternative's transcript from any reasonable Deepgram
    result shape (typed object, raw dict, or future variant). Returns "" if
    the shape doesn't match — callers treat empty as "skip"."""
    channel = _get(message, "channel")
    if channel is None:
        return ""
    alternatives = _get(channel, "alternatives") or []
    if not alternatives:
        return ""
    first = alternatives[0]
    return (_get(first, "transcript", "") or "").strip()


class DeepgramTranscriber:
    """Streams Twilio mulaw audio to Deepgram and emits transcripts.

    Built against the Deepgram Python SDK v7 async API:
        async with client.listen.v1.connect(...) as socket:
            await socket.send_media(audio_bytes)

    Includes an autofix layer that tries multiple parameter shapes / model names
    on first connect and caches the winning combination.
    """

    # Cached winning connect parameters. Persists across instances within the
    # same process so the second call doesn't re-probe.
    _learned_connect_params: dict[str, Any] | None = None
    _learned_model: str | None = None

    def __init__(
        self,
        on_transcript: Callable[[str, bool, bool], None] | None = None,
        on_status: Callable[[str], None] | None = None,
    ):
        # on_transcript receives (text, is_final, speech_final).
        #   is_final     — Deepgram has finalized this 1-2s chunk's words.
        #   speech_final — endpointing detected a real pause (caller stopped).
        # Push to a prompt mapper only when speech_final is True; accumulate
        # is_final chunks until then. Treating them as the same flag fragments
        # IVR menu prompts mid-sentence.
        self.on_transcript = on_transcript
        self.on_status = on_status

        api_key = os.getenv("DEEPGRAM_API_KEY", "")
        if not api_key:
            self._notify("[deepgram] DEEPGRAM_API_KEY not set in environment")
            logger.warning("DEEPGRAM_API_KEY missing — transcriber will be disabled")

        self._api_key = api_key
        self._client: Any = None
        self._connect_cm: Any = None
        self._socket: Any = None
        self._recv_task: asyncio.Task[None] | None = None

        # Diagnostic counters — surfaced via stats() and periodic logging.
        self._frames_sent = 0
        self._bytes_sent = 0
        self._messages_received = 0
        self._transcripts_emitted = 0
        self._connect_attempts = 0
        self._connect_started_at: float | None = None
        self._last_send_at: float | None = None

        try:
            from deepgram import AsyncDeepgramClient

            self._client = AsyncDeepgramClient(api_key=api_key) if api_key else None
            logger.debug("DeepgramTranscriber initialized (client=%s)", bool(self._client))
        except ImportError as exc:
            self._notify(f"[deepgram] SDK not installed: {exc}")
            logger.warning("Deepgram SDK not installed: %s", exc)

    def _notify(self, msg: str) -> None:
        logger.debug("notify: %s", msg)
        if self.on_status:
            try:
                self.on_status(msg)
            except Exception as exc:
                logger.error("on_status callback raised: %s", exc)

    async def connect(self) -> bool:
        if self._client is None:
            self._notify("[deepgram] no client — cannot connect")
            return False

        self._connect_started_at = time.monotonic()
        cls = type(self)

        # Fast path: a previous successful connection taught us the right shape.
        if cls._learned_connect_params is not None and cls._learned_model is not None:
            self._connect_attempts += 1
            logger.debug(
                "connect attempt %d: using learned params model=%s flags=%s",
                self._connect_attempts,
                cls._learned_model,
                cls._learned_connect_params,
            )
            if await self._try_connect(cls._learned_model, cls._learned_connect_params):
                return True
            logger.warning("learned connect params failed — re-probing")
            cls._learned_connect_params = None
            cls._learned_model = None

        # Probe path: walk variants until one sticks.
        last_error: Exception | None = None
        for model in _MODEL_FALLBACKS:
            for variant in _CONNECT_PARAM_VARIANTS:
                self._connect_attempts += 1
                logger.debug(
                    "connect attempt %d: model=%s variant=%s",
                    self._connect_attempts,
                    model,
                    variant,
                )
                try:
                    if await self._try_connect(model, variant):
                        cls._learned_model = model
                        cls._learned_connect_params = variant
                        logger.info(
                            "connect: success after %d attempts (model=%s, variant=%s)",
                            self._connect_attempts,
                            model,
                            variant,
                        )
                        return True
                except Exception as exc:
                    last_error = exc
                    logger.debug("variant failed: %s", exc)

        self._notify(f"[deepgram] all connect variants failed: {last_error}")
        logger.error("connect: exhausted %d variants, last error=%s", self._connect_attempts, last_error)
        return False

    async def _try_connect(self, model: str, variant: dict[str, Any]) -> bool:
        try:
            self._connect_cm = self._client.listen.v1.connect(
                model=model,
                language="en-US",
                encoding="mulaw",
                sample_rate=8000,
                channels=1,
                # 500ms of silence ⇒ Deepgram emits speech_final=True. Without
                # this, speech_final never fires and prompts stay fragmented.
                endpointing=500,
                **variant,
            )
            self._socket = await self._connect_cm.__aenter__()
            self._recv_task = asyncio.create_task(self._recv_loop())
            elapsed = (time.monotonic() - (self._connect_started_at or time.monotonic())) * 1000
            logger.info("Deepgram connection started in %.1f ms", elapsed)
            return True
        except Exception as exc:
            logger.debug("_try_connect failed: %s", exc)
            self._notify(f"[deepgram] connect attempt failed: {exc}")
            self._socket = None
            if self._connect_cm is not None:
                try:
                    await self._connect_cm.__aexit__(type(exc), exc, exc.__traceback__)
                except Exception:
                    pass
            self._connect_cm = None
            return False

    async def _recv_loop(self) -> None:
        logger.debug("recv loop: starting")
        try:
            async for message in self._socket:
                self._messages_received += 1
                if self._messages_received <= 3 or self._messages_received % 50 == 0:
                    logger.debug(
                        "recv #%d: type=%s",
                        self._messages_received,
                        type(message).__name__,
                    )
                self._handle_message(message)
        except asyncio.CancelledError:
            logger.debug("recv loop: cancelled")
            raise
        except Exception as exc:
            logger.error("recv loop error: %s", exc, exc_info=True)
            self._notify(f"[deepgram] recv error: {exc}")
        finally:
            logger.debug(
                "recv loop: exiting (messages=%d transcripts=%d)",
                self._messages_received,
                self._transcripts_emitted,
            )

    def _handle_message(self, message: Any) -> None:
        # Duck-type the response: SDK upgrades have repeatedly renamed/restructured
        # the result type, so checking for a usable shape is more durable than
        # isinstance(message, ListenV1Results).
        sentence = _extract_transcript(message)
        if not sentence:
            return
        is_final = bool(_get(message, "is_final", False))
        speech_final = bool(_get(message, "speech_final", False))
        self._transcripts_emitted += 1
        logger.debug(
            "transcript #%d (is_final=%s speech_final=%s len=%d): %s",
            self._transcripts_emitted,
            is_final,
            speech_final,
            len(sentence),
            sentence[:80],
        )
        if self.on_transcript:
            try:
                self.on_transcript(sentence, is_final, speech_final)
            except Exception as exc:
                logger.error("on_transcript callback raised: %s", exc, exc_info=True)

    async def process_audio(self, audio_data: bytes) -> None:
        if self._socket is None:
            if self._frames_sent == 0:
                logger.warning("process_audio called with no socket — frames will be dropped")
            return
        try:
            await self._socket.send_media(audio_data)
            self._frames_sent += 1
            self._bytes_sent += len(audio_data)
            self._last_send_at = time.monotonic()
            if self._frames_sent <= 3 or self._frames_sent % 100 == 0:
                logger.debug(
                    "send #%d: %d bytes (total=%d)",
                    self._frames_sent,
                    len(audio_data),
                    self._bytes_sent,
                )
        except Exception as exc:
            logger.error("send error on frame %d: %s", self._frames_sent + 1, exc)
            self._notify(f"[deepgram] send error: {exc}")

    async def close(self) -> None:
        logger.debug(
            "close: frames_sent=%d bytes_sent=%d messages=%d transcripts=%d",
            self._frames_sent,
            self._bytes_sent,
            self._messages_received,
            self._transcripts_emitted,
        )
        if self._socket is not None:
            try:
                await self._socket.send_close_stream()
            except Exception as exc:
                logger.debug("close: send_close_stream failed: %s", exc)

        if self._recv_task is not None:
            self._recv_task.cancel()
            try:
                await self._recv_task
            except (asyncio.CancelledError, Exception):
                pass
            self._recv_task = None

        if self._connect_cm is not None:
            try:
                await self._connect_cm.__aexit__(None, None, None)
            except Exception as exc:
                logger.debug("close: __aexit__ failed: %s", exc)
            self._connect_cm = None

        self._socket = None
        logger.debug("close: done")

    def stats(self) -> dict[str, Any]:
        return {
            "frames_sent": self._frames_sent,
            "bytes_sent": self._bytes_sent,
            "messages_received": self._messages_received,
            "transcripts_emitted": self._transcripts_emitted,
            "connect_attempts": self._connect_attempts,
            "connected": self._socket is not None,
            "last_send_age_ms": (
                None
                if self._last_send_at is None
                else int((time.monotonic() - self._last_send_at) * 1000)
            ),
        }
