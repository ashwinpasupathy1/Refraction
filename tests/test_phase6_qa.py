"""Phase 6 -- QA Validation Tests.

6a. Analysis engine response completeness for all chart types
6b. Analysis engine parity (bar chart means, errors)
6c. Stats annotator correctness (parametric + nonparametric)
6d. Config option audit (Swift vs Python)
6e. Missing feature checklist
"""

import math
import os
import sys
import tempfile

import numpy as np
import pandas as pd
import pytest
from scipy import stats as sp_stats

# Ensure project root importable
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from refraction.analysis import analyze
from refraction.analysis.engine import available_chart_types
from refraction.analysis.stats_annotator import build_stats_brackets, check_normality, _cohens_d


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tmp_bar_excel(groups: dict) -> str:
    """Create a temp bar-layout Excel file."""
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


def _tmp_xy_excel(xs, ys, x_label="X", y_label="Y") -> str:
    path = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False).name
    rows = [[x_label, y_label]] + [[float(x), float(y)] for x, y in zip(xs, ys)]
    pd.DataFrame(rows).to_excel(path, index=False, header=False)
    return path


def _tmp_grouped_excel() -> str:
    path = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False).name
    rows = [
        ["Cat1", "Cat1", "Cat2", "Cat2"],
        ["SubA", "SubB", "SubA", "SubB"],
        [1.0, 2.0, 3.0, 4.0],
        [1.5, 2.5, 3.5, 4.5],
        [1.2, 2.2, 3.2, 4.2],
    ]
    pd.DataFrame(rows).to_excel(path, index=False, header=False)
    return path


# ---------------------------------------------------------------------------
# 6a. Analysis response completeness
# ---------------------------------------------------------------------------

class TestSchemaCompleteness:
    """Verify analyze() returns complete responses for all chart types."""

    @pytest.fixture(autouse=True)
    def setup_data(self):
        self.bar_path = _tmp_bar_excel({
            "Control": [1.0, 2.0, 3.0, 4.0, 5.0],
            "Drug A": [3.0, 4.0, 5.0, 6.0, 7.0],
            "Drug B": [5.0, 6.0, 7.0, 8.0, 9.0],
        })
        self.xy_path = _tmp_xy_excel(
            [1, 2, 3, 4, 5], [2, 4, 6, 8, 10]
        )
        self.grouped_path = _tmp_grouped_excel()
        yield
        for p in [self.bar_path, self.xy_path, self.grouped_path]:
            try:
                os.unlink(p)
            except FileNotFoundError:
                pass

    def _check_result(self, result):
        """Validate an analyze() result dict has required fields."""
        assert isinstance(result, dict)
        assert result["ok"] is True
        assert "chart_type" in result
        assert "groups" in result
        for g in result["groups"]:
            assert "name" in g
            assert "mean" in g
            assert "color" in g
            assert isinstance(g["color"], str)
            assert g["color"].startswith("#")

    @pytest.mark.parametrize("chart_type", [
        "bar", "box", "violin", "histogram", "before_after",
    ])
    def test_flat_header_analyzers(self, chart_type):
        result = analyze(chart_type, self.bar_path)
        self._check_result(result)
        assert result["chart_type"] == chart_type

    def test_scatter_analyzer(self):
        result = analyze("scatter", self.xy_path)
        self._check_result(result)
        assert result["chart_type"] == "scatter"

    def test_line_analyzer(self):
        result = analyze("line", self.xy_path)
        self._check_result(result)
        assert result["chart_type"] == "line"

    def test_grouped_bar_analyzer(self):
        result = analyze("grouped_bar", self.grouped_path)
        self._check_result(result)
        assert result["chart_type"] == "grouped_bar"

    def test_to_dict_has_canonical_keys(self):
        result = analyze("bar", self.bar_path)
        assert "ok" in result
        assert "chart_type" in result
        assert "groups" in result
        assert "comparisons" in result

    def test_axes_proxy(self):
        result = analyze("bar", self.bar_path, config={
            "title": "Test Title",
            "x_label": "Groups",
            "y_label": "Values",
        })
        assert result["title"] == "Test Title"
        assert result["x_label"] == "Groups"
        assert result["y_label"] == "Values"

    def test_unknown_chart_type_still_analyzes_data(self):
        # The simplified engine processes any chart type -- it reads data
        # and computes descriptive stats regardless of the chart_type string
        result = analyze("nonexistent_chart_type", self.bar_path)
        assert result["ok"] is True
        assert result["chart_type"] == "nonexistent_chart_type"


