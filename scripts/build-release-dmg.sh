#!/usr/bin/env bash
# Build a Tauri release DMG/app for Pathline (not the Dock launcher wrappers).
#
# Usage:
#   PATHLINE_API_URL=https://api.example.com ./scripts/build-release-dmg.sh
#
# Requires: Rust toolchain, CMake (Whisper), Node, macOS for .dmg output.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'
info() { printf '%b\n' "${GREEN}▸${NC} $*"; }
fail() { printf '%b\n' "${RED}✗${NC} $*" >&2; exit 1; }

API_URL="${PATHLINE_API_URL:-}"
if [[ -z "$API_URL" ]]; then
  fail "Set PATHLINE_API_URL to an https:// origin (e.g. https://api.example.com).
Relative /api is browser-dev only and must not ship in the Tauri webview."
fi
case "$API_URL" in
  https://*) ;;
  *) fail "PATHLINE_API_URL must be an https:// origin, got: $API_URL" ;;
esac

info "Fetching / verifying bundled Whisper model ..."
"$ROOT/desktop/src-tauri/resources/models/fetch-model.sh"

MODEL="$ROOT/desktop/src-tauri/resources/models/ggml-tiny.en.bin"
EXPECTED="921e4cf8686fdd993dcd081a5da5b6c365bfde1162e72b08d75ac75289920b1f"
if command -v shasum >/dev/null 2>&1; then
  ACTUAL="$(shasum -a 256 "$MODEL" | awk '{print $1}')"
else
  ACTUAL="$(sha256sum "$MODEL" | awk '{print $1}')"
fi
[[ "$ACTUAL" == "$EXPECTED" ]] || fail "Whisper model checksum mismatch"

info "Building client + Tauri with PATHLINE_API_URL=$API_URL ..."
export PATHLINE_API_URL
# Compile-time inject for api_boundary.rs (option_env!)
(
  cd "$ROOT/client" && npm run build
)
(
  cd "$ROOT/desktop" && PATHLINE_API_URL="$API_URL" npm run build
)

info "Release build finished. Artifacts under desktop/src-tauri/target/release/bundle/"
info "Next (operator): ./scripts/notarize-macos.sh <path-to-Pathline.app-or.dmg>"
info "Note: scripts/build-macos-app.sh builds Dock *launcher* wrappers only — not this release."
