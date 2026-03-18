#!/usr/bin/env bash
# Claude Plotter — One-command setup
# Usage: ./setup.sh [desktop|web|build]
#
#   ./setup.sh           — install everything (Python + Node + build SPA)
#   ./setup.sh desktop   — desktop only (Python deps, no Node needed)
#   ./setup.sh web       — web mode (Python + Node + build SPA)
#   ./setup.sh build     — build React SPA only (assumes Node installed)

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

MODE="${1:-all}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# ── Check Python ────────────────────────────────────────────────
check_python() {
    if command -v python3 &>/dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
        ok "Python $PYTHON_VERSION found"
    else
        err "Python 3 not found. Install from https://python.org or: brew install python3"
        exit 1
    fi
}

# ── Check/install Node.js ───────────────────────────────────────
check_node() {
    if command -v node &>/dev/null && command -v npm &>/dev/null; then
        NODE_VERSION=$(node --version 2>&1)
        ok "Node.js $NODE_VERSION found"
        return 0
    fi

    warn "Node.js not found."

    # Try Homebrew on macOS
    if [[ "$(uname)" == "Darwin" ]] && command -v brew &>/dev/null; then
        info "Installing Node.js via Homebrew..."
        brew install node
        ok "Node.js installed"
        return 0
    fi

    # Suggest manual install
    err "Please install Node.js: https://nodejs.org or: brew install node"
    return 1
}

# ── Install Python dependencies ─────────────────────────────────
install_python_deps() {
    info "Installing Python dependencies..."
    if [[ "$MODE" == "web" ]]; then
        pip3 install -r requirements-web.txt --quiet
    else
        pip3 install -r requirements.txt --quiet
    fi
    ok "Python dependencies installed"
}

# ── Build React SPA ─────────────────────────────────────────────
build_spa() {
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
}

# ── Verify setup ────────────────────────────────────────────────
verify() {
    info "Verifying setup..."

    # Quick import check
    python3 -c "
import plotter_functions, plotter_widgets, plotter_validators, plotter_results
import plotter_server
print('  Python modules: OK')
" 2>&1 || { err "Python module import failed"; exit 1; }

    if [ -d "plotter_web/dist" ]; then
        echo "  React SPA: OK"
    else
        echo "  React SPA: not built (web mode won't serve UI)"
    fi

    ok "Setup complete!"
    echo ""
    echo "  To run:"
    if [[ "$MODE" == "desktop" ]]; then
        echo "    python3 plotter_barplot_app.py"
    elif [[ "$MODE" == "web" ]]; then
        echo "    python3 plotter_web_server.py"
        echo "    Open http://localhost:7331"
    else
        echo "    Desktop:  python3 plotter_barplot_app.py"
        echo "    Web:      python3 plotter_web_server.py → http://localhost:7331"
    fi
    echo ""
}

# ── Main ────────────────────────────────────────────────────────
echo ""
echo "  Claude Plotter Setup"
echo "  ===================="
echo ""

check_python

case "$MODE" in
    desktop)
        install_python_deps
        ;;
    web)
        install_python_deps
        check_node && build_spa
        ;;
    build)
        check_node && build_spa
        ;;
    all)
        install_python_deps
        if check_node; then
            build_spa
        else
            warn "Skipping React SPA build (Node.js not available)"
            warn "Desktop mode will still work. Install Node.js for web mode."
        fi
        ;;
    *)
        echo "Usage: ./setup.sh [desktop|web|build|all]"
        exit 1
        ;;
esac

verify
