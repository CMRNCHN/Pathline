#!/usr/bin/env python3
"""Interactive CLI to test call script phrase matching."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "packages" / "shared-python" / "src"))

from promptpath_shared.call_script import IVRNavigator, load_call_script  # noqa: E402

SECRETS = {"account_pin": "1234", "ssn_last4": "5678"}


def main() -> None:
    script_path = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "flows" / "lab-account-status.yaml")
    script = load_call_script(script_path)
    nav = IVRNavigator(script, SECRETS)

    print(f"Loaded: {script.name} ({script.id})")
    print(f"Start: {script.start_at}")
    print("Paste IVR phrases (empty line to quit). Type 'state' to show current state.\n")

    while True:
        try:
            line = input(f"[{nav.current_state}] IVR> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not line:
            break
        if line == "state":
            print(f"  state={nav.current_state} captured={nav.captured}")
            continue

        actions = nav.feed_transcript_replace(line)
        for action in actions:
            if action.type == "send_dtmf":
                print(f"  → SEND DTMF: {action.resolved_send!r}  (matched: {action.matched_hear!r})")
            elif action.type == "goto":
                print(f"  → GOTO: {action.state}")
            elif action.type == "capture":
                print(f"  → CAPTURE [{action.capture_key}]: {action.transcript[:80]}...")
            elif action.type == "discover":
                print(f"  ? DISCOVER — unmapped prompt at state '{action.state}'")
                print("    Add mapping: hear='...' send='...' goto='...'")
            elif action.type == "done":
                print(f"  ✓ DONE — captured: {nav.captured}")
            elif action.type == "fail":
                print(f"  ✗ FAIL at {action.state}")
            elif action.type == "wait":
                print(f"  … WAIT (no match yet)")


if __name__ == "__main__":
    main()
