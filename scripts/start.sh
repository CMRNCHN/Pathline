#!/usr/bin/env bash
# Pathline — one-command setup and start
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

API_PORT="${API_PORT:-8000}"
CLIENT_PORT="${CLIENT_PORT:-3000}"
LOG_DIR="$ROOT/.logs"
PID_DIR="$ROOT/.pids"
VENV="$ROOT/.venv"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}▸${NC} $*"; }
warn()  { echo -e "${YELLOW}▸${NC} $*"; }
fail()  { echo -e "${RED}✗${NC} $*" >&2; exit 1; }

free_port() {
  local port="$1"
  local pids
  pids=$(lsof -t -iTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)
  if [[ -n "$pids" ]]; then
    warn "Freeing port $port (stopping existing process)..."
    kill $pids 2>/dev/null || true
    sleep 0.5
  fi
}

cleanup() {
  echo ""
  info "Shutting down..."
  [[ -f "$PID_DIR/api.pid" ]] && kill "$(cat "$PID_DIR/api.pid")" 2>/dev/null || true
  [[ -f "$PID_DIR/client.pid" ]] && kill "$(cat "$PID_DIR/client.pid")" 2>/dev/null || true
  rm -f "$PID_DIR"/*.pid
  exit 0
}

wait_for_url() {
  local url="$1"
  local name="$2"
  local tries=30
  while (( tries > 0 )); do
    if curl -sf "$url" >/dev/null 2>&1; then
      info "$name is ready"
      return 0
    fi
    sleep 0.5
    (( tries-- )) || true
  done
  fail "$name failed to start — check $LOG_DIR"
}

# ── Prerequisites ──────────────────────────────────────────────
command -v python3 >/dev/null || fail "python3 not found. Install Python 3.12+."
command -v node    >/dev/null || fail "node not found. Install Node.js 20+."
command -v npm     >/dev/null || fail "npm not found."

# ── Environment ────────────────────────────────────────────────
if [[ ! -f "$ROOT/.env" ]]; then
  info "Creating .env from .env.example..."
  cp "$ROOT/.env.example" "$ROOT/.env"
fi

mkdir -p "$LOG_DIR" "$PID_DIR"

# ── Python setup ───────────────────────────────────────────────
if [[ -d "$VENV" && ! -f "$VENV/bin/activate" ]]; then
  warn "Removing incomplete virtual environment..."
  rm -rf "$VENV"
fi

if [[ ! -d "$VENV" ]]; then
  info "Creating Python virtual environment..."
  if ! python3 -m venv "$VENV" 2>/dev/null; then
    fail "Could not create .venv — install python3-venv (e.g. apt install python3.12-venv), then run npm start again."
  fi
fi

info "Installing Python dependencies..."
# shellcheck disable=SC1091
source "$VENV/bin/activate"
pip install -q --upgrade pip
pip install -q -e packages/shared-python -e services/api

# ── Client setup ───────────────────────────────────────────────
if [[ ! -d "$ROOT/client/node_modules" ]]; then
  info "Installing client dependencies (first run)..."
  (cd "$ROOT/client" && npm install)
else
  info "Client dependencies OK"
fi

# ── Free ports & start ─────────────────────────────────────────
free_port "$API_PORT"
free_port "$CLIENT_PORT"

DAEMON="${PATHLINE_DAEMON:-${PROMPTPATH_DAEMON:-0}}"  # legacy PromptPath
if [[ "$DAEMON" != "1" ]]; then
  trap cleanup INT TERM
fi

info "Starting API on http://localhost:$API_PORT ..."
JWT_SECRET="${JWT_SECRET:-$(openssl rand -hex 32 2>/dev/null || python3 -c 'import secrets; print(secrets.token_hex(32))')}"
SESSION_PEPPER="${SESSION_PEPPER:-$(openssl rand -hex 32 2>/dev/null || python3 -c 'import secrets; print(secrets.token_hex(32))')}"

JWT_SECRET="$JWT_SECRET" SESSION_PEPPER="$SESSION_PEPPER" \
  uvicorn pathline_api.main:app \
    --host 127.0.0.1 \
    --port "$API_PORT" \
    --reload \
    >"$LOG_DIR/api.log" 2>&1 &
echo $! >"$PID_DIR/api.pid"

wait_for_url "http://127.0.0.1:$API_PORT/health" "API"

info "Starting client on http://localhost:$CLIENT_PORT ..."
rm -rf "$ROOT/client/node_modules/.vite"
(cd "$ROOT/client" && npm run dev -- --host 127.0.0.1 --port "$CLIENT_PORT" --strictPort) \
  >"$LOG_DIR/client.log" 2>&1 &
echo $! >"$PID_DIR/client.pid"

wait_for_url "http://127.0.0.1:$CLIENT_PORT" "Client"

# ── Done ───────────────────────────────────────────────────────
if [[ "$DAEMON" == "1" ]]; then
  if [[ "$(uname)" == "Darwin" ]]; then
    open "http://localhost:$CLIENT_PORT" 2>/dev/null || true
    osascript -e "display notification \"http://localhost:$CLIENT_PORT\" with title \"Pathline is running\" subtitle \"Use Pathline Stop.app or scripts/stop.sh to quit\""
  fi
  exit 0
fi

echo ""
echo -e "${GREEN}Pathline is running${NC}"
echo ""
echo "  App:    http://localhost:$CLIENT_PORT"
echo "  API:    http://localhost:$API_PORT/health"
echo ""
echo "  Logs:   $LOG_DIR/api.log"
echo "          $LOG_DIR/client.log"
echo ""
echo "  Press Ctrl+C to stop both services"
echo "  Or run: ./scripts/stop.sh"
echo ""

# Open browser on macOS
if [[ "$(uname)" == "Darwin" ]]; then
  open "http://localhost:$CLIENT_PORT" 2>/dev/null || true
fi

wait
