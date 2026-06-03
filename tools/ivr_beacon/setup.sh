#!/bin/bash
# IVR Beacon — one-time setup for macOS
# Run from the Pathline repo root:
#   bash tools/ivr_beacon/setup.sh
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
BEACON_DIR="$REPO_DIR/tools/ivr_beacon"
PROBE_DIR="$REPO_DIR/tools/ivr_probe"
IVR_DIR="$HOME/ivr"
AGENTS_DIR="$HOME/Library/LaunchAgents"
PLIST_ID="com.ivr.probe.hourly"
PLIST_DST="$AGENTS_DIR/$PLIST_ID.plist"

green()  { echo "$(tput setaf 2)✓ $*$(tput sgr0)"; }
yellow() { echo "$(tput setaf 3)→ $*$(tput sgr0)"; }
red()    { echo "$(tput setaf 1)✗ $*$(tput sgr0)"; }

echo ""
echo "IVR Beacon Setup"
echo "━━━━━━━━━━━━━━━━"
echo "Repo:   $REPO_DIR"
echo "IVR:    $IVR_DIR"
echo ""

# ── 1. Twilio credentials ──────────────────────────────────────────────────────

if [[ -z "${TWILIO_ACCOUNT_SID:-}" ]]; then
    read -rp "TWILIO_ACCOUNT_SID:   " TWILIO_ACCOUNT_SID
fi
if [[ -z "${TWILIO_AUTH_TOKEN:-}" ]]; then
    read -rsp "TWILIO_AUTH_TOKEN:    " TWILIO_AUTH_TOKEN; echo ""
fi
if [[ -z "${TWILIO_PHONE_NUMBER:-}" ]]; then
    read -rp "TWILIO_PHONE_NUMBER:  " TWILIO_PHONE_NUMBER
fi

# ── 2. Create ~/ivr/ directory structure ───────────────────────────────────────

mkdir -p "$IVR_DIR/results"
green "Created $IVR_DIR/"

# ── 3. Copy probe files ────────────────────────────────────────────────────────

cp "$PROBE_DIR/probe.py"  "$IVR_DIR/probe.py"
cp "$PROBE_DIR/suite.json" "$IVR_DIR/suite.json"
green "Copied probe.py and suite.json → $IVR_DIR/"

# ── 4. Install jobs.json (skip if user already has one) ───────────────────────

if [[ ! -f "$IVR_DIR/jobs.json" ]]; then
    cp "$BEACON_DIR/ivr/jobs.json" "$IVR_DIR/jobs.json"
    green "Installed default jobs.json → $IVR_DIR/jobs.json"
    yellow "Edit $IVR_DIR/jobs.json to set your real card numbers"
else
    yellow "Skipped jobs.json (already exists at $IVR_DIR/jobs.json)"
fi

# ── 5. Generate run_ivr_batch.sh with repo path baked in ──────────────────────

sed "s|__REPO_PATH__|$REPO_DIR|g" \
    "$BEACON_DIR/ivr/run_ivr_batch.sh" > "$IVR_DIR/run_ivr_batch.sh"
chmod +x "$IVR_DIR/run_ivr_batch.sh"
green "Generated $IVR_DIR/run_ivr_batch.sh (PYTHONPATH → $REPO_DIR)"

# ── 6. Generate and install launchd plist ─────────────────────────────────────

mkdir -p "$AGENTS_DIR"

sed \
    -e "s|HOME_DIR|$HOME|g" \
    -e "s|TWILIO_SID_VALUE|$TWILIO_ACCOUNT_SID|g" \
    -e "s|TWILIO_TOKEN_VALUE|$TWILIO_AUTH_TOKEN|g" \
    -e "s|TWILIO_NUMBER_VALUE|$TWILIO_PHONE_NUMBER|g" \
    "$BEACON_DIR/launchd/com.ivr.probe.hourly.plist" > "$PLIST_DST"

green "Installed launchd plist → $PLIST_DST"

# ── 7. Load the LaunchAgent ────────────────────────────────────────────────────

if launchctl list "$PLIST_ID" &>/dev/null; then
    launchctl unload "$PLIST_DST" 2>/dev/null || true
fi
launchctl load "$PLIST_DST"
green "Loaded LaunchAgent ($PLIST_ID) — runs every hour, also at load"

# ── 8. Build the dashboard app ────────────────────────────────────────────────

APP_DIR="$BEACON_DIR/BeaconApp"
echo ""
echo "Building IVR Beacon dashboard..."
if command -v swift &>/dev/null; then
    (cd "$APP_DIR" && swift build -c release 2>&1) && \
        green "Dashboard built: $APP_DIR/.build/release/IVRBeacon" || \
        { red "swift build failed — see output above"; }
    echo ""
    yellow "To run the dashboard:"
    echo "  $APP_DIR/.build/release/IVRBeacon"
else
    yellow "Swift not found — install Xcode Command Line Tools, then:"
    echo "  cd $APP_DIR && swift build -c release"
fi

# ── Done ──────────────────────────────────────────────────────────────────────

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
green "IVR Beacon installed."
echo ""
echo "  Jobs config:  $IVR_DIR/jobs.json"
echo "  Results:      $IVR_DIR/results/<job_name>/latest.json"
echo "  Logs:         /tmp/ivr_probe.log"
echo "  Schedule:     every 3600s (launchd)"
echo ""
yellow "Next: edit $IVR_DIR/jobs.json with your real card numbers"
echo ""
echo "Test a single run now:"
echo "  bash $IVR_DIR/run_ivr_batch.sh"
echo ""
echo "Tail the log:"
echo "  tail -f /tmp/ivr_probe.log"
echo ""
