#!/usr/bin/env bash
# build_app.sh — Build Refraction as a macOS .app and optional .dmg
#
# Usage:
#   ./build_app.sh           # build .app only
#   ./build_app.sh --dmg     # build .app + .dmg installer
#   ./build_app.sh --clean   # wipe previous build artefacts first
#   ./build_app.sh --sign    # code sign + notarize (requires Apple Developer ID)
#
# Flags can be combined:
#   ./build_app.sh --clean --dmg --sign
#
# Prerequisites (must be on PATH):
#   python3      — with all packages from requirements.txt installed
#   node / npm   — for building the React SPA
#   pyinstaller  — pip install pyinstaller
#   create-dmg   — (optional) brew install create-dmg — for pretty DMG

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
BUILD_DMG=false
CODE_SIGN=false
DEVELOPER_ID="${DEVELOPER_ID:-}"  # "Developer ID Application: Your Name (TEAMID)"

for arg in "$@"; do
    case "$arg" in
        --clean) CLEAN=true ;;
        --dmg)   BUILD_DMG=true ;;
        --sign)  CODE_SIGN=true ;;
        -h|--help)
            echo "Usage: $0 [--clean] [--dmg] [--sign]"
            echo ""
            echo "  --clean   Remove build/, dist/, and plotter_web/dist/ before building."
            echo "  --dmg     Create a .dmg installer after building the .app."
            echo "  --sign    Code sign and notarize (requires DEVELOPER_ID env var)."
            echo ""
            echo "Environment variables:"
            echo "  DEVELOPER_ID    Apple Developer ID for code signing"
            echo "                  e.g. 'Developer ID Application: John Doe (ABC123)'"
            echo "  APPLE_ID        Apple ID email for notarization"
            echo "  APPLE_TEAM_ID   Apple Team ID for notarization"
            echo "  NOTARY_KEYCHAIN_PROFILE  Keychain profile for notarytool"
            exit 0
            ;;
        *) warn "Unknown argument: $arg (ignored)" ;;
    esac
done

echo ""
echo -e "${BOLD}╔══════════════════════════════════════╗${NC}"
echo -e "${BOLD}║        Refraction — App Builder         ║${NC}"
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
if [ ! -f "refraction.spec" ]; then
    die "refraction.spec not found. Has it been deleted?"
fi
info "  refraction.spec: found"

# icon (optional — warn but continue)
if [ ! -f "assets/AppIcon.icns" ]; then
    warn "assets/AppIcon.icns not found. Run: python3 generate_refraction_logos.py"
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
python3 -m PyInstaller refraction.spec \
    --noconfirm \
    --log-level WARN

echo ""

# ── 4. Verify output ──────────────────────────────────────────────────────────
APP_BUNDLE="$SCRIPT_DIR/dist/Refraction.app"

if [ ! -d "$APP_BUNDLE" ]; then
    die "Build finished but 'dist/Refraction.app' not found. Check PyInstaller output above."
fi

# Calculate bundle size (du -sh gives human-readable total)
APP_SIZE="$(du -sh "$APP_BUNDLE" 2>/dev/null | cut -f1)"

# ── 5. Code signing (optional) ──────────────────────────────────────────────
if [ "$CODE_SIGN" = true ]; then
    echo ""
    info "Code signing..."

    if [ -z "$DEVELOPER_ID" ]; then
        warn "DEVELOPER_ID not set. Skipping code signing."
        warn "Set it with: export DEVELOPER_ID='Developer ID Application: Your Name (TEAMID)'"
        CODE_SIGN=false
    else
        info "  Signing with: $DEVELOPER_ID"

        # Sign all frameworks and dylibs first, then the app itself
        find "$APP_BUNDLE" \( -name "*.dylib" -o -name "*.so" -o -name "*.framework" \) -print0 | while IFS= read -r -d '' lib; do
            codesign --force --sign "$DEVELOPER_ID" --options runtime "$lib" 2>/dev/null || true
        done

        # Sign the main executable
        codesign --force --sign "$DEVELOPER_ID" \
            --options runtime \
            --entitlements /dev/stdin "$APP_BUNDLE" <<ENTITLEMENTS
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>com.apple.security.cs.allow-unsigned-executable-memory</key>
    <true/>
    <key>com.apple.security.network.client</key>
    <true/>
    <key>com.apple.security.network.server</key>
    <true/>
    <key>com.apple.security.files.user-selected.read-write</key>
    <true/>
