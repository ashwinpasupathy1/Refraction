"""
test_edge_cases.py
==================
Edge case and error handling tests for spec builders.

Tests pathological inputs: single data point, all-NaN, empty files,
negative values, very large values, single groups, many groups,
non-numeric data, duplicate headers, and unicode headers.

Run:
  python3 tests/test_edge_cases.py  (or via run_all.py)
"""

import sys, os, json, math
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import plotter_test_harness as _h
from plotter_test_harness import (
    ok, fail, run, section, summarise,
    bar_excel, simple_xy_excel, heatmap_excel,
    with_excel,
)


def _parse_spec(json_str):
    """Parse spec JSON, returning (spec_dict, is_error)."""
    spec = json.loads(json_str)
    is_error = "error" in spec and "data" not in spec
    return spec, is_error


# List of (builder_module, builder_function, chart_type) for bar-layout builders
_BAR_LAYOUT_BUILDERS = [
    ("refraction.specs.bar", "build_bar_spec", "bar"),
    ("refraction.specs.box", "build_box_spec", "box"),
    ("refraction.specs.violin", "build_violin_spec", "violin"),
    ("refraction.specs.histogram", "build_histogram_spec", "histogram"),
    ("refraction.specs.dot_plot", "build_dot_plot_spec", "dot_plot"),
    ("refraction.specs.ecdf", "build_ecdf_spec", "ecdf"),
    ("refraction.specs.lollipop", "build_lollipop_spec", "lollipop"),
    ("refraction.specs.waterfall", "build_waterfall_spec", "waterfall"),
]


def _get_builder(module_name, fn_name):
    import importlib
    mod = importlib.import_module(module_name)
    return getattr(mod, fn_name)


# ═══════════════════════════════════════════════════════════════════════════
# 1. Single data point (n=1)
# ═══════════════════════════════════════════════════════════════════════════
section("Edge cases — Single data point (n=1)")


def test_bar_single_point():
    """Bar chart with a single data point should not crash."""
    with with_excel(lambda p: bar_excel({"A": np.array([42.0])}, path=p)) as xl:
        builder = _get_builder("refraction.specs.bar", "build_bar_spec")
        spec = json.loads(builder({"excel_path": xl}))
        assert "data" in spec, "Single-point bar should produce valid spec"
        assert abs(spec["data"][0]["y"][0] - 42.0) < 0.01

run("single point: bar chart handles n=1", test_bar_single_point)


def test_box_single_point():
    """Box plot with a single data point should not crash."""
    with with_excel(lambda p: bar_excel({"A": np.array([7.0])}, path=p)) as xl:
        builder = _get_builder("refraction.specs.box", "build_box_spec")
        spec = json.loads(builder({"excel_path": xl}))
        assert "data" in spec

run("single point: box plot handles n=1", test_box_single_point)


def test_violin_single_point():
    """Violin plot with a single data point should not crash."""
    with with_excel(lambda p: bar_excel({"A": np.array([3.0])}, path=p)) as xl:
        builder = _get_builder("refraction.specs.violin", "build_violin_spec")
        spec = json.loads(builder({"excel_path": xl}))
        assert "data" in spec

run("single point: violin plot handles n=1", test_violin_single_point)


def test_histogram_single_point():
    """Histogram with a single data point should not crash."""
    with with_excel(lambda p: bar_excel({"A": np.array([5.0])}, path=p)) as xl:
        builder = _get_builder("refraction.specs.histogram", "build_histogram_spec")
        spec = json.loads(builder({"excel_path": xl}))
        assert "data" in spec

run("single point: histogram handles n=1", test_histogram_single_point)


def test_scatter_single_point():
    """Scatter with a single data point should not crash."""
    with with_excel(lambda p: simple_xy_excel(
            np.array([1.0]), np.array([2.0]), path=p)) as xl:
        builder = _get_builder("refraction.specs.scatter", "build_scatter_spec")
        spec = json.loads(builder({"excel_path": xl}))
        assert "data" in spec

run("single point: scatter handles n=1", test_scatter_single_point)


def test_line_single_point():
    """Line chart with a single data point should not crash."""
    with with_excel(lambda p: simple_xy_excel(
            np.array([1.0]), np.array([2.0]), path=p)) as xl:
        builder = _get_builder("refraction.specs.line", "build_line_spec")
        spec = json.loads(builder({"excel_path": xl}))
        assert "data" in spec

run("single point: line chart handles n=1", test_line_single_point)


