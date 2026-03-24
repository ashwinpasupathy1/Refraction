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

import plotter_test_harness as _h
from plotter_test_harness import ok, fail, run, section, summarise, bar_excel

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

section("Schema validation")


def test_to_dict_json_serializable():
    spec = ChartSpec(chart_type="bar")
    d = spec.to_dict()
    # Must not raise
    json.dumps(d)

run("ChartSpec.to_dict() returns JSON-serializable dict", test_to_dict_json_serializable)


def test_schema_version():
    spec = ChartSpec()
    assert spec.schema_version == "1.0", f"got {spec.schema_version}"

run("schema_version is '1.0'", test_schema_version)


def test_chart_type_matches():
    spec = ChartSpec(chart_type="bar")
    assert spec.chart_type == "bar"

run("chart_type matches what was set", test_chart_type_matches)


def test_required_top_level_keys():
    spec = ChartSpec(chart_type="bar")
    d = spec.to_dict()
    for key in ("data", "axes", "style", "annotations"):
        assert key in d, f"missing key: {key}"

run("all required top-level keys present", test_required_top_level_keys)


def test_to_dict_data_has_groups():
    spec = ChartSpec(chart_type="bar", data={"groups": []})
    d = spec.to_dict()
    assert "groups" in d["data"], "data missing 'groups' key"

run("to_dict data has groups key", test_to_dict_data_has_groups)


def test_schema_version_constant():
    assert SCHEMA_VERSION == "1.0"

run("SCHEMA_VERSION constant is '1.0'", test_schema_version_constant)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  2. Bar analyzer correctness
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

section("Bar analyzer correctness")


def test_bar_known_mean():
    with _h.with_excel(lambda p: bar_excel({"G": np.array([1, 2, 3, 4, 5])}, path=p)) as path:
        spec = analyze_bar(path)
        mean = spec.data["groups"][0]["mean"]
        assert abs(mean - 3.0) < 1e-9, f"expected 3.0, got {mean}"

run("known data [1,2,3,4,5] -> mean=3.0", test_bar_known_mean)


def test_bar_sem_calculation():
    vals = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    sd = float(np.std(vals, ddof=1))
    expected_sem = sd / math.sqrt(len(vals))
    with _h.with_excel(lambda p: bar_excel({"G": vals}, path=p)) as path:
        spec = analyze_bar(path, error_type="SEM")
        err = spec.data["groups"][0]["error"]
        assert abs(err - expected_sem) < 1e-9, f"SEM mismatch: {err} vs {expected_sem}"

run("SEM = SD/sqrt(n) verified against manual computation", test_bar_sem_calculation)


def test_bar_sd_error():
    vals = np.array([2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0])
    expected_sd = float(np.std(vals, ddof=1))
    with _h.with_excel(lambda p: bar_excel({"G": vals}, path=p)) as path:
        spec = analyze_bar(path, error_type="SD")
        err = spec.data["groups"][0]["error"]
        assert abs(err - expected_sd) < 1e-9, f"SD mismatch: {err} vs {expected_sd}"

run("SD error type works correctly", test_bar_sd_error)


def test_bar_ci95_error():
    from scipy import stats as sp_stats
    vals = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    sd = float(np.std(vals, ddof=1))
    se = sd / math.sqrt(len(vals))
    t_crit = sp_stats.t.ppf(0.975, df=len(vals) - 1)
    expected_ci = se * t_crit
    with _h.with_excel(lambda p: bar_excel({"G": vals}, path=p)) as path:
        spec = analyze_bar(path, error_type="CI95")
        err = spec.data["groups"][0]["error"]
        assert abs(err - expected_ci) < 1e-9, f"CI95 mismatch: {err} vs {expected_ci}"

run("CI95 error type works correctly", test_bar_ci95_error)


def test_bar_three_groups_count():
    groups = {
        "Control": np.array([1, 2, 3]),
        "Drug A": np.array([4, 5, 6]),
        "Drug B": np.array([7, 8, 9]),
    }
    with _h.with_excel(lambda p: bar_excel(groups, path=p)) as path:
        spec = analyze_bar(path)
        n_groups = len(spec.data["groups"])
        assert n_groups == 3, f"expected 3 groups, got {n_groups}"

run("3 groups -> 3 entries in data.groups", test_bar_three_groups_count)


def test_bar_group_names_match():
    groups = {"Alpha": np.array([1, 2]), "Beta": np.array([3, 4])}
    with _h.with_excel(lambda p: bar_excel(groups, path=p)) as path:
        spec = analyze_bar(path)
        names = [g["name"] for g in spec.data["groups"]]
        assert names == ["Alpha", "Beta"], f"names mismatch: {names}"

