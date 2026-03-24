"""
plotter_test_harness.py — DEPRECATED thin compat layer.

This module is retained for backward compatibility with test files that
have not yet been migrated to pytest. New tests should use pytest fixtures
from tests/conftest.py instead.

All fixture writers and shared data are re-exported from conftest.
"""

import sys
import os
import warnings

# ── Ensure importability ──────────────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_HERE)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# Re-export from conftest for backward compat
from tests.conftest import (
    pf,
    PLOT_PARAM_DEFAULTS,
    _with_excel as with_excel,
    _bar_excel as bar_excel,
    _line_excel as line_excel,
    _simple_xy_excel as simple_xy_excel,
    _grouped_excel as grouped_excel,
    _km_excel as km_excel,
    _heatmap_excel as heatmap_excel,
    _two_way_excel as two_way_excel,
    _contingency_excel as contingency_excel,
    _chi_gof_excel as chi_gof_excel,
    _bland_altman_excel as bland_altman_excel,
    _forest_excel as forest_excel,
    _bubble_excel as bubble_excel,
    PAIRED_GROUPS,
    THREE_GROUPS,
    SCATTER_XS,
    SCATTER_YS,
)

import numpy as np
import pandas as pd

# Matplotlib import (lazy — may not be available)
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:
    plt = None


def close_fig(fig) -> None:
    """No-op — kept for backward compatibility."""
    pass


# ── Deprecated harness functions ──────────────────────────────────────────
# These exist only so that old non-migrated test files (test_canvas_renderer,
# test_control, etc.) can still be imported without errors.

PASS = 0
FAIL = 0
ERRORS = []


def ok(name):
    global PASS
    PASS += 1


def fail(name, reason=""):
    global FAIL
    FAIL += 1
    ERRORS.append(f"  FAIL: {name}: {reason}")


def run(name, fn):
    try:
        fn()
        ok(name)
    except Exception as exc:
        fail(name, str(exc))


def section(title):
    pass


def summarise(label=""):
    return FAIL == 0
