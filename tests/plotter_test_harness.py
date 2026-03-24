"""
plotter_test_harness.py
=======================
Shared harness, fixtures, and bootstrap for all Refraction test suites.

Importing this module:
  • Locates and imports plotter_functions
  • Exports: pf, np, pd
  • Exports: ok, fail, run, section, summarise
  • Exports: all Excel fixture writers
  • Exports: @with_excel context manager / decorator

Usage in a test file:
    from plotter_test_harness import *
    from plotter_test_harness import pf, run, section, bar_excel, with_excel
"""

import sys
import os
import warnings
import traceback
import tempfile
import contextlib
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

# ── Locate plotter_functions ────────────────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
_LEGACY_SRC = os.path.join(_HERE, "claude_plotter_src")

for _candidate in (_HERE, _LEGACY_SRC):
    if os.path.isfile(os.path.join(_candidate, "plotter_functions.py")):
        if _candidate not in sys.path:
            sys.path.insert(0, _candidate)
        break

import plotter_functions as pf  # noqa: E402

# Re-export key constants so test files can access them via the harness
PLOT_PARAM_DEFAULTS = pf.PLOT_PARAM_DEFAULTS


# ─────────────────────────────────────────────────────────────────────────────
# Harness
# ─────────────────────────────────────────────────────────────────────────────

# Module-level counters — each test file that does `from plotter_test_harness
# import *` gets its OWN namespace for these, so counters stay per-file.
# When run_all.py imports multiple suites it aggregates via summarise().
PASS   = 0
FAIL   = 0
ERRORS: List[str] = []


def ok(name: str) -> None:
    global PASS
    PASS += 1
    print(f"  ✓  {name}")


def fail(name: str, reason: str) -> None:
    global FAIL
    FAIL += 1
    msg = f"  ✗  {name}\n       {reason}"
    ERRORS.append(msg)
    print(msg)


def run(name: str, fn) -> None:
    """Run fn(); call ok(name) on success, fail(name, …) on any exception."""
    try:
        fn()
        ok(name)
    except Exception as exc:
        tb_lines = traceback.format_exc().splitlines()
        ctx = tb_lines[-3] if len(tb_lines) >= 3 else ""
        fail(name, f"{type(exc).__name__}: {exc}\n       {ctx}")


def section(title: str) -> None:
    print(f"\n{'━' * 64}\n  {title}\n{'━' * 64}")


def summarise(label: str = "") -> bool:
    """Print PASS/FAIL totals; return True if all passed."""
    tag = f"  [{label}]" if label else ""
    print(f"\n{'━' * 64}")
    print(f"  RESULTS{tag}")
    print(f"{'━' * 64}")
    print(f"  ✓  PASSED: {PASS}")
    print(f"  ✗  FAILED: {FAIL}")
    print(f"  TOTAL:     {PASS + FAIL}")
    if ERRORS:
        print(f"\n{'━' * 64}")
        print("  FAILURES:")
        print(f"{'━' * 64}")
        for e in ERRORS:
            print(e)
    return FAIL == 0


def close_fig(fig) -> None:
    """No-op — kept for backward compatibility with existing test calls."""
    pass


# ─────────────────────────────────────────────────────────────────────────────
# Context manager: temporary Excel file
# ─────────────────────────────────────────────────────────────────────────────

@contextlib.contextmanager
def with_excel(write_fn=None, suffix=".xlsx"):
    """Context manager that creates a temp Excel file, yields its path,
    then deletes it on exit regardless of exceptions.

    Usage — passing a writer function::

        with with_excel(lambda p: bar_excel(groups, path=p)) as p:
            fig, ax = pf.plotter_barplot(p)
            close_fig(fig)

    Usage — getting a raw path to write manually::

        with with_excel() as p:
            pd.DataFrame(...).to_excel(p, index=False)
            fig, ax = pf.plotter_barplot(p)
            close_fig(fig)
    """
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    tmp.close()
    try:
        if write_fn is not None:
            write_fn(tmp.name)
        yield tmp.name
    finally:
        try:
            os.unlink(tmp.name)
        except FileNotFoundError:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# Excel fixture writers
