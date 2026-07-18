#!/usr/bin/env bash
# Tauri beforeDevCommand: start Vite, or reuse one already on CLIENT_PORT.
# When reusing, stay alive so Tauri does not treat beforeDevCommand as failed.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CLIENT_PORT="${CLIENT_PORT:-3000}"

port_in_use() {
  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -iTCP:"$CLIENT_PORT" -sTCP:LISTEN >/dev/null 2>&1
    return $?
  fi
  # Fallback: bash /dev/tcp (macOS/Linux bash)
  (echo >/dev/tcp/127.0.0.1/"$CLIENT_PORT") >/dev/null 2>&1
}

if port_in_use; then
  echo "▸ [client] reusing existing Vite on 127.0.0.1:${CLIENT_PORT}"
  # Keep this process alive for the Tauri session; exit when parent dies.
  while true; do sleep 3600; done
fi

exec npm run dev --prefix "$ROOT/client"
