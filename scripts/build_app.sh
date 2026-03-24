#!/bin/bash
# build_app.sh — Build the Refraction macOS app with bundled Python.
#
# Steps:
#   1. Bundle Python environment into Resources/python-env/
#   2. Build the SwiftUI app via xcodebuild
#
# Usage:
#   bash scripts/build_app.sh [--skip-python] [--configuration Debug|Release]
#
# Options:
#   --skip-python       Skip Python bundling (use for fast iteration on Swift)
#   --configuration X   Build configuration (default: Release)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

SKIP_PYTHON=false
CONFIGURATION="Release"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --skip-python)
            SKIP_PYTHON=true
            shift
            ;;
        --configuration)
            CONFIGURATION="${2:?Missing value for --configuration}"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "=== Refraction Build ==="
echo "Configuration: $CONFIGURATION"
echo "Skip Python:   $SKIP_PYTHON"
echo ""

# Step 1: Run Python tests
echo "Step 1: Running Python tests..."
cd "$PROJECT_ROOT"
if python3 -m pytest tests/ -q --tb=short 2>&1; then
    echo "  Tests passed."
else
    echo "ERROR: Python tests failed. Fix them before building."
    exit 1
fi
echo ""

# Step 2: Bundle Python environment
if [[ "$SKIP_PYTHON" == "false" ]]; then
    echo "Step 2: Bundling Python environment..."
    bash "$SCRIPT_DIR/bundle_python.sh"
    echo ""
else
    echo "Step 2: Skipping Python bundling (--skip-python)"
    echo ""
fi

# Step 3: Generate app icons (if not already generated)
ICON_DIR="$PROJECT_ROOT/RefractionApp/Refraction/Assets.xcassets/AppIcon.appiconset"
if [[ ! -f "$ICON_DIR/icon_1024x1024.png" ]]; then
    echo "Step 3: Generating app icons..."
    python3 "$SCRIPT_DIR/generate_icon.py"
    echo ""
else
    echo "Step 3: App icons already exist, skipping."
    echo ""
fi

# Step 4: Generate Xcode project via XcodeGen
XCODE_PROJECT_DIR="$PROJECT_ROOT/RefractionApp"
if [[ -f "$XCODE_PROJECT_DIR/project.yml" ]]; then
    echo "Step 4: Generating Xcode project via XcodeGen..."
    if command -v xcodegen &>/dev/null; then
        cd "$XCODE_PROJECT_DIR"
        xcodegen generate
        cd "$PROJECT_ROOT"
    else
        echo "  XcodeGen not found. Install with: brew install xcodegen"
        echo "  Skipping — will use existing .xcodeproj if present."
    fi
    echo ""
else
    echo "Step 4: No project.yml found, skipping XcodeGen."
    echo ""
fi

# Step 5: Build the Swift app
echo "Step 5: Building Refraction.app ($CONFIGURATION)..."

if [[ -d "$XCODE_PROJECT_DIR/Refraction.xcodeproj" ]]; then
    # Xcode project exists — use xcodebuild
    cd "$XCODE_PROJECT_DIR"
    xcodebuild \
        -project Refraction.xcodeproj \
        -scheme Refraction \
        -configuration "$CONFIGURATION" \
        -derivedDataPath "$XCODE_PROJECT_DIR/build" \
        2>&1 | tail -20

    APP_PATH="$XCODE_PROJECT_DIR/build/Build/Products/$CONFIGURATION/Refraction.app"
elif command -v swift &>/dev/null; then
    # No Xcode project — try swift build (Swift Package Manager)
    echo "  No .xcodeproj found. The SwiftUI app requires Xcode to build."
    echo "  Open RefractionApp/ in Xcode and build from there, or create"
    echo "  a Package.swift for SPM-based builds."
    echo ""
    echo "  For development, you can run the Python server standalone:"
    echo "    python3 -m uvicorn refraction.server.api:app --port 7331"
    exit 0
else
    echo "ERROR: Neither xcodebuild nor swift found. Install Xcode."
    exit 1
fi

echo ""
echo "=== Build Complete ==="
if [[ -n "${APP_PATH:-}" ]] && [[ -d "$APP_PATH" ]]; then
    APP_SIZE=$(du -sh "$APP_PATH" | cut -f1)
    echo "App location: $APP_PATH"
    echo "App size:     $APP_SIZE"
else
    echo "Build finished. Check Xcode for output location."
fi
