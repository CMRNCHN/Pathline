#!/usr/bin/env bash
# PromptPath Tier C — lab Asterisk (TLS) + API + web client
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

info "Generating lab SIP TLS credentials and config..."
"$ROOT/scripts/lab-sip-setup.sh"

# shellcheck disable=SC1091
source "$ROOT/lab/asterisk/generated/credentials.env"

start_docker_asterisk() {
  command -v docker >/dev/null || return 1
  docker info >/dev/null 2>&1 || return 1

  info "Starting lab Asterisk in Docker (TLS ${LAB_SIP_TLS_PORT})..."
  docker compose --profile lab up -d asterisk

  info "Waiting for SIP TLS port ${LAB_SIP_TLS_PORT}..."
  for _ in $(seq 1 30); do
    if (echo >/dev/tcp/127.0.0.1/"${LAB_SIP_TLS_PORT}") 2>/dev/null; then
      info "Asterisk SIP/TLS listening on 127.0.0.1:${LAB_SIP_TLS_PORT}"
      return 0
    fi
    sleep 1
  done
  warn "Docker Asterisk did not open TLS port — trying native fallback..."
  return 1
}

start_native_asterisk() {
  command -v asterisk >/dev/null || fail "Install asterisk (apt install asterisk) or fix Docker."

  info "Applying lab config to native Asterisk..."
  sudo mkdir -p /etc/asterisk/keys
  sudo cp "$ROOT/lab/asterisk/generated/tls/"* /etc/asterisk/keys/
  sudo cp "$ROOT/lab/asterisk/generated/pjsip.lab.conf" /etc/asterisk/pjsip.lab.conf
  sudo cp "$ROOT/lab/asterisk/extensions_lab.conf" /etc/asterisk/extensions_lab.conf

  MARKER="# PromptPath lab block"
  if ! sudo grep -qF "$MARKER" /etc/asterisk/extensions.conf 2>/dev/null; then
    sudo bash -c "echo '' >> /etc/asterisk/extensions.conf"
    sudo bash -c "echo '$MARKER' >> /etc/asterisk/extensions.conf"
    sudo bash -c "cat /etc/asterisk/extensions_lab.conf >> /etc/asterisk/extensions.conf"
  fi
  if ! sudo grep -qF "$MARKER" /etc/asterisk/pjsip.conf 2>/dev/null; then
    sudo bash -c "echo '' >> /etc/asterisk/pjsip.conf"
    sudo bash -c "echo '$MARKER' >> /etc/asterisk/pjsip.conf"
    sudo bash -c "cat /etc/asterisk/pjsip.lab.conf >> /etc/asterisk/pjsip.conf"
  fi

  # Fix key paths for native install (template uses /etc/asterisk/keys/)
  if ! pgrep -x asterisk >/dev/null 2>&1; then
    info "Starting native Asterisk..."
    sudo asterisk -g -c >/tmp/asterisk.log 2>&1 &
    sleep 2
  else
    sudo asterisk -rx "module reload res_pjsip.so" 2>/dev/null || true
    sudo asterisk -rx "dialplan reload" 2>/dev/null || true
  fi

  info "Native Asterisk running — TLS ${LAB_SIP_TLS_PORT}"
}

if ! start_docker_asterisk; then
  start_native_asterisk
fi

echo ""
info "Starting PromptPath API + client..."
echo ""
echo "  Lab IVR:     dial 1000 on softphone (TLS ${LAB_SIP_TLS_PORT})"
echo "  SIP user:    ${LAB_SIP_USER}"
echo "  SIP pass:    (see lab/asterisk/generated/credentials.env or .env)"
echo "  Web app:     http://localhost:${CLIENT_PORT}"
echo "  Run script:  Lab account status (Asterisk 1000)"
echo "  RTP ports:   ${RTP_START}-${RTP_END}/udp"
echo ""
echo "  Softphone: transport TLS, server 127.0.0.1:${LAB_SIP_TLS_PORT}, accept self-signed cert"
echo "  See docs/lab-run.md"
echo ""

exec "$ROOT/scripts/start.sh"
