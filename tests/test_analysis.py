"""
test_analysis.py
================
Tests for the renderer-independent analysis engine (refraction/analysis/).

Covers: schema validation, bar analyzer correctness, stats integration,
edge cases, engine dispatcher, and shared helpers.
"""

import sys
import os
import math
import json

import numpy as np

from tests.conftest import (
    pf, _with_excel, _bar_excel as bar_excel,
)

# ── Import analysis modules ──────────────────────────────────────────────────
from refraction.analysis.schema import ChartSpec, SCHEMA_VERSION, Axes, Style, Annotations
from refraction.analysis.helpers import resolve_colors, extract_config
from refraction.analysis.bar import analyze_bar, _calc_error
from refraction.analysis.stats_annotator import annotate, check_normality, _cohens_d
from refraction.analysis.engine import analyze, available_chart_types
from refraction.core.config import PRISM_PALETTE


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  1. Schema validation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━



def test_to_dict_json_serializable():
    spec = ChartSpec(chart_type="bar")
    d = spec.to_dict()
    # Must not raise
    json.dumps(d)



def test_schema_version():
    spec = ChartSpec()
    assert spec.schema_version == "1.0", f"got {spec.schema_version}"



def test_chart_type_matches():
    spec = ChartSpec(chart_type="bar")
    assert spec.chart_type == "bar"



def test_required_top_level_keys():
    spec = ChartSpec(chart_type="bar")
    d = spec.to_dict()
    for key in ("data", "axes", "style", "annotations"):
        assert key in d, f"missing key: {key}"



def test_to_dict_data_has_groups():
    spec = ChartSpec(chart_type="bar", data={"groups": []})
    d = spec.to_dict()
    assert "groups" in d["data"], "data missing 'groups' key"



def test_schema_version_constant():
    assert SCHEMA_VERSION == "1.0"



# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  2. Bar analyzer correctness
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━



def test_bar_known_mean():
    with _with_excel(lambda p: bar_excel({"G": np.array([1, 2, 3, 4, 5])}, path=p)) as path:
        spec = analyze_bar(path)
        mean = spec.data["groups"][0]["mean"]
        assert abs(mean - 3.0) < 1e-9, f"expected 3.0, got {mean}"



def test_bar_sem_calculation():
    vals = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    sd = float(np.std(vals, ddof=1))
    expected_sem = sd / math.sqrt(len(vals))
    with _with_excel(lambda p: bar_excel({"G": vals}, path=p)) as path:
        spec = analyze_bar(path, error_type="SEM")
        err = spec.data["groups"][0]["error"]
        assert abs(err - expected_sem) < 1e-9, f"SEM mismatch: {err} vs {expected_sem}"



def test_bar_sd_error():
    vals = np.array([2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0])
    expected_sd = float(np.std(vals, ddof=1))
    with _with_excel(lambda p: bar_excel({"G": vals}, path=p)) as path:
        spec = analyze_bar(path, error_type="SD")
        err = spec.data["groups"][0]["error"]
        assert abs(err - expected_sd) < 1e-9, f"SD mismatch: {err} vs {expected_sd}"



def test_bar_ci95_error():
    from scipy import stats as sp_stats
    vals = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    sd = float(np.std(vals, ddof=1))
    se = sd / math.sqrt(len(vals))
    t_crit = sp_stats.t.ppf(0.975, df=len(vals) - 1)
    expected_ci = se * t_crit
    with _with_excel(lambda p: bar_excel({"G": vals}, path=p)) as path:
        spec = analyze_bar(path, error_type="CI95")
        err = spec.data["groups"][0]["error"]
        assert abs(err - expected_ci) < 1e-9, f"CI95 mismatch: {err} vs {expected_ci}"



def test_bar_three_groups_count():
    groups = {
        "Control": np.array([1, 2, 3]),
        "Drug A": np.array([4, 5, 6]),
        "Drug B": np.array([7, 8, 9]),
    }
    with _with_excel(lambda p: bar_excel(groups, path=p)) as path:
        spec = analyze_bar(path)
        n_groups = len(spec.data["groups"])
        assert n_groups == 3, f"expected 3 groups, got {n_groups}"



