#!/usr/bin/env bash
# Codesign + notarize a Pathline.app or Pathline.dmg (operator-run).
#
# Prerequisites (never commit secrets):
#   - Developer ID Application certificate in Keychain
#   - notarytool keychain profile (default: pathline-notary)
#
# Usage:
#   PATHLINE_SIGN_IDENTITY="Developer ID Application: Your Name (TEAMID)" \
#     ./scripts/notarize-macos.sh path/to/Pathline.app
#   ./scripts/notarize-macos.sh path/to/Pathline.dmg
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'
info() { printf '%b\n' "${GREEN}▸${NC} $*"; }
fail() { printf '%b\n' "${RED}✗${NC} $*" >&2; exit 1; }

TARGET="${1:-}"
[[ -n "$TARGET" ]] || fail "Usage: $0 <Pathline.app|Pathline.dmg>"
[[ -e "$TARGET" ]] || fail "Not found: $TARGET"

IDENTITY="${PATHLINE_SIGN_IDENTITY:-}"
PROFILE="${PATHLINE_NOTARY_PROFILE:-pathline-notary}"

[[ -n "$IDENTITY" ]] || fail "Set PATHLINE_SIGN_IDENTITY to your Developer ID Application identity."

info "Codesigning $TARGET ..."
codesign --deep --force --options runtime --sign "$IDENTITY" "$TARGET"
codesign --verify --verbose=2 "$TARGET"

if [[ "$TARGET" == *.dmg ]]; then
  SUBMIT="$TARGET"
elif [[ "$TARGET" == *.app ]]; then
  # Prefer submitting a DMG; if given an .app, sign only and remind operator.
  info "Signed .app. Create a DMG (Tauri bundle) then re-run this script on the .dmg for notarization."
  exit 0
else
  fail "Expected .app or .dmg"
fi

info "Submitting $SUBMIT to Apple notary service (profile=$PROFILE) ..."
xcrun notarytool submit "$SUBMIT" --keychain-profile "$PROFILE" --wait
info "Stapling ticket ..."
xcrun stapler staple "$SUBMIT"
info "Done. Verify Gatekeeper with: spctl --assess --type open --verbose '$SUBMIT'"
