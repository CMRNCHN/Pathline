#!/usr/bin/env bash
# Linux desktop launcher (.desktop file + icon, optional dock pin)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ICON_DIR="$HOME/.local/share/icons"
APPS_DIR="$HOME/.local/share/applications"
DESKTOP="$APPS_DIR/promptpath.desktop"
DESKTOP_ID="promptpath.desktop"
ICON_SRC="$ROOT/assets/icon/generated/promptpath-256.png"

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "This installer is for Linux."
  echo "On macOS run from the repo root:  npm run install"
  echo "Repo root: $ROOT"
  exit 1
fi

ensure_launcher_png() {
  if [[ -f "$ICON_SRC" ]]; then
    return 0
  fi
  if ! python3 -c "import PIL" 2>/dev/null; then
    python3 -m pip install -q pillow
  fi
  python3 "$ROOT/scripts/generate-app-icon.py" --png-only
}

ensure_launcher_png

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

pin_gnome_dock() {
  command -v gsettings >/dev/null 2>&1 || return 1
  gsettings list-schemas 2>/dev/null | grep -q '^org.gnome.shell$' || return 1

  local current new
  current="$(gsettings get org.gnome.shell favorite-apps)"
  if [[ "$current" == *"$DESKTOP_ID"* ]]; then
    echo "  → Already pinned to GNOME dock"
    return 0
  fi

  # Append to favorites array (gsettings format: ['a.desktop', 'b.desktop'])
  new="${current%]}, '${DESKTOP_ID}']"
  gsettings set org.gnome.shell favorite-apps "$new"
  echo "  → Pinned to GNOME dock"
}

echo "Installed $DESKTOP"
echo "  Icon: $ICON_DIR/promptpath.png"
echo "  Repo: $ROOT"

if [[ -n "${XDG_CURRENT_DESKTOP:-}" ]]; then
  pin_gnome_dock || true
  echo ""
  echo "Search \"PromptPath\" in your app launcher, or pin it to your dock/panel."
else
  echo ""
  echo "No desktop session detected here (headless/SSH/cloud VM)."
  echo "On a Linux machine with a desktop, run this same command there:"
  echo "  cd $ROOT && npm run install"
fi
