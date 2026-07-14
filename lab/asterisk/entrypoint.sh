#!/bin/sh
set -eu

MARKER="# Pathline lab block"
EXT="/etc/asterisk/extensions.conf"
PJSIP="/etc/asterisk/pjsip.conf"

if ! grep -qF "$MARKER" "$EXT" 2>/dev/null; then
  {
    echo ""
    echo "$MARKER"
    cat /lab/extensions_lab.conf
  } >> "$EXT"
fi

if ! grep -qF "$MARKER" "$PJSIP" 2>/dev/null; then
  {
    echo ""
    echo "$MARKER"
    cat /lab/pjsip.lab.conf
  } >> "$PJSIP"
fi

exec asterisk -f -vvv
