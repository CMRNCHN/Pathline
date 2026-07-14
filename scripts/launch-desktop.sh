#!/usr/bin/env bash
# Launch PromptPath Tauri desktop (API sidecar + shell)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PATH="${HOME}/.cargo/bin:${PATH}"
export DISPLAY="${DISPLAY:-:1}"

RELEASE="$ROOT/desktop/src-tauri/target/release/promptpath-desktop"
DEBUG="$ROOT/desktop/src-tauri/target/debug/promptpath-desktop"

# Default to live Vite + tauri dev so UI always loads.
# Set PROMPTPATH_USE_RELEASE=1 to force the packaged binary (needs a rebuild after UI changes).
USE_RELEASE="${PROMPTPATH_USE_RELEASE:-0}"

ensure_api() {
  if curl -sf "http://127.0.0.1:${API_PORT:-8000}/health" >/dev/null 2>&1; then
    return 0
  fi
  mkdir -p "$ROOT/.logs" "$ROOT/.pids"
  if [[ -d "$ROOT/.venv" ]]; then
    # shellcheck disable=SC1091
    source "$ROOT/.venv/bin/activate"
  fi
  if command -v uvicorn >/dev/null 2>&1; then
    JWT_SECRET="${JWT_SECRET:-devsecret}" SESSION_PEPPER="${SESSION_PEPPER:-devpepper}" \
      uvicorn promptpath_api.main:app --host 127.0.0.1 --port "${API_PORT:-8000}" \
      >"$ROOT/.logs/api-desktop.log" 2>&1 &
    echo $! >"$ROOT/.pids/api-desktop.pid"
    sleep 1
  fi
}

# Focus existing window if already running
if pgrep -f '[p]romptpath-desktop' >/dev/null 2>&1; then
  echo "PromptPath desktop is already running."
  exit 0
fi

ensure_api

if [[ "$USE_RELEASE" == "1" && -x "$RELEASE" ]]; then
  if [[ ! -f "$ROOT/client/dist/index.html" ]]; then
    (cd "$ROOT/client" && npm run build)
  fi
  echo "Launching release binary (PROMPTPATH_USE_RELEASE=1)..."
  exec "$RELEASE"
fi

# Preferred path: full desktop:dev (starts Vite on 127.0.0.1:3000 + Tauri)
if [[ -d "$ROOT/desktop/node_modules" ]]; then
  exec "$ROOT/scripts/desktop-dev.sh"
fi

if [[ -x "$DEBUG" ]]; then
  if ! curl -sf "http://127.0.0.1:3000" >/dev/null 2>&1; then
    mkdir -p "$ROOT/.logs" "$ROOT/.pids"
    (cd "$ROOT/client" && npm run dev -- --host 127.0.0.1 --port 3000 --strictPort) \
      >"$ROOT/.logs/client-desktop.log" 2>&1 &
    echo $! >"$ROOT/.pids/client-desktop.pid"
    for _ in $(seq 1 30); do
      curl -sf "http://127.0.0.1:3000" >/dev/null 2>&1 && break
      sleep 0.4
    done
  fi
  exec "$DEBUG"
fi

exec "$ROOT/scripts/desktop-dev.sh"
