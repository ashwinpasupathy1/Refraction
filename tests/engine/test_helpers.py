"""
test_helpers.py
===============
Tests for helper/utility functions in refraction.core.chart_helpers.

Covers: _fmt_bar_label, _smart_xrotation, _scale_errorbar_lw, _n_labels,
        _effect_label, _style_kwargs, _param, PRISM_PALETTE, PLOT_PARAM_DEFAULTS.

No UI, no API, no Tk, no Plotly required.
"""

import math

import numpy as np
import pytest

from refraction.core.chart_helpers import (
    PLOT_PARAM_DEFAULTS,
    PRISM_PALETTE,
    _effect_label,
    _fmt_bar_label,
    _n_labels,
    _param,
    _scale_errorbar_lw,
    _smart_xrotation,
    _style_kwargs,
)


# ============================================================================
# _fmt_bar_label
# ============================================================================

class TestFmtBarLabel:
    """Tests for _fmt_bar_label — formats bar-top numeric labels."""

    def test_zero(self):
        """0 -> '0'."""
        assert _fmt_bar_label(0) == "0"

    def test_nan_returns_empty(self):
        """NaN -> empty string."""
        assert _fmt_bar_label(float("nan")) == ""

    def test_small_number_two_decimals(self):
        """Values in [0.001, 10): 2 decimal places. 3.14159 -> '3.14'."""
        assert _fmt_bar_label(3.14159) == "3.14"

    def test_medium_number_one_decimal(self):
        """Values in [10, 100): 1 decimal place. 42.789 -> '42.8'."""
        assert _fmt_bar_label(42.789) == "42.8"

    def test_large_number_no_decimal(self):
        """Values in [100, 1000): 0 decimal places. 123.456 -> '123'."""
        assert _fmt_bar_label(123.456) == "123"

    def test_very_large_scientific(self):
        """Values >= 1000: scientific notation. 1234 -> '1.23e+03'."""
        result = _fmt_bar_label(1234)
        assert "e" in result.lower()

    def test_very_small_scientific(self):
        """Values < 0.001: scientific notation. 0.0001 -> '1.00e-04'."""
        result = _fmt_bar_label(0.0001)
        assert "e" in result.lower()

    def test_negative_value(self):
        """Negative values work: -5.67 -> '-5.67'."""
        assert _fmt_bar_label(-5.67) == "-5.67"


# ============================================================================
# _smart_xrotation
# ============================================================================

class TestSmartXRotation:
    """Tests for _smart_xrotation — decides x-axis label rotation."""

    def test_few_short_labels_horizontal(self):
        """2 groups with short names -> horizontal (0 degrees).
        Crowding = 2 * 1 = 2 <= 12 and n_groups = 2 <= 4."""
        rotation, ha = _smart_xrotation(["A", "B"])
        assert rotation == 0
        assert ha == "center"

    def test_many_groups_rotated(self):
        """5+ groups -> rotated (45 degrees).
        len > 4 triggers rotation regardless of label length."""
        rotation, ha = _smart_xrotation(["A", "B", "C", "D", "E"])
        assert rotation == 45
        assert ha == "right"

    def test_long_labels_rotated(self):
        """Long labels with few groups -> crowding > 12 triggers rotation.
        crowding = 3 * 10 = 30 > 12."""
        rotation, ha = _smart_xrotation(["Treatment A", "Treatment B", "Treatment C"])
        assert rotation == 45

    def test_empty_returns_horizontal(self):
        """Empty group list -> horizontal."""
        rotation, ha = _smart_xrotation([])
        assert rotation == 0


# ============================================================================
# _scale_errorbar_lw
# ============================================================================

class TestScaleErrorbarLw:
    """Tests for _scale_errorbar_lw — scales error bar linewidth with bar width."""

    def test_default_bar_width(self):
        """At bar_width=0.6 (default), linewidth = 1.0."""
        assert _scale_errorbar_lw(0.6) == pytest.approx(1.0, abs=0.01)

    def test_proportional_scaling(self):
        """Linewidth scales linearly: bar_width=1.2 -> lw=2.0."""
        assert _scale_errorbar_lw(1.2) == pytest.approx(2.0, abs=0.01)

    def test_minimum_clamped(self):
        """Linewidth is clamped to minimum 0.5."""
        assert _scale_errorbar_lw(0.01) >= 0.5

    def test_zero_bar_width(self):
        """bar_width=0 -> clamped to 0.5."""
        assert _scale_errorbar_lw(0.0) == 0.5


