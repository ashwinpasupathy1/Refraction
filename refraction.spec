# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for Refraction
# Targets macOS .app bundle with bundled React SPA
#
# Usage:
#   pyinstaller refraction.spec
#
# Prerequisites:
#   pip install pyinstaller
#   cd plotter_web && npm install && npm run build

import os
import sys
from pathlib import Path

block_cipher = None

# ── Paths ────────────────────────────────────────────────────────────────────
HERE = os.path.dirname(os.path.abspath(SPEC))  # noqa: F821 — SPEC is PyInstaller built-in
WEB_DIST = os.path.join(HERE, "plotter_web", "dist")
ICON_PATH = os.path.join(HERE, "assets", "AppIcon.icns")

# ── Hidden imports ────────────────────────────────────────────────────────────
# All plotter_* modules are imported lazily or via importlib; list them
# explicitly so PyInstaller's static analyser includes them.
PLOTTER_HIDDEN_IMPORTS = [
    # Core application
    "plotter_functions",
    "plotter_widgets",
    "plotter_validators",
    "plotter_results",
    # Phase 2 infrastructure
    "plotter_registry",
    "plotter_tabs",
    "plotter_app_icons",
    "plotter_presets",
    "plotter_session",
    "plotter_events",
    "plotter_types",
    "plotter_undo",
    "plotter_errors",
    "plotter_comparisons",
    "plotter_project",
    "plotter_import_pzfx",
    "plotter_wiki_content",
    "plotter_app_wiki",
    # Phase 3 server + webview
    "plotter_server",
    "plotter_webview",
    "plotter_plotly_theme",
    # Spec builders (all 29 chart types — loaded via importlib.import_module)
    "plotter_spec_bar",
    "plotter_spec_grouped_bar",
    "plotter_spec_line",
    "plotter_spec_scatter",
    "plotter_spec_box",
    "plotter_spec_violin",
    "plotter_spec_histogram",
    "plotter_spec_dot_plot",
    "plotter_spec_raincloud",
    "plotter_spec_qq",
    "plotter_spec_ecdf",
    "plotter_spec_before_after",
    "plotter_spec_repeated_measures",
    "plotter_spec_subcolumn",
    "plotter_spec_stacked_bar",
    "plotter_spec_area",
    "plotter_spec_lollipop",
    "plotter_spec_waterfall",
    "plotter_spec_pyramid",
    "plotter_spec_kaplan_meier",
    "plotter_spec_heatmap",
    "plotter_spec_bland_altman",
    "plotter_spec_forest_plot",
    "plotter_spec_bubble",
    "plotter_spec_curve_fit",
    "plotter_spec_column_stats",
    "plotter_spec_contingency",
    "plotter_spec_chi_square_gof",
    "plotter_spec_two_way_anova",
    # Web server entry point
    "plotter_web_server",
    # FastAPI / uvicorn internals (not always found by static analysis)
    "fastapi",
    "fastapi.middleware.cors",
    "fastapi.staticfiles",
    "fastapi.responses",
    "uvicorn",
    "uvicorn.main",
    "uvicorn.config",
    "uvicorn.lifespan.on",
    "uvicorn.loops.auto",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.http.httptools_impl",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.protocols.websockets.websockets_impl",
    "uvicorn.protocols.websockets.wsproto_impl",
    "uvicorn.logging",
    "pydantic",
    "starlette",
    "starlette.middleware",
    "starlette.middleware.cors",
    "starlette.staticfiles",
    "starlette.routing",
    # Data / science stack
    "pandas",
    "numpy",
    "scipy",
    "scipy.stats",
    "plotly",
    "plotly.graph_objs",
    "plotly.io",
    # Excel reading
    "openpyxl",
    "xlrd",
    # pywebview
    "webview",
]

# ── Data files ────────────────────────────────────────────────────────────────
datas = []

# Bundle the built React SPA (must be built before running PyInstaller)
if os.path.isdir(WEB_DIST):
    datas.append((WEB_DIST, "plotter_web/dist"))
else:
    print(
        "WARNING: plotter_web/dist/ not found. "
        "Run 'cd plotter_web && npm install && npm run build' first.",
        file=sys.stderr,
    )

# ── Excludes ──────────────────────────────────────────────────────────────────
# Omit things that are not needed in the desktop .app bundle to reduce size.
EXCLUDES = [
    # Test infrastructure
    "pytest",
    "_pytest",
    "tests",
    "test_stats_verification",
    "run_all",
    # Tk/matplotlib are NOT excluded — they are used by the legacy
    # plotter_barplot_app.py path which may still be invoked.
    # If you only want the web-only build, uncomment the lines below:
    # "tkinter",
    # "_tkinter",
    # "matplotlib",
    # "seaborn",
    # Jupyter / IPython (pulled in transitively by some packages)
    "IPython",
    "ipykernel",
    "notebook",
    "jupyter_client",
    "jupyter_core",
    # Build tools
    "distutils",
    "setuptools",
    "pip",
    "wheel",
    # Unused stdlib
    "xmlrpc",
    "http.server",
    "pdb",
    "doctest",
    "unittest",
]

# ── Analysis ──────────────────────────────────────────────────────────────────
a = Analysis(
    ["plotter_desktop.py"],
    pathex=[HERE],
    binaries=[],
    datas=datas,
    hiddenimports=PLOTTER_HIDDEN_IMPORTS,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)  # noqa: F821

# ── Single executable (used by BUNDLE below on macOS) ─────────────────────────
exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,   # binaries go into COLLECT / .app bundle
    name="Refraction",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,           # no terminal window on macOS
    icon=ICON_PATH if os.path.exists(ICON_PATH) else None,
)

# ── Collect all pieces ────────────────────────────────────────────────────────
coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Refraction",
)

# ── macOS .app bundle ─────────────────────────────────────────────────────────
app = BUNDLE(  # noqa: F821
    coll,
    name="Refraction.app",
    icon=ICON_PATH if os.path.exists(ICON_PATH) else None,
    bundle_identifier="com.refraction.app",
    info_plist={
        # Display name shown in Finder and Dock
        "CFBundleName": "Refraction",
        "CFBundleDisplayName": "Refraction",
        # Version / build strings
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0.0",
        # Bundle type and creator
        "CFBundlePackageType": "APPL",
        # Minimum macOS version (12 = Monterey; pywebview WKWebView requires ≥10.15)
        "LSMinimumSystemVersion": "12.0",
        # Allow localhost network access (needed for FastAPI server at 127.0.0.1)
        "NSAppTransportSecurity": {
            "NSAllowsLocalNetworking": True,
        },
        # Microphone / camera not used; no entitlements needed for those.
        # High-resolution display support
        "NSHighResolutionCapable": True,
        # Suppress "App is not optimized for your Mac" on Apple Silicon
        "LSArchitecturePriority": ["arm64", "x86_64"],
        # Dock category
        "LSApplicationCategoryType": "public.app-category.graphics-design",
        # Copyright
        "NSHumanReadableCopyright": "Built by Claude (Anthropic) with Ashwin Pasupathy",
        # Document types handled (optional — .cplot project files)
        "CFBundleDocumentTypes": [
            {
                "CFBundleTypeName": "Refraction Project",
                "CFBundleTypeExtensions": ["cplot", "refraction"],
                "CFBundleTypeRole": "Editor",
                "LSHandlerRank": "Owner",
            },
        ],
    },
)
