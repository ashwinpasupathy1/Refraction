#!/usr/bin/env bash
# Refraction — One-command setup
# Usage: ./setup.sh

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info()  { echo -e "${BLUE}[INFO]${NC} $*"; }
ok()    { echo -e "${GREEN}[OK]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()   { echo -e "${RED}[ERROR]${NC} $*"; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "  Refraction Setup"
echo "  ================"
echo ""

# ── Check Python ────────────────────────────────────────────────
if command -v python3 &>/dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    ok "Python $PYTHON_VERSION found"
else
    err "Python 3 not found. Install from https://python.org or: brew install python3"
    exit 1
fi

# ── Install Python dependencies ─────────────────────────────────
info "Installing Python dependencies..."
pip3 install -r requirements.txt --quiet
ok "Python dependencies installed"

# ── Check/install Node.js ───────────────────────────────────────
if command -v node &>/dev/null && command -v npm &>/dev/null; then
    NODE_VERSION=$(node --version 2>&1)
    ok "Node.js $NODE_VERSION found"

    # Build React SPA
    info "Building React SPA..."
    cd "$SCRIPT_DIR/plotter_web"

    if [ ! -d "node_modules" ]; then
        info "Installing Node dependencies..."
        npm install --silent 2>&1 | tail -1
    fi

    npm run build 2>&1 | tail -3
    cd "$SCRIPT_DIR"

    if [ -d "plotter_web/dist" ]; then
        ok "React SPA built → plotter_web/dist/"
    else
        err "Build failed — plotter_web/dist/ not created"
        exit 1
    fi
else
    warn "Node.js not found. The SPA will be auto-built on first launch."
    warn "Install Node.js for faster startup: https://nodejs.org or: brew install node"
fi

# ── Verify setup ────────────────────────────────────────────────
info "Verifying setup..."

python3 -c "
from refraction.core import chart_helpers, validators
from refraction.app import widgets, results
from refraction.server import api
print('  Python modules: OK')
" 2>&1 || { err "Python module import failed"; exit 1; }

if [ -d "plotter_web/dist" ]; then
    echo "  React SPA: OK"
else
    echo "  React SPA: will auto-build on first launch"
fi

ok "Setup complete!"
echo ""
echo "  To run:  python3 plotter_desktop.py"
echo ""