run("group names match column headers", test_bar_group_names_match)


def test_bar_colors_from_palette():
    groups = {"A": np.array([1]), "B": np.array([2]), "C": np.array([3])}
    with _h.with_excel(lambda p: bar_excel(groups, path=p)) as path:
        spec = analyze_bar(path)
        colors = [g["color"] for g in spec.data["groups"]]
        expected = PRISM_PALETTE[:3]
        assert colors == expected, f"colors mismatch: {colors} vs {expected}"

run("colors from PRISM_PALETTE when no color specified", test_bar_colors_from_palette)


def test_bar_raw_points_included():
    vals = np.array([1.0, 2.0, 3.0])
    with _h.with_excel(lambda p: bar_excel({"G": vals}, path=p)) as path:
        spec = analyze_bar(path, show_points=True)
        pts = spec.data["groups"][0].get("raw_points")
        assert pts is not None, "raw_points missing when show_points=True"
        assert pts == [1.0, 2.0, 3.0], f"raw_points mismatch: {pts}"

run("raw_points included when show_points=True", test_bar_raw_points_included)


def test_bar_raw_points_excluded():
    vals = np.array([1.0, 2.0, 3.0])
    with _h.with_excel(lambda p: bar_excel({"G": vals}, path=p)) as path:
        spec = analyze_bar(path, show_points=False)
        pts = spec.data["groups"][0].get("raw_points")
        assert pts is None, f"raw_points should be absent, got {pts}"

run("raw_points excluded when show_points=False", test_bar_raw_points_excluded)


def test_bar_axes_labels():
    with _h.with_excel(lambda p: bar_excel({"G": np.array([1, 2])}, path=p)) as path:
        spec = analyze_bar(path, title="My Title", xlabel="X", ytitle="Y Axis")
        assert spec.axes.title == "My Title"
        assert spec.axes.xlabel == "X"
        assert spec.axes.ylabel == "Y Axis"

run("axes have correct labels from config", test_bar_axes_labels)


def test_bar_suggested_range_positive():
    # All positive means -> suggested_range[0] should be 0
    with _h.with_excel(lambda p: bar_excel({"G": np.array([5, 6, 7])}, path=p)) as path:
        spec = analyze_bar(path)
        sr = spec.axes.suggested_range
        assert sr[0] == 0.0, f"expected y_min=0, got {sr[0]}"

run("suggested_range[0] is 0 for positive data", test_bar_suggested_range_positive)


def test_bar_suggested_range_above_max():
    vals = np.array([10.0, 20.0, 30.0])
    with _h.with_excel(lambda p: bar_excel({"G": vals}, path=p)) as path:
        spec = analyze_bar(path, error_type="SEM")
        sr = spec.axes.suggested_range
        mean = float(np.mean(vals))
        sd = float(np.std(vals, ddof=1))
        sem = sd / math.sqrt(len(vals))
        assert sr[1] > mean + sem, f"suggested_range[1]={sr[1]} not > mean+sem={mean+sem}"

run("suggested_range[1] > max(mean + error)", test_bar_suggested_range_above_max)


def test_bar_chart_type_field():
    with _h.with_excel(lambda p: bar_excel({"G": np.array([1])}, path=p)) as path:
        spec = analyze_bar(path)
        assert spec.chart_type == "bar"

run("analyze_bar sets chart_type='bar'", test_bar_chart_type_field)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  3. Stats integration
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

section("Stats integration")


def test_stats_two_groups_welch():
    groups = {
        "Control": np.array([1.0, 2.0, 3.0, 4.0, 5.0]),
        "Treatment": np.array([6.0, 7.0, 8.0, 9.0, 10.0]),
    }
    with _h.with_excel(lambda p: bar_excel(groups, path=p)) as path:
        spec = analyze_bar(path, stats_test="parametric")
        brackets = spec.annotations.brackets
        assert len(brackets) >= 1, f"expected >= 1 bracket, got {len(brackets)}"
        br = brackets[0]
        assert br.group_a == "Control" and br.group_b == "Treatment"

run("parametric + 2 groups -> Welch t-test comparison", test_stats_two_groups_welch)


