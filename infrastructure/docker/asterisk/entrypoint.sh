#!/bin/sh
# Render the optional SIP trunk from TRUNK_* env vars, then start Asterisk.
# Keeps real credentials out of the image and out of git — they arrive at
# runtime via the container environment (infrastructure/.env), never baked in.
set -eu

TEMPLATE=/etc/asterisk/pjsip_trunk.conf.template
OUT=/etc/asterisk/pjsip_trunk.conf

if [ -n "${TRUNK_HOST:-}" ] && [ -n "${TRUNK_USER:-}" ] && [ -n "${TRUNK_PASS:-}" ]; then
    export TRUNK_FROM_USER="${TRUNK_FROM_USER:-$TRUNK_USER}"
    export GATEWAY_IP="${GATEWAY_IP:-}"
    # Only substitute our own vars, so nothing else in the file is touched.
    envsubst '$TRUNK_HOST $TRUNK_USER $TRUNK_PASS $TRUNK_FROM_USER $GATEWAY_IP' \
        < "$TEMPLATE" > "$OUT"
    echo "[entrypoint] SIP trunk enabled for ${TRUNK_HOST} (registration endpoint 'trunk')."
    echo "[entrypoint] Dial with PULSE_ENDPOINT=\"PJSIP/<number>@trunk\"."
else
    : > "$OUT"
    echo "[entrypoint] No TRUNK_* credentials set; SIP trunk disabled."
    echo "[entrypoint] Set TRUNK_HOST / TRUNK_USER / TRUNK_PASS in infrastructure/.env to enable."
fi

exec asterisk -f -vvv
