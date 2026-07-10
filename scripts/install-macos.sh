#!/usr/bin/env bash
# Install PromptPath launcher (icon + Dock pin) on macOS
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BIN_DIR="$HOME/.local/bin"
APPS_DIR="$HOME/Applications"
APP_PATH="$APPS_DIR/PromptPath.app"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This installer is for macOS. On Linux, run: ./scripts/install-linux-desktop.sh"
  exit 1
fi

echo "Installing PromptPath from: $ROOT"

mkdir -p "$BIN_DIR" "$APPS_DIR"

# Global terminal commands
ln -sf "$ROOT/bin/promptpath" "$BIN_DIR/promptpath"
ln -sf "$ROOT/bin/promptpath-stop" "$BIN_DIR/promptpath-stop"
echo "  → $BIN_DIR/promptpath"
echo "  → $BIN_DIR/promptpath-stop"

# Icon + .app bundles
"$ROOT/scripts/build-macos-app.sh"
ln -sfn "$ROOT/PromptPath.app" "$APP_PATH"
ln -sfn "$ROOT/PromptPath Stop.app" "$APPS_DIR/PromptPath Stop.app"
echo "  → $APP_PATH"
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

pin_to_dock() {
  local app="$1"
  local label="$2"
  local resolved
  resolved="$(cd "$(dirname "$app")" && pwd)/$(basename "$app")"

  if defaults read com.apple.dock persistent-apps 2>/dev/null | grep -Fq "$resolved"; then
    echo "  → Dock already has $label"
    return 0
  fi

  if command -v dockutil >/dev/null 2>&1; then
    dockutil --add "$resolved" --no-restart >/dev/null
    echo "  → Pinned $label to Dock (dockutil)"
  else
    defaults write com.apple.dock persistent-apps -array-add "$(cat <<PLIST
<dict>
  <key>tile-data</key>
  <dict>
    <key>file-data</key>
    <dict>
      <key>_CFURLString</key>
      <string>file://${resolved}/</string>
      <key>_CFURLStringType</key>
      <integer>0</integer>
    </dict>
    <key>file-label</key>
    <string>${label}</string>
    <key>file-type</key>
    <integer>41</integer>
  </dict>
</dict>
PLIST
)"
    echo "  → Pinned $label to Dock"
  fi
}

pin_to_dock "$APP_PATH" "PromptPath"
killall Dock 2>/dev/null || true

echo ""
echo "Done — PromptPath is in your Dock."
echo ""
echo "  Click the icon to start (opens http://localhost:3000)"
echo "  promptpath-stop  — stop background services"
echo ""
echo "Run:  source ~/.zshrc   (or open a new terminal)"
