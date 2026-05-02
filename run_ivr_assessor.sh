#!/usr/bin/env bash
set -euo pipefail

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

if [ -f "$DIR/.env" ]; then
    set -a
    source "$DIR/.env"
    set +a
fi

"$DIR/backend/python/.venv/bin/python" -m ivr_assessor.cli "$@"
# Check if the command failed and exit with its code
exit $?