# All writers return the path they wrote, accept an optional path= kwarg.
# ─────────────────────────────────────────────────────────────────────────────

def _tmp_path(suffix=".xlsx") -> str:
    t = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    t.close()
    return t.name


def bar_excel(groups: Dict[str, np.ndarray], path: Optional[str] = None) -> str:
    """Flat header layout: Row 1 = group names, Rows 2+ = values.
    Groups may have different lengths; shorter columns are NaN-padded."""
    path = path or _tmp_path()
    names = list(groups.keys())
    max_n = max(len(v) for v in groups.values())
    rows  = [names]
    for i in range(max_n):
        rows.append([
            float(groups[n][i]) if i < len(groups[n]) else None
            for n in names
        ])
    pd.DataFrame(rows).to_excel(path, index=False, header=False)
    return path


def line_excel(series: Dict[str, np.ndarray], x_vals: np.ndarray,
               path: Optional[str] = None) -> str:
    """XY line layout: Row 1 = X-label | series names (repeated across reps).
    Rows 2+: x | rep1 | rep2 ..."""
    path = path or _tmp_path()
    s_names = list(series.keys())
    # series[name] is a 2-D array (n_x, n_reps) or list of rep lists
    header = ["X"] + [n for n in s_names for _ in series[n][0]]
    rows   = [header]
    for i, x in enumerate(x_vals):
        row = [float(x)]
        for n in s_names:
            row += [float(v) for v in series[n][i]]
        rows.append(row)
    pd.DataFrame(rows).to_excel(path, index=False, header=False)
    return path


def simple_xy_excel(xs: np.ndarray, ys: np.ndarray,
                    x_label: str = "X", y_label: str = "Series",
                    path: Optional[str] = None) -> str:
    """Single-series XY layout (scatter / curve_fit): X col + Y col."""
    path = path or _tmp_path()
    rows = [[x_label, y_label]] + [[float(x), float(y)] for x, y in zip(xs, ys)]
    pd.DataFrame(rows).to_excel(path, index=False, header=False)
    return path


def grouped_excel(categories: List[str], subgroups: List[str],
                  data: Dict[str, Dict[str, np.ndarray]],
                  path: Optional[str] = None) -> str:
    """Grouped bar layout: Row 1 = categories (repeated), Row 2 = subgroups."""
    path = path or _tmp_path()
    all_vals = [v for cat in categories for sub in subgroups
                for v in (data[cat].get(sub) or [])]
    max_n = max(len(data[cat].get(sub, [])) for cat in categories
                for sub in subgroups) if all_vals else 1
    row1 = [cat for cat in categories for _ in subgroups]
    row2 = [sub for _   in categories for sub in subgroups]
    rows = [row1, row2]
    for i in range(max_n):
        rows.append([
            float(data[cat].get(sub, [None] * max_n)[i])
            if i < len(data[cat].get(sub, [])) else None
            for cat in categories for sub in subgroups
        ])
    pd.DataFrame(rows).to_excel(path, index=False, header=False)
    return path


def km_excel(groups: Dict[str, Dict[str, np.ndarray]],
             path: Optional[str] = None) -> str:
    """KM layout: Row 1 = group names (each spans 2 cols),
    Row 2 = Time|Event headers, Rows 3+ = data."""
    path = path or _tmp_path()
    names  = list(groups.keys())
    row1   = [n for n in names for _ in range(2)]
    row2   = ["Time", "Event"] * len(names)
    max_n  = max(len(groups[n]["time"]) for n in names)
    rows   = [row1, row2]
    for i in range(max_n):
        row = []
        for n in names:
            t = groups[n]["time"]; e = groups[n]["event"]
            row += [float(t[i]) if i < len(t) else None,
                    float(e[i]) if i < len(e) else None]
        rows.append(row)
    pd.DataFrame(rows).to_excel(path, index=False, header=False)
    return path


def heatmap_excel(matrix: np.ndarray, row_labels: List[str],
                  col_labels: List[str], path: Optional[str] = None) -> str:
    """Heatmap layout: top-left blank, row 1 = col labels,
    col A rows 2+ = row labels, rest = matrix values."""
    path = path or _tmp_path()
    rows = [[""] + col_labels]
    for rl, row in zip(row_labels, matrix):
        rows.append([rl] + [float(v) for v in row])
    pd.DataFrame(rows).to_excel(path, index=False, header=False)
    return path