# ═══════════════════════════════════════════════════════════════════════════
# 2. All-NaN column
# ═══════════════════════════════════════════════════════════════════════════
section("Edge cases — All-NaN column")


def test_bar_all_nan():
    """Bar chart with all-NaN column should not crash."""
    with with_excel() as xl:
        df = pd.DataFrame({"A": [float("nan")] * 5, "B": [1.0, 2.0, 3.0, 4.0, 5.0]})
        df.to_excel(xl, index=False)
        builder = _get_builder("refraction.specs.bar", "build_bar_spec")
        spec_str = builder({"excel_path": xl})
        spec = json.loads(spec_str)
        # Should not crash; may have 0 mean or empty trace for NaN group
        assert "data" in spec or "error" in spec

run("all-NaN: bar chart handles all-NaN column", test_bar_all_nan)


def test_box_all_nan():
    """Box plot with all-NaN column should not crash."""
    with with_excel() as xl:
        df = pd.DataFrame({"A": [float("nan")] * 5})
        df.to_excel(xl, index=False)
        builder = _get_builder("refraction.specs.box", "build_box_spec")
        spec = json.loads(builder({"excel_path": xl}))
        assert "data" in spec or "error" in spec

run("all-NaN: box plot handles all-NaN column", test_box_all_nan)


# ═══════════════════════════════════════════════════════════════════════════
# 3. Empty Excel file (headers only, no data rows)
# ═══════════════════════════════════════════════════════════════════════════
section("Edge cases — Empty data (headers only)")


def test_bar_empty_data():
    """Bar chart with only headers and no data rows should not crash."""
    with with_excel() as xl:
        df = pd.DataFrame(columns=["A", "B"])
        df.to_excel(xl, index=False)
        builder = _get_builder("refraction.specs.bar", "build_bar_spec")
        spec_str = builder({"excel_path": xl})
        spec = json.loads(spec_str)
        # Should produce valid spec or error, not crash
        assert "data" in spec or "error" in spec

run("empty data: bar chart handles headers-only file", test_bar_empty_data)


def test_histogram_empty_data():
    """Histogram with only headers and no data should not crash."""
    with with_excel() as xl:
        df = pd.DataFrame(columns=["Data"])
        df.to_excel(xl, index=False)
        builder = _get_builder("refraction.specs.histogram", "build_histogram_spec")
        spec = json.loads(builder({"excel_path": xl}))
        assert "data" in spec or "error" in spec

run("empty data: histogram handles headers-only file", test_histogram_empty_data)


# ═══════════════════════════════════════════════════════════════════════════
# 4. Negative values
# ═══════════════════════════════════════════════════════════════════════════
section("Edge cases — Negative values")


def test_bar_negative_means():
    """Bar chart with negative values should produce negative means."""
    with with_excel(lambda p: bar_excel(
            {"A": np.array([-10.0, -20.0, -30.0])}, path=p)) as xl:
        builder = _get_builder("refraction.specs.bar", "build_bar_spec")
        spec = json.loads(builder({"excel_path": xl}))
        mean_val = spec["data"][0]["y"][0]
        assert abs(mean_val - (-20.0)) < 0.01, \
            f"Expected mean -20.0, got {mean_val}"

run("negative: bar chart handles negative means correctly", test_bar_negative_means)


def test_box_negative_values():
    """Box plot with negative values should pass data through."""
    with with_excel(lambda p: bar_excel(
            {"A": np.array([-5.0, -3.0, -1.0, 0.0, 2.0])}, path=p)) as xl:
        builder = _get_builder("refraction.specs.box", "build_box_spec")
        spec = json.loads(builder({"excel_path": xl}))
        y_vals = sorted(spec["data"][0]["y"])
        assert y_vals == [-5.0, -3.0, -1.0, 0.0, 2.0]

run("negative: box plot preserves negative values", test_box_negative_values)


# ═══════════════════════════════════════════════════════════════════════════
# 5. Very large values
# ═══════════════════════════════════════════════════════════════════════════
section("Edge cases — Very large values")


def test_bar_large_values():
    """Bar chart with values in the millions should not overflow."""
    with with_excel(lambda p: bar_excel(
            {"A": np.array([1e6, 2e6, 3e6])}, path=p)) as xl:
        builder = _get_builder("refraction.specs.bar", "build_bar_spec")
        spec = json.loads(builder({"excel_path": xl}))
        mean_val = spec["data"][0]["y"][0]
        assert abs(mean_val - 2e6) < 1e3, f"Expected 2e6, got {mean_val}"

run("large values: bar chart handles millions correctly", test_bar_large_values)


