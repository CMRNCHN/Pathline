#!/usr/bin/env bash
#
# ARI DTMF transport probe — raw, uncontaminated, wire-level evidence.
#
# ONE question, answered by runtime signals (NOT by reading Asterisk source):
#
#     On POST /ari/channels/{id}/dtmf, does ARI read `dtmf` from a JSON body,
#     a form-urlencoded body, or neither (query only)?
#
# This script DECIDES NOTHING. It emits the raw request and the raw response for
# each variant and stops. A human classifies A/B/C afterward from two facts:
#   (1) the HTTP status, and (2) whether the channel/IVR actually advanced.
#
# It shares no code with the Pulse Swift client on purpose: a probe that reuses
# the client's request builder would only confirm the client's own encoding
# assumptions, not ARI's real behavior.
#
# ─────────────────────────────────────────────────────────────────────────────
# HARD PRECONDITION — a REAL, LIVE channel id.
#
# A fake or dead channel makes ARI fail at route/channel resolution (404) BEFORE
# it ever inspects `dtmf`. That 404 says nothing about body-vs-query encoding —
# it only means "you never reached the handler that parses anything." That is the
# exact trap this probe refuses to repeat: it verifies the channel is live first
# and aborts if it is not.
#
# ─────────────────────────────────────────────────────────────────────────────
# HOW TO GET A LIVE CHANNEL ID (do this first, in another terminal):
#
#   1. Start the container:
#        docker compose -f infrastructure/docker-compose.yml up asterisk -d
#
#   2. Originate a loopback call with a chosen channel id, into the pulse app:
#        curl -sS -X POST \
#          "http://127.0.0.1:8088/ari/channels?endpoint=Local/1000@ivr-test&app=pulse&channelId=probe-1&api_key=ari:ari"
#
#      (Or click Run Probe in Pulse and read the channel id from the transcript.)
#
#   3. While the call is up, run THIS script with that id:
#        ./tools/ivr_beacon/probe-ari-dtmf.sh probe-1
#
# NEVER pass a real card number to this probe. Use a throwaway digit (default 5).
# This probe is for transport discovery only, not for sending cardholder data.
# ─────────────────────────────────────────────────────────────────────────────

set -u

HOST="${PULSE_ARI_HOST:-127.0.0.1}"
PORT="${PULSE_ARI_PORT:-8088}"
KEY="${PULSE_ARI_API_KEY:-ari:ari}"
CH="${1:-}"
DTMF="${2:-5}"

base="http://${HOST}:${PORT}/ari"

if [ -z "$CH" ]; then
  echo "usage: $0 <live-channel-id> [dtmf-digit]" >&2
  echo "  <live-channel-id> must be an ACTIVE channel (see header for how to get one)." >&2
  echo "  [dtmf-digit] defaults to 5. Never pass a real card number." >&2
  exit 2
fi

case "$DTMF" in
  *[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]*)
    echo "REFUSING: the dtmf value looks card-shaped (13+ digits)." >&2
    echo "This probe is for transport discovery only — use a throwaway digit." >&2
    exit 2 ;;
esac

# ── PRECONDITION: the channel must be live, or the probe is invalid ───────────
echo "=== PRECONDITION: channel must be live (else DTMF results are meaningless) ==="
pre_body="$(mktemp)"
pre_status="$(curl -sS -o "$pre_body" -w '%{http_code}' \
  "${base}/channels/${CH}?api_key=${KEY}")"
echo "GET /channels/${CH} -> HTTP ${pre_status}"
echo "--- body ---"
cat "$pre_body"; echo
rm -f "$pre_body"

if [ "$pre_status" != "200" ]; then
  echo
  echo "PRECONDITION FAILED: channel '${CH}' is not live (HTTP ${pre_status})."
  echo "A non-live channel makes ARI fail at route/channel resolution — any DTMF"
  echo "result below would reflect that, NOT body-vs-query encoding. Aborting."
  echo "Originate a real call, capture its channel id, and retry while it is up."
  exit 1
fi

# ── Fire each variant and emit the raw wire trace + status. No interpretation. ─
probe() {
  label="$1"; shift
  echo
  echo "============================================================"
  echo "VARIANT: ${label}"
  echo "============================================================"
  # -v prints the raw request line, headers, and response status to stderr;
  # 2>&1 folds it into stdout so the full exchange is captured verbatim.
  curl -sS -v "$@" 2>&1
  echo
}

probe "JSON body (Content-Type: application/json)" \
  -X POST "${base}/channels/${CH}/dtmf?api_key=${KEY}" \
  -H 'Content-Type: application/json' \
  --data "{\"dtmf\":\"${DTMF}\"}" \
  -w 'HTTP_STATUS:%{http_code}\n'

probe "form-urlencoded body (Content-Type: application/x-www-form-urlencoded)" \
  -X POST "${base}/channels/${CH}/dtmf?api_key=${KEY}" \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data "dtmf=${DTMF}" \
  -w 'HTTP_STATUS:%{http_code}\n'

# ── What to observe. The script asserts nothing; you classify A/B/C by hand. ──
cat <<'EOF'

============================================================
OBSERVE — this script does not decide. Record two facts per variant:
  1. HTTP_STATUS:  2xx vs 4xx
  2. Did the channel/IVR advance? (watch the Pulse transcript / ARI events)

Then classify by hand:
  A → 2xx AND the IVR advanced      → no code change
  B → 2xx BUT nothing happened      → encoding accepted but not applied
  C → 4xx (e.g. "DTMF is required") → encoding rejected

ORDERING CAVEAT: both variants ran against the SAME live channel. If the FIRST
variant returned 2xx, it may have changed channel state before the second ran.
To isolate cleanly, re-run each variant against its OWN fresh channel.
============================================================
EOF
