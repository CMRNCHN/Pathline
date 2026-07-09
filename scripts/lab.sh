#!/usr/bin/env bash
# PromptPath Tier C — lab Asterisk + API + web client
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

API_PORT="${API_PORT:-8000}"
CLIENT_PORT="${CLIENT_PORT:-3000}"
RTP_START="${RTP_START:-10000}"
RTP_END="${RTP_END:-10100}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}▸${NC} $*"; }
warn()  { echo -e "${YELLOW}▸${NC} $*"; }
fail()  { echo -e "${RED}✗${NC} $*" >&2; exit 1; }

command -v docker >/dev/null || fail "Docker is required for the lab IVR. Install Docker and retry."

if ! docker info >/dev/null 2>&1; then
  fail "Docker daemon is not running. Start Docker and retry."
fi

info "Building and starting lab Asterisk (extension 1000, SIP lab/lab)..."
docker compose --profile lab up --build -d asterisk

info "Waiting for SIP port 5060..."
for _ in $(seq 1 30); do
  if nc -z 127.0.0.1 5060 2>/dev/null || (echo >/dev/tcp/127.0.0.1/5060) 2>/dev/null; then
    info "Asterisk SIP is listening on 127.0.0.1:5060"
    break
  fi
  sleep 1
done

echo ""
info "Starting PromptPath API + client (same as ./scripts/start.sh)..."
echo ""
echo "  Lab IVR:     dial 1000 on a softphone registered to 127.0.0.1:5060 (lab/lab)"
echo "  Web app:     http://localhost:${CLIENT_PORT}"
echo "  Run script:  Lab account status (Asterisk 1000)"
echo "  RTP ports:   ${RTP_START}-${RTP_END}/udp (mapped for audio)"
echo ""
echo "  See docs/lab-run.md for the full walkthrough."
echo ""

exec "$ROOT/scripts/start.sh"