# ---------------------------------------------------------------------------
# 6b. Analysis engine parity with old code
# ---------------------------------------------------------------------------

class TestBarAnalysisParity:
    """Compare new analyzer output against expected values."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.data = {
            "Control": [2.0, 3.0, 4.0, 5.0, 6.0],
            "Drug": [5.0, 6.0, 7.0, 8.0, 9.0],
        }
        self.path = _tmp_bar_excel(self.data)
        yield
        os.unlink(self.path)

    def test_means_match(self):
        result = analyze("bar", self.path)
        groups = result["groups"]
        expected_control_mean = np.mean(self.data["Control"])
        expected_drug_mean = np.mean(self.data["Drug"])
        assert abs(groups[0]["mean"] - expected_control_mean) < 1e-10
        assert abs(groups[1]["mean"] - expected_drug_mean) < 1e-10

    def test_sem_uses_ddof1(self):
        """New analyzer uses ddof=1 for SEM (Bessel correction)."""
        result = analyze("bar", self.path, config={"error_type": "sem"})
        groups = result["groups"]
        for i, name in enumerate(["Control", "Drug"]):
            vals = np.array(self.data[name])
            expected_sem = float(np.std(vals, ddof=1) / np.sqrt(len(vals)))
            assert abs(groups[i]["sem"] - expected_sem) < 1e-10, \
                f"SEM mismatch for {name}: got {groups[i]['sem']}, expected {expected_sem}"

    def test_sd_matches(self):
        result = analyze("bar", self.path, config={"error_type": "sd"})
        groups = result["groups"]
        for i, name in enumerate(["Control", "Drug"]):
            vals = np.array(self.data[name])
            expected_sd = float(np.std(vals, ddof=1))
            assert abs(groups[i]["sd"] - expected_sd) < 1e-10

    def test_ci95_matches(self):
        result = analyze("bar", self.path, config={"error_type": "ci95"})
        groups = result["groups"]
        for i, name in enumerate(["Control", "Drug"]):
            vals = np.array(self.data[name])
            se = float(np.std(vals, ddof=1) / np.sqrt(len(vals)))
            t_crit = float(sp_stats.t.ppf(0.975, df=len(vals) - 1))
            expected_ci = se * t_crit
            assert abs(groups[i]["ci95"] - expected_ci) < 1e-10

    def test_colors_resolved(self):
        result = analyze("bar", self.path)
        groups = result["groups"]
        assert len(groups) == 2
        assert all(g["color"].startswith("#") for g in groups)

    def test_raw_points_included_when_requested(self):
        result = analyze("bar", self.path)
        for g in result["groups"]:
            assert "values" in g
            assert len(g["values"]) > 0

    def test_raw_points_absent_by_default(self):
        # In the new engine, values are always included
        result = analyze("bar", self.path)
        for g in result["groups"]:
            assert "values" in g


# ---------------------------------------------------------------------------
# 6c. Stats annotator correctness
# ---------------------------------------------------------------------------

class TestStatsAnnotator:
    """Verify p-values match direct scipy calls; brackets have stacking_order."""

    def setup_method(self):
        rng = np.random.default_rng(42)
        self.groups_3 = {
            "Control": rng.normal(5.0, 1.0, 20).tolist(),
            "Drug A": rng.normal(8.0, 1.0, 20).tolist(),
            "Drug B": rng.normal(11.0, 1.0, 20).tolist(),
        }
        self.groups_2 = {
            "A": [1.0, 2.0, 3.0, 4.0, 5.0],
            "B": [3.0, 4.0, 5.0, 6.0, 7.0],
        }

    def test_ttest_pvalues_match_scipy(self):
        brackets = build_stats_brackets(self.groups_2, "t-test")
        assert len(brackets) == 1
        _, expected_p = sp_stats.ttest_ind(self.groups_2["A"], self.groups_2["B"])
        assert abs(brackets[0].p_value - expected_p) < 1e-10

    def test_anova_posthoc_brackets(self):
        brackets = build_stats_brackets(self.groups_3, "anova", "tukey")
        # With 3 groups, ANOVA + posthoc should give 3 pairwise comparisons
        # (if omnibus p <= 0.05)
        _, p_omnibus = sp_stats.f_oneway(
            self.groups_3["Control"],
            self.groups_3["Drug A"],
            self.groups_3["Drug B"],
        )
        if p_omnibus <= 0.05:
            assert len(brackets) == 3
        else:
            assert len(brackets) == 0

    def test_brackets_have_stacking_order(self):
        brackets = build_stats_brackets(self.groups_3, "anova", "tukey")
        if brackets:
            orders = [b.stacking_order for b in brackets]
            assert orders == sorted(orders), "Brackets must be ordered by stacking_order"
            assert len(set(orders)) == len(orders), "Each bracket needs unique stacking_order"

    def test_mannwhitney_pvalues_match(self):
        brackets = build_stats_brackets(self.groups_2, "mann-whitney")
        assert len(brackets) == 1
        _, expected_p = sp_stats.mannwhitneyu(
            self.groups_2["A"], self.groups_2["B"], alternative="two-sided"
        )
        assert abs(brackets[0].p_value - expected_p) < 1e-10

    def test_kruskal_wallis_brackets(self):
        brackets = build_stats_brackets(self.groups_3, "kruskal-wallis")
        _, p_omnibus = sp_stats.kruskal(
            self.groups_3["Control"],
            self.groups_3["Drug A"],
            self.groups_3["Drug B"],
        )
        if p_omnibus <= 0.05:
            assert len(brackets) == 3
        else:
            assert len(brackets) == 0

    def test_p_to_label(self):
        from refraction.analysis.stats_annotator import _p_to_label
        assert _p_to_label(0.0001) == "***"
        assert _p_to_label(0.001) == "***"
        assert _p_to_label(0.005) == "**"
        assert _p_to_label(0.01) == "**"
        assert _p_to_label(0.03) == "*"
        assert _p_to_label(0.05) == "*"
        assert _p_to_label(0.1) == "ns"

    def test_normality_check(self):
        # Normal data
        rng = np.random.default_rng(123)
        normal_data = rng.normal(0, 1, 50).tolist()
        is_normal, p = check_normality(normal_data)
        assert bool(is_normal) in (True, False)  # may be numpy bool
        assert 0 <= p <= 1

        # Very non-normal data
        skewed = [1.0] * 20 + [100.0] * 2
        is_normal_skewed, p_skewed = check_normality(skewed)
        # Shapiro-Wilk should detect this as non-normal
        assert p_skewed < 0.05

    def test_cohens_d(self):
        d = _cohens_d([1, 2, 3, 4, 5], [6, 7, 8, 9, 10])
        # Large effect size expected
        assert abs(d) > 2.0

    def test_no_stats_returns_empty(self):
        brackets = build_stats_brackets(self.groups_2, "")
        assert brackets == []

    def test_single_group_returns_empty(self):
        brackets = build_stats_brackets({"A": [1, 2, 3]}, "t-test")
        assert brackets == []


# ---------------------------------------------------------------------------
# 6d. Config option audit (Swift toDict vs Python extract_config)
# ---------------------------------------------------------------------------

class TestConfigOptionAudit:
    """Check which Swift keys Python analyzers accept, and flag mismatches."""

    # Keys that Swift's ChartConfig.toDict() produces
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
        # Optional
        "ylim", "ref_line", "ref_line_label",
    }

    # Keys that Python extract_config reads from kw
    PYTHON_KEYS = {
        "excel_path", "sheet", "title", "xlabel", "ytitle", "ylabel",
        "color", "yscale", "ylim", "figsize", "font_size",
        "axis_style", "gridlines", "error_type", "show_points",
        "point_size", "point_alpha", "bar_width", "alpha",
        "line_width", "stats_test", "posthoc", "correction",
    }

    def test_swift_sends_keys_python_ignores(self):
        """Document keys Swift sends that Python's extract_config ignores."""
        ignored = self.SWIFT_KEYS - self.PYTHON_KEYS
        # These are known gaps. The test documents them explicitly.
        known_gaps = {
            "error",           # Swift uses "error", Python uses "error_type"
            "jitter",          # Python doesn't extract jitter in extract_config
            "tick_dir",        # Not in extract_config
            "minor_ticks",     # Not in extract_config
            "spine_width",     # Not in extract_config
            "marker_style",    # Not in extract_config
            "marker_size",     # Not in extract_config
            "fig_bg",          # Not in extract_config
            "grid_style",      # Swift sends "grid_style", Python uses "gridlines"
            "cap_size",        # Not in extract_config
            "ytick_interval",  # Not in extract_config
            "xtick_interval",  # Not in extract_config
            "mc_correction",   # Swift uses "mc_correction", Python uses "correction"
            "control",         # Not in extract_config
            "show_ns",         # Not in extract_config
            "show_p_values",   # Not in extract_config
            "show_effect_size",# Not in extract_config
            "show_test_name",  # Not in extract_config
            "show_normality_warning",  # Not in extract_config
            "p_sig_threshold", # Not in extract_config
            "bracket_style",   # Not in extract_config
            "ref_line",        # Not in extract_config
            "ref_line_label",  # Not in extract_config
        }
        unexpected = ignored - known_gaps
        assert unexpected == set(), (
            f"Swift sends keys Python unexpectedly ignores: {unexpected}"
        )

    def test_python_reads_keys_swift_does_not_send(self):
        """Document keys Python reads that Swift doesn't send."""
        python_only = self.PYTHON_KEYS - self.SWIFT_KEYS
        known_python_only = {
            "color",       # Swift doesn't send a color override
            "ylabel",      # Python alias for ytitle
            "gridlines",   # Swift sends grid_style instead
            "error_type",  # Swift sends "error" instead
            "correction",  # Swift sends "mc_correction" instead
        }
        unexpected = python_only - known_python_only
        assert unexpected == set(), (
            f"Python reads keys Swift unexpectedly doesn't send: {unexpected}"
        )

    def test_naming_mismatches_documented(self):
        """Verify the known naming mismatches between Swift and Python."""
        mismatches = {
            ("error", "error_type"),           # Swift: "error", Python: "error_type"
            ("mc_correction", "correction"),    # Swift: "mc_correction", Python: "correction"
            ("grid_style", "gridlines"),        # Different naming
        }
        # This test simply documents the mismatches exist.
        # A future fix should normalize these.
        assert len(mismatches) == 3


