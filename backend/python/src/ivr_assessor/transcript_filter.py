"""Transcript deduplication and noise gate.

Sits between STT output and the routing callbacks. Drops:
  - Results shorter than MIN_CHAR_COUNT (noise/artifacts)
  - Exact duplicates within a rolling window (last N utterances)

Confidence filtering is handled upstream in FasterWhisperTranscriber
(avg_logprob threshold) so it is not duplicated here.

Usage:
    filter = TranscriptFilter(on_transcript=my_callback)
    # Use filter as the on_transcript callback passed to the transcriber:
    transcriber = create_transcriber(on_transcript=filter, ...)
    # Call filter.reset() at the start of each new call.
"""
from __future__ import annotations

import logging
import re
from collections import deque
from typing import Callable

logger = logging.getLogger(__name__)

_PUNCT_RE = re.compile(r"[^\w\s]")


class TranscriptFilter:
    """Dedup + length gate between STT output and routing callbacks.

    The filter is callable and matches the `on_transcript` signature:
        filter(text: str, is_final: bool, speech_final: bool) -> None

    Pass it directly as `on_transcript` to the transcriber factory.
    """

    MIN_CHAR_COUNT = 2
    DEFAULT_WINDOW_SIZE = 3

    def __init__(
        self,
        on_transcript: Callable[[str, bool, bool], None],
        window_size: int = DEFAULT_WINDOW_SIZE,
    ) -> None:
        self._on_transcript = on_transcript
        self._window: deque[str] = deque(maxlen=window_size)
        self._received = 0
        self._passed = 0
        self._dropped_short = 0
        self._dropped_dedup = 0
        self._last_text: str = ""

    def __call__(self, text: str, is_final: bool, speech_final: bool) -> None:
        self._received += 1

        if len(text.strip()) < self.MIN_CHAR_COUNT:
            self._dropped_short += 1
            logger.debug("transcript dropped (too short %d chars): %r", len(text), text)
            return

        normalized = self._normalize(text)
        if normalized in self._window:
            self._dropped_dedup += 1
            logger.debug("transcript dropped (dedup): %r", text[:60])
            return

        self._window.append(normalized)
        self._passed += 1
        self._last_text = text
        try:
            self._on_transcript(text, is_final, speech_final)
        except Exception as exc:
            logger.error("on_transcript callback raised: %s", exc, exc_info=True)

    def _normalize(self, text: str) -> str:
        """Lowercase, strip punctuation, collapse whitespace."""
        return " ".join(_PUNCT_RE.sub("", text.lower()).split())

    def reset(self, *, reset_counters: bool = False) -> None:
        """Clear the dedup window — call at the start of each new call."""
        self._window.clear()
        if reset_counters:
            self._received = 0
            self._passed = 0
            self._dropped_short = 0
            self._dropped_dedup = 0
            self._last_text = ""

    def stats(self) -> dict[str, int | str]:
        stats: dict[str, int | str] = {
            "received": self._received,
            "passed": self._passed,
            "dropped_short": self._dropped_short,
            "dropped_dedup": self._dropped_dedup,
            "window_size": len(self._window),
        }
        if self._last_text:
            stats["last_text"] = self._last_text[:120]
        return stats
