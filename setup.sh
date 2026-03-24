#!/usr/bin/env bash
# Refraction -- One-command setup
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

# -- Check Python --
if command -v python3 &>/dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    ok "Python $PYTHON_VERSION found"
else
    err "Python 3 not found. Install from https://python.org or: brew install python3"
    exit 1
fi

# -- Install Python dependencies --
info "Installing Python dependencies..."
pip3 install -r requirements.txt --quiet
ok "Python dependencies installed"

# -- Verify setup --
info "Verifying setup..."

python3 -c "
from refraction.analysis import analyze
from refraction.core import chart_helpers, validators, registry
from refraction.server import api
print('  Python modules: OK')
" 2>&1 || { err "Python module import failed"; exit 1; }

ok "Setup complete!"
echo ""
echo "  The Python analysis server powers the SwiftUI desktop app."
echo "  To run tests:  python3 -m pytest tests/ -v"
echo "  Open RefractionApp/ in Xcode for the native app."
echo ""
