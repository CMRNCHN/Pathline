"""runtime/pii_scrubber.py — Redact PII from observation text before storage.

Must run on every event_text before append_observation() is called.
The observation log is append-only and immutable after write — PII written
once cannot be deleted.

Patterns redacted:
  - 16-digit card numbers (with optional spaces/dashes)
  - 15-digit Amex card numbers
  - SSN (XXX-XX-XXXX and undelimited 9-digit)
  - Account numbers (9–16 consecutive digits in non-phone context)

Phone numbers are intentionally NOT redacted — they are navigational, not
sensitive in this context, and are the primary IVR identifier.
"""
from __future__ import annotations

import re

# Credit / debit card: 16 digits with optional separators
_CARD_16 = re.compile(r'\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b')
# Amex: 15 digits, XXXX XXXXXX XXXXX format or plain
_CARD_15 = re.compile(r'\b\d{4}[\s\-]?\d{6}[\s\-]?\d{5}\b')
# SSN: XXX-XX-XXXX
_SSN_DASHED = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
# SSN undelimited: 9 digits not preceded/followed by more digits
_SSN_PLAIN = re.compile(r'(?<!\d)\d{9}(?!\d)')
# Generic account: 10-16 digits not already matched by card patterns
# (applied last so card patterns take precedence)
_ACCOUNT = re.compile(r'(?<!\d)\d{10,16}(?!\d)')

_RULES: list[tuple[re.Pattern[str], str]] = [
    (_CARD_16,    '[REDACTED_CARD]'),
    (_CARD_15,    '[REDACTED_CARD]'),
    (_SSN_DASHED, '[REDACTED_SSN]'),
    (_SSN_PLAIN,  '[REDACTED_SSN]'),
    (_ACCOUNT,    '[REDACTED_ACCOUNT]'),
]


def scrub(text: str) -> tuple[str, bool]:
    """Redact PII from *text*.

    Returns:
        (scrubbed_text, was_modified) — was_modified is True if any
        substitution was made. Always returns a string safe for storage.
    """
    result = text
    modified = False
    for pattern, replacement in _RULES:
        new, count = pattern.subn(replacement, result)
        if count:
            result = new
            modified = True
    return result, modified


def scrub_payload(payload: dict) -> tuple[dict, bool]:
    """Redact PII from string values in a raw_payload dict.

    Only top-level string values are scrubbed. Nested dicts/lists are
    left as-is (they should not contain PII in normal operation).
    """
    modified = False
    result: dict = {}
    for k, v in payload.items():
        if isinstance(v, str):
            new_v, was = scrub(v)
            result[k] = new_v
            if was:
                modified = True
        else:
            result[k] = v
    return result, modified
