#!/bin/bash
# Pathline Pulse — one-command bring-up.
#
# Collapses the whole local dance into a single command:
#   container (build + start) → wait for ARI → build Pulse → launch it.
#
# The ONE thing this can't do for you: create a SIP provider account. Once you
# have SIP credentials, put them in infrastructure/.env (see below) and re-run.
#
#   bash tools/ivr_beacon/dial.sh
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_DIR"

COMPOSE="infrastructure/docker-compose.yml"
ENV_FILE="infrastructure/.env"
ARI="http://127.0.0.1:8088/ari/asterisk/info?api_key=ari:ari"
BINARY="tools/ivr_beacon/BeaconApp/.build/release/PathlinePulse"

green()  { echo "$(tput setaf 2 2>/dev/null)✓ $*$(tput sgr0 2>/dev/null)"; }
yellow() { echo "$(tput setaf 3 2>/dev/null)→ $*$(tput sgr0 2>/dev/null)"; }

# ── 0. SIP trunk creds (the part only you can supply) ─────────────────────────
[ -f "$ENV_FILE" ] || touch "$ENV_FILE"
HAVE_TRUNK=0
if grep -q '^TRUNK_HOST=' "$ENV_FILE" && grep -q '^TRUNK_USER=' "$ENV_FILE"; then
    HAVE_TRUNK=1
fi

# ── 1. Start the Asterisk container ───────────────────────────────────────────
yellow "Starting Asterisk container (builds the first time)…"
docker compose -f "$COMPOSE" up asterisk -d --build

# ── 2. Wait for ARI ───────────────────────────────────────────────────────────
yellow "Waiting for ARI on :8088…"
for _ in $(seq 1 30); do
    if curl -fsS "$ARI" >/dev/null 2>&1; then green "ARI is up."; break; fi
    sleep 2
done
curl -fsS "$ARI" >/dev/null 2>&1 || { yellow "ARI never came up — check 'docker compose -f $COMPOSE logs asterisk'."; exit 1; }

# ── 3. Trunk status ───────────────────────────────────────────────────────────
if [ "$HAVE_TRUNK" -eq 1 ]; then
    green "SIP trunk creds found in $ENV_FILE."
    docker compose -f "$COMPOSE" logs asterisk 2>/dev/null | grep -iE "trunk|regist" | tail -3 || true
    ENDPOINT="PJSIP/18009505114@trunk"
else
    yellow "No SIP trunk creds yet — using the local test IVR (won't reach a real line)."
    echo "    To dial a real number, add these to $ENV_FILE and re-run:"
    echo "      TRUNK_HOST=sip.your-provider.example"
    echo "      TRUNK_USER=your-account"
    echo "      TRUNK_PASS=your-secret"
    ENDPOINT="Local/1000@ivr-test/n"
fi

# ── 4. Build Pulse ────────────────────────────────────────────────────────────
yellow "Building Pulse…"
swift build -c release --package-path tools/ivr_beacon/BeaconApp
green "Built."

# ── 5. Launch ─────────────────────────────────────────────────────────────────
green "Launching Pulse (menu bar). Endpoint: $ENDPOINT"
echo "    Pick a template, type your card number, click Run Probe."
exec env PULSE_ENDPOINT="$ENDPOINT" "$BINARY"
