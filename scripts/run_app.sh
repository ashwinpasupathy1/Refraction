#!/bin/bash
# run_app.sh — Build and launch Refraction from the current branch.
#
# This script lets you test the full application (SwiftUI + Python backend)
# on any branch or worktree before merging. It:
#   1. Runs the Python test suite (gate on 0 failures)
#   2. Generates the Xcode project from project.yml via XcodeGen
#   3. Builds the app via xcodebuild
#   4. Launches it with REFRACTION_ROOT pointing at this branch's code
#
# Usage:
#   bash scripts/run_app.sh                  # full build + launch
#   bash scripts/run_app.sh --skip-tests     # skip Python tests
#   bash scripts/run_app.sh --skip-python    # skip Python bundling
#   bash scripts/run_app.sh --debug          # build Debug config
#   bash scripts/run_app.sh --api-only       # just start the Python server
#
# Prerequisites:
#   brew install xcodegen    (one-time setup)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
XCODE_PROJECT_DIR="$PROJECT_ROOT/RefractionApp"

SKIP_TESTS=false
SKIP_PYTHON=false
API_ONLY=false
CONFIGURATION="Debug"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --skip-tests)   SKIP_TESTS=true;  shift ;;
        --skip-python)  SKIP_PYTHON=true; shift ;;
        --api-only)     API_ONLY=true;    shift ;;
        --debug)        CONFIGURATION="Debug";   shift ;;
        --release)      CONFIGURATION="Release"; shift ;;
        -h|--help)
            echo "Usage: bash scripts/run_app.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --skip-tests    Skip Python test suite"
            echo "  --skip-python   Skip Python environment bundling"
            echo "  --api-only      Just start the Python API server (no SwiftUI)"
            echo "  --debug         Build Debug configuration (default)"
            echo "  --release       Build Release configuration"
            echo "  -h, --help      Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1 (use --help for usage)"
            exit 1
            ;;
    esac
done

BRANCH="$(cd "$PROJECT_ROOT" && git branch --show-current 2>/dev/null || echo 'unknown')"
echo "=== Refraction — Run from Branch ==="
echo "Branch:        $BRANCH"
echo "Project root:  $PROJECT_ROOT"
echo "Configuration: $CONFIGURATION"
echo ""

# ── Step 1: Python tests ────────────────────────────────────────────
if [[ "$SKIP_TESTS" == "false" ]]; then
    echo "Step 1: Running Python tests..."
    cd "$PROJECT_ROOT"
    if python3 run_all.py 2>&1; then
        echo "  Tests passed."
    else
        echo ""
        echo "ERROR: Tests failed. Fix them before running the app."
        echo "  python3 run_all.py"
        exit 1
    fi
    echo ""
else
    echo "Step 1: Skipping tests (--skip-tests)"
    echo ""
fi

# ── API-only mode ───────────────────────────────────────────────────
if [[ "$API_ONLY" == "true" ]]; then
    echo "Starting Python API server on http://127.0.0.1:7331 ..."
    echo "  Press Ctrl+C to stop."
    echo ""
    cd "$PROJECT_ROOT"
    PYTHONPATH="$PROJECT_ROOT" exec python3 -c \
        "import uvicorn; from refraction.server.api import _make_app; uvicorn.run(_make_app(), host='127.0.0.1', port=7331)"
fi

# ── Step 2: Check prerequisites ─────────────────────────────────────
if ! command -v xcodegen &>/dev/null; then
    echo "ERROR: XcodeGen not found. Install it with:"
    echo "  brew install xcodegen"
    exit 1
fi

if ! command -v xcodebuild &>/dev/null; then
    echo "ERROR: xcodebuild not found. Install Xcode from the App Store."
    exit 1
fi

if [[ ! -f "$XCODE_PROJECT_DIR/project.yml" ]]; then
    echo "ERROR: RefractionApp/project.yml not found."
    echo "  This file is needed to generate the Xcode project."
    exit 1
fi

# ── Step 3: Generate Xcode project ──────────────────────────────────
echo "Step 2: Generating Xcode project..."
cd "$XCODE_PROJECT_DIR"
xcodegen generate
cd "$PROJECT_ROOT"
echo ""

# ── Step 4: Build the app ───────────────────────────────────────────
echo "Step 3: Building Refraction.app ($CONFIGURATION)..."
cd "$XCODE_PROJECT_DIR"
xcodebuild \
    -project Refraction.xcodeproj \
    -scheme Refraction \
    -configuration "$CONFIGURATION" \
    -derivedDataPath "$XCODE_PROJECT_DIR/build" \
    2>&1 | tail -30

APP_PATH="$XCODE_PROJECT_DIR/build/Build/Products/$CONFIGURATION/Refraction.app"

if [[ ! -d "$APP_PATH" ]]; then
    echo ""
    echo "ERROR: Build failed — $APP_PATH not found."
    echo "  Run xcodebuild manually to see full errors."
    exit 1
fi
echo ""

# ── Step 5: Launch ──────────────────────────────────────────────────
echo "Step 4: Launching Refraction..."
echo "  App:   $APP_PATH"
echo "  Root:  $PROJECT_ROOT"
echo "  Branch: $BRANCH"
echo ""

# Set REFRACTION_ROOT so PythonServer.swift finds this branch's code
REFRACTION_ROOT="$PROJECT_ROOT" open "$APP_PATH"

echo "=== Refraction is running ==="
echo "  The app will start its own Python server from: $PROJECT_ROOT"
echo "  Logs: ~/Library/Logs/Refraction/"
echo "  API:  http://127.0.0.1:7331/health"
