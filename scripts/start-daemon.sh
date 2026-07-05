#!/usr/bin/env bash
# Background start — for PromptPath.app (no terminal required)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

API_PORT="${API_PORT:-8000}"
CLIENT_PORT="${CLIENT_PORT:-3000}"
LOG_DIR="$ROOT/.logs"
PID_DIR="$ROOT/.pids"
VENV="$ROOT/.venv"

mkdir -p "$LOG_DIR" "$PID_DIR"

# Already running?
if [[ -f "$PID_DIR/api.pid" ]] && kill -0 "$(cat "$PID_DIR/api.pid")" 2>/dev/null; then
  if [[ "$(uname)" == "Darwin" ]]; then
    osascript -e "display notification \"Already running at http://localhost:$CLIENT_PORT\" with title \"PromptPath\""
    open "http://localhost:$CLIENT_PORT" 2>/dev/null || true
  fi
  exit 0
fi

# Delegate setup + start to start.sh logic without blocking
export PROMPTPATH_DAEMON=1
exec "$ROOT/scripts/start.sh"