def test_bar_group_names_match():
    groups = {"Alpha": np.array([1, 2]), "Beta": np.array([3, 4])}
    with _with_excel(lambda p: bar_excel(groups, path=p)) as path:
        spec = analyze_bar(path)
        names = [g["name"] for g in spec.data["groups"]]
        assert names == ["Alpha", "Beta"], f"names mismatch: {names}"



def test_bar_colors_from_palette():
    groups = {"A": np.array([1]), "B": np.array([2]), "C": np.array([3])}
    with _with_excel(lambda p: bar_excel(groups, path=p)) as path:
        spec = analyze_bar(path)
        colors = [g["color"] for g in spec.data["groups"]]
        expected = PRISM_PALETTE[:3]
        assert colors == expected, f"colors mismatch: {colors} vs {expected}"



def test_bar_raw_points_included():
    vals = np.array([1.0, 2.0, 3.0])
    with _with_excel(lambda p: bar_excel({"G": vals}, path=p)) as path:
        spec = analyze_bar(path, show_points=True)
        pts = spec.data["groups"][0].get("raw_points")
        assert pts is not None, "raw_points missing when show_points=True"
        assert pts == [1.0, 2.0, 3.0], f"raw_points mismatch: {pts}"



def test_bar_raw_points_excluded():
    vals = np.array([1.0, 2.0, 3.0])
    with _with_excel(lambda p: bar_excel({"G": vals}, path=p)) as path:
        spec = analyze_bar(path, show_points=False)
        pts = spec.data["groups"][0].get("raw_points")
        assert pts is None, f"raw_points should be absent, got {pts}"



def test_bar_axes_labels():
    with _with_excel(lambda p: bar_excel({"G": np.array([1, 2])}, path=p)) as path:
        spec = analyze_bar(path, title="My Title", xlabel="X", ytitle="Y Axis")
        assert spec.axes.title == "My Title"
        assert spec.axes.xlabel == "X"
        assert spec.axes.ylabel == "Y Axis"



def test_bar_suggested_range_positive():
    # All positive means -> suggested_range[0] should be 0
    with _with_excel(lambda p: bar_excel({"G": np.array([5, 6, 7])}, path=p)) as path:
        spec = analyze_bar(path)
        sr = spec.axes.suggested_range
        assert sr[0] == 0.0, f"expected y_min=0, got {sr[0]}"



def test_bar_suggested_range_above_max():
    vals = np.array([10.0, 20.0, 30.0])
    with _with_excel(lambda p: bar_excel({"G": vals}, path=p)) as path:
        spec = analyze_bar(path, error_type="SEM")
        sr = spec.axes.suggested_range
        mean = float(np.mean(vals))
        sd = float(np.std(vals, ddof=1))
        sem = sd / math.sqrt(len(vals))
        assert sr[1] > mean + sem, f"suggested_range[1]={sr[1]} not > mean+sem={mean+sem}"



def test_bar_chart_type_field():
    with _with_excel(lambda p: bar_excel({"G": np.array([1])}, path=p)) as path:
        spec = analyze_bar(path)
        assert spec.chart_type == "bar"



# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  3. Stats integration
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━



# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  3. Stats tests — TODO: rewrite by hand against R/Prism reference values
#     See STATS_TEST_PLAN.md for what needs testing.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  4. Edge cases
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━



def test_empty_column_nan():
    # Column with all NaN values
    groups = {"Good": np.array([1.0, 2.0, 3.0]), "Empty": np.array([float("nan"), float("nan")])}
    with _with_excel(lambda p: bar_excel(groups, path=p)) as path:
        # Should not raise
        spec = analyze_bar(path)
        # Empty group should still appear
        assert len(spec.data["groups"]) == 2



def test_single_point_error_zero():
    with _with_excel(lambda p: bar_excel({"G": np.array([42.0])}, path=p)) as path:
        spec = analyze_bar(path, error_type="SEM")
        err = spec.data["groups"][0]["error"]
        assert err == 0.0, f"single data point should have error=0, got {err}"



