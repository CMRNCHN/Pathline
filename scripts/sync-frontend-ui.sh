#!/usr/bin/env bash
# Sync client/ → frontend-ui/ for sharing
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
rsync -a --delete \
  --exclude node_modules \
  --exclude dist \
  "$ROOT/client/" "$ROOT/frontend-ui/"
cp "$ROOT/frontend-ui/README.md" "$ROOT/frontend-ui/README.md.bak" 2>/dev/null || true
# Restore share README if rsync overwrote it
if [[ -f "$ROOT/frontend-ui/README.md.bak" ]]; then
  mv "$ROOT/frontend-ui/README.md.bak" "$ROOT/frontend-ui/README.md"
fi
echo "Synced client/ → frontend-ui/"
