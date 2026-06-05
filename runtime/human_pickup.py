"""runtime/human_pickup.py — Detect live human agents during autonomous calls.

This is a safety gate. An autonomous agent must not converse with a live
human. When is_human_pickup() returns True with sufficient confidence,
the session_manager must hang up within 2 seconds.

Detection uses three signals in priority order:
  1. Twilio's AnsweredBy header (most reliable when available)
  2. Transcript keyword matching (human speech patterns vs IVR patterns)
  3. Words-per-second heuristic (very low wps = natural human pacing)

Tune thresholds after first 20 real calls reveal false positive/negative rates.
"""
from __future__ import annotations

import re

# Phrases characteristic of a live human agent greeting
_HUMAN_PATTERNS = re.compile(
    r'\b('
    r'how can i help( you)?'
    r'|my name is \w+'
    r'|this is \w+ (from|at|with|speaking)'
    r'|one moment please'
    r'|let me (pull up|look into|check)'
    r'|can i get your (name|account|number)'
    r'|i\'ll (transfer|connect|put) you'
    r'|how may i (assist|help)'
    r'|thank you for (holding|waiting), (this is|i\'m)'
    r')',
    re.IGNORECASE,
)

# Phrases characteristic of IVR systems (counter-signal)
_IVR_PATTERNS = re.compile(
    r'\b('
    r'press \d'
    r'|for \w[\w\s]{1,20} press'
    r'|please (hold|press|enter|say)'
    r'|thank you for calling'
    r'|our (menu|hours|office)'
    r'|to speak with a representative'
    r'|if you (know|would like)'
    r')',
    re.IGNORECASE,
)


def is_human_pickup(
    transcript: str,
    words_per_second: float | None = None,
    twilio_answered_by: str | None = None,
) -> tuple[bool, float]:
    """Determine whether a live human has answered the call.

    Args:
        transcript: The STT transcript to evaluate.
        words_per_second: WPS from ObservationQuality (None if unavailable).
        twilio_answered_by: Value from Twilio's AnsweredBy field, if available.
            Values: 'human', 'machine_start', 'machine_end_silence',
                    'machine_end_other', 'fax', 'unknown'

    Returns:
        (is_human, confidence) where confidence is in [0.0, 1.0].
        Caller should hang up when is_human=True AND confidence >= 0.65.
    """
    # Signal 1: Twilio's own classification (most authoritative)
    if twilio_answered_by == 'human':
        return True, 1.0
    if twilio_answered_by in ('machine_start', 'machine_end_silence',
                               'machine_end_other', 'fax'):
        return False, 0.92

    # Signal 2: Transcript pattern matching
    human_hits = len(_HUMAN_PATTERNS.findall(transcript))
    ivr_hits = len(_IVR_PATTERNS.findall(transcript))

    score = 0.0
    score += min(0.55, human_hits * 0.25)    # each human signal adds up to 0.25
    score -= min(0.40, ivr_hits * 0.20)      # each IVR signal subtracts

    # Signal 3: WPS heuristic
    # Natural human speech: 2.0–3.5 wps. IVR TTS: 3.5–5.0 wps.
    # Very slow (< 1.8 wps) with no IVR patterns = probably human.
    if words_per_second is not None and words_per_second < 1.8 and ivr_hits == 0:
        score += 0.20

    score = max(0.0, min(1.0, score))
    return score >= 0.65, score