def test_very_large_values():
    big = np.array([1e15, 2e15, 3e15])
    with _with_excel(lambda p: bar_excel({"Big": big}, path=p)) as path:
        spec = analyze_bar(path)
        mean = spec.data["groups"][0]["mean"]
        assert math.isfinite(mean), f"overflow: mean={mean}"



def test_unknown_chart_type_raises():
    # New engine returns error dict instead of raising ValueError
    result = analyze("nonexistent_chart", "/fake/path.xlsx")
    assert result["ok"] is False
    assert "error" in result



def test_negative_means_range():
    groups = {"Neg": np.array([-10.0, -20.0, -30.0])}
    with _with_excel(lambda p: bar_excel(groups, path=p)) as path:
        spec = analyze_bar(path)
        sr = spec.axes.suggested_range
        assert sr[0] < 0, f"suggested_range[0] should be negative for negative data, got {sr[0]}"



# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  5. Engine dispatcher
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━



def test_engine_bar():
    with _with_excel(lambda p: bar_excel({"G": np.array([1, 2, 3])}, path=p)) as path:
        result = analyze("bar", path)
        assert isinstance(result, dict)
        assert result["ok"] is True
        assert result["chart_type"] == "bar"



def test_available_chart_types():
    types = available_chart_types()
    assert isinstance(types, list)
    assert "bar" in types



def test_engine_invalid_type():
    # New engine returns error dict instead of raising ValueError
    result = analyze("zzzz_invalid", "/fake.xlsx")
    assert result["ok"] is False
    assert "error" in result



# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  6. Helpers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━



def test_resolve_colors_none():
    colors = resolve_colors(None, 3)
    assert len(colors) == 3
    assert colors == PRISM_PALETTE[:3]



def test_resolve_colors_single():
    colors = resolve_colors("#FF0000", 3)
    assert colors == ["#FF0000", "#FF0000", "#FF0000"]



def test_resolve_colors_list_cycle():
    colors = resolve_colors(["#FF0000", "#00FF00"], 4)
    assert len(colors) == 4
    assert colors == ["#FF0000", "#00FF00", "#FF0000", "#00FF00"]



def test_extract_config_ytitle():
    cfg = extract_config({"ytitle": "My Y", "title": "T"})
    assert cfg["ylabel"] == "My Y"
    # Both ytitle and ylabel are present (aliases)



def test_extract_config_defaults():
    cfg = extract_config({})
    assert cfg["show_points"] is False
    assert cfg["stats_test"] is None
    assert cfg["error_type"] == "SEM"



# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Merged from test_phase6_qa.py — Analysis parity, stats annotator, config audit
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

import tempfile
import pandas as pd
from scipy import stats as sp_stats


def _tmp_bar_excel_qa(groups: dict) -> str:
    """Create a temp bar-layout Excel file. Merged from test_phase6_qa.py."""
    path = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False).name
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


