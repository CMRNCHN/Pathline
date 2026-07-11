#!/usr/bin/env bash
# Smoke-test the lab YAML flow without Asterisk (phrase matching only).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

python3 -m pip install -q -e packages/shared-python

PHRASES=(
  "press 1 for account"
  "press 9 for touch tone"
  "enter your pin"
  "last four of your social"
  "press 1 for balance"
  "your balance is 1234 dollars"
)

printf '%s\n' "${PHRASES[@]}" | python3 "$ROOT/scripts/test-navigator.py" "$ROOT/flows/lab-account-status.yaml"
