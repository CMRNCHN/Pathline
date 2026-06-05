"""runtime/observation_quality.py — Thin observation quality assessment.

Five fields only. Anything more is premature until real STT failures
are observed in production.

Used as a pre-write gate in session_manager.py:
  quality = assess(obs_id, text, confidence, is_final, duration_ms)
  if not quality.stt_is_final:
      return  # skip — wait for final transcript
  if quality.is_suspicious:
      log warning but still write — don't drop, tag for review
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class ObservationQuality:
    observation_id: str
    stt_confidence: float       # raw confidence from Deepgram [0.0, 1.0]
    stt_is_final: bool          # True = final transcript; False = interim/partial
    words_per_second: float | None   # None if duration_ms == 0
    is_suspicious: bool         # high confidence + very low wps = hallucination signal
    assessed_at: datetime


def assess(
    observation_id: str,
    transcript: str,
    confidence: float,
    is_final: bool,
    duration_ms: int,
) -> ObservationQuality:
    """Assess quality of a single STT event.

    Args:
        observation_id: The obs_id this quality record covers.
        transcript: The raw STT text.
        confidence: STT provider confidence [0.0, 1.0].
        is_final: Whether Deepgram marked this as a final (not interim) result.
        duration_ms: Audio segment duration in milliseconds.

    Returns:
        ObservationQuality with five fields.
    """
    word_count = len(transcript.split()) if transcript.strip() else 0

    if duration_ms > 0 and word_count > 0:
        wps = word_count / (duration_ms / 1000.0)
    else:
        wps = None

    # Suspicious: confident transcript but suspiciously few words per second.
    # Real IVR prompts run 2–4 wps. Below 1.0 at high confidence = likely
    # hallucination (STT is "hearing" music or silence as coherent speech).
    suspicious = (
        is_final
        and confidence > 0.80
        and wps is not None
        and wps < 1.0
        and word_count >= 3   # single-word transcripts can be legitimately slow
    )

    return ObservationQuality(
        observation_id=observation_id,
        stt_confidence=confidence,
        stt_is_final=is_final,
        words_per_second=wps,
        is_suspicious=suspicious,
        assessed_at=datetime.now(timezone.utc),
    )
