#!/usr/bin/env bash
# Run the full desktop lab loop in one command:
#   1. start the lab stack (Asterisk + API + Vite webview host) in the background
#   2. load generated SIP credentials into the environment
#   3. launch the desktop app (Tauri + rsiprtp bridge) which owns the call
#
# This is the primary desktop automation path (docs/lab-run.md / npm start).
# Vite stays up only as the Tauri webview host — do not open it in a browser.
# Ctrl+C stops the desktop app; run ./scripts/stop.sh to stop the background stack.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

GREEN='\033[0;32m'
NC='\033[0m'
info() { printf '%b\n' "${GREEN}▸${NC} $*"; }

# 1. Lab stack in daemon mode so this script continues to the desktop app.
info "Starting lab stack (Asterisk + API + client) in background ..."
PATHLINE_DAEMON=1 "$ROOT/scripts/lab.sh"

# 2. Load generated lab SIP credentials so the rsiprtp bridge can register.
CREDS="$ROOT/lab/asterisk/generated/credentials.env"
if [[ -f "$CREDS" ]]; then
  info "Loading lab SIP credentials from ${CREDS}"
  # shellcheck disable=SC1090
  set -a
  source "$CREDS"
  set +a
fi

# 3. Desktop app owns the call (foreground). Ctrl+C returns here.
export PATHLINE_SIP_PROFILE=lab
info "Launching desktop app (npm run desktop:dev) ..."
exec npm run desktop:dev
