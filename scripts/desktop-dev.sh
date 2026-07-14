#!/usr/bin/env bash
# PromptPath desktop dev — API sidecar + Tauri shell
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

API_PORT="${API_PORT:-8000}"
LOG_DIR="$ROOT/.logs"
PID_DIR="$ROOT/.pids"
VENV="$ROOT/.venv"
PID_FILE="$PID_DIR/api-desktop.pid"
LOG_FILE="$LOG_DIR/api-desktop.log"
API_OWNED=0

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}▸${NC} $*"; }
warn()  { echo -e "${YELLOW}▸${NC} $*"; }
fail()  { echo "$*" >&2; exit 1; }

check_linux_tauri_deps() {
  [[ "$(uname -s)" == "Linux" ]] || return 0
  command -v pkg-config >/dev/null || return 0
  if pkg-config --exists gdk-3.0 'gdk-3.0 >= 3.22' 2>/dev/null; then
    return 0
  fi
  fail "Missing Linux libraries for Tauri (gdk-3.0 not found).

Install once, then rerun npm run desktop:dev:
  ./scripts/install-linux-tauri-deps.sh

Or manually (Debian/Ubuntu 22.04+):
  sudo apt install libgtk-3-dev libwebkit2gtk-4.1-dev libayatana-appindicator3-dev librsvg2-dev build-essential pkg-config

On macOS, build from the repo root — Linux packages are not required."
}

api_ready() {
  local body
  body="$(curl -sf "http://127.0.0.1:${API_PORT}/health" 2>/dev/null || true)"
  [[ -n "$body" ]] && echo "$body" | grep -q '"status"[[:space:]]*:[[:space:]]*"ok"'
}

start_api() {
  if api_ready; then
    info "[api] healthy on 127.0.0.1:${API_PORT} (reusing existing)"
    API_OWNED=0
    return 0
  fi

  if command -v lsof >/dev/null 2>&1; then
    if lsof -nP -iTCP:"$API_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
      fail "Port ${API_PORT} is occupied but /health is not ok.
Stop the process on that port, or set API_PORT to a free port.
Do not kill unrelated processes from this script."
    fi
  fi

  command -v python3 >/dev/null || fail "python3 not found. Install Python 3.12+."

  if [[ ! -d "$VENV" ]]; then
    info "Creating Python virtual environment..."
    if ! python3 -m venv "$VENV" 2>/dev/null; then
      fail "Could not create .venv — install python3-venv, then retry."
    fi
  fi

  mkdir -p "$LOG_DIR" "$PID_DIR"
  # shellcheck disable=SC1091
  source "$VENV/bin/activate"
  pip install -q --upgrade pip
  pip install -q -e packages/shared-python -e services/api

  JWT_SECRET="${JWT_SECRET:-$(openssl rand -hex 32 2>/dev/null || python3 -c 'import secrets; print(secrets.token_hex(32))')}"
  SESSION_PEPPER="${SESSION_PEPPER:-$(openssl rand -hex 32 2>/dev/null || python3 -c 'import secrets; print(secrets.token_hex(32))')}"

  info "[api] starting sidecar on 127.0.0.1:${API_PORT} ..."
  JWT_SECRET="$JWT_SECRET" SESSION_PEPPER="$SESSION_PEPPER" \
    uvicorn promptpath_api.main:app \
      --host 127.0.0.1 \
      --port "$API_PORT" \
      --reload \
      >"$LOG_FILE" 2>&1 &
  echo $! >"$PID_FILE"
  API_OWNED=1

  for _ in $(seq 1 40); do
    if api_ready; then
      info "[api] healthy on 127.0.0.1:${API_PORT}"
      return 0
    fi
    sleep 0.5
  done

  if [[ -f "$PID_FILE" ]]; then
    kill "$(cat "$PID_FILE")" 2>/dev/null || true
    rm -f "$PID_FILE"
  fi
  API_OWNED=0
  fail "API failed to become healthy — see $LOG_FILE"
}

cleanup() {
  if [[ "$API_OWNED" == "1" && -f "$PID_FILE" ]]; then
    kill "$(cat "$PID_FILE")" 2>/dev/null || true
    rm -f "$PID_FILE"
  fi
}

trap cleanup EXIT INT TERM

if [[ ! -d "$ROOT/desktop/node_modules" ]]; then
  info "Installing desktop dependencies..."
  (cd "$ROOT/desktop" && npm install)
fi

# Client source/deps are owned elsewhere — require an existing install.
if [[ ! -d "$ROOT/client/node_modules" ]]; then
  fail "client/node_modules missing.
From the repo root run:  (cd client && npm install)
Then retry:  npm run desktop:dev"
fi

start_api

check_linux_tauri_deps

export API_PORT
# Persist ownership for cleanup after exec replaces this shell image's
# normal path — write a marker only when we own the process.
if [[ "$API_OWNED" == "1" ]]; then
  echo "1" >"$PID_DIR/api-desktop.owned"
else
  rm -f "$PID_DIR/api-desktop.owned"
fi

# Re-bind cleanup to read marker (exec'd child exit → trap on this process tree root).
cleanup() {
  if [[ -f "$PID_DIR/api-desktop.owned" && -f "$PID_FILE" ]]; then
    kill "$(cat "$PID_FILE")" 2>/dev/null || true
    rm -f "$PID_FILE" "$PID_DIR/api-desktop.owned"
  fi
}
trap cleanup EXIT INT TERM

info "[desktop] launching tauri dev"
cd "$ROOT/desktop"
# Do not exec — preserve EXIT/INT/TERM traps for owned API cleanup.
npm run dev