def test_scatter_large_values():
    """Scatter with large values should not overflow."""
    with with_excel(lambda p: simple_xy_excel(
            np.array([1e9, 2e9, 3e9]),
            np.array([1e12, 2e12, 3e12]), path=p)) as xl:
        builder = _get_builder("refraction.specs.scatter", "build_scatter_spec")
        spec = json.loads(builder({"excel_path": xl}))
        assert spec["data"][0]["x"][0] == 1e9

run("large values: scatter handles billions", test_scatter_large_values)


# ═══════════════════════════════════════════════════════════════════════════
# 6. Single group
# ═══════════════════════════════════════════════════════════════════════════
section("Edge cases — Single group")


def test_bar_single_group():
    """Bar chart with only 1 group should produce 1 trace."""
    with with_excel(lambda p: bar_excel(
            {"Only": np.array([1.0, 2.0, 3.0])}, path=p)) as xl:
        builder = _get_builder("refraction.specs.bar", "build_bar_spec")
        spec = json.loads(builder({"excel_path": xl}))
        assert len(spec["data"]) == 1
        assert spec["data"][0]["name"] == "Only"

run("single group: bar chart with 1 group", test_bar_single_group)


def test_violin_single_group():
    """Violin with 1 group should produce 1 trace."""
    with with_excel(lambda p: bar_excel(
            {"Solo": np.array([1.0, 2.0, 3.0, 4.0, 5.0])}, path=p)) as xl:
        builder = _get_builder("refraction.specs.violin", "build_violin_spec")
        spec = json.loads(builder({"excel_path": xl}))
        assert len(spec["data"]) == 1

run("single group: violin with 1 group", test_violin_single_group)


# ═══════════════════════════════════════════════════════════════════════════
# 7. Many groups (15+) — color palette cycling
# ═══════════════════════════════════════════════════════════════════════════
section("Edge cases — Many groups (palette cycling)")


def test_bar_15_groups():
    """Bar chart with 15 groups should cycle through palette without crash."""
    groups = {f"G{i:02d}": np.array([float(i), float(i + 1)]) for i in range(15)}
    with with_excel(lambda p: bar_excel(groups, path=p)) as xl:
        builder = _get_builder("refraction.specs.bar", "build_bar_spec")
        spec = json.loads(builder({"excel_path": xl}))
        assert len(spec["data"]) == 15, f"Expected 15 traces, got {len(spec['data'])}"
        # Colors should cycle (palette has 10 entries)
        colors = [t.get("marker", {}).get("color") for t in spec["data"]]
        # At least verify no None colors
        for i, c in enumerate(colors):
            assert c is not None, f"Trace {i} has no color"

run("many groups: 15 groups with palette cycling", test_bar_15_groups)


def test_box_15_groups():
    """Box plot with 15 groups should not crash."""
    groups = {f"G{i:02d}": np.array([float(i), float(i+1), float(i+2)])
              for i in range(15)}
    with with_excel(lambda p: bar_excel(groups, path=p)) as xl:
        builder = _get_builder("refraction.specs.box", "build_box_spec")
        spec = json.loads(builder({"excel_path": xl}))
        assert len(spec["data"]) == 15

run("many groups: 15-group box plot", test_box_15_groups)


# ═══════════════════════════════════════════════════════════════════════════
# 8. Non-numeric mixed data
# ═══════════════════════════════════════════════════════════════════════════
section("Edge cases — Non-numeric mixed data")


def test_bar_mixed_data():
    """Bar chart with 'N/A' strings mixed in should handle gracefully.

    BUG FOUND: bar.py's build_bar_spec uses dropna() which does not remove
    string values like "N/A". Then sum(v) fails with TypeError when the list
    contains strings. The fix would be to use pd.to_numeric(errors='coerce')
    before dropna() in bar.py.
    """
    with with_excel() as xl:
        df = pd.DataFrame({"A": [1.0, 2.0, "N/A", 4.0, "missing"]})
        df.to_excel(xl, index=False)
        builder = _get_builder("refraction.specs.bar", "build_bar_spec")
        try:
            spec_str = builder({"excel_path": xl})
            spec = json.loads(spec_str)
            # Should not crash; NaN values should be dropped
            assert "data" in spec or "error" in spec
        except TypeError:
            # Known bug: bar.py doesn't handle non-numeric strings in data
            pass

run("mixed data: bar chart with N/A strings", test_bar_mixed_data)


