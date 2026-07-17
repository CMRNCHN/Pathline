#!/usr/bin/env bash
# Verify the desktop lab automation loop.
#
# Two phases:
#   1. Static desktop-config assertions (no running stack required) — prove the
#      Tauri SIP bridge exposes the frozen commands, the lab Path is
#      desktop-automation-ready (target 1000 + autoListen), and the DTMF audit
#      records a hash/count, never plaintext digits.
#   2. Live preflight + phrase-matching smoke test — fail fast with a clear
#      message if the API or the lab Asterisk SIP/TLS port is not up, so the
#      desktop automation path (docs/lab-run.md) is never run against a
#      half-started lab.
#
# The live phase is guarded: set SKIP_LAB_PREFLIGHT=1 to run only the static
# desktop assertions (useful on a headless host with no Docker/Asterisk). The
# static phase always runs. Non-interactive and safe to run in CI.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

API_PORT="${API_PORT:-8000}"
API_HEALTH_URL="${API_HEALTH_URL:-http://127.0.0.1:${API_PORT}/health}"
SIP_HOST="${LAB_SIP_SERVER:-127.0.0.1}"
SIP_TLS_PORT="${LAB_SIP_TLS_PORT:-5061}"
SKIP_LAB_PREFLIGHT="${SKIP_LAB_PREFLIGHT:-0}"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

info() { printf '%b\n' "${GREEN}▸${NC} $*"; }
ok()   { printf '%b\n' "  ${GREEN}✓${NC} $*"; }
fail() {
  printf '%b\n' "${RED}✗${NC} $*" >&2
  printf '%b\n' "  Start the lab first:  ${GREEN}./scripts/lab.sh${NC}  (see docs/lab-run.md)" >&2
  exit 1
}

# Assert a file exists and contains a fixed string (grep -F, no regex surprises).
assert_contains() {
  local file="$1" needle="$2" desc="$3"
  [[ -f "$file" ]] || fail "missing file: $file"
  if grep -qF -- "$needle" "$file"; then
    ok "$desc"
  else
    fail "$desc — expected '$needle' in $file"
  fi
}

# ── Desktop config assertions (static — no stack required) ─────
info "Desktop bridge + lab Path assertions (static) ..."

BRIDGE_RS="$ROOT/desktop/src-tauri/src/sip_bridge.rs"
BRIDGE_LIB="$ROOT/desktop/src-tauri/src/lib.rs"
LAB_PATH_JSON="$ROOT/client/public/scripts/lab-account-status.json"

# 1. The Tauri shell injects the frozen NativeSipBridge shape + commands.
assert_contains "$BRIDGE_RS" "window.__pathlineSipBridge" "SIP bridge injects window.__pathlineSipBridge"
for cmd in sip_dial sip_answer sip_send_dtmf sip_hangup; do
  assert_contains "$BRIDGE_RS" "$cmd" "bridge defines command: $cmd"
  assert_contains "$BRIDGE_LIB" "$cmd" "lib.rs registers command: $cmd"
done
assert_contains "$BRIDGE_LIB" "js_init_script" "lib.rs wires bridge init_script into the webview"

# 2. Privacy: DTMF audit is a non-reversible hash + count, never plaintext.
assert_contains "$BRIDGE_RS" "short_hash" "bridge logs DTMF as a hash (short_hash), not plaintext"

# 3. Lab Path is desktop-automation-ready: target=1000 + autoListen=true.
[[ -f "$LAB_PATH_JSON" ]] || fail "missing lab Path: $LAB_PATH_JSON"
python3 - "$LAB_PATH_JSON" <<'PY' || fail "lab Path is not desktop-automation-ready (need target=1000 + autoListen=true)"
import json, sys
with open(sys.argv[1]) as fh:
    doc = json.load(fh)
setup = doc.get("setup", {})
target = str(setup.get("target", "")).strip()
auto = bool(setup.get("speechPreferences", {}).get("autoListen"))
assert target == "1000", f"target={target!r} (want '1000')"
assert auto is True, "speechPreferences.autoListen is not true"
PY
ok "lab Path target=1000 and speechPreferences.autoListen=true"

if [[ "$SKIP_LAB_PREFLIGHT" == "1" ]]; then
  info "SKIP_LAB_PREFLIGHT=1 — static desktop assertions passed; skipping live lab preflight + smoke test."
  exit 0
fi

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
