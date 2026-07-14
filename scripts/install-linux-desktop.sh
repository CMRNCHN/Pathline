#!/usr/bin/env bash
# Linux desktop launcher (.desktop file + icon, dock/panel pin)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ICON_DIR="$HOME/.local/share/icons"
APPS_DIR="$HOME/.local/share/applications"
DESKTOP_DIR="$HOME/Desktop"
DESKTOP="$APPS_DIR/pathline.desktop"
DESKTOP_ID="pathline.desktop"
ICON_SRC="$ROOT/assets/icon/generated/pathline-256.png"
ICON_FALLBACK="$ROOT/desktop/src-tauri/icons/128x128.png"
LAUNCHER="$ROOT/scripts/launch-desktop.sh"

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "This installer is for Linux."
  echo "On macOS run from the repo root:  npm run install"
  echo "Repo root: $ROOT"
  exit 1
fi

chmod +x "$LAUNCHER" "$ROOT/scripts/desktop-dev.sh" 2>/dev/null || true

ensure_launcher_png() {
  if [[ -f "$ICON_SRC" ]]; then
    return 0
  fi
  if [[ -f "$ICON_FALLBACK" ]]; then
    ICON_SRC="$ICON_FALLBACK"
    return 0
  fi
  if ! python3 -c "import PIL" 2>/dev/null; then
    python3 -m pip install -q pillow
  fi
  python3 "$ROOT/scripts/generate-app-icon.py" --png-only
  ICON_SRC="$ROOT/assets/icon/generated/pathline-256.png"
}

ensure_launcher_png

mkdir -p "$ICON_DIR" "$APPS_DIR" "$DESKTOP_DIR"
cp "$ICON_SRC" "$ICON_DIR/pathline.png"

cat >"$DESKTOP" <<DESKTOP
[Desktop Entry]
Version=1.0
Type=Application
Name=Pathline
Comment=Pathline desktop — local API + Tauri shell
Exec=$LAUNCHER
Icon=$ICON_DIR/pathline.png
Terminal=false
Categories=Development;Utility;Network;
StartupNotify=true
StartupWMClass=pathline-desktop
DESKTOP

chmod +x "$DESKTOP"
cp "$DESKTOP" "$DESKTOP_DIR/pathline.desktop"
chmod +x "$DESKTOP_DIR/pathline.desktop"
# Mark trusted so XFCE does not block “Untrusted application launcher”
gio set "$DESKTOP_DIR/pathline.desktop" metadata::trusted true 2>/dev/null || true
gio set "$DESKTOP" metadata::trusted true 2>/dev/null || true
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

  new="${current%]}, '${DESKTOP_ID}']"
  gsettings set org.gnome.shell favorite-apps "$new"
  echo "  → Pinned to GNOME dock"
}

pin_xfce_panel() {
  command -v xfconf-query >/dev/null 2>&1 || return 1
  xfconf-query -c xfce4-panel -p /panels/panel-1/plugin-ids >/dev/null 2>&1 || return 1

  local plugin_id=42
  local launcher_dir="$HOME/.config/xfce4/panel/launcher-${plugin_id}"
  local item="16700000001.desktop"

  # Reuse existing plugin-42 if already a launcher
  if xfconf-query -c xfce4-panel -p /plugins/plugin-${plugin_id} >/dev/null 2>&1; then
    local kind
    kind="$(xfconf-query -c xfce4-panel -p /plugins/plugin-${plugin_id} 2>/dev/null || true)"
    if [[ "$kind" != "launcher" ]]; then
      plugin_id=142
      launcher_dir="$HOME/.config/xfce4/panel/launcher-${plugin_id}"
    fi
  fi

  mkdir -p "$launcher_dir"
  cp "$DESKTOP" "$launcher_dir/$item"
  chmod +x "$launcher_dir/$item"

  if ! xfconf-query -c xfce4-panel -p /plugins/plugin-${plugin_id} >/dev/null 2>&1; then
    xfconf-query -c xfce4-panel -n -t string -p /plugins/plugin-${plugin_id} -s "launcher"
  else
    xfconf-query -c xfce4-panel -p /plugins/plugin-${plugin_id} -s "launcher"
  fi

  if xfconf-query -c xfce4-panel -p /plugins/plugin-${plugin_id}/items >/dev/null 2>&1; then
    xfconf-query -c xfce4-panel -p /plugins/plugin-${plugin_id}/items -a -t string -s "$item" 2>/dev/null \
      || xfconf-query -c xfce4-panel -p /plugins/plugin-${plugin_id}/items -t string -s "$item"
  else
    xfconf-query -c xfce4-panel -n -a -t string -p /plugins/plugin-${plugin_id}/items -s "$item"
  fi

  local ids
  ids="$(xfconf-query -c xfce4-panel -p /panels/panel-1/plugin-ids | grep -E '^[0-9]+$' || true)"
  if ! echo "$ids" | grep -qx "$plugin_id"; then
    # Rebuild array including new plugin near the end (before last separator if present)
    local args=()
    while read -r id; do
      [[ -n "$id" ]] && args+=(-t int -s "$id")
    done <<<"$ids"
    args+=(-t int -s "$plugin_id")
    xfconf-query -c xfce4-panel -p /panels/panel-1/plugin-ids "${args[@]}"
  fi

  # Nudge panel to reload
  xfce4-panel -r 2>/dev/null || true
  echo "  → Pinned to XFCE panel (dock)"
}

echo "Installed $DESKTOP"
echo "  Icon: $ICON_DIR/pathline.png"
echo "  Launch: $LAUNCHER"
echo "  Desktop shortcut: $DESKTOP_DIR/pathline.desktop"
echo "  Repo: $ROOT"

pin_gnome_dock || true
pin_xfce_panel || true

echo ""
echo "Click the Pathline icon in the panel/dock or Desktop to launch."