def test_stats_three_groups_anova():
    groups = {
        "Control": np.array([1.0, 2.0, 3.0, 4.0, 5.0]),
        "Drug A": np.array([6.0, 7.0, 8.0, 9.0, 10.0]),
        "Drug B": np.array([11.0, 12.0, 13.0, 14.0, 15.0]),
    }
    with _h.with_excel(lambda p: bar_excel(groups, path=p)) as path:
        spec = analyze_bar(path, stats_test="parametric")
        brackets = spec.annotations.brackets
        # 3 groups -> C(3,2) = 3 pairwise comparisons
        assert len(brackets) == 3, f"expected 3 brackets, got {len(brackets)}"

run("parametric + 3 groups -> ANOVA + pairwise comparisons", test_stats_three_groups_anova)


def test_brackets_have_stacking_order():
    groups = {
        "A": np.array([1.0, 2.0, 3.0, 4.0, 5.0]),
        "B": np.array([6.0, 7.0, 8.0, 9.0, 10.0]),
        "C": np.array([11.0, 12.0, 13.0, 14.0, 15.0]),
    }
    with _h.with_excel(lambda p: bar_excel(groups, path=p)) as path:
        spec = analyze_bar(path, stats_test="parametric")
        for br in spec.annotations.brackets:
            assert hasattr(br, "stacking_order"), "bracket missing stacking_order"
            assert isinstance(br.stacking_order, int)

run("brackets have stacking_order field", test_brackets_have_stacking_order)


def test_brackets_sorted_by_span():
    groups = {
        "A": np.array([1.0, 2.0, 3.0, 4.0, 5.0]),
        "B": np.array([6.0, 7.0, 8.0, 9.0, 10.0]),
        "C": np.array([11.0, 12.0, 13.0, 14.0, 15.0]),
    }
    with _h.with_excel(lambda p: bar_excel(groups, path=p)) as path:
        spec = analyze_bar(path, stats_test="parametric")
        brackets = spec.annotations.brackets
        orders = [br.stacking_order for br in brackets]
        assert orders == sorted(orders), f"stacking_order not sorted: {orders}"

run("brackets sorted by span width (narrow first)", test_brackets_sorted_by_span)


def test_p_values_reasonable():
    groups = {
        "A": np.array([1.0, 2.0, 3.0, 4.0, 5.0]),
        "B": np.array([6.0, 7.0, 8.0, 9.0, 10.0]),
    }
    with _h.with_excel(lambda p: bar_excel(groups, path=p)) as path:
        spec = analyze_bar(path, stats_test="parametric")
        for br in spec.annotations.brackets:
            assert 0 < br.p_value <= 1.0, f"bad p-value: {br.p_value}"

run("p-values are reasonable (0 < p <= 1)", test_p_values_reasonable)


def test_effect_sizes_present():
    groups = {
        "A": np.array([1.0, 2.0, 3.0, 4.0, 5.0]),
        "B": np.array([6.0, 7.0, 8.0, 9.0, 10.0]),
    }
    with _h.with_excel(lambda p: bar_excel(groups, path=p)) as path:
        spec = analyze_bar(path, stats_test="parametric")
        for br in spec.annotations.brackets:
            assert br.effect_size is not None, "effect_size missing"
            assert math.isfinite(br.effect_size), f"effect_size not finite: {br.effect_size}"

run("effect sizes (Cohen's d) present and finite", test_effect_sizes_present)


def test_normality_results_present():
    groups = {
        "A": np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0]),
        "B": np.array([7.0, 8.0, 9.0, 10.0, 11.0, 12.0]),
    }
    with _h.with_excel(lambda p: bar_excel(groups, path=p)) as path:
        spec = analyze_bar(path, stats_test="parametric")
        normality = spec.annotations.normality
        assert len(normality) == 2, f"expected 2 normality results, got {len(normality)}"
        for nr in normality:
            assert nr.group in ("A", "B")

run("normality results present for each group", test_normality_results_present)


def test_no_stats_without_test():
    groups = {
        "A": np.array([1.0, 2.0, 3.0]),
        "B": np.array([4.0, 5.0, 6.0]),
    }
    with _h.with_excel(lambda p: bar_excel(groups, path=p)) as path:
        spec = analyze_bar(path)  # no stats_test
        assert len(spec.annotations.brackets) == 0, "brackets should be empty"

run("no stats when stats_test is not set", test_no_stats_without_test)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  4. Edge cases
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

section("Edge cases")


def test_single_group_no_stats():
    with _h.with_excel(lambda p: bar_excel({"Only": np.array([1, 2, 3])}, path=p)) as path:
        spec = analyze_bar(path, stats_test="parametric")
        assert len(spec.annotations.brackets) == 0, "single group should have no brackets"

