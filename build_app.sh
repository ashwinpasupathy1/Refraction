#!/usr/bin/env bash
# build_app.sh — Build Claude Plotter as a macOS .app bundle
#
# Usage:
#   ./build_app.sh           # full build
#   ./build_app.sh --clean   # wipe previous build artefacts first
#
# Prerequisites (must be on PATH):
#   python3   — with all packages from requirements.txt installed
#   node / npm — for building the React SPA
#   pyinstaller — pip install pyinstaller

set -euo pipefail

# ── Resolve script directory (works even when called from another dir) ────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Colour helpers ────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'  # no colour

info()    { echo -e "${CYAN}[build]${NC} $*"; }
success() { echo -e "${GREEN}[build]${NC} $*"; }
warn()    { echo -e "${YELLOW}[build]${NC} WARNING: $*"; }
error()   { echo -e "${RED}[build]${NC} ERROR: $*" >&2; }
die()     { error "$*"; exit 1; }

# ── Parse arguments ───────────────────────────────────────────────────────────
CLEAN=false
for arg in "$@"; do
    case "$arg" in
        --clean) CLEAN=true ;;
        -h|--help)
            echo "Usage: $0 [--clean]"
            echo ""
            echo "  --clean   Remove build/, dist/, and plotter_web/dist/ before building."
            exit 0
            ;;
        *) warn "Unknown argument: $arg (ignored)" ;;
    esac
done

echo ""
echo -e "${BOLD}╔══════════════════════════════════════╗${NC}"
echo -e "${BOLD}║      Claude Plotter — App Builder    ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════╝${NC}"
echo ""

# ── Optional clean ────────────────────────────────────────────────────────────
if [ "$CLEAN" = true ]; then
    info "--clean requested: removing previous build artefacts..."
    rm -rf build dist plotter_web/dist
    success "Clean complete."
fi

# ── 1. Check prerequisites ────────────────────────────────────────────────────
info "Checking prerequisites..."

# python3
if ! command -v python3 &>/dev/null; then
    die "python3 not found. Install Python 3.11+ from https://www.python.org"
fi
PYTHON_VERSION="$(python3 --version 2>&1)"
info "  python3  : $PYTHON_VERSION"

# node
if ! command -v node &>/dev/null; then
    die "node not found. Install Node.js 18+ from https://nodejs.org"
fi
NODE_VERSION="$(node --version)"
info "  node     : $NODE_VERSION"

# npm
if ! command -v npm &>/dev/null; then
    die "npm not found (should ship with Node.js)."
fi
NPM_VERSION="$(npm --version)"
info "  npm      : $NPM_VERSION"

# pyinstaller
if ! python3 -m PyInstaller --version &>/dev/null 2>&1; then
    die "PyInstaller not found. Install with: pip install pyinstaller"
fi
PYINSTALLER_VERSION="$(python3 -m PyInstaller --version 2>&1)"
info "  pyinstaller: $PYINSTALLER_VERSION"

# plotter_desktop.py (entry point created by another agent)
if [ ! -f "plotter_desktop.py" ]; then
    die "plotter_desktop.py not found. This file must exist before building the app bundle."
fi
info "  plotter_desktop.py: found"

# spec file
if [ ! -f "claude_plotter.spec" ]; then
    die "claude_plotter.spec not found. Has it been deleted?"
fi
info "  claude_plotter.spec: found"

# icon (optional — warn but continue)
if [ ! -f "assets/icon.icns" ]; then
    warn "assets/icon.icns not found. The app will use PyInstaller's default icon."
    warn "To add one: mkdir -p assets && cp your_icon.icns assets/icon.icns"
fi

success "All required prerequisites satisfied."
echo ""

# ── 2. Build React SPA ────────────────────────────────────────────────────────
info "Building React SPA (plotter_web)..."

if [ ! -d "plotter_web" ]; then
    die "plotter_web/ directory not found."
fi

cd plotter_web

info "  Running: npm install"
npm install --prefer-offline 2>&1 | tail -5

info "  Running: npm run build"
npm run build 2>&1 | tail -20

cd "$SCRIPT_DIR"

if [ ! -d "plotter_web/dist" ]; then
    die "npm run build did not produce plotter_web/dist/. Check build errors above."
fi

DIST_FILES="$(find plotter_web/dist -type f | wc -l | tr -d ' ')"
success "React SPA built successfully ($DIST_FILES files in plotter_web/dist/)."
echo ""

# ── 3. Run PyInstaller ────────────────────────────────────────────────────────
info "Running PyInstaller..."
python3 -m PyInstaller claude_plotter.spec \
    --noconfirm \
    --log-level WARN

echo ""

# ── 4. Verify output ──────────────────────────────────────────────────────────
APP_BUNDLE="$SCRIPT_DIR/dist/Claude Plotter.app"

if [ ! -d "$APP_BUNDLE" ]; then
    die "Build finished but 'dist/Claude Plotter.app' not found. Check PyInstaller output above."
fi

# Calculate bundle size (du -sh gives human-readable total)
APP_SIZE="$(du -sh "$APP_BUNDLE" 2>/dev/null | cut -f1)"

echo ""
echo -e "${BOLD}╔══════════════════════════════════════╗${NC}"
echo -e "${BOLD}║            Build Complete!           ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════╝${NC}"
echo ""
success "App bundle  : $APP_BUNDLE"
success "Bundle size : $APP_SIZE"
echo ""
info "To run the app:"
echo "    open \"$APP_BUNDLE\""
echo ""
info "To copy to /Applications:"
echo "    cp -r \"$APP_BUNDLE\" /Applications/"
echo ""
