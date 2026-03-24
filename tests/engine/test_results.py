"""Tests for refraction.analysis.results — linked results tables."""

import os
import sys
import tempfile

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from refraction.analysis.results import (
    descriptive_stats,
    normality_test,
    two_group_test,
    multi_group_test,
    build_results_section,
)


class TestDescriptiveStats:
    def test_basic_stats(self):
        vals = [1, 2, 3, 4, 5]
        result = descriptive_stats(vals, "G1")
        assert result["group"] == "G1"
        assert result["n"] == 5
        assert result["mean"] == pytest.approx(3.0)
        assert result["median"] == pytest.approx(3.0)
        assert result["min"] == pytest.approx(1.0)
        assert result["max"] == pytest.approx(5.0)

    def test_sd_and_sem(self):
        vals = [10, 20, 30, 40, 50]
        result = descriptive_stats(vals)
        assert result["sd"] > 0
        assert result["sem"] > 0
        assert result["sem"] < result["sd"]

    def test_quartiles(self):
        vals = list(range(1, 101))
        result = descriptive_stats(vals)
        assert result["q1"] == pytest.approx(25.75, abs=1)
        assert result["q3"] == pytest.approx(75.25, abs=1)
        assert result["iqr"] > 0

    def test_confidence_interval(self):
        vals = [10, 20, 30, 40, 50]
        result = descriptive_stats(vals)
        assert result["ci95_lower"] < result["mean"]
        assert result["ci95_upper"] > result["mean"]

    def test_empty_group(self):
        result = descriptive_stats([], "Empty")
        assert result["n"] == 0
        assert result["mean"] is None

    def test_single_value(self):
        result = descriptive_stats([42.0])
        assert result["n"] == 1
        assert result["mean"] == pytest.approx(42.0)

    def test_handles_nan(self):
        result = descriptive_stats([1, 2, np.nan, 4, 5])
        assert result["n"] == 4  # NaN excluded


class TestNormalityTest:
    def test_normal_data(self):
        rng = np.random.RandomState(42)
        vals = rng.normal(0, 1, 100).tolist()
        result = normality_test(vals, "Normal")
        assert result["test"] == "Shapiro-Wilk"
        assert result["p"] > 0.05
        assert result["normal"] is True

    def test_non_normal_data(self):
        vals = [1] * 50 + [100] * 50  # Bimodal / non-normal
        result = normality_test(vals, "Bimodal")
        assert result["p"] < 0.05
        assert result["normal"] is False

    def test_too_few_values(self):
        result = normality_test([1, 2])
        assert result["statistic"] is None
        assert result["normal"] is None

    def test_returns_group_name(self):
        result = normality_test([1, 2, 3, 4, 5], "MyGroup")
        assert result["group"] == "MyGroup"


class TestTwoGroupTest:
    def test_welch_t_test(self):
        a = [1, 2, 3, 4, 5]
        b = [10, 11, 12, 13, 14]
        result = two_group_test(a, b, "A", "B")
        assert result["test"] == "Welch t-test"
        assert result["p"] < 0.01
        assert result["groups"] == ["A", "B"]
        assert result["effect_size"] > 0
        assert result["effect_type"] == "Cohen's d"

    def test_paired_t_test(self):
        a = [1, 2, 3, 4, 5]
        b = [2, 3, 4, 5, 6]
        result = two_group_test(a, b, "Before", "After", paired=True)
        assert result["test"] == "Paired t-test"
        assert result["p"] < 0.05

    def test_no_difference(self):
        rng = np.random.RandomState(42)
        a = rng.normal(50, 10, 100).tolist()
        b = rng.normal(50, 10, 100).tolist()
        result = two_group_test(a, b)
        assert result["p"] > 0.01  # Should not be significant


class TestMultiGroupTest:
    def test_anova_significant(self):
        groups = {
            "A": [1, 2, 3, 4, 5],
            "B": [10, 11, 12, 13, 14],
            "C": [20, 21, 22, 23, 24],
        }
        result = multi_group_test(groups)
        assert result["test"] == "One-way ANOVA"
        assert result["p"] < 0.001
        assert result["statistic"] > 0

    def test_anova_not_significant(self):
        rng = np.random.RandomState(42)
        groups = {
            "A": rng.normal(50, 10, 20).tolist(),
            "B": rng.normal(50, 10, 20).tolist(),
            "C": rng.normal(50, 10, 20).tolist(),
        }
        result = multi_group_test(groups)
        assert result["p"] > 0.01

    def test_insufficient_groups(self):
        result = multi_group_test({"A": [1, 2, 3]})
        assert result["statistic"] is None


class TestBuildResultsSection:
    def test_two_groups(self):
        groups = {
            "Control": [1, 2, 3, 4, 5],
            "Drug": [6, 7, 8, 9, 10],
        }
        results = build_results_section(groups)
        assert "descriptive" in results
        assert "normality" in results
        assert "tests" in results
        assert len(results["descriptive"]) == 2
        assert len(results["normality"]) == 2
        assert len(results["tests"]) >= 1

    def test_three_groups_has_pairwise(self):
        groups = {
            "A": [1, 2, 3, 4, 5],
            "B": [6, 7, 8, 9, 10],
            "C": [11, 12, 13, 14, 15],
        }
        results = build_results_section(groups)
        # Should have ANOVA + 3 pairwise comparisons
        assert len(results["tests"]) == 4

    def test_paired_flag(self):
        groups = {
            "Before": [1, 2, 3, 4, 5],
            "After": [2, 3, 4, 5, 6],
        }
        results = build_results_section(groups, paired=True)
        assert results["tests"][0]["test"] == "Paired t-test"


class TestResultsInSpecs:
    """Test that the analysis engine returns complete results for various chart types."""

    @pytest.fixture
    def bar_excel(self):
        path = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False).name
        pd.DataFrame({"A": [1, 2, 3, 4, 5], "B": [6, 7, 8, 9, 10]}).to_excel(
            path, index=False
        )
        yield path
        os.unlink(path)

    def test_bar_spec_has_results(self, bar_excel):
        from refraction.analysis import analyze
        result = analyze("bar", bar_excel)
        assert result["ok"] is True
        assert "groups" in result
        assert len(result["groups"]) == 2

    def test_box_spec_has_results(self, bar_excel):
        from refraction.analysis import analyze
        result = analyze("box", bar_excel)
        assert result["ok"] is True
        assert "groups" in result

    def test_violin_spec_has_results(self, bar_excel):
        from refraction.analysis import analyze
        result = analyze("violin", bar_excel)
        assert result["ok"] is True
        assert "groups" in result

    def test_histogram_spec_has_results(self, bar_excel):
        from refraction.analysis import analyze
        result = analyze("histogram", bar_excel)
        assert result["ok"] is True
        assert "groups" in result

    def test_dot_plot_spec_has_results(self, bar_excel):
        from refraction.analysis import analyze
        result = analyze("dot_plot", bar_excel)
        assert result["ok"] is True
        assert "groups" in result

    def test_before_after_spec_has_results(self, bar_excel):
        from refraction.analysis import analyze
        result = analyze("before_after", bar_excel)
        assert result["ok"] is True
        assert "groups" in result
