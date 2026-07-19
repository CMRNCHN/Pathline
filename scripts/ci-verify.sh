#!/usr/bin/env bash
# Local equivalent of the CI release gates. Does not perform Apple signing,
# notarization, or carrier trunk acceptance — those require external secrets.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'
ok() { printf '%b\n' "${GREEN}✓${NC} $*"; }
fail() { printf '%b\n' "${RED}✗${NC} $*"; exit 1; }

info() { printf '%b\n' "${GREEN}▸${NC} $*"; }

info "Client unit tests"
(cd client && npm test)
ok "client tests"

info "Client production build"
(cd client && npm run build)
ok "client build"

info "STT fixture"
(cd client && npm run stt:fixture)
ok "stt fixture"

info "API tests"
(
  cd services/api
  export PATHLINE_ENV=development
  export JWT_SECRET="${JWT_SECRET:-ci-jwt-secret-not-for-production}"
  export SESSION_PEPPER="${SESSION_PEPPER:-ci-session-pepper-not-for-production}"
  export DATABASE_URL="${DATABASE_URL:-sqlite+aiosqlite:///./ci-pathline.db}"
  export CORS_ALLOW_ORIGINS="${CORS_ALLOW_ORIGINS:-http://127.0.0.1:3000}"
  pytest -q
)
ok "api tests"

info "Alembic migration"
(
  cd services/api
  export PATHLINE_ENV=development
  export JWT_SECRET="${JWT_SECRET:-ci-jwt-secret-not-for-production}"
  export SESSION_PEPPER="${SESSION_PEPPER:-ci-session-pepper-not-for-production}"
  export DATABASE_URL=sqlite+aiosqlite:///./ci-migrate.db
  rm -f ci-migrate.db
  alembic upgrade head
)
ok "alembic upgrade head"

if [[ "${SKIP_CARGO:-0}" == "1" ]]; then
  info "Skipping cargo test (SKIP_CARGO=1)"
else
  info "Desktop Rust tests"
  (
    cd desktop/src-tauri
    export PATHLINE_SIP_PROFILE=lab
    cargo test
  )
  ok "cargo test"
fi

info "Static lab verification"
SKIP_LAB_PREFLIGHT=1 bash scripts/lab-verify-flow.sh
ok "lab static verification"

info "Model resource checksum"
python3 - <<'PY'
import hashlib, json, pathlib, sys
root = pathlib.Path("desktop/src-tauri/resources/models")
manifest = json.loads((root / "model-manifest.json").read_text())
path = root / manifest["filename"]
if not path.exists():
    sys.exit(f"missing model: {path}")
digest = hashlib.sha256(path.read_bytes()).hexdigest()
assert digest == manifest["sha256"], (digest, manifest["sha256"])
print(digest)
PY
ok "model checksum"

cat <<'EOF'

All local CI gates passed.

External / operator gates (not run here):
  - Recorded macOS Tauri → Asterisk → Whisper → DTMF → encrypted callstate acceptance
  - Live packet capture proving no STT/transcript egress
  - Production SIP trunk with SRTP (blocked until rsiprtp gains SRTP)
  - Apple Developer ID signing + notarization
  - Clean-machine install/upgrade/rollback of a signed release DMG
EOF
