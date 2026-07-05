#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PORT="${PORT:-8000}"

if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Port $PORT is already in use. Either:"
  echo "  kill \$(lsof -t -iTCP:$PORT -sTCP:LISTEN)   # stop existing API"
  echo "  PORT=8001 $0                                 # use another port"
  exit 1
fi

pip install -q -e packages/shared-python -e services/api
echo "Starting PromptPath API (v1) on :$PORT..."
uvicorn promptpath_api.main:app --host 0.0.0.0 --port "$PORT" --reload