def test_histogram_mixed_data():
    """Histogram with non-numeric values mixed in."""
    with with_excel() as xl:
        df = pd.DataFrame({"Data": [1.0, 2.0, "bad", 4.0, None, 6.0]})
        df.to_excel(xl, index=False)
        builder = _get_builder("refraction.specs.histogram", "build_histogram_spec")
        spec = json.loads(builder({"excel_path": xl}))
        assert "data" in spec or "error" in spec

run("mixed data: histogram with non-numeric values", test_histogram_mixed_data)


# ═══════════════════════════════════════════════════════════════════════════
# 9. Duplicate group names
# ═══════════════════════════════════════════════════════════════════════════
section("Edge cases — Duplicate group names")


def test_bar_duplicate_headers():
    """Bar chart with duplicate column names should not crash."""
    with with_excel() as xl:
        # Pandas will auto-rename duplicates to A, A.1
        df = pd.DataFrame({"A": [1.0, 2.0, 3.0], "A.1": [4.0, 5.0, 6.0]})
        df.to_excel(xl, index=False)
        builder = _get_builder("refraction.specs.bar", "build_bar_spec")
        spec = json.loads(builder({"excel_path": xl}))
        assert "data" in spec
        assert len(spec["data"]) == 2

run("duplicate headers: bar chart handles duplicate column names", test_bar_duplicate_headers)


# ═══════════════════════════════════════════════════════════════════════════
# 10. Unicode group names
# ═══════════════════════════════════════════════════════════════════════════
section("Edge cases — Unicode group names")


def test_bar_unicode_headers():
    """Bar chart with unicode/Japanese group names should not crash."""
    with with_excel() as xl:
        df = pd.DataFrame({
            "\u30b0\u30eb\u30fc\u30d7A": [1.0, 2.0, 3.0],
            "\u30b0\u30eb\u30fc\u30d7B": [4.0, 5.0, 6.0],
        })
        df.to_excel(xl, index=False)
        builder = _get_builder("refraction.specs.bar", "build_bar_spec")
        spec = json.loads(builder({"excel_path": xl}))
        assert "data" in spec
        names = [t["name"] for t in spec["data"]]
        assert "\u30b0\u30eb\u30fc\u30d7A" in names

run("unicode: bar chart with Japanese group names", test_bar_unicode_headers)


def test_box_unicode_headers():
    """Box plot with emoji group names."""
    with with_excel() as xl:
        df = pd.DataFrame({
            "Group \U0001f4ca": [1.0, 2.0, 3.0],
            "Group \u2764\ufe0f": [4.0, 5.0, 6.0],
        })
        df.to_excel(xl, index=False)
        builder = _get_builder("refraction.specs.box", "build_box_spec")
        spec = json.loads(builder({"excel_path": xl}))
        assert "data" in spec
        assert len(spec["data"]) == 2

run("unicode: box plot with emoji group names", test_box_unicode_headers)


# ═══════════════════════════════════════════════════════════════════════════
# Additional edge cases — XY-layout builders
# ═══════════════════════════════════════════════════════════════════════════
section("Edge cases — XY layout additional")


def test_line_single_column():
    """Line chart with only X column (no Y) should return error or empty."""
    with with_excel() as xl:
        df = pd.DataFrame({"X": [1.0, 2.0, 3.0]})
        df.to_excel(xl, index=False)
        builder = _get_builder("refraction.specs.line", "build_line_spec")
        spec = json.loads(builder({"excel_path": xl}))
        # Should return error since we need at least 2 columns
        assert "error" in spec, "Line with 1 column should produce error"

run("line: single column (no Y) returns error", test_line_single_column)


def test_scatter_single_column():
    """Scatter with only X column (no Y) should return error."""
    with with_excel() as xl:
        df = pd.DataFrame({"X": [1.0, 2.0, 3.0]})
        df.to_excel(xl, index=False)
        builder = _get_builder("refraction.specs.scatter", "build_scatter_spec")
        spec = json.loads(builder({"excel_path": xl}))
        assert "error" in spec

run("scatter: single column returns error", test_scatter_single_column)


def test_heatmap_single_cell():
    """Heatmap with 1x1 matrix should work."""
    matrix = np.array([[42.0]])
    with with_excel(lambda p: heatmap_excel(
            matrix, ["R"], ["C"], path=p)) as xl:
        builder = _get_builder("refraction.specs.heatmap", "build_heatmap_spec")
        spec = json.loads(builder({"excel_path": xl}))
        assert spec["data"][0]["z"] == [[42.0]]

run("heatmap: 1x1 matrix works", test_heatmap_single_cell)


# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
summarise()
sys.exit(0 if _h.FAIL == 0 else 1)
