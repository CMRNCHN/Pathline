#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
VENV_PYTHON="$DIR/backend/python/.venv/bin/python"

if [[ -x "$VENV_PYTHON" ]]; then
  PYTHON_BIN="$VENV_PYTHON"
else
  PYTHON_BIN="${PYTHON_BIN:-python3}"
fi

PYTHONPATH="$DIR/backend/python/src${PYTHONPATH:+:$PYTHONPATH}" \
  "$PYTHON_BIN" -m ivr_assessor.cli "$@"