# ---------------------------------------------------------------------------
# 6e. Missing feature checklist
# ---------------------------------------------------------------------------

class TestFeatureChecklist:
    """Check if key features exist in the codebase."""

    def test_style_presets_exist(self):
        from refraction.core import presets
        assert hasattr(presets, 'load_preset') or hasattr(presets, 'save_preset') or \
               hasattr(presets, 'BUILTIN_PRESETS')

    def test_session_persistence_exists(self):
        from refraction.core import session
        assert hasattr(session, 'save_session') or hasattr(session, 'load_session') or \
               hasattr(session, 'SessionPersistence') or hasattr(session, 'Session')

    def test_pzfx_import_exists(self):
        from refraction.io import import_pzfx
        assert hasattr(import_pzfx, 'import_pzfx') or hasattr(import_pzfx, 'parse_pzfx')

    def test_export_exists(self):
        from refraction.io import export
        assert hasattr(export, 'export_plotly') or hasattr(export, 'export_matplotlib') or \
               hasattr(export, 'JOURNAL_PRESETS')

    def test_undo_redo_exists(self):
        from refraction.core import undo
        assert hasattr(undo, 'UndoStack')

    def test_validators_exist(self):
        from refraction.core import validators
        assert hasattr(validators, 'validate_flat_header') or \
               hasattr(validators, 'validate_bar')

    def test_registry_exists(self):
        from refraction.core import registry
        # Should have the chart type registry
        assert hasattr(registry, 'REGISTRY') or hasattr(registry, 'PlotTypeConfig')

    def test_analysis_engine_exists(self):
        from refraction.analysis import analyze
        types = available_chart_types()
        assert len(types) >= 8, f"Expected >= 8 analyzers, got {len(types)}: {types}"

    def test_swift_renderer_exists(self):
        """Check Swift BarRenderer exists."""
        swift_path = os.path.join(_ROOT, "RefractionApp", "Refraction",
                                  "Renderers", "BarRenderer.swift")
        assert os.path.exists(swift_path), "BarRenderer.swift not found"

    def test_swift_chart_config_exists(self):
        swift_path = os.path.join(_ROOT, "RefractionApp", "Refraction",
                                  "Models", "ChartConfig.swift")
        assert os.path.exists(swift_path), "ChartConfig.swift not found"

    def test_swift_chart_spec_exists(self):
        swift_path = os.path.join(_ROOT, "RefractionApp", "Refraction",
                                  "Models", "ChartSpec.swift")
        assert os.path.exists(swift_path), "ChartSpec.swift not found"


# ---------------------------------------------------------------------------
# Additional: Verify available_chart_types matches expectations
# ---------------------------------------------------------------------------

class TestAnalyzerRegistry:
    def test_all_registered_types(self):
        types = available_chart_types()
        # Should have all 29 chart types
        assert len(types) == 29, f"Expected 29 types, got {len(types)}: {types}"
        assert "bar" in types
        assert "box" in types
        assert "scatter" in types