def two_way_excel(records: List[tuple], path: Optional[str] = None) -> str:
    """Two-way ANOVA long-format: columns Factor_A, Factor_B, Value."""
    path = path or _tmp_path()
    pd.DataFrame(records, columns=["Factor_A", "Factor_B", "Value"]
                 ).to_excel(path, index=False)
    return path


def contingency_excel(row_labels: List[str], col_labels: List[str],
                      matrix: np.ndarray, path: Optional[str] = None) -> str:
    """Contingency layout: top-left blank, row 1 = outcomes, col A = groups."""
    path = path or _tmp_path()
    rows = [[""] + col_labels]
    for rl, row in zip(row_labels, matrix):
        rows.append([rl] + [int(v) for v in row])
    pd.DataFrame(rows).to_excel(path, index=False, header=False)
    return path


def chi_gof_excel(categories: List[str], observed: List[float],
                  expected: Optional[List[float]] = None,
                  path: Optional[str] = None) -> str:
    """Chi-square GoF: Row 1 = cats, Row 2 = observed, Row 3 = expected (opt)."""
    path = path or _tmp_path()
    rows = [categories, [float(v) for v in observed]]
    if expected is not None:
        rows.append([float(v) for v in expected])
    pd.DataFrame(rows).to_excel(path, index=False, header=False)
    return path


def bland_altman_excel(method_a: np.ndarray, method_b: np.ndarray,
                       names: tuple = ("Method A", "Method B"),
                       path: Optional[str] = None) -> str:
    """Bland-Altman: Row 1 = method names, Rows 2+ = paired values."""
    path = path or _tmp_path()
    n = min(len(method_a), len(method_b))
    rows = [[names[0], names[1]]] + [
        [float(method_a[i]), float(method_b[i])] for i in range(n)
    ]
    pd.DataFrame(rows).to_excel(path, index=False, header=False)
    return path


def forest_excel(studies: List[str], effects: List[float],
                 ci_lo: List[float], ci_hi: List[float],
                 weights: Optional[List[float]] = None,
                 path: Optional[str] = None) -> str:
    """Forest plot: header row + Study/Effect/CI_lo/CI_hi/Weight columns."""
    path = path or _tmp_path()
    df = pd.DataFrame({
        "Study":  studies,
        "Effect": [float(v) for v in effects],
        "CI_lo":  [float(v) for v in ci_lo],
        "CI_hi":  [float(v) for v in ci_hi],
        **({"Weight": [float(v) for v in weights]} if weights else {}),
    })
    df.to_excel(path, index=False)
    return path


def bubble_excel(xs: np.ndarray, ys: np.ndarray, sizes: np.ndarray,
                 series_name: str = "S1", path: Optional[str] = None) -> str:
    """Bubble chart: Row 1 = [X, series, series], Rows 2+ = [x, y, size]."""
    path = path or _tmp_path()
    rows = [["X", series_name, series_name]] + [
        [float(x), float(y), float(s)]
        for x, y, s in zip(xs, ys, sizes)
    ]
    pd.DataFrame(rows).to_excel(path, index=False, header=False)
    return path


# ─────────────────────────────────────────────────────────────────────────────
# Canonical shared datasets (same seed = reproducible across all suites)
# ─────────────────────────────────────────────────────────────────────────────

_rng = np.random.default_rng(42)

# Two groups — paired / before-after
PAIRED_GROUPS = {
    "Before": _rng.normal(5.0, 1.0, 10),
    "After":  _rng.normal(7.0, 1.0, 10),
}

# Three groups — standard stats
THREE_GROUPS = {
    "Control": _rng.normal(5.0, 1.0, 12),
    "Drug A":  _rng.normal(8.0, 1.0, 12),
    "Drug B":  _rng.normal(11.0, 1.0, 12),
}

# Scatter/line XY data
SCATTER_XS = np.linspace(1, 10, 15)
SCATTER_YS = 2.5 * SCATTER_XS + 1.0 + _rng.normal(0, 1.5, 15)
