"""
prism_registry.py
=================
Chart-type registry for Refraction.

Contains:
- PlotTypeConfig  — dataclass describing one chart type's UI contract
- _REGISTRY_SPECS — ordered list of all 29 registered chart types
- Shared UI maps  — ERROR_TYPE_MAP, STATS_TEST_MAP, MARKER_STYLE_MAP
- PAD             — global UI padding constant

Importing this module from plotter_barplot_app.py keeps the main app file
focused on UI logic rather than data definitions.

To add a new chart type, append a PlotTypeConfig entry to _REGISTRY_SPECS.
No other file needs to change (except plotter_functions.py for the function,
plotter_validators.py for the validator, and test_comprehensive.py for tests).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, List, Set, Optional
import inspect


# ---------------------------------------------------------------------------
# Shared string-to-internal-value maps  -  used by _collect and extra_collect
# ---------------------------------------------------------------------------

ERROR_TYPE_MAP = {
    "SEM (Standard Error)":    "sem",
    "SD (Standard Deviation)": "sd",
    "95% CI":                  "ci95",
}

STATS_TEST_MAP = {
    "Paired":          "paired",
    "Parametric":      "parametric",
    "Non-parametric":  "nonparametric",
    "Permutation":     "permutation",
    "One-sample":      "one_sample",
}

MARKER_STYLE_MAP = {
    "Different Markers": "auto",
    "Circle (o)":    "o",
    "Square (s)":    "s",
    "Triangle (^)":  "^",
    "Diamond (D)":   "D",
    "Down-Triangle (v)": "v",
    "Star (*)":      "*",
    "Plus (P)":      "P",
    "Cross (X)":     "X",
    "Hexagon (h)":   "h",
}

# UI padding constant  -  change once to respace the whole UI
PAD = 16


# ---------------------------------------------------------------------------
# PlotTypeConfig  -  describes one chart type's UI contract
# ---------------------------------------------------------------------------

@dataclass
class PlotTypeConfig:
    key:         str            # internal key e.g. "bar"
    label:       str            # tab label e.g. "📊 Bar"
    fn_name:     str            # name of function in plotter_functions module
    tab_mode:    str            # passed to _tab_data / _tab_axes
    stats_tab:   str            # "standard" | "scatter" | "kaplan_meier" | etc.
    validate:    str            # name of validation method e.g. "_validate_bar"
    # Optional hook: called as extra_collect(app, kw) to inject chart-specific kwargs.
    extra_collect: Optional[Callable] = None
    # Legacy: kept for backward compat but no longer required.
    strip_keys:  Set[str] = field(default_factory=set)
    keep_keys:   Set[str] = field(default_factory=set)
    # ── Original geometry flags (drive _tab_axes widget visibility) ────────
    axes_has_bar_width: bool = True
    axes_has_line_opts: bool = False
    # ── Capability flags  -  single source of truth for _tab_axes mode sets ──
    # These replace the hardcoded _POINTS_MODES / _CAP_MODES / _LEGEND_MODES
    # sets inside _tab_axes.  Adding a new chart type only requires setting
    # these here; _tab_axes reads them via the active spec.
    has_points:    bool = False   # shows jittered data points (point size/alpha sliders)
    has_error_bars:bool = False   # draws error bars (cap size slider)
    has_legend:    bool = False   # has a data legend (legend position combobox)
    has_stats:     bool = True    # shows significance brackets (stats tab)
    x_continuous:  bool = False   # continuous x-axis (x-limit controls visible)

    def filter_kwargs(self, kw: dict[str, Any], fn: Any) -> dict[str, Any]:
        """Return only the kwargs that fn actually accepts, using its signature.
        This replaces all manual strip_keys / keep_keys maintenance  -  adding a
        new parameter to a plot function is sufficient; no registry edit needed."""
        try:
            sig    = inspect.signature(fn)
            params = set(sig.parameters.keys())
            # Always pass through VAR_KEYWORD (**kwargs) functions unfiltered
            for p in sig.parameters.values():
                if p.kind == inspect.Parameter.VAR_KEYWORD:
                    return kw
            return {k: v for k, v in kw.items() if k in params}
        except (ValueError, TypeError):
            if self.keep_keys:
                return {k: v for k, v in kw.items() if k in self.keep_keys}
            return {k: v for k, v in kw.items()
                    if k not in self.strip_keys}


# ---------------------------------------------------------------------------
# Registry  -  add new chart types here
# ---------------------------------------------------------------------------

_REGISTRY_SPECS = [
    PlotTypeConfig(
        key="bar", label="Bar Chart", fn_name="plotter_barplot",
        tab_mode="bar", stats_tab="standard",
        validate="_validate_bar",
        has_points=True, has_error_bars=True, has_legend=False, has_stats=True, x_continuous=False,
        axes_has_bar_width=True, axes_has_line_opts=False,
        extra_collect=lambda app, kw: kw.update({
            "xtick_labels": [s.strip() for s in app._get_var("xtick_labels_str", "").split(",")
                             if s.strip()] or None,
        }),
    ),
    PlotTypeConfig(
        key="line", label="Line Graph", fn_name="plotter_linegraph",
        tab_mode="line", stats_tab="standard",
        validate="_validate_line",
        has_points=True, has_error_bars=True, has_legend=True, has_stats=True, x_continuous=True,
        axes_has_bar_width=False, axes_has_line_opts=True,
        extra_collect=lambda app, kw: kw.update({
            "twin_y_series": [s.strip() for s in app._get_var("twin_y_series_str", "").split(",")
                              if s.strip()] or None,
            "ref_vline":       float(app._get_var("ref_vline_x", "0") or 0)
                               if app._get_var("ref_vline_enabled", False) else None,
            "ref_vline_label": app._get_var("ref_vline_label", ""),
        }),
    ),
    PlotTypeConfig(
        key="grouped_bar", label="Grouped Bar", fn_name="plotter_grouped_barplot",
        tab_mode="grouped_bar", stats_tab="grouped_bar",
        validate="_validate_grouped_bar",
        has_points=True, has_error_bars=True, has_legend=True, has_stats=True, x_continuous=False,
        axes_has_bar_width=True, axes_has_line_opts=False,
        extra_collect=lambda app, kw: kw.update({
            "show_anova_per_group": app._get_var("show_anova_per_group", False),
        }),
    ),
    PlotTypeConfig(
        key="box", label="Box Plot", fn_name="plotter_boxplot",
        tab_mode="box", stats_tab="standard",
        validate="_validate_bar",
        has_points=True, has_error_bars=False, has_legend=False, has_stats=True, x_continuous=False,
        axes_has_bar_width=False, axes_has_line_opts=False,
    ),
    PlotTypeConfig(
        key="scatter", label="Scatter Plot", fn_name="plotter_scatterplot",
        tab_mode="scatter", stats_tab="scatter",
        validate="_validate_line",
        has_points=True, has_error_bars=False, has_legend=True, has_stats=True, x_continuous=True,
        axes_has_bar_width=False, axes_has_line_opts=True,
        extra_collect=lambda app, kw: kw.update({
            "show_regression":       app._get_var("show_regression", False),
            "show_ci_band":          app._get_var("show_ci_band", False),
            "show_prediction_band":  app._get_var("show_prediction_band", False),
            "ref_vline":       float(app._get_var("ref_vline_x", "0") or 0)
                               if app._get_var("ref_vline_enabled", False) else None,
            "ref_vline_label": app._get_var("ref_vline_label", ""),
            "show_correlation":      app._get_var("show_correlation", False),
            "correlation_type":      ("spearman" if app._get_var("correlation_type", "Pearson") == "Spearman" else "pearson"),
            "gridlines":             app._get_var("gridlines", False),
            "show_regression_table": app._get_var("show_regression_table", False),
        }),
    ),
    PlotTypeConfig(
        key="violin", label="Violin Plot", fn_name="plotter_violin",
        tab_mode="box", stats_tab="standard",
        validate="_validate_bar",
        has_points=True, has_error_bars=False, has_legend=False, has_stats=True, x_continuous=False,
        axes_has_bar_width=False, axes_has_line_opts=False,
    ),
    PlotTypeConfig(
        key="kaplan_meier", label="Survival Curve", fn_name="plotter_kaplan_meier",
        tab_mode="kaplan_meier", stats_tab="kaplan_meier",
        validate="_validate_kaplan_meier",
        has_points=False, has_error_bars=False, has_legend=True, has_stats=False, x_continuous=True,
        axes_has_bar_width=False, axes_has_line_opts=False,
        extra_collect=lambda app, kw: kw.update({
            "show_ci":      app._get_var("show_ci", True),
            "show_censors": app._get_var("show_censors", True),
            "show_at_risk": app._get_var("show_at_risk", False),
        }),
    ),
    PlotTypeConfig(
        key="heatmap", label="Heatmap", fn_name="plotter_heatmap",
        tab_mode="heatmap", stats_tab="heatmap",
        validate="_validate_heatmap",
        has_points=False, has_error_bars=False, has_legend=False, has_stats=False, x_continuous=False,
        axes_has_bar_width=False, axes_has_line_opts=False,
        extra_collect=lambda app, kw: kw.update({
            "annotate":     app._get_var("annotate", False),
            "cluster_rows": app._get_var("cluster_rows", False),
            "cluster_cols": app._get_var("cluster_cols", False),
            "robust":       app._get_var("robust", False),
            "fmt":          app._get_var("heatmap_fmt", ".2f"),
            **{k: (lambda v: None if not v else float(v))(app._get_var(f"heatmap_{k}", ""))
               for k in ("vmin", "vmax", "center")},
        }),
    ),
    PlotTypeConfig(
        key="two_way_anova", label="Two-Way ANOVA", fn_name="plotter_two_way_anova",
        tab_mode="two_way_anova", stats_tab="two_way_anova",
        validate="_validate_two_way_anova",
        has_points=False, has_error_bars=True, has_legend=False, has_stats=True, x_continuous=False,
        axes_has_bar_width=True, axes_has_line_opts=False,
        extra_collect=lambda app, kw: kw.update({
            "show_posthoc":     app._get_var("show_posthoc", False),
            "show_effect_size": app._get_var("show_effect_size", False),
        }),
    ),
    PlotTypeConfig(
        key="before_after", label="Before / After", fn_name="plotter_before_after",
        tab_mode="before_after", stats_tab="before_after",
        validate="_validate_bar",
        has_points=True, has_error_bars=True, has_legend=False, has_stats=True, x_continuous=False,
        axes_has_bar_width=False, axes_has_line_opts=False,
        extra_collect=lambda app, kw: kw.update({
            "show_n_labels": app._get_var("show_n_labels", False),
        }),
    ),
    PlotTypeConfig(
        key="histogram", label="Histogram", fn_name="plotter_histogram",
        tab_mode="histogram", stats_tab="histogram",
        validate="_validate_bar",
        has_points=False, has_error_bars=False, has_legend=True, has_stats=False, x_continuous=True,
        axes_has_bar_width=False, axes_has_line_opts=False,
        extra_collect=lambda app, kw: kw.update({
            "bins":           int(app._get_var("hist_bins", "0") or 0),
            "density":        app._get_var("hist_density", False),
            "overlay_normal": app._get_var("hist_overlay_normal", False),
        }),
    ),
    PlotTypeConfig(
        key="subcolumn_scatter", label="Subcolumn", fn_name="plotter_subcolumn_scatter",
        tab_mode="subcolumn_scatter", stats_tab="subcolumn_scatter",
        validate="_validate_bar",
        has_points=True, has_error_bars=True, has_legend=False, has_stats=True, x_continuous=False,
        axes_has_bar_width=False, axes_has_line_opts=False,
        extra_collect=lambda app, kw: kw.update({
            # show_n_labels is not in _collect_stats so needs explicit injection
            "show_n_labels": app._get_var("show_n_labels", True),
        }),
    ),
    PlotTypeConfig(
        key="curve_fit", label="Curve Fit", fn_name="plotter_curve_fit",
        tab_mode="scatter", stats_tab="curve_fit",
        validate="_validate_line",
        has_points=True, has_error_bars=False, has_legend=True, has_stats=False, x_continuous=True,
        axes_has_bar_width=False, axes_has_line_opts=True,
        extra_collect=lambda app, kw: kw.update({
            "model_name":    app._get_var("curve_model", "4PL Sigmoidal (EC50/IC50)"),
            "show_ci_band":  app._get_var("cf_show_ci", True),
            "show_residuals":app._get_var("cf_show_residuals", False),
            "show_equation": app._get_var("cf_show_equation", True),
            "show_r2":       app._get_var("cf_show_r2", True),
            "show_params":   app._get_var("cf_show_params", True),
            "gridlines":     app._get_var("gridlines", False),
        }),
    ),
    PlotTypeConfig(
        key="column_stats", label="Col Statistics", fn_name="plotter_column_stats",
        tab_mode="bar", stats_tab="column_stats",
        validate="_validate_bar",
        has_points=False, has_error_bars=False, has_legend=False, has_stats=False, x_continuous=False,
        axes_has_bar_width=False, axes_has_line_opts=False,
        extra_collect=lambda app, kw: kw.update({
            "show_normality": app._get_var("cs_show_normality", True),
            "show_ci":        app._get_var("cs_show_ci", True),
            "show_cv":        app._get_var("cs_show_cv", True),
        }),
    ),
    PlotTypeConfig(
        key="contingency", label="Contingency", fn_name="plotter_contingency",
        tab_mode="bar", stats_tab="contingency",
        validate="_validate_contingency",
        has_points=False, has_error_bars=False, has_legend=True, has_stats=False, x_continuous=False,
        axes_has_bar_width=True, axes_has_line_opts=False,
        extra_collect=lambda app, kw: kw.update({
            "show_percentages": app._get_var("ct_show_pct", True),
            "show_expected":    app._get_var("ct_show_expected", False),
        }),
    ),
    PlotTypeConfig(
        key="repeated_measures", label="Repeated Meas.", fn_name="plotter_repeated_measures",
        tab_mode="before_after", stats_tab="repeated_measures",
        validate="_validate_bar",
        has_points=True, has_error_bars=True, has_legend=False, has_stats=True, x_continuous=False,
        axes_has_bar_width=False, axes_has_line_opts=False,
        extra_collect=lambda app, kw: kw.update({
            "show_subject_lines": app._get_var("rm_show_lines", True),
            # test_type is specific to this function (not stats_test)
            "test_type": STATS_TEST_MAP.get(app._get_var("rm_test_type", "Parametric"), "parametric"),
            # error is shared but repeated_measures uses a different UI path
            "error": ERROR_TYPE_MAP.get(app._get_var("error", "SEM (Standard Error)"), "sem"),
            # P18: custom x-tick labels
            "xtick_labels": [s.strip() for s in app._get_var("xtick_labels_str", "").split(",")
                             if s.strip()] or None,
        }),
    ),
    PlotTypeConfig(
        key="chi_square_gof", label="Chi-Sq GoF", fn_name="plotter_chi_square_gof",
        tab_mode="bar", stats_tab="chi_square_gof",
        validate="_validate_chi_square_gof",
        has_points=False, has_error_bars=False, has_legend=False, has_stats=False, x_continuous=False,
        axes_has_bar_width=False, axes_has_line_opts=False,
        extra_collect=lambda app, kw: kw.update({
            "expected_equal": app._get_var("gof_expected_equal", True),
        }),
    ),
    PlotTypeConfig(
        key="stacked_bar", label="Stacked Bar", fn_name="plotter_stacked_bar",
        tab_mode="grouped_bar", stats_tab="stacked_bar",
        validate="_validate_grouped_bar",
        has_points=False, has_error_bars=False, has_legend=True, has_stats=False, x_continuous=False,
        axes_has_bar_width=True, axes_has_line_opts=False,
        extra_collect=lambda app, kw: kw.update({
            "mode":              app._get_var("stacked_mode", "absolute"),
            "horizontal":        app._get_var("stacked_horizontal", False),
            "xtick_labels":      [s.strip() for s in app._get_var("xtick_labels_str", "").split(",")
                                  if s.strip()] or None,
            "alpha":             app._get_float("bar_alpha", 0.85),
            "show_value_labels": app._get_var("stacked_value_labels", False),
        }),
    ),
    PlotTypeConfig(
        key="bubble", label="Bubble Chart", fn_name="plotter_bubble",
        tab_mode="scatter", stats_tab="bubble",
        validate="_validate_line",
        has_points=True, has_error_bars=False, has_legend=True, has_stats=False, x_continuous=True,
        axes_has_bar_width=False, axes_has_line_opts=False,
        extra_collect=lambda app, kw: kw.update({
            "bubble_scale": app._get_float("bubble_scale", 1.0),
            "show_labels":  app._get_var("bubble_show_labels", False),
            "gridlines":    app._get_var("gridlines", False),
        }),
    ),
    PlotTypeConfig(
        key="dot_plot", label="Dot Plot", fn_name="plotter_dot_plot",
        tab_mode="bar", stats_tab="dot_plot",
        validate="_validate_bar",
        has_points=True, has_error_bars=False, has_legend=False, has_stats=True, x_continuous=False,
        axes_has_bar_width=False, axes_has_line_opts=False,
        extra_collect=lambda app, kw: kw.update({
            "show_mean":   app._get_var("dp_show_mean", True),
            "show_median": app._get_var("dp_show_median", False),
        }),
    ),
    PlotTypeConfig(
        key="bland_altman", label="Bland-Altman", fn_name="plotter_bland_altman",
        tab_mode="bar", stats_tab="bland_altman",
        validate="_validate_bland_altman",
        has_points=True, has_error_bars=False, has_legend=False, has_stats=False, x_continuous=True,
        axes_has_bar_width=False, axes_has_line_opts=False,
        extra_collect=lambda app, kw: kw.update({
            "show_ci": app._get_var("ba_show_ci", True),
        }),
    ),
    PlotTypeConfig(
        key="forest_plot", label="Forest Plot", fn_name="plotter_forest_plot",
        tab_mode="bar", stats_tab="forest_plot",
        validate="_validate_forest_plot",
        has_points=True, has_error_bars=False, has_legend=False, has_stats=False, x_continuous=False,
        axes_has_bar_width=False, axes_has_line_opts=False,
        extra_collect=lambda app, kw: kw.update({
            "ref_value":    app._get_float("fp_ref_value", 0.0),
            "show_weights": app._get_var("fp_show_weights", True),
            "show_summary": app._get_var("fp_show_summary", True),
        }),
    ),
    PlotTypeConfig(
        key="area_chart", label="Area Chart", fn_name="plotter_area_chart",
        tab_mode="line", stats_tab="standard",
        validate="_validate_line",
        has_points=False, has_error_bars=False, has_legend=True, has_stats=True, x_continuous=False,
        axes_has_bar_width=False, axes_has_line_opts=True,
        extra_collect=lambda app, kw: kw.update({
            "stacked":    False,
            "fill_alpha": 0.25,
        }),
    ),
    PlotTypeConfig(
        key="raincloud", label="Raincloud", fn_name="plotter_raincloud",
        tab_mode="bar", stats_tab="standard",
        validate="_validate_bar",
        has_points=True, has_error_bars=False, has_legend=False, has_stats=True, x_continuous=False,
        axes_has_bar_width=False, axes_has_line_opts=False,
        extra_collect=lambda app, kw: kw.update({
            "show_box": True,
        }),
    ),
    PlotTypeConfig(
        key="qq_plot", label="Q-Q Plot", fn_name="plotter_qq_plot",
        tab_mode="bar", stats_tab="column_stats",
        validate="_validate_bar",
        has_points=True, has_error_bars=False, has_legend=False, has_stats=False, x_continuous=False,
        axes_has_bar_width=False, axes_has_line_opts=False,
        extra_collect=lambda app, kw: kw.update({
            "show_ci_band": True,
            "ci_alpha":     0.15,
        }),
    ),
    PlotTypeConfig(
        key="lollipop", label="Lollipop", fn_name="plotter_lollipop",
        tab_mode="bar", stats_tab="standard",
        validate="_validate_bar",
        has_points=False, has_error_bars=True, has_legend=False, has_stats=True, x_continuous=False,
        axes_has_bar_width=False, axes_has_line_opts=False,
        extra_collect=lambda app, kw: kw.update({
            "marker_size": 10.0,
            "stem_width":  1.5,
        }),
    ),
    PlotTypeConfig(
        key="waterfall", label="Waterfall", fn_name="plotter_waterfall",
        tab_mode="bar", stats_tab="standard",
        validate="_validate_bar",
        has_points=False, has_error_bars=False, has_legend=False, has_stats=False, x_continuous=False,
        axes_has_bar_width=True, axes_has_line_opts=False,
        extra_collect=lambda app, kw: kw.update({
            "show_connector_lines": True,
            "show_total":           True,
        }),
    ),
    PlotTypeConfig(
        key="pyramid", label="Pyramid", fn_name="plotter_pyramid",
        tab_mode="grouped_bar", stats_tab="standard",
        validate="_validate_pyramid",
        has_points=False, has_error_bars=False, has_legend=True, has_stats=False, x_continuous=False,
        axes_has_bar_width=True, axes_has_line_opts=False,
        extra_collect=None,
    ),
    PlotTypeConfig(
        key="ecdf", label="ECDF", fn_name="plotter_ecdf",
        tab_mode="bar", stats_tab="standard",
        validate="_validate_bar",
        has_points=False, has_error_bars=False, has_legend=True, has_stats=True, x_continuous=False,
        axes_has_bar_width=False, axes_has_line_opts=True,
        extra_collect=lambda app, kw: kw.update({
            "complementary": False,
        }),
    ),
]


# ---------------------------------------------------------------------------
# Keyboard shortcuts  -  Command+1 through Command+9 → chart type keys
# ---------------------------------------------------------------------------

KEYBOARD_SHORTCUTS = {
    1: "bar",
    2: "line",
    3: "grouped_bar",
    4: "box",
    5: "scatter",
    6: "violin",
    7: "kaplan_meier",
    8: "heatmap",
    9: "histogram",
}

# Note: this maps Command+1 through Command+9 to chart types.
# The actual keybinding happens in the app (Agent F), but the
# mapping is defined here as the single source of truth.
