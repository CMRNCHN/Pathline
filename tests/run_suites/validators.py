"""Validation functions for run suite step assertions."""
from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# PAN patterns: 13–19 digit sequences (with optional separators)
# Catches Visa, MC, Amex, Discover, and generic long-digit strings.
_PAN_RE = re.compile(
    r"""
    (?<!\d)          # no digit before
    (?:
        \d{4}[-\s]?  # 4-digit group with optional separator
    ){3,4}
    \d{1,4}          # final partial group
    (?!\d)           # no digit after
    """,
    re.VERBOSE,
)

# Luhn check to reduce false positives
def _luhn_check(digits: str) -> bool:
    nums = [int(c) for c in digits if c.isdigit()]
    if len(nums) < 13:
        return False
    total = 0
    for i, n in enumerate(reversed(nums)):
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def contains_raw_pan(text: str) -> bool:
    """Return True if text contains what looks like a raw card number."""
    stripped = re.sub(r"[\s\-]", "", text)
    for m in _PAN_RE.finditer(text):
        digits = re.sub(r"\D", "", m.group(0))
        if len(digits) >= 13 and _luhn_check(digits):
            return True
    # Also check the fully-stripped version for runs of digits
    digit_runs = re.findall(r"\d{13,19}", stripped)
    for run in digit_runs:
        if _luhn_check(run):
            return True
    return False


def validate_text_contains(actual: str | None, expected: str) -> tuple[bool, str]:
    """Check that actual transcript contains expected substring (case-insensitive).

    Returns (passed, reason).
    """
    if actual is None:
        return False, f"No transcript received (expected to contain: {expected!r})"
    if expected.lower() in actual.lower():
        return True, ""
    return False, f"Expected text {expected!r} not found in: {actual!r}"


def validate_expected_event(
    received_event: str | None, expected_event: str
) -> tuple[bool, str]:
    """Check that received_event matches expected_event."""
    if received_event is None:
        return False, f"No event received (expected: {expected_event!r})"
    if received_event == expected_event:
        return True, ""
    return False, f"Expected event {expected_event!r} but got {received_event!r}"


def validate_intent(actual_intent: str | None, expected_intent: str) -> tuple[bool, str]:
    """Check that detected intent matches expected."""
    if actual_intent is None:
        return False, f"No intent detected (expected: {expected_intent!r})"
    if actual_intent.lower() == expected_intent.lower():
        return True, ""
    return False, f"Expected intent {expected_intent!r} but got {actual_intent!r}"


def validate_node(actual_node: str | None, expected_node: str) -> tuple[bool, str]:
    """Check that the current routing node matches expected."""
    if actual_node is None:
        return False, f"No node event received (expected: {expected_node!r})"
    if actual_node == expected_node:
        return True, ""
    return False, f"Expected node {expected_node!r} but at {actual_node!r}"


def validate_no_pan_in_payload(payload: dict[str, Any]) -> tuple[bool, str]:
    """Scan every string value in payload for raw PAN. Fail if found."""
    flagged: list[str] = []
    for key, val in payload.items():
        if isinstance(val, str) and contains_raw_pan(val):
            flagged.append(key)
    if flagged:
        return False, f"Raw card number detected in payload fields: {flagged}"
    return True, ""


def validate_no_pan_in_log(log_lines: list[str]) -> tuple[bool, str]:
    """Scan log lines for raw PANs. Fail if any found."""
    for i, line in enumerate(log_lines):
        if contains_raw_pan(line):
            return False, f"Raw card number detected in log line {i + 1}"
    return True, ""


def validate_secure_card_token(token: str | None) -> tuple[bool, str]:
    """Check that a secure card token is present and looks like a token (not a PAN)."""
    if not token:
        return False, "No secure card token present"
    if contains_raw_pan(token):
        return False, f"Token appears to be a raw PAN rather than an opaque token: {token!r}"
    # Tokens should not be all digits
    if token.isdigit():
        return False, f"Token is all digits — likely a raw PAN: {token!r}"
    return True, ""


def validate_secure_card_deleted(deleted_flag: bool | None) -> tuple[bool, str]:
    if deleted_flag:
        return True, ""
    return False, "Secure card was not deleted as expected"