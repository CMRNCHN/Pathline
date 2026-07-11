#!/usr/bin/env bash
# Install PromptPath launcher for the current OS (macOS Dock or Linux .desktop)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

case "$(uname -s)" in
  Darwin)
    exec "$ROOT/scripts/install-macos.sh"
    ;;
  Linux)
    exec "$ROOT/scripts/install-linux-desktop.sh"
    ;;
  *)
    echo "Unsupported OS: $(uname -s)"
    echo "Run manually from: $ROOT"
    exit 1
    ;;
esac
