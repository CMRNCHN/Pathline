#!/usr/bin/env python3
"""
Live demo: walk through the test IVR using AsteriskTelephonyClient.
Run from repo root:  python scripts/demo_ivr.py
"""
import os
import sys
import time

os.environ["TELEPHONY_MODE"] = "asterisk"

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from runtime.telephony.asterisk_client import AsteriskTelephonyClient

RESET  = "\033[0m"
BOLD   = "\033[1m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
CYAN   = "\033[36m"
GRAY   = "\033[90m"

def banner(text): print(f"\n{BOLD}{CYAN}{'─'*50}{RESET}\n{BOLD}{text}{RESET}")
def step(text):   print(f"  {YELLOW}▶{RESET}  {text}")
def ok(text):     print(f"  {GREEN}✔{RESET}  {text}")
def info(text):   print(f"  {GRAY}{text}{RESET}")


def run_scenario(name, digits, description):
    banner(f"Scenario: {name}")
    client = AsteriskTelephonyClient()

    step(f"Dialling IVR extension 1000…")
    sid = client.dial("+15550001000")
    ok(f"Call originated  sid={sid}")

    step("Waiting for IVR to answer and play menu (2s)…")
    time.sleep(2)

    for digit in digits:
        step(f"Sending DTMF  '{digit}'  — {description}")
        client.send_dtmf(sid, digit)
        time.sleep(1)

    step("Hanging up…")
    client.hangup(sid)
    ok("Done.\n")


def main():
    print(f"\n{BOLD}Pathline IVR Demo — Asterisk local PBX{RESET}")
    print("IVR menu:  1=status  2=echo  9=hangup  other=reprompt")

    run_scenario("Press 1 → System OK",    ["1"], "status check")
    run_scenario("Press 9 → clean hangup", ["9"], "clean exit")
    run_scenario("Invalid → reprompt → invalid → hangup", ["5", "5"], "error handling")

    banner("All scenarios complete")
    print("  Check Asterisk logs for full call trace:")
    print("  docker compose -f infrastructure/docker-compose.yml logs asterisk --tail=40\n")


if __name__ == "__main__":
    main()