</dict>
</plist>
ENTITLEMENTS

        # Verify signature
        if codesign --verify --deep --strict "$APP_BUNDLE" 2>/dev/null; then
            success "Code signing verified."
        else
            warn "Code signing verification failed. The app may trigger Gatekeeper warnings."
        fi

        # Notarize if credentials are available
        NOTARY_PROFILE="${NOTARY_KEYCHAIN_PROFILE:-}"
        if [ -n "$NOTARY_PROFILE" ]; then
            info "Notarizing..."
            # Create a zip for notarization
            NOTARY_ZIP="$SCRIPT_DIR/dist/Claude_Plotter_notarize.zip"
            ditto -c -k --keepParent "$APP_BUNDLE" "$NOTARY_ZIP"

            xcrun notarytool submit "$NOTARY_ZIP" \
                --keychain-profile "$NOTARY_PROFILE" \
                --wait

            # Staple the notarization ticket
            xcrun stapler staple "$APP_BUNDLE"
            rm -f "$NOTARY_ZIP"
            success "Notarization complete and stapled."
        else
            info "Skipping notarization (set NOTARY_KEYCHAIN_PROFILE to enable)."
            info "To set up: xcrun notarytool store-credentials 'refraction' \\"
            info "  --apple-id your@email.com --team-id TEAMID --password app-specific-pwd"
        fi
    fi
fi

# ── 6. Build DMG (optional) ────────────────────────────────────────────────
DMG_PATH=""
if [ "$BUILD_DMG" = true ]; then
    echo ""
    info "Building DMG installer..."

    DMG_PATH="$SCRIPT_DIR/dist/Refraction.dmg"
    rm -f "$DMG_PATH"

    if command -v create-dmg &>/dev/null; then
        # Pretty DMG with Applications shortcut and layout
        info "  Using create-dmg for styled installer..."
        create-dmg \
            --volname "Refraction" \
            --window-pos 200 120 \
            --window-size 600 400 \
            --icon-size 100 \
            --icon "Refraction.app" 150 190 \
            --app-drop-link 450 190 \
            --hide-extension "Refraction.app" \
            --no-internet-enable \
            "$DMG_PATH" \
            "$APP_BUNDLE" \
            || {
                # create-dmg returns non-zero even on success sometimes
                if [ -f "$DMG_PATH" ]; then
                    true  # DMG was created despite exit code
                else
                    warn "create-dmg failed. Falling back to hdiutil..."
                    hdiutil create -volname "Refraction" \
                        -srcfolder "$APP_BUNDLE" \
                        -ov -format UDZO \
                        "$DMG_PATH"
                fi
            }
    else
        # Fallback: plain DMG via hdiutil
        info "  create-dmg not found. Using hdiutil (plain DMG, no styling)."
        info "  For a prettier DMG: brew install create-dmg"
        hdiutil create -volname "Refraction" \
            -srcfolder "$APP_BUNDLE" \
            -ov -format UDZO \
            "$DMG_PATH"
    fi

    if [ -f "$DMG_PATH" ]; then
        DMG_SIZE="$(du -sh "$DMG_PATH" 2>/dev/null | cut -f1)"
        success "DMG created: $DMG_PATH ($DMG_SIZE)"
    else
        warn "DMG creation failed."
    fi
fi

# ── Done ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}╔══════════════════════════════════════╗${NC}"
echo -e "${BOLD}║            Build Complete!           ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════╝${NC}"
echo ""
success "App bundle  : $APP_BUNDLE"
success "Bundle size : $APP_SIZE"
if [ -n "$DMG_PATH" ] && [ -f "$DMG_PATH" ]; then
    success "DMG         : $DMG_PATH"
fi
if [ "$CODE_SIGN" = true ] && [ -n "$DEVELOPER_ID" ]; then
    success "Signed with : $DEVELOPER_ID"
fi
echo ""
info "To run the app:"
echo "    open \"$APP_BUNDLE\""
echo ""
info "To copy to /Applications:"
echo "    cp -r \"$APP_BUNDLE\" /Applications/"
if [ -n "$DMG_PATH" ] && [ -f "$DMG_PATH" ]; then
    echo ""
    info "To distribute:"
    echo "    Share dist/Refraction.dmg"
fi
echo ""