run("single group -> no stats, no brackets", test_single_group_no_stats)


def test_empty_column_nan():
    # Column with all NaN values
    groups = {"Good": np.array([1.0, 2.0, 3.0]), "Empty": np.array([float("nan"), float("nan")])}
    with _h.with_excel(lambda p: bar_excel(groups, path=p)) as path:
        # Should not raise
        spec = analyze_bar(path)
        # Empty group should still appear
        assert len(spec.data["groups"]) == 2

run("empty column (all NaN) handled gracefully", test_empty_column_nan)


def test_single_point_error_zero():
    with _h.with_excel(lambda p: bar_excel({"G": np.array([42.0])}, path=p)) as path:
        spec = analyze_bar(path, error_type="SEM")
        err = spec.data["groups"][0]["error"]
        assert err == 0.0, f"single data point should have error=0, got {err}"

run("single data point per group -> error is 0", test_single_point_error_zero)


def test_very_large_values():
    big = np.array([1e15, 2e15, 3e15])
    with _h.with_excel(lambda p: bar_excel({"Big": big}, path=p)) as path:
        spec = analyze_bar(path)
        mean = spec.data["groups"][0]["mean"]
        assert math.isfinite(mean), f"overflow: mean={mean}"

run("very large values -> no overflow", test_very_large_values)


def test_unknown_chart_type_raises():
    # New engine returns error dict instead of raising ValueError
    result = analyze("nonexistent_chart", "/fake/path.xlsx")
    assert result["ok"] is False
    assert "error" in result

run("analyze() with unknown chart_type returns error dict", test_unknown_chart_type_raises)


def test_negative_means_range():
    groups = {"Neg": np.array([-10.0, -20.0, -30.0])}
    with _h.with_excel(lambda p: bar_excel(groups, path=p)) as path:
        spec = analyze_bar(path)
        sr = spec.axes.suggested_range
        assert sr[0] < 0, f"suggested_range[0] should be negative for negative data, got {sr[0]}"

run("suggested_range[0] is negative for data with negative means", test_negative_means_range)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  5. Engine dispatcher
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

section("Engine dispatcher")


def test_engine_bar():
    with _h.with_excel(lambda p: bar_excel({"G": np.array([1, 2, 3])}, path=p)) as path:
        result = analyze("bar", path)
        assert isinstance(result, dict)
        assert result["ok"] is True
        assert result["chart_type"] == "bar"

run("analyze() with chart_type='bar' returns result dict", test_engine_bar)


def test_available_chart_types():
    types = available_chart_types()
    assert isinstance(types, list)
    assert "bar" in types

run("available_chart_types() returns list including 'bar'", test_available_chart_types)


def test_engine_invalid_type():
    # New engine returns error dict instead of raising ValueError
    result = analyze("zzzz_invalid", "/fake.xlsx")
    assert result["ok"] is False
    assert "error" in result

run("analyze() with invalid type returns error dict", test_engine_invalid_type)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  6. Helpers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

section("Helpers")


def test_resolve_colors_none():
    colors = resolve_colors(None, 3)
    assert len(colors) == 3
    assert colors == PRISM_PALETTE[:3]

run("resolve_colors(None, 3) returns 3 palette colors", test_resolve_colors_none)


def test_resolve_colors_single():
    colors = resolve_colors("#FF0000", 3)
    assert colors == ["#FF0000", "#FF0000", "#FF0000"]

run("resolve_colors('#FF0000', 3) returns 3 copies", test_resolve_colors_single)


def test_resolve_colors_list_cycle():
    colors = resolve_colors(["#FF0000", "#00FF00"], 4)
    assert len(colors) == 4
    assert colors == ["#FF0000", "#00FF00", "#FF0000", "#00FF00"]

run("resolve_colors list cycles correctly", test_resolve_colors_list_cycle)


def test_extract_config_ytitle():
    cfg = extract_config({"ytitle": "My Y", "title": "T"})
    assert cfg["ylabel"] == "My Y"
    # Both ytitle and ylabel are present (aliases)

run("extract_config maps 'ytitle' to 'ylabel'", test_extract_config_ytitle)


def test_extract_config_defaults():
    cfg = extract_config({})
    assert cfg["show_points"] is False
    assert cfg["stats_test"] is None
    assert cfg["error_type"] == "SEM"

run("extract_config sets correct defaults", test_extract_config_defaults)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    summarise("analysis")
    sys.exit(0 if _h.FAIL == 0 else 1)
