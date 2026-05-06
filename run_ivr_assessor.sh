#!/usr/bin/env bash
# run_ivr_assessor.sh — launch IVR assessor CLI or Docker stack
#
# Usage:
#   ./run_ivr_assessor.sh [CLI COMMAND]       — run any CLI command via venv
#   ./run_ivr_assessor.sh docker-up           — start docker-compose stack
#   ./run_ivr_assessor.sh docker-down         — stop docker-compose stack
#   ./run_ivr_assessor.sh docker-logs         — tail docker-compose logs
#
# Tunnel control (for the CLI / live-map-gui command):
#   TUNNEL_BACKEND=ngrok        (default) — use ngrok (must be running separately)
#   TUNNEL_BACKEND=cloudflare   — start cloudflared quick tunnel automatically
#   TUNNEL_BACKEND=none         — no tunnel (LAN / direct access only)
#
# Examples:
#   ./run_ivr_assessor.sh live-map-gui
#   TUNNEL_BACKEND=cloudflare ./run_ivr_assessor.sh live-map-gui
#   ./run_ivr_assessor.sh docker-up
set -euo pipefail

DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
VENV_PYTHON="$DIR/backend/python/.venv/bin/python"

if [[ -x "$VENV_PYTHON" ]]; then
  PYTHON_BIN="$VENV_PYTHON"
else
  PYTHON_BIN="${PYTHON_BIN:-python3}"
fi

TUNNEL_BACKEND="${TUNNEL_BACKEND:-ngrok}"

# ── Docker commands ────────────────────────────────────────────────────────────
case "${1:-}" in
  docker-up)
    echo "Starting docker-compose stack…"
    docker compose -f "$DIR/docker-compose.yml" up -d
    echo "API health: $(curl -sf http://localhost:8081/healthz || echo 'not ready yet')"
    exit 0
    ;;
  docker-down)
    docker compose -f "$DIR/docker-compose.yml" down
    exit 0
    ;;
  docker-logs)
    docker compose -f "$DIR/docker-compose.yml" logs -f
    exit 0
    ;;
esac

# ── Cloudflare Tunnel (optional) ───────────────────────────────────────────────
if [[ "$TUNNEL_BACKEND" == "cloudflare" ]]; then
  if ! command -v cloudflared &>/dev/null; then
    echo "ERROR: cloudflared not found. Install with: brew install cloudflare/cloudflare/cloudflared" >&2
    exit 1
  fi
  # Start a quick tunnel in the background; its URL appears in the logs.
  echo "Starting Cloudflare quick tunnel on port 8081…"
  cloudflared tunnel --url http://localhost:8081 --no-autoupdate &
  CLOUDFLARED_PID=$!
  # Give it a moment to print the URL before the CLI starts logging too.
  sleep 2
  trap 'kill $CLOUDFLARED_PID 2>/dev/null || true' EXIT
fi

# ── Run CLI command ────────────────────────────────────────────────────────────
PYTHONPATH="$DIR/backend/python/src${PYTHONPATH:+:$PYTHONPATH}" \
  "$PYTHON_BIN" -m ivr_assessor.cli "$@"
