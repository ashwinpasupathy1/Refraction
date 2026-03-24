"""
conftest.py — pytest fixtures for Refraction test suites.

Provides temporary Excel file fixtures and shared test data that replaces
the old plotter_test_harness.py ok/fail/run/section/summarise machinery.
"""

import os
import sys
import tempfile
import contextlib
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import pytest

# ── Ensure project root is importable ──────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_HERE)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from refraction.core import chart_helpers as pf  # noqa: E402

# Re-export for test files that import from conftest
PLOT_PARAM_DEFAULTS = pf.PLOT_PARAM_DEFAULTS


# ---------------------------------------------------------------------------
# Temporary Excel file context manager
# ---------------------------------------------------------------------------

@contextlib.contextmanager
def _with_excel(write_fn=None, suffix=".xlsx"):
    """Context manager: create a temp Excel file, yield path, clean up."""
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


# ---------------------------------------------------------------------------
# Excel fixture writers — each returns the path it wrote
# ---------------------------------------------------------------------------

def _tmp_path(suffix=".xlsx") -> str:
    t = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    t.close()
    return t.name


def _bar_excel(groups: Dict[str, np.ndarray], path: Optional[str] = None) -> str:
    """Flat header layout: Row 1 = group names, Rows 2+ = values."""
    path = path or _tmp_path()
    names = list(groups.keys())
    max_n = max(len(v) for v in groups.values())
    rows = [names]
    for i in range(max_n):
        rows.append([
            float(groups[n][i]) if i < len(groups[n]) else None
            for n in names
        ])
    pd.DataFrame(rows).to_excel(path, index=False, header=False)
    return path


def _line_excel(series: Dict[str, np.ndarray], x_vals: np.ndarray,
                path: Optional[str] = None) -> str:
    """XY line layout."""
    path = path or _tmp_path()
    s_names = list(series.keys())
    header = ["X"] + [n for n in s_names for _ in series[n][0]]
    rows = [header]
    for i, x in enumerate(x_vals):
        row = [float(x)]
        for n in s_names:
            row += [float(v) for v in series[n][i]]
        rows.append(row)
    pd.DataFrame(rows).to_excel(path, index=False, header=False)
    return path


def _simple_xy_excel(xs: np.ndarray, ys: np.ndarray,
                     x_label: str = "X", y_label: str = "Series",
                     path: Optional[str] = None) -> str:
    """Single-series XY layout (scatter / curve_fit): X col + Y col."""
    path = path or _tmp_path()
    rows = [[x_label, y_label]] + [[float(x), float(y)] for x, y in zip(xs, ys)]
    pd.DataFrame(rows).to_excel(path, index=False, header=False)
    return path


def _grouped_excel(categories: List[str], subgroups: List[str],
                   data: Dict[str, Dict[str, np.ndarray]],
                   path: Optional[str] = None) -> str:
    """Grouped bar layout."""
    path = path or _tmp_path()
    all_vals = [v for cat in categories for sub in subgroups
                for v in (data[cat].get(sub) or [])]
    max_n = max(len(data[cat].get(sub, [])) for cat in categories
                for sub in subgroups) if all_vals else 1
    row1 = [cat for cat in categories for _ in subgroups]
    row2 = [sub for _ in categories for sub in subgroups]
    rows = [row1, row2]
    for i in range(max_n):
        rows.append([
            float(data[cat].get(sub, [None] * max_n)[i])
            if i < len(data[cat].get(sub, [])) else None
            for cat in categories for sub in subgroups
        ])
    pd.DataFrame(rows).to_excel(path, index=False, header=False)
    return path


def _km_excel(groups: Dict[str, Dict[str, np.ndarray]],
              path: Optional[str] = None) -> str:
    """KM layout."""
    path = path or _tmp_path()
    names = list(groups.keys())
    row1 = [n for n in names for _ in range(2)]
    row2 = ["Time", "Event"] * len(names)
    max_n = max(len(groups[n]["time"]) for n in names)
    rows = [row1, row2]
    for i in range(max_n):
        row = []
        for n in names:
            t = groups[n]["time"]; e = groups[n]["event"]
            row += [float(t[i]) if i < len(t) else None,
                    float(e[i]) if i < len(e) else None]
        rows.append(row)
    pd.DataFrame(rows).to_excel(path, index=False, header=False)
    return path


def _heatmap_excel(matrix: np.ndarray, row_labels: List[str],
                   col_labels: List[str], path: Optional[str] = None) -> str:
    """Heatmap layout."""
    path = path or _tmp_path()
    rows = [[""] + col_labels]
    for rl, row in zip(row_labels, matrix):
        rows.append([rl] + [float(v) for v in row])
    pd.DataFrame(rows).to_excel(path, index=False, header=False)
    return path


