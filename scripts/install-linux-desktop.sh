#!/usr/bin/env bash
# Linux desktop launcher (.desktop file + icon)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ICON_DIR="$HOME/.local/share/icons"
APPS_DIR="$HOME/.local/share/applications"
DESKTOP="$APPS_DIR/promptpath.desktop"
ICON_SRC="$ROOT/assets/icon/generated/promptpath-256.png"

python3 "$ROOT/scripts/generate-app-icon.py" >/dev/null

mkdir -p "$ICON_DIR" "$APPS_DIR"
cp "$ICON_SRC" "$ICON_DIR/promptpath.png"

cat >"$DESKTOP" <<DESKTOP
[Desktop Entry]
Type=Application
Name=PromptPath
Comment=Start PromptPath API and web client
Exec=env PROMPTPATH_DAEMON=1 $ROOT/scripts/start-daemon.sh
Icon=$ICON_DIR/promptpath.png
Terminal=false
Categories=Development;Utility;
StartupNotify=true
DESKTOP

chmod +x "$DESKTOP"
update-desktop-database "$APPS_DIR" 2>/dev/null || true

echo "Installed $DESKTOP"
echo "Search \"PromptPath\" in your app launcher, or pin it to your dock/panel."
