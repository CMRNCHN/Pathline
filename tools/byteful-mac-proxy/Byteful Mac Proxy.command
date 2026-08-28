#!/bin/bash
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"
echo "Starting Byteful Mac Proxy…"
exec /usr/bin/env python3 "$DIR/byteful_mac_proxy.py"
