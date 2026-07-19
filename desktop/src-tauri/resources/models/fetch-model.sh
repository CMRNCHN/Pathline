#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
MODEL="$ROOT/ggml-tiny.en.bin"
URL="https://huggingface.co/ggerganov/whisper.cpp/resolve/90a64d80ea254cf67575b41a5971f972c79f7b45/ggml-tiny.en.bin"
SHA256="921e4cf8686fdd993dcd081a5da5b6c365bfde1162e72b08d75ac75289920b1f"
TMP="$MODEL.download"

checksum() {
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$1" | awk '{print $1}'
  else
    sha256sum "$1" | awk '{print $1}'
  fi
}

if [[ -f "$MODEL" ]] && [[ "$(checksum "$MODEL")" == "$SHA256" ]]; then
  printf 'Whisper model already verified: %s\n' "$MODEL"
  exit 0
fi

rm -f "$TMP"
curl --fail --location --retry 3 --output "$TMP" "$URL"
ACTUAL="$(checksum "$TMP")"
if [[ "$ACTUAL" != "$SHA256" ]]; then
  rm -f "$TMP"
  printf 'Whisper model checksum mismatch: expected %s, got %s\n' "$SHA256" "$ACTUAL" >&2
  exit 1
fi

mv "$TMP" "$MODEL"
printf 'Downloaded and verified Whisper model: %s\n' "$MODEL"
