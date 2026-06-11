#!/bin/bash
# Pathline Pulse — build & preflight for macOS.
#
# Pulse is an interactive menu bar app that probes an IVR through a local
# Asterisk instance over ARI. It is not a scheduled job, so this script does
# not install a LaunchAgent or any cloud credentials — it builds the app and
# checks that Asterisk ARI is reachable, then tells you how to run it.
#
# Run from the Pathline repo root:
#   bash tools/ivr_beacon/setup.sh
#
# Configure the probe (optional) before running the app, via env vars:
#   PULSE_TARGET           IVR number to dial            (default +18009505114)
#   PULSE_MENU_DIGITS      DTMF after the greeting       (default **11)
#   PULSE_CARD_DIGITS      DTMF after the card prompt    (override with a test card)
#   PULSE_ARI_HOST/PORT    Asterisk ARI host/port        (default 127.0.0.1:8088)
#   PULSE_ARI_API_KEY      ARI user:pass                 (default ari:ari)
#   PULSE_ARI_APP          Stasis app name               (default pulse)
#   PULSE_TALK_SILENCE_MS  TALK_DETECT silence threshold (default 1500, NEEDS CALIBRATION)
#   PULSE_MIN_PROMPT_MS    minimum real-prompt duration  (default 2000, NEEDS CALIBRATION)
#
# See tools/ivr_beacon/README.md for Asterisk setup and the testing checklist.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
APP_DIR="$REPO_DIR/tools/ivr_beacon/BeaconApp"
BINARY="$APP_DIR/.build/release/PathlinePulse"

ARI_HOST="${PULSE_ARI_HOST:-127.0.0.1}"
ARI_PORT="${PULSE_ARI_PORT:-8088}"
ARI_API_KEY="${PULSE_ARI_API_KEY:-ari:ari}"

green()  { echo "$(tput setaf 2 2>/dev/null)✓ $*$(tput sgr0 2>/dev/null)"; }
yellow() { echo "$(tput setaf 3 2>/dev/null)→ $*$(tput sgr0 2>/dev/null)"; }
red()    { echo "$(tput setaf 1 2>/dev/null)✗ $*$(tput sgr0 2>/dev/null)"; }

echo ""
echo "Pathline Pulse Setup"
echo "━━━━━━━━━━━━━━━━━━━━"
echo "Repo: $REPO_DIR"
echo "App:  $APP_DIR"
echo ""

# ── 1. Build the app ──────────────────────────────────────────────────────────

if ! command -v swift &>/dev/null; then
    red "Swift not found. Install Xcode Command Line Tools (xcode-select --install), then:"
    echo "    cd $APP_DIR && swift build -c release"
    exit 1
fi

echo "Building Pulse (release)..."
if (cd "$APP_DIR" && swift build -c release); then
    green "Built: $BINARY"
else
    red "swift build failed — see output above"
    exit 1
fi

# ── 2. Preflight: is Asterisk ARI reachable? ─────────────────────────────────

echo ""
echo "Checking Asterisk ARI at $ARI_HOST:$ARI_PORT ..."
ARI_URL="http://$ARI_HOST:$ARI_PORT/ari/asterisk/info?api_key=$ARI_API_KEY"
if curl -fsS --max-time 5 "$ARI_URL" >/dev/null 2>&1; then
    green "ARI reachable — Asterisk is up and the credentials work."
else
    yellow "ARI not reachable at $ARI_HOST:$ARI_PORT (or credentials rejected)."
    echo "    Pulse needs a local Asterisk with ARI/HTTP enabled before it can probe."
    echo "    See the 'Asterisk prerequisites' section of tools/ivr_beacon/README.md."
fi

# ── Done ─────────────────────────────────────────────────────────────────────

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
green "Pulse is built."
echo ""
yellow "Run it (override PULSE_* env vars first to target your own IVR):"
echo "    $BINARY"
echo ""
echo "Then click the waveform icon in the menu bar → 'Run Probe'."
echo "Full testing checklist: tools/ivr_beacon/README.md"
echo ""