# Merged from test_phase6_qa.py
class TestBarAnalysisParity:
    """Compare analyzer output against expected values."""

    @staticmethod
    def _setup_data():
        data = {
            "Control": [2.0, 3.0, 4.0, 5.0, 6.0],
            "Drug": [5.0, 6.0, 7.0, 8.0, 9.0],
        }
        path = _tmp_bar_excel_qa(data)
        return data, path

    def test_means_match(self):
        data, path = self._setup_data()
        try:
            result = analyze("bar", path)
            groups = result["groups"]
            expected_control_mean = np.mean(data["Control"])
            expected_drug_mean = np.mean(data["Drug"])
            assert abs(groups[0]["mean"] - expected_control_mean) < 1e-10
            assert abs(groups[1]["mean"] - expected_drug_mean) < 1e-10
        finally:
            import os; os.unlink(path)

    def test_sem_uses_ddof1(self):
        data, path = self._setup_data()
        try:
            result = analyze("bar", path, config={"error_type": "sem"})
            groups = result["groups"]
            for i, name in enumerate(["Control", "Drug"]):
                vals = np.array(data[name])
                expected_sem = float(np.std(vals, ddof=1) / np.sqrt(len(vals)))
                assert abs(groups[i]["sem"] - expected_sem) < 1e-10, \
                    f"SEM mismatch for {name}: got {groups[i]['sem']}, expected {expected_sem}"
        finally:
            import os; os.unlink(path)

    def test_sd_matches(self):
        data, path = self._setup_data()
        try:
            result = analyze("bar", path, config={"error_type": "sd"})
            groups = result["groups"]
            for i, name in enumerate(["Control", "Drug"]):
                vals = np.array(data[name])
                expected_sd = float(np.std(vals, ddof=1))
                assert abs(groups[i]["sd"] - expected_sd) < 1e-10
        finally:
            import os; os.unlink(path)

    def test_ci95_matches(self):
        data, path = self._setup_data()
        try:
            result = analyze("bar", path, config={"error_type": "ci95"})
            groups = result["groups"]
            for i, name in enumerate(["Control", "Drug"]):
                vals = np.array(data[name])
                se = float(np.std(vals, ddof=1) / np.sqrt(len(vals)))
                t_crit = float(sp_stats.t.ppf(0.975, df=len(vals) - 1))
                expected_ci = se * t_crit
                assert abs(groups[i]["ci95"] - expected_ci) < 1e-10
        finally:
            import os; os.unlink(path)

    def test_colors_resolved(self):
        _, path = self._setup_data()
        try:
            result = analyze("bar", path)
            groups = result["groups"]
            assert len(groups) == 2
            assert all(g["color"].startswith("#") for g in groups)
        finally:
            import os; os.unlink(path)


# Merged from test_phase6_qa.py
# TestStatsAnnotatorQA — deleted. See STATS_TEST_PLAN.md for rewrite plan.


# Merged from test_phase6_qa.py
class TestConfigOptionAudit:
    """Check which Swift keys Python analyzers accept, and flag mismatches."""

    SWIFT_KEYS = {
        "excel_path", "sheet", "title", "xlabel", "ytitle",
        "error", "show_points", "jitter", "point_size", "point_alpha",
        "axis_style", "tick_dir", "minor_ticks", "spine_width",
        "figsize", "font_size", "bar_width", "line_width", "marker_style",
        "marker_size", "fig_bg", "grid_style", "alpha", "cap_size",
        "yscale", "ytick_interval", "xtick_interval",
        "stats_test", "posthoc", "mc_correction", "control",
        "show_ns", "show_p_values", "show_effect_size", "show_test_name",
        "show_normality_warning", "p_sig_threshold", "bracket_style",
        "ylim", "ref_line", "ref_line_label",
    }

    PYTHON_KEYS = {
        "excel_path", "sheet", "title", "xlabel", "ytitle", "ylabel",
        "color", "yscale", "ylim", "figsize", "font_size",
        "axis_style", "gridlines", "error_type", "show_points",
        "point_size", "point_alpha", "bar_width", "alpha",
        "line_width", "stats_test", "posthoc", "correction",
    }

    def test_swift_sends_keys_python_ignores(self):
        ignored = self.SWIFT_KEYS - self.PYTHON_KEYS
        known_gaps = {
            "error", "jitter", "tick_dir", "minor_ticks", "spine_width",
            "marker_style", "marker_size", "fig_bg", "grid_style",
            "cap_size", "ytick_interval", "xtick_interval",
            "mc_correction", "control", "show_ns", "show_p_values",
            "show_effect_size", "show_test_name", "show_normality_warning",
            "p_sig_threshold", "bracket_style", "ref_line", "ref_line_label",
        }
        unexpected = ignored - known_gaps
        assert unexpected == set(), (
            f"Swift sends keys Python unexpectedly ignores: {unexpected}"
        )

    def test_python_reads_keys_swift_does_not_send(self):
        python_only = self.PYTHON_KEYS - self.SWIFT_KEYS
        known_python_only = {
            "color", "ylabel", "gridlines", "error_type", "correction",
        }
        unexpected = python_only - known_python_only
        assert unexpected == set(), (
            f"Python reads keys Swift unexpectedly doesn't send: {unexpected}"
        )

