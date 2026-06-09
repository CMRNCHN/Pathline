"""runtime/stt/deepgram_client.py — Deepgram streaming STT over WebSocket.

Receives audio from an asyncio.Queue (fed by Twilio Media Streams),
connects to Deepgram's live transcription API, and calls on_transcript
for every result.

The caller decides what to do with each TranscriptEvent — this module is
pure infrastructure.

Requirements:
    pip install deepgram-sdk>=3.0.0
    Environment: DEEPGRAM_API_KEY

Usage in session_manager:
    client = DeepgramStreamClient(api_key=os.environ['DEEPGRAM_API_KEY'])
    await client.stream(audio_queue, on_transcript=handle_transcript)
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Awaitable, Callable

logger = logging.getLogger(__name__)


@dataclass
class TranscriptEvent:
    """One STT result from Deepgram."""

    text: str
    """The transcript text. May be empty for silence/noise frames."""

    is_final: bool
    """True = final result for this utterance; False = interim/partial."""

    confidence: float
    """Deepgram's transcript confidence [0.0, 1.0].
    Only meaningful for is_final=True results."""

    t_ms: int
    """Epoch milliseconds when this event was produced (client-side clock)."""

    duration_ms: int
    """Audio segment duration in milliseconds. Used to compute WPS."""

    channel: int = 0
    """Deepgram channel index (0 = inbound audio from IVR)."""

    words: list[dict] = field(default_factory=list)
    """Word-level timing data from Deepgram (for future use)."""


OnTranscript = Callable[[TranscriptEvent], Awaitable[None]]


class DeepgramStreamClient:
    """Stream audio to Deepgram and call on_transcript for each result.

    Args:
        api_key: Deepgram API key.
        language: BCP-47 language code (default: 'en-US').
        model: Deepgram model (default: 'nova-2-general').
    """

    _OPTIONS = {
        'model':            'nova-2-general',
        'language':         'en-US',
        'punctuate':        True,
        'smart_format':     True,
        'interim_results':  True,
        'utterance_end_ms': 1000,   # silence gap that ends an utterance
        'encoding':         'mulaw', # Twilio default codec
        'sample_rate':      8000,   # Twilio 8kHz
        'channels':         1,
    }

    def __init__(
        self,
        api_key: str,
        language: str = 'en-US',
        model: str = 'nova-2-general',
    ) -> None:
        self._api_key = api_key
        self._options = {**self._OPTIONS, 'language': language, 'model': model}

    async def stream(
        self,
        audio_queue: asyncio.Queue,
        on_transcript: OnTranscript,
    ) -> None:
        """Connect to Deepgram, consume audio_queue, fire on_transcript.

        Runs until audio_queue receives a sentinel None value, or until
        the Deepgram connection closes.

        Args:
            audio_queue: Queue of bytes (mulaw audio from Twilio) or None sentinel.
            on_transcript: Async callback invoked for every TranscriptEvent.
        """
        try:
            from deepgram import DeepgramClient, LiveTranscriptionEvents, LiveOptions
        except ImportError as e:
            raise RuntimeError(
                "deepgram-sdk is required: pip install deepgram-sdk>=3.0.0"
            ) from e

        dg = DeepgramClient(self._api_key)
        options = LiveOptions(**self._options)

        connection = dg.listen.asynclive.v('1')
        utterance_start_ms: dict[int, int] = {}

        async def _on_message(_, result, **__) -> None:
            channel = result.channel_index[0] if result.channel_index else 0
            alt = result.channel.alternatives[0] if result.channel.alternatives else None
            if not alt or not alt.transcript:
                return

            is_final = result.is_final
            now_ms = int(time.time() * 1000)

            # Track utterance start for duration calculation
            if channel not in utterance_start_ms:
                utterance_start_ms[channel] = now_ms
            duration_ms = now_ms - utterance_start_ms[channel]
            if is_final:
                utterance_start_ms.pop(channel, None)

            event = TranscriptEvent(
                text=alt.transcript,
                is_final=is_final,
                confidence=alt.confidence or 0.0,
                t_ms=now_ms,
                duration_ms=max(0, duration_ms),
                channel=channel,
                words=[w.__dict__ if hasattr(w, '__dict__') else {} for w in (alt.words or [])],
            )
            await on_transcript(event)

        async def _on_error(_, error, **__) -> None:
            logger.error('Deepgram error: %s', error)

        connection.on(LiveTranscriptionEvents.Transcript, _on_message)
        connection.on(LiveTranscriptionEvents.Error, _on_error)

        if not await connection.start(options):
            raise RuntimeError('Deepgram connection failed to start')

        logger.info('Deepgram streaming started')

        # Pump audio from queue to Deepgram
        try:
            while True:
                chunk = await audio_queue.get()
                if chunk is None:
                    break  # sentinel — call ended
                await connection.send(chunk)
        finally:
            await connection.finish()
            logger.info('Deepgram streaming finished')
