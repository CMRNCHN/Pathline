#!/usr/bin/env python3
"""IVR Card Status Probe — standalone CLI.

Makes a single call to the IVR, sends the two DTMF entries (**11 + card number),
captures the spoken response, matches it against the configured status keywords,
and prints the result.

Usage
-----
    python tools/ivr_probe/probe.py --card 4111111111111111

    # Override target number
    python tools/ivr_probe/probe.py --card 4111111111111111 --phone +18009505114

    # Use a custom suite file
    python tools/ivr_probe/probe.py --card 4111111111111111 --suite path/to/suite.json

    # Dry-run (no real call, useful for testing the script itself)
    python tools/ivr_probe/probe.py --card 4111111111111111 --dry-run

Required env vars (for live calls)
-----------------------------------
    TWILIO_ACCOUNT_SID
    TWILIO_AUTH_TOKEN
    TWILIO_PHONE_NUMBER   (your Twilio outbound caller ID)

Output
------
    STATUS:     green
    TRANSCRIPT: please enter your five digit zip code
    MATCHED:    five_digit_zipcode

    If no keyword matches:
    STATUS:     UNKNOWN
    TRANSCRIPT: <raw IVR text>
    MATCHED:    (none)
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import re
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Allow running from repo root or from this directory.
_HERE = Path(__file__).parent
_REPO_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from analyst.telecom.run_suites.loader import import_suite_json
from analyst.telecom.run_suites.models import (
    RunSuite,
    TestScenario,
    TestStep,
    StepAction,
)
from analyst.telecom.run_suites.runner import SuiteRunner
from analyst.telecom.run_suites.status import SuiteRunStatus

_TEMPLATE_RE = re.compile(r"\{\{([A-Z0-9_]+)\}\}")
_DEFAULT_SUITE = _HERE / "suite.json"


def _load_suite(suite_path: Path) -> RunSuite:
    with suite_path.open(encoding="utf-8") as f:
        return import_suite_json(f.read())


def _build_probe_suite(suite: RunSuite, card_number: str, target_number: str | None) -> RunSuite:
    """Return a new RunSuite with a single scenario that captures transcript without
    asserting any expected_text_contains — so the call always completes and we
    match keywords ourselves afterward."""

    base = suite.base_steps
    if not base:
        raise ValueError("Suite has no base_steps — cannot build probe scenario.")

    resolved: list[TestStep] = []
    for step in base:
        cloned = copy.copy(step)
        if cloned.input_value:
            cloned.input_value = _TEMPLATE_RE.sub(
                lambda m: card_number if m.group(1) == "CARD_NUMBER" else m.group(0),
                cloned.input_value,
            )
        # Strip expected_text_contains from transcript step — we want it to always
        # capture, not fail on a non-match.
        if cloned.action == StepAction.WAIT_FOR_TRANSCRIPT:
            cloned.expected_text_contains = None
        resolved.append(cloned)

    probe_scenario = TestScenario(
        scenario_id="probe",
        name="IVR Probe",
        steps=resolved,
        target_number=target_number or suite.target_number or "",
    )

    return RunSuite(
        suite_id="ivr_probe_run",
        name="IVR Probe Run",
        target_number=target_number or suite.target_number or "",
        scenarios=[probe_scenario],
    )


def _collect_status_rules(suite: RunSuite) -> list[tuple[str, str]]:
    """Return [(keyword, status_label), ...] from all scenarios that have both."""
    rules = []
    for sc in suite.scenarios:
        if sc.expected_text_contains and sc.ivr_status_label:
            rules.append((sc.expected_text_contains.lower(), sc.ivr_status_label))
    return rules


def _match_status(transcript: str, rules: list[tuple[str, str]]) -> tuple[str, str]:
    """Return (status_label, matched_keyword). First match wins. Status is uppercased."""
    t = transcript.lower()
    for keyword, label in rules:
        if keyword in t:
            return label.upper(), keyword
    return "UNMATCHED", ""


def run(
    card_number: str,
    suite_path: Path = _DEFAULT_SUITE,
    target_number: str | None = None,
    telephony: Any = None,
    dry_run: bool = False,
) -> dict[str, str]:
    """Run the probe. Returns {status, transcript, matched_keyword}."""
    suite = _load_suite(suite_path)
    rules = _collect_status_rules(suite)
    probe_suite = _build_probe_suite(suite, card_number, target_number)

    runner = SuiteRunner(suite=probe_suite, telephony=None if dry_run else telephony)

    if dry_run:
        # Inject a fake transcript so the wait_for_transcript step passes.
        def _inject():
            time.sleep(0.2)
            runner.push_transcript("[dry-run] no real call made", is_final=True, speech_final=True)
        threading.Thread(target=_inject, daemon=True).start()

    runner.start()
    runner._thread.join(timeout=120)

    result = runner.run_result
    if result is None:
        return {"status": "ERROR", "transcript": "", "matched_keyword": ""}

    # Pull the transcript from the wait_for_transcript step result.
    transcript = ""
    for sc_result in result.scenario_results:
        for step_result in sc_result.step_results:
            if step_result.transcript_snippet:
                transcript = step_result.transcript_snippet
                break

    if result.status == SuiteRunStatus.ERRORED:
        return {"status": "ERROR", "transcript": transcript, "matched_keyword": ""}

    status, matched = _match_status(transcript, rules)
    return {"status": status, "transcript": transcript, "matched_keyword": matched}


def _build_telephony(target_number: str) -> Any:
    sid = os.environ.get("TWILIO_ACCOUNT_SID", "")
    token = os.environ.get("TWILIO_AUTH_TOKEN", "")
    from_num = os.environ.get("TWILIO_PHONE_NUMBER", "")
    if not all([sid, token, from_num]):
        print(
            "ERROR: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_PHONE_NUMBER "
            "must be set for live calls.\nUse --dry-run to test without a real call.",
            file=sys.stderr,
        )
        sys.exit(1)
    from runtime.telephony.twilio_client import TwilioTelephonyClient
    return TwilioTelephonyClient(
        account_sid=sid,
        auth_token=token,
        twilio_number=from_num,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="IVR card status probe")
    parser.add_argument("--card", required=True, help="Card number to probe")
    parser.add_argument("--phone", help="Override target IVR phone number")
    parser.add_argument("--suite", type=Path, default=_DEFAULT_SUITE, help="Suite JSON path")
    parser.add_argument("--dry-run", action="store_true", help="Skip real call, inject fake transcript")
    parser.add_argument(
        "--format", choices=["text", "json"], default="text",
        help="Output format (default: text)"
    )
    args = parser.parse_args()

    telephony = None
    if not args.dry_run:
        suite = _load_suite(args.suite)
        number = args.phone or suite.target_number
        telephony = _build_telephony(number)

    if args.format == "text":
        print(f"Probing card: {'*' * (len(args.card) - 4)}{args.card[-4:]}  (calling IVR...)")

    outcome = run(
        card_number=args.card,
        suite_path=args.suite,
        target_number=args.phone,
        telephony=telephony,
        dry_run=args.dry_run,
    )

    if args.format == "json":
        print(json.dumps(outcome))
    else:
        print()
        print(f"STATUS:     {outcome['status']}")
        print(f"TRANSCRIPT: {outcome['transcript'] or '(none captured)'}")
        print(f"MATCHED:    {outcome['matched_keyword'] or '(none)'}")


if __name__ == "__main__":
    main()
