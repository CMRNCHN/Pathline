#!/usr/bin/env bash
# Build Pathline.app and Pathline Stop.app in the project root
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

ICON_SRC="$ROOT/assets/icon/generated/Pathline.icns"

info() { echo "▸ $*"; }

ensure_icon() {
  if [[ -f "$ICON_SRC" ]]; then
    return 0
  fi
  info "Generating app icon..."
  python3 -m pip install -q -r "$ROOT/scripts/requirements-launcher.txt"
  python3 "$ROOT/scripts/generate-app-icon.py" --icns-only
  python3 "$ROOT/scripts/generate-app-icon.py" --png-only
}

build_app() {
  local name="$1"
  local script="$2"
  local bundle_id="$3"
  local app_dir="$ROOT/$name.app"
  local icon_name="AppIcon"

  rm -rf "$app_dir"
  mkdir -p "$app_dir/Contents/MacOS" "$app_dir/Contents/Resources"

  cp "$ICON_SRC" "$app_dir/Contents/Resources/${icon_name}.icns"

  cat >"$app_dir/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleDevelopmentRegion</key>
  <string>en</string>
  <key>CFBundleExecutable</key>
  <string>launch</string>
  <key>CFBundleIconFile</key>
  <string>${icon_name}</string>
  <key>CFBundleIdentifier</key>
  <string>${bundle_id}</string>
  <key>CFBundleInfoDictionaryVersion</key>
  <string>6.0</string>
  <key>CFBundleName</key>
  <string>${name}</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>CFBundleShortVersionString</key>
  <string>1.0</string>
  <key>CFBundleVersion</key>
  <string>1</string>
  <key>LSMinimumSystemVersion</key>
  <string>11.0</string>
  <key>NSHighResolutionCapable</key>
  <true/>
</dict>
</plist>
PLIST

  cat >"$app_dir/Contents/MacOS/launch" <<LAUNCH
#!/usr/bin/env bash
set -euo pipefail
ROOT="\$(cd "\$(dirname "\$0")/../../.." && pwd)"
exec "\$ROOT/$script"
LAUNCH

  chmod +x "$app_dir/Contents/MacOS/launch"
  info "Built $app_dir"
}

ensure_icon
build_app "Pathline" "scripts/launch-desktop.sh" "com.pathline.desktop"
build_app "Pathline Stop" "scripts/stop.sh" "dev.pathline.stop"

echo ""
echo "Double-click Pathline.app to start the Tauri desktop shell."
echo "Double-click Pathline Stop.app to stop."
echo "Run ./scripts/install-macos.sh to link into ~/Applications and pin to the Dock."
