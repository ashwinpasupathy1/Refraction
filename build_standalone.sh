#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Find prism_barplot_app.py — prefer loose file, fall back to app bundle
PY_SCRIPT="$SCRIPT_DIR/prism_barplot_app.py"
if [ ! -f "$PY_SCRIPT" ]; then
    PY_SCRIPT="$SCRIPT_DIR/Claude Prism.app/Contents/Resources/prism_barplot_app.py"
fi
if [ ! -f "$PY_SCRIPT" ]; then
    echo "✗ Cannot find prism_barplot_app.py"; exit 1
fi

# Find prism_functions.py
PY_FUNCS="$SCRIPT_DIR/prism_functions.py"
if [ ! -f "$PY_FUNCS" ]; then
    PY_FUNCS="$SCRIPT_DIR/Claude Prism.app/Contents/Resources/prism_functions.py"
fi
if [ ! -f "$PY_FUNCS" ]; then
    echo "✗ Cannot find prism_functions.py"; exit 1
fi

# Locate icons — prefer loose files in the same folder, fall back to app bundle
if [ -f "$SCRIPT_DIR/AppIcon.png" ]; then
    ICON_PNG="$SCRIPT_DIR/AppIcon.png"
else
    ICON_PNG="$SCRIPT_DIR/Claude Prism.app/Contents/Resources/AppIcon.png"
fi
if [ -f "$SCRIPT_DIR/AppIcon.icns" ]; then
    ICON_ICNS="$SCRIPT_DIR/AppIcon.icns"
else
    ICON_ICNS="$SCRIPT_DIR/Claude Prism.app/Contents/Resources/AppIcon.icns"
fi

echo "=== Claude Prism — Standalone Builder ==="
echo "Script:    $PY_SCRIPT"
echo "Functions: $PY_FUNCS"
echo ""

PYTHON=$(which python3)
echo "Using Python: $PYTHON ($($PYTHON --version))"

BUILD_DIR="$SCRIPT_DIR/_standalone_build"
rm -rf "$BUILD_DIR" && mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

cp "$PY_SCRIPT" ./prism_barplot_app.py
cp "$PY_FUNCS"  ./prism_functions.py
[ -f "$ICON_PNG" ]  && cp "$ICON_PNG"  ./AppIcon.png  && echo "  Icon PNG copied"
[ -f "$ICON_ICNS" ] && cp "$ICON_ICNS" ./AppIcon.icns && echo "  Icon ICNS copied"

echo ""
echo "→ Setting up build environment…"
$PYTHON -m venv _buildenv
source _buildenv/bin/activate
pip install --quiet --upgrade pip

echo "→ Installing packages…"
pip install pyinstaller matplotlib numpy pandas scipy seaborn openpyxl pillow tkinterdnd2 pyobjc-framework-Cocoa

# Build the spec
cat > claude_prism.spec << 'SPECEOF'
# -*- mode: python ; coding: utf-8 -*-
import os
_datas = [('prism_functions.py', '.')]
if os.path.exists('AppIcon.png'):  _datas.append(('AppIcon.png',  '.'))
if os.path.exists('AppIcon.icns'): _datas.append(('AppIcon.icns', '.'))
a = Analysis(
    ['prism_barplot_app.py'],
    pathex=['.'],
    binaries=[],
    datas=_datas,
    hiddenimports=[
        'matplotlib', 'matplotlib.backends.backend_tkagg',
        'matplotlib.backends.backend_agg',
        'matplotlib.ticker', 'matplotlib.figure',
        'pandas', 'numpy', 'numpy.core', 'numpy.lib',
        'scipy', 'scipy.stats', 'scipy.stats._stats_py',
        'scipy.optimize', 'scipy.special',
        'seaborn', 'openpyxl', 'openpyxl.styles',
        'tkinter', 'tkinter.ttk', 'tkinter.filedialog',
        'tkinter.messagebox', 'tkinter.font',
        'tkinterdnd2',
        'PIL', 'PIL.ImageTk', 'PIL.Image',
        'prism_functions',
        'itertools', 'warnings', 'collections',
        'inspect', 'textwrap', 'threading', 'traceback',
        'json', 'glob', 'datetime',
    ],
    hookspath=[],
    noarchive=False,
    collect_all=['scipy', 'seaborn', 'tkinterdnd2'],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name='Claude Prism',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='AppIcon.icns' if os.path.exists('AppIcon.icns') else None,
)
coll = COLLECT(
    exe, a.binaries, a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Claude Prism',
)
app = BUNDLE(
    coll,
    name='Claude Prism.app',
    icon='AppIcon.icns' if os.path.exists('AppIcon.icns') else None,
    bundle_identifier='com.local.claudeprism',
    info_plist={
        'CFBundleName':              'Claude Prism',
        'CFBundleDisplayName':       'Claude Prism',
        'CFBundleShortVersionString':'1.0',
        'CFBundleVersion':           '1.0.0',
        # CFBundleIconFile tells macOS which icon to use when Cocoa
        # reinitialises NSApplication — the extension is omitted per Apple spec.
        # Without this key the OS falls back to a generic low-res icon.
        'CFBundleIconFile':          'AppIcon',
        'NSHighResolutionCapable':   True,
        'NSPrincipalClass':          'NSApplication',
        'NSRequiresAquaSystemAppearance': False,
        # Suppress the Python runtime warning about multiple NSApplication instances
        'NSAppleScriptEnabled': False,
    },
)
SPECEOF

echo ""
echo "→ Building standalone app (this takes a few minutes)…"
pyinstaller claude_prism.spec 2>&1

deactivate

DEST="$SCRIPT_DIR/Claude Prism.app"

if [ -d "dist/Claude Prism.app" ]; then
    rm -rf "$DEST"
    mv "dist/Claude Prism.app" "$DEST"
    cd "$SCRIPT_DIR"
    rm -rf "$BUILD_DIR"

    echo ""
    echo "✓ Done! Claude Prism.app is ready."
    echo ""
    echo "→ Cleaning up build files…"
    # Only delete loose files if they exist (they may already be gone)
    [ -f "$SCRIPT_DIR/prism_barplot_app.py" ] && rm -f "$SCRIPT_DIR/prism_barplot_app.py"
    [ -f "$SCRIPT_DIR/prism_functions.py" ]   && rm -f "$SCRIPT_DIR/prism_functions.py"
    [ -f "$SCRIPT_DIR/build_standalone.sh" ]  && rm -f "$SCRIPT_DIR/build_standalone.sh"
    echo "  Cleanup done."
    echo ""
    echo "  Drag 'Claude Prism.app' into your Applications folder to install."
else
    echo ""
    echo "✗ Build failed — dist/Claude Prism.app not found."
    echo "  Check the output above for errors."
    exit 1
fi