# ============================================================================
# _n_labels
# ============================================================================

class TestNLabels:
    """Tests for _n_labels — generates tick labels with n= counts."""

    def test_basic_output(self):
        """Each label includes group name and sample size."""
        groups = {"Control": np.array([1, 2, 3]), "Drug": np.array([4, 5])}
        labels = _n_labels(["Control", "Drug"], groups, 12.0)
        assert labels == ["Control\nn=3", "Drug\nn=2"]

    def test_preserves_order(self):
        """Labels follow group_order, not dict insertion order."""
        groups = {"B": np.array([1]), "A": np.array([2, 3])}
        labels = _n_labels(["A", "B"], groups, 12.0)
        assert labels[0] == "A\nn=2"
        assert labels[1] == "B\nn=1"


# ============================================================================
# _effect_label
# ============================================================================

class TestEffectLabel:
    """Tests for _effect_label — Cohen's d magnitude descriptor."""

    @pytest.mark.parametrize("d, expected", [
        (0.0, "negligible"),     # |d| < 0.2
        (0.1, "negligible"),
        (0.19, "negligible"),
        (0.2, "small"),          # 0.2 <= |d| < 0.5
        (0.3, "small"),
        (0.49, "small"),
        (0.5, "medium"),         # 0.5 <= |d| < 0.8
        (0.7, "medium"),
        (0.79, "medium"),
        (0.8, "large"),          # |d| >= 0.8
        (1.5, "large"),
        (10.0, "large"),
    ])
    def test_boundaries(self, d, expected):
        """Cohen (1988) cutoffs: <0.2 negligible, 0.2-0.5 small, 0.5-0.8 medium, >=0.8 large."""
        assert _effect_label(d) == expected

    def test_negative_values(self):
        """Negative d uses absolute value."""
        assert _effect_label(-0.9) == "large"
        assert _effect_label(-0.1) == "negligible"


# ============================================================================
# _style_kwargs
# ============================================================================

class TestStyleKwargs:
    """Tests for _style_kwargs — extracts style params from a dict."""

    def test_extracts_known_keys(self):
        """Returns dict with style keys from input."""
        kw = {"axis_style": "closed", "tick_dir": "in", "font_size": 14}
        sk = _style_kwargs(kw)
        assert sk["axis_style"] == "closed"
        assert sk["tick_dir"] == "in"

    def test_defaults_for_missing_keys(self):
        """Missing keys get PLOT_PARAM_DEFAULTS values."""
        sk = _style_kwargs({})
        assert sk["axis_style"] == PLOT_PARAM_DEFAULTS["axis_style"]
        assert sk["tick_dir"] == PLOT_PARAM_DEFAULTS["tick_dir"]

    def test_does_not_leak_extra_keys(self):
        """Only style-related keys are returned, not arbitrary input keys."""
        sk = _style_kwargs({"axis_style": "open", "some_random_key": 42})
        assert "some_random_key" not in sk


# ============================================================================
# _param
# ============================================================================

class TestParam:
    """Tests for _param — retrieves a value with PLOT_PARAM_DEFAULTS fallback."""

    def test_returns_value_from_dict(self):
        """If key is in dict, return that value."""
        assert _param({"cap_size": 8.0}, "cap_size") == 8.0

    def test_falls_back_to_default(self):
        """If key is missing, return PLOT_PARAM_DEFAULTS value."""
        assert _param({}, "cap_size") == PLOT_PARAM_DEFAULTS["cap_size"]

    def test_unknown_key_returns_none(self):
        """If key is in neither dict nor defaults, return None."""
        assert _param({}, "nonexistent_key_xyz") is None


# ============================================================================
# Constants
# ============================================================================

class TestConstants:
    """Tests for module-level constants."""

    def test_prism_palette_has_10_colors(self):
        """PRISM_PALETTE has exactly 10 hex color strings."""
        assert len(PRISM_PALETTE) == 10
        for c in PRISM_PALETTE:
            assert c.startswith("#")
            assert len(c) == 7  # #RRGGBB format

    def test_plot_param_defaults_has_expected_keys(self):
        """PLOT_PARAM_DEFAULTS contains all critical style keys."""
        expected_keys = {"axis_style", "tick_dir", "minor_ticks", "point_size",
                         "point_alpha", "cap_size", "figsize", "font_size"}
        for key in expected_keys:
            assert key in PLOT_PARAM_DEFAULTS, f"Missing key: {key}"
