#!/usr/bin/env bash
# Preflight the lab stack, then smoke-test the lab flow (phrase matching only).
#
# Fails fast with a clear message if the API or the lab Asterisk SIP/TLS port
# is not up, so the desktop automation path (docs/lab-run.md) is not run
# against a half-started lab. Non-interactive and safe to run in CI.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

API_PORT="${API_PORT:-8000}"
API_HEALTH_URL="${API_HEALTH_URL:-http://127.0.0.1:${API_PORT}/health}"
SIP_HOST="${LAB_SIP_SERVER:-127.0.0.1}"
SIP_TLS_PORT="${LAB_SIP_TLS_PORT:-5061}"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

info() { printf '%b\n' "${GREEN}▸${NC} $*"; }
fail() {
  printf '%b\n' "${RED}✗${NC} $*" >&2
  printf '%b\n' "  Start the lab first:  ${GREEN}./scripts/lab.sh${NC}  (see docs/lab-run.md)" >&2
  exit 1
}

# ── Preflight: API health ──────────────────────────────────────
info "Checking API health at ${API_HEALTH_URL} ..."
if ! curl -sf "$API_HEALTH_URL" >/dev/null 2>&1; then
  fail "API is not responding at ${API_HEALTH_URL}."
fi

# ── Preflight: lab Asterisk SIP/TLS port ───────────────────────
info "Checking lab Asterisk SIP/TLS on ${SIP_HOST}:${SIP_TLS_PORT} ..."
if ! (exec 3<>"/dev/tcp/${SIP_HOST}/${SIP_TLS_PORT}") 2>/dev/null; then
  fail "Lab Asterisk SIP/TLS port ${SIP_HOST}:${SIP_TLS_PORT} is not open."
fi
exec 3>&- 2>/dev/null || true

info "Preflight OK — API healthy, SIP/TLS ${SIP_TLS_PORT} open."

# ── Flow smoke test (phrase matching only, no call) ────────────
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