def _two_way_excel(records: List[tuple], path: Optional[str] = None) -> str:
    """Two-way ANOVA long-format."""
    path = path or _tmp_path()
    pd.DataFrame(records, columns=["Factor_A", "Factor_B", "Value"]
                 ).to_excel(path, index=False)
    return path


def _contingency_excel(row_labels: List[str], col_labels: List[str],
                       matrix: np.ndarray, path: Optional[str] = None) -> str:
    """Contingency layout."""
    path = path or _tmp_path()
    rows = [[""] + col_labels]
    for rl, row in zip(row_labels, matrix):
        rows.append([rl] + [int(v) for v in row])
    pd.DataFrame(rows).to_excel(path, index=False, header=False)
    return path


def _chi_gof_excel(categories: List[str], observed: List[float],
                   expected: Optional[List[float]] = None,
                   path: Optional[str] = None) -> str:
    """Chi-square GoF layout."""
    path = path or _tmp_path()
    rows = [categories, [float(v) for v in observed]]
    if expected is not None:
        rows.append([float(v) for v in expected])
    pd.DataFrame(rows).to_excel(path, index=False, header=False)
    return path


def _bland_altman_excel(method_a: np.ndarray, method_b: np.ndarray,
                        names: tuple = ("Method A", "Method B"),
                        path: Optional[str] = None) -> str:
    """Bland-Altman layout."""
    path = path or _tmp_path()
    n = min(len(method_a), len(method_b))
    rows = [[names[0], names[1]]] + [
        [float(method_a[i]), float(method_b[i])] for i in range(n)
    ]
    pd.DataFrame(rows).to_excel(path, index=False, header=False)
    return path


def _forest_excel(studies: List[str], effects: List[float],
                  ci_lo: List[float], ci_hi: List[float],
                  weights: Optional[List[float]] = None,
                  path: Optional[str] = None) -> str:
    """Forest plot layout."""
    path = path or _tmp_path()
    df = pd.DataFrame({
        "Study": studies,
        "Effect": [float(v) for v in effects],
        "CI_lo": [float(v) for v in ci_lo],
        "CI_hi": [float(v) for v in ci_hi],
        **({"Weight": [float(v) for v in weights]} if weights else {}),
    })
    df.to_excel(path, index=False)
    return path


def _bubble_excel(xs: np.ndarray, ys: np.ndarray, sizes: np.ndarray,
                  series_name: str = "S1", path: Optional[str] = None) -> str:
    """Bubble chart layout."""
    path = path or _tmp_path()
    rows = [["X", series_name, series_name]] + [
        [float(x), float(y), float(s)]
        for x, y, s in zip(xs, ys, sizes)
    ]
    pd.DataFrame(rows).to_excel(path, index=False, header=False)
    return path


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def bar_excel():
    """Yields a factory function that creates temp bar Excel files."""
    return _bar_excel


@pytest.fixture
def line_excel():
    return _line_excel


@pytest.fixture
def simple_xy_excel():
    return _simple_xy_excel


@pytest.fixture
def grouped_excel():
    return _grouped_excel


@pytest.fixture
def km_excel():
    return _km_excel


@pytest.fixture
def heatmap_excel():
    return _heatmap_excel


@pytest.fixture
def two_way_excel():
    return _two_way_excel


@pytest.fixture
def contingency_excel():
    return _contingency_excel


@pytest.fixture
def chi_gof_excel():
    return _chi_gof_excel


@pytest.fixture
def bland_altman_excel():
    return _bland_altman_excel


@pytest.fixture
def forest_excel():
    return _forest_excel


@pytest.fixture
def bubble_excel():
    return _bubble_excel


@pytest.fixture
def with_excel():
    """Yields the _with_excel context manager."""
    return _with_excel


@pytest.fixture
def close_fig():
    """No-op for backward compat."""
    def _noop(fig):
        pass
    return _noop


# ---------------------------------------------------------------------------
# Canonical shared datasets
# ---------------------------------------------------------------------------

_rng = np.random.default_rng(42)

PAIRED_GROUPS = {
    "Before": _rng.normal(5.0, 1.0, 10),
    "After": _rng.normal(7.0, 1.0, 10),
}

THREE_GROUPS = {
    "Control": _rng.normal(5.0, 1.0, 12),
    "Drug A": _rng.normal(8.0, 1.0, 12),
    "Drug B": _rng.normal(11.0, 1.0, 12),
}

SCATTER_XS = np.linspace(1, 10, 15)
SCATTER_YS = 2.5 * SCATTER_XS + 1.0 + _rng.normal(0, 1.5, 15)
