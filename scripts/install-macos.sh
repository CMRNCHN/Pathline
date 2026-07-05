#!/usr/bin/env bash
# Install PromptPath so it works from anywhere on macOS
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BIN_DIR="$HOME/.local/bin"
APPS_DIR="$HOME/Applications"

echo "Installing PromptPath from: $ROOT"

mkdir -p "$BIN_DIR" "$APPS_DIR"

# Global terminal commands
ln -sf "$ROOT/bin/promptpath" "$BIN_DIR/promptpath"
ln -sf "$ROOT/bin/promptpath-stop" "$BIN_DIR/promptpath-stop"
echo "  → $BIN_DIR/promptpath"
echo "  → $BIN_DIR/promptpath-stop"

# Rebuild and link macOS apps
"$ROOT/scripts/build-macos-app.sh" >/dev/null
ln -sf "$ROOT/PromptPath.app" "$APPS_DIR/PromptPath.app"
ln -sf "$ROOT/PromptPath Stop.app" "$APPS_DIR/PromptPath Stop.app"
echo "  → $APPS_DIR/PromptPath.app"
echo "  → $APPS_DIR/PromptPath Stop.app"

# Ensure ~/.local/bin is on PATH for zsh
ZSHRC="$HOME/.zshrc"
MARKER="# PromptPath"
if ! grep -qF "$MARKER" "$ZSHRC" 2>/dev/null; then
  cat >>"$ZSHRC" <<'EOF'

# PromptPath — global launch commands
export PATH="$HOME/.local/bin:$PATH"
EOF
  echo "  → Added ~/.local/bin to PATH in ~/.zshrc"
else
  echo "  → ~/.zshrc already configured"
fi

echo ""
echo "Done. Use any of these from any directory:"
echo ""
echo "  promptpath          # start (terminal, foreground)"
echo "  promptpath-stop     # stop background services"
echo ""
echo "  Or open Spotlight → \"PromptPath\" → double-click the app"
echo ""
echo "Run:  source ~/.zshrc   (or open a new terminal)"
