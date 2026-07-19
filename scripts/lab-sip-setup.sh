#!/usr/bin/env bash
# Generate TLS certs, SIP credentials, and rendered PJSIP config for the lab IVR.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

ENV_FILE="$ROOT/.env"
GENERATED="$ROOT/lab/asterisk/generated"
TLS_DIR="$GENERATED/tls"
CREDS_FILE="$GENERATED/credentials.env"

mkdir -p "$TLS_DIR"

if [[ ! -f "$ENV_FILE" ]]; then
  cp "$ROOT/.env.example" "$ENV_FILE"
fi

# shellcheck disable=SC1090
set -a
source "$ENV_FILE"
set +a

LAB_SIP_USER="${LAB_SIP_USER:-pathline-lab}"
LAB_SIP_TLS_PORT="${LAB_SIP_TLS_PORT:-5061}"

ensure_env_var() {
  local key="$1"
  local value="$2"
  if grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
    # Replace empty placeholders (e.g. LAB_SIP_PASSWORD= from .env.example).
    if grep -Eq "^${key}=[[:space:]]*$" "$ENV_FILE" 2>/dev/null; then
      local tmp
      tmp="$(mktemp)"
      awk -v key="$key" -v value="$value" '
        BEGIN { replaced = 0 }
        index($0, key "=") == 1 && !replaced {
          print key "=" value
          replaced = 1
          next
        }
        { print }
      ' "$ENV_FILE" > "$tmp"
      mv "$tmp" "$ENV_FILE"
    fi
    return 0
  fi
  echo "${key}=${value}" >> "$ENV_FILE"
}

if [[ -z "${LAB_SIP_PASSWORD:-}" ]]; then
  LAB_SIP_PASSWORD="$(openssl rand -base64 32 | tr -d '/+=' | head -c 32)"
  ensure_env_var "LAB_SIP_USER" "$LAB_SIP_USER"
  ensure_env_var "LAB_SIP_TLS_PORT" "$LAB_SIP_TLS_PORT"
  ensure_env_var "LAB_SIP_PASSWORD" "$LAB_SIP_PASSWORD"
  # Keep the generated password in-shell; do not re-source .env here or an
  # empty placeholder line would wipe the value again.
fi

if [[ ! -f "$TLS_DIR/asterisk.crt" || ! -f "$TLS_DIR/asterisk.key" ]]; then
  openssl req -x509 -newkey rsa:2048 -nodes \
    -keyout "$TLS_DIR/asterisk.key" \
    -out "$TLS_DIR/asterisk.crt" \
    -days 825 \
    -subj "/CN=127.0.0.1/O=Pathline Lab/C=US" \
    2>/dev/null
  chmod 600 "$TLS_DIR/asterisk.key"
  chmod 644 "$TLS_DIR/asterisk.crt"
fi

TEMPLATE="$ROOT/lab/asterisk/pjsip.lab.conf.template"
OUTPUT="$GENERATED/pjsip.lab.conf"

sed \
  -e "s/\${LAB_SIP_USER}/${LAB_SIP_USER}/g" \
  -e "s/\${LAB_SIP_PASSWORD}/${LAB_SIP_PASSWORD}/g" \
  -e "s/\${LAB_SIP_TLS_PORT}/${LAB_SIP_TLS_PORT}/g" \
  "$TEMPLATE" > "$OUTPUT"

cat > "$CREDS_FILE" <<EOF
# Lab softphone — local dev only. Do not commit.
LAB_SIP_USER=${LAB_SIP_USER}
LAB_SIP_PASSWORD=${LAB_SIP_PASSWORD}
LAB_SIP_TLS_PORT=${LAB_SIP_TLS_PORT}
LAB_SIP_TRANSPORT=tls
LAB_SIP_SERVER=127.0.0.1
EOF
chmod 600 "$CREDS_FILE"

echo "Lab SIP ready: TLS ${LAB_SIP_TLS_PORT}, user ${LAB_SIP_USER}"
echo "Credentials: ${CREDS_FILE}"
