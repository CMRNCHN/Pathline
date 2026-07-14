#!/usr/bin/env bash
# Install Pathline launcher (icon + Dock pin) on macOS
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BIN_DIR="$HOME/.local/bin"
APPS_DIR="$HOME/Applications"
APP_PATH="$APPS_DIR/Pathline.app"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This installer is for macOS."
  echo "You are on: $(uname -s)"
  echo ""
  echo "From the repo root, run instead:"
  echo "  cd $ROOT"
  echo "  npm run install"
  echo ""
  echo "(/path/to/Pathline was just an example — use your real clone path.)"
  exit 1
fi

echo "Installing Pathline from: $ROOT"

mkdir -p "$BIN_DIR" "$APPS_DIR"

# Global terminal commands
ln -sf "$ROOT/bin/pathline" "$BIN_DIR/pathline"
ln -sf "$ROOT/bin/pathline-stop" "$BIN_DIR/pathline-stop"
echo "  → $BIN_DIR/pathline"
echo "  → $BIN_DIR/pathline-stop"

# Icon + .app bundles
"$ROOT/scripts/build-macos-app.sh"
ln -sfn "$ROOT/Pathline.app" "$APP_PATH"
ln -sfn "$ROOT/Pathline Stop.app" "$APPS_DIR/Pathline Stop.app"
echo "  → $APP_PATH"
echo "  → $APPS_DIR/Pathline Stop.app"

# Ensure ~/.local/bin is on PATH for zsh
ZSHRC="$HOME/.zshrc"
MARKER="# Pathline"
if ! grep -qF "$MARKER" "$ZSHRC" 2>/dev/null; then
  cat >>"$ZSHRC" <<'EOF'

# Pathline — global launch commands
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

pin_to_dock "$APP_PATH" "Pathline"
killall Dock 2>/dev/null || true

echo ""
echo "Done — Pathline is in your Dock."
echo ""
echo "  Click the icon to start the Tauri desktop app"
echo "  pathline-stop  — stop background services"
echo ""
echo "Run:  source ~/.zshrc   (or open a new terminal)"
