#!/usr/bin/env bash
# Stop PromptPath API + client started by start.sh or PromptPath.app
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PID_DIR="$ROOT/.pids"

stopped=0

if [[ -f "$PID_DIR/api.pid" ]]; then
  kill "$(cat "$PID_DIR/api.pid")" 2>/dev/null || true
  rm -f "$PID_DIR/api.pid"
  stopped=1
fi

if [[ -f "$PID_DIR/client.pid" ]]; then
  kill "$(cat "$PID_DIR/client.pid")" 2>/dev/null || true
  rm -f "$PID_DIR/client.pid"
  stopped=1
fi

# Kill stray Vite dev servers for this project (stale HMR breaks the UI)
if pkill -f "$ROOT/client.*vite" 2>/dev/null; then
  stopped=1
fi

if (( stopped )); then
  echo "PromptPath stopped."
else
  echo "PromptPath is not running."
fi
