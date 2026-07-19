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
CREDS="$ROOT/lab/asterisk/generated/credentials.env"
if [[ -f "$CREDS" ]]; then
  # shellcheck disable=SC1090
  set -a
  source "$CREDS"
  set +a
fi

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
file_sha256() {
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$1" | awk '{print $1}'
  else
    sha256sum "$1" | awk '{print $1}'
  fi
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
LAB_DIALPLAN="$ROOT/lab/asterisk/extensions_lab.conf"
WHISPER_RS="$ROOT/desktop/src-tauri/src/whisper_bridge.rs"
WHISPER_MODEL="$ROOT/desktop/src-tauri/resources/models/ggml-tiny.en.bin"

# 1. The Tauri shell injects the frozen NativeSipBridge shape + commands.
assert_contains "$BRIDGE_RS" "window.__pathlineSipBridge" "SIP bridge injects window.__pathlineSipBridge"
for cmd in sip_dial sip_answer sip_send_dtmf sip_hangup; do
  assert_contains "$BRIDGE_RS" "$cmd" "bridge defines command: $cmd"
  assert_contains "$BRIDGE_LIB" "$cmd" "lib.rs registers command: $cmd"
done
assert_contains "$BRIDGE_LIB" "js_init_script" "lib.rs wires bridge init_script into the webview"
assert_contains "$WHISPER_RS" "window.__pathlineWhisper" "desktop injects native Whisper bridge"
assert_contains "$BRIDGE_LIB" "whisper_transcribe" "lib.rs registers local Whisper inference"
[[ -f "$WHISPER_MODEL" ]] || fail "bundled Whisper model missing; run desktop/src-tauri/resources/models/fetch-model.sh"
MODEL_SHA="$(file_sha256 "$WHISPER_MODEL")"
[[ "$MODEL_SHA" == "921e4cf8686fdd993dcd081a5da5b6c365bfde1162e72b08d75ac75289920b1f" ]] \
  || fail "bundled Whisper model checksum mismatch"
ok "bundled Whisper tiny.en model checksum verified"

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

python3 - "$LAB_DIALPLAN" <<'PY' || fail "lab dialplan has duplicate extensions or invalid Goto targets"
import re, sys
from collections import defaultdict

contexts = set()
extensions = defaultdict(set)
gotos = []
context = None
for number, raw in enumerate(open(sys.argv[1]), 1):
    line = raw.split(";", 1)[0].strip()
    match = re.fullmatch(r"\[([^\]]+)\]", line)
    if match:
        context = match.group(1)
        contexts.add(context)
        continue
    match = re.match(r"exten\s*=>\s*([^,]+),([^,]+),", line)
    if match and context:
        key = (match.group(1).strip(), match.group(2).strip())
        assert key not in extensions[context], f"duplicate {context}/{key} on line {number}"
        extensions[context].add(key)
    for target, extension in re.findall(r"Goto\(([^,()]+),([^,()]+),\d+\)", line):
        gotos.append((number, target.strip(), extension.strip()))

assert ("1000", "1") in extensions["lab-ivr"], "lab-ivr/1000 missing"
for number, target, extension in gotos:
    assert target in contexts, f"line {number}: missing context {target}"
    assert (extension, "1") in extensions[target], f"line {number}: missing {target}/{extension}/1"
PY
ok "lab dialplan contexts, routes, and extension uniqueness validated"

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

# ── Loaded dialplan validation ─────────────────────────────────
info "Validating loaded Asterisk dialplan ..."
if docker compose --profile lab ps --status running asterisk 2>/dev/null | grep -q asterisk; then
  ASTERISK_CLI=(docker compose --profile lab exec -T asterisk asterisk -rx)
elif command -v asterisk >/dev/null 2>&1; then
  ASTERISK_CLI=(asterisk -rx)
else
  fail "Asterisk CLI is unavailable."
fi

for context in lab-ivr lab-main-menu lab-touch-tone lab-pin-entry lab-ssn-entry lab-status-menu lab-read-status; do
  OUTPUT="$("${ASTERISK_CLI[@]}" "dialplan show ${context}")" || fail "could not inspect loaded context ${context}"
  [[ "$OUTPUT" == *"[$context]"* || "$OUTPUT" == *"'$context'"* ]] \
    || fail "loaded Asterisk dialplan is missing context ${context}"
done
ok "loaded Asterisk dialplan contains every IVR context"

# ── Authenticated SIP/TLS traversal ────────────────────────────
info "Placing authenticated SIP/TLS traversal call ..."
python3 "$ROOT/scripts/lab-sip-traversal.py" || fail "SIP/TLS IVR traversal did not reach remote BYE"
ok "SIP/TLS call traversed the complete IVR"

# ── Flow smoke test (phrase matching only, no call) ────────────
info "Phrase-matching smoke test ..."
if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON="$ROOT/.venv/bin/python"
else
  PYTHON="python3"
fi
"$PYTHON" -m pip install -q -e "$ROOT/packages/shared-python" >/dev/null 2>&1 || true

PHRASES=(
  "press 1 for account"
  "press 9 for touch tone"
  "enter your pin"
  "last four of your social"
  "press 1 for balance"
  "your balance is 1234 dollars"
)

printf '%s\n' "${PHRASES[@]}" | "$PYTHON" "$ROOT/scripts/test-navigator.py" "$ROOT/flows/lab-account-status.yaml"
ok "phrase-matching smoke test completed"
info "Lab verification complete."
