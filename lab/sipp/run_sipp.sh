#!/usr/bin/env bash
# SIPp load test against lab Asterisk instance
# Usage: ./run_sipp.sh [asterisk_host]

HOST="${1:-localhost}"
PORT="${2:-5060}"

echo "Running SIPp UAC test against ${HOST}:${PORT}..."
echo "Requires SIPp installed: brew install sipp (macOS)"

if ! command -v sipp &>/dev/null; then
  echo "SIPp not found. Install with: brew install sipp"
  exit 1
fi

# Basic UAC scenario — calls extension 1000
sipp "${HOST}:${PORT}" \
  -sn uac \
  -s 1000 \
  -m 1 \
  -trace_msg \
  -trace_err
