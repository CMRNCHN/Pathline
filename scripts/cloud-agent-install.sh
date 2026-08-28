#!/usr/bin/env bash
# Idempotent Cloud Agent bootstrap for the Pathline v1 dev environment
# (thin FastAPI service + browser authoring/manual-fallback client).
#
# Runs after the repository is checked out. It only prepares dependencies and
# generated state — it never starts long-running servers (those live in the
# environment.json "terminals").
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# ── System dependency: python venv support ─────────────────────────────
# Creating .venv needs the OS python3.12-venv package (ensurepip). The base
# image ships python3.12 but not this package (see AGENTS.md).
if ! python3 -c "import ensurepip" >/dev/null 2>&1; then
  echo "▸ Installing python3.12-venv (required for venv creation)..."
  sudo apt-get update -qq
  sudo apt-get install -y -qq python3.12-venv
fi

# ── Local dev env file ─────────────────────────────────────────────────
if [[ ! -f .env ]]; then
  echo "▸ Creating .env from .env.example..."
  cp .env.example .env
fi

# ── Python venv + editable installs ────────────────────────────────────
if [[ -d .venv && ! -f .venv/bin/activate ]]; then
  echo "▸ Removing incomplete virtual environment..."
  rm -rf .venv
fi
if [[ ! -d .venv ]]; then
  echo "▸ Creating Python virtual environment..."
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate
echo "▸ Installing Python dependencies (shared-python + services/api[test])..."
pip install -q --upgrade pip
pip install -q -e packages/shared-python -e "services/api[test]"

# ── Client dependencies ────────────────────────────────────────────────
echo "▸ Installing client dependencies..."
(cd client && npm install --no-audit --no-fund)

echo "✓ Cloud Agent install complete."
