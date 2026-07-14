#!/usr/bin/env bash
# Install system libraries required to build/run Tauri 2 on Debian/Ubuntu Linux.
set -euo pipefail

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "Linux desktop deps are only needed on Linux. On macOS, use: npm run desktop:dev"
  exit 0
fi

if ! command -v apt-get >/dev/null 2>&1; then
  echo "This script supports Debian/Ubuntu (apt). Install Tauri prerequisites manually:" >&2
  echo "  https://v2.tauri.app/start/prerequisites/" >&2
  exit 1
fi

PACKAGES=(
  build-essential
  curl
  wget
  file
  pkg-config
  libssl-dev
  libgtk-3-dev
  libwebkit2gtk-4.1-dev
  libayatana-appindicator3-dev
  librsvg2-dev
)

echo "Installing Tauri 2 Linux build dependencies..."
sudo apt-get update
sudo apt-get install -y "${PACKAGES[@]}"

if pkg-config --exists gdk-3.0 'gdk-3.0 >= 3.22'; then
  echo "Tauri Linux dependencies OK (gdk-3.0 found)."
else
  echo "gdk-3.0 still missing after install — check your distro version (Ubuntu 22.04+ / Debian 12+)." >&2
  exit 1
fi
