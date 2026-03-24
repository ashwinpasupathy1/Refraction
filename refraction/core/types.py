"""plotter_types.py — Typed dataclasses for Refract plot requests."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

try:
    from typing import TypedDict
except ImportError:
    from typing_extensions import TypedDict


# ---------------------------------------------------------------------------
# PlotKwargs — TypedDict for the flat kwargs dict passed through the system.
# This is the canonical type for `kw` parameters in chart functions, spec
# builders, and the FastAPI /render endpoint.
# ---------------------------------------------------------------------------

class PlotKwargs(TypedDict, total=False):
    """Common kwargs dict passed to chart functions and spec builders."""

    # ── Data source ────────────────────────────────────────────────────────
    excel_path: str
    sheet: int | str

    # ── Labels ─────────────────────────────────────────────────────────────
    title: str
    xlabel: str
    ytitle: str
    yscale: str
    ylim: tuple[float, float] | None
    ref_line: float | None
    ref_line_label: str

    # ── Layout ─────────────────────────────────────────────────────────────
    figsize: tuple[float, float]
    font_size: float
    bar_width: float

    # ── Style ──────────────────────────────────────────────────────────────
    color: str | list[str] | None
    axis_style: str
    tick_dir: str
    minor_ticks: bool
    point_size: float
    point_alpha: float
    cap_size: float
    ytick_interval: float
    xtick_interval: float
    fig_bg: str
    spine_width: float
    gridlines: bool
    grid_style: str

    # ── Error bars ─────────────────────────────────────────────────────────
    error: str  # "sem" | "sd" | "ci95"

    # ── Stats ──────────────────────────────────────────────────────────────
    stats_test: str
    posthoc: str
    mc_correction: str
    control: str | None
    n_permutations: int
    show_ns: bool
    show_p_values: bool
    show_effect_size: bool
    show_test_name: bool
    show_normality_warning: bool
    p_sig_threshold: float
    bracket_style: str
    custom_pairs: list[tuple[str, str]] | None

    # ── Display ────────────────────────────────────────────────────────────
    show_points: bool
    show_n_labels: bool
    show_value_labels: bool
    jitter: float
    alpha: float

    # ── Chart-type specific ────────────────────────────────────────────────
    chart_type: str


# ---------------------------------------------------------------------------
# ValidationResult — return type for validator functions.
# ---------------------------------------------------------------------------

ValidationResult = Tuple[List[str], List[str]]  # (errors, warnings)


@dataclass
class DataSource:
    excel_path: str = ""
    sheet: Union[int, str] = 0


@dataclass
class StyleParams:
    color: str = "default"
    axis_style: str = "open"
    tick_dir: str = "out"
    minor_ticks: bool = False
    point_size: float = 6.0
    point_alpha: float = 0.80
    cap_size: float = 4.0
    spine_width: float = 0.8
    fig_bg: str = "white"
    grid_style: str = "none"
    legend_pos: str = "best"
    bar_width: float = 0.6
    line_width: float = 1.5
    marker_style: str = "o"
    marker_size: float = 6.0
    font_size: float = 12.0
    alpha: float = 0.85
    open_points: bool = False
    horizontal: bool = False
    show_median: bool = True
    notch: bool = False


@dataclass
class LabelParams:
    title: str = ""
    xlabel: str = ""
    ytitle: str = ""
    yscale: str = "linear"
    xscale: str = "linear"
    ylim: Optional[Tuple[float, float]] = None
    xlim: Optional[Tuple[float, float]] = None
    ref_line: Optional[float] = None
    ref_line_label: str = ""


@dataclass
class StatsParams:
    show_stats: bool = False
    stats_test: str = "auto"
    posthoc: str = "tukey"
    mc_correction: str = "holm"
    control: str = ""
    show_ns: bool = True
    show_p_values: bool = False
    show_effect_size: bool = False
    show_test_name: bool = False
    show_normality_warning: bool = True
    p_sig_threshold: float = 0.05
    bracket_style: str = "bracket"
    custom_pairs: Optional[List] = None


@dataclass
class DisplayParams:
    show_points: bool = False
    show_n_labels: bool = False
    show_value_labels: bool = False
    error: str = "sem"
    figsize: Tuple[float, float] = (5.0, 5.0)


@dataclass
class PlotRequest:
    data: DataSource = field(default_factory=DataSource)
    style: StyleParams = field(default_factory=StyleParams)
    labels: LabelParams = field(default_factory=LabelParams)
    stats: StatsParams = field(default_factory=StatsParams)
    display: DisplayParams = field(default_factory=DisplayParams)
    chart_type: str = "bar"
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_flat_dict(self) -> dict:
        """Flatten all sub-dataclasses into a single dict."""
        result = {}
        result.update(asdict(self.data))
        result.update(asdict(self.style))
        result.update(asdict(self.labels))
        result.update(asdict(self.stats))
        result.update(asdict(self.display))
        result["chart_type"] = self.chart_type
        result.update(self.extra)
        return result

    @classmethod
    def from_flat_dict(cls, kw: dict) -> "PlotRequest":
        """Build a PlotRequest from a flat kwargs dict."""
        def pick(dc_cls):
            import dataclasses
            keys = {f.name for f in dataclasses.fields(dc_cls)}
            return {k: v for k, v in kw.items() if k in keys}

        return cls(
            data=DataSource(**pick(DataSource)),
            style=StyleParams(**pick(StyleParams)),
            labels=LabelParams(**pick(LabelParams)),
            stats=StatsParams(**pick(StatsParams)),
            display=DisplayParams(**pick(DisplayParams)),
            chart_type=kw.get("chart_type", "bar"),
            extra={k: v for k, v in kw.items()
                   if k not in {"chart_type"} and k not in PlotRequest.from_flat_dict.__doc__},
        )

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_flat_dict(), default=str)


# ---------------------------------------------------------------------------
# ChartData — parsed chart data passed between the parse layer and Plotly
# spec builders.
#
# Design rationale
# ----------------
# Every Plotly spec builder previously called pd.read_excel() independently,
# so a single render caused multiple disk reads.  ChartData is parsed ONCE
# per render in _do_run and then shared across all consumers.
#
# Layout variants
# ---------------
# Flat-header (bar, box, violin, dot_plot, before_after, histogram, …):
#   groups  → list of column header strings
#   values  → dict mapping group name → list[float] (NaN already dropped)
#   means / sems / ns populated automatically by parse_flat_header()
#
# Line / scatter / curve_fit:
#   groups  → series names (columns after the X column)
#   x_values → numeric X axis values
#   series  → dict mapping series name → list[float] Y values
#
# Complex charts (heatmap, two_way_anova, kaplan_meier, forest_plot, …):
#   raw_df  → the raw DataFrame exactly as read by pandas; each chart
#             function interprets it according to its own layout rules.
#
# All chart types may additionally access raw_df for ad-hoc inspection.
# ---------------------------------------------------------------------------

@dataclass
class ChartData:
    """Parsed chart data — one instance per render, shared across consumers."""

    chart_type: str = ""
    source_path: str = ""
    source_sheet: Union[int, str] = 0

    # ── Flat-header layout (bar, box, violin, etc.) ───────────────────────
    groups: List[str] = field(default_factory=list)
    values: Dict[str, List[float]] = field(default_factory=dict)

    # Derived stats (computed once; consumers must NOT recompute)
    means: Dict[str, float] = field(default_factory=dict)
    sems:  Dict[str, float] = field(default_factory=dict)
    ns:    Dict[str, int]   = field(default_factory=dict)

    # ── Line / scatter layout ─────────────────────────────────────────────
    x_values: Optional[List[float]] = None
    series: Dict[str, List[float]] = field(default_factory=dict)

    # ── Raw DataFrame for complex / non-flat layouts ──────────────────────
    # Type is Any to avoid importing pandas at module level.
    raw_df: Any = field(default=None, repr=False)

    def n_groups(self) -> int:
        """Number of groups / series."""
        return len(self.groups) or len(self.series)

    def is_empty(self) -> bool:
        """True if no data was successfully parsed."""
        return (not self.groups and not self.series
                and self.x_values is None and self.raw_df is None)


def parse_flat_header(excel_path: str, sheet: Union[int, str],
                      chart_type: str = "") -> "ChartData":
    """Parse a flat-header Excel sheet into a ChartData instance.

    Row 0 = group names, rows 1+ = numeric values (NaN = missing replicate).

    This is the canonical parser for: bar, box, violin, dot_plot,
    before_after, repeated_measures, histogram, area_chart, raincloud,
    qq_plot, lollipop, waterfall, ecdf, subcolumn_scatter.
    """
    import pandas as pd
    import math

    cd = ChartData(chart_type=chart_type,
                   source_path=excel_path,
                   source_sheet=sheet)
    try:
        df = pd.read_excel(excel_path, sheet_name=sheet, header=0)
    except Exception:
        return cd  # empty — caller should surface the error

    cd.raw_df = df
    cd.groups = [str(c) for c in df.columns]

    for g in cd.groups:
        col = df[g].dropna()
        nums = [float(v) for v in col if _safe_float(v) is not None]
        cd.values[g] = nums
        n = len(nums)
        cd.ns[g] = n
        if n > 0:
            mean = sum(nums) / n
            cd.means[g] = mean
            cd.sems[g] = (
                math.sqrt(sum((x - mean) ** 2 for x in nums) / n) / math.sqrt(n)
                if n > 1 else 0.0
            )
        else:
            cd.means[g] = 0.0
            cd.sems[g] = 0.0

    return cd


def _safe_float(v) -> Optional[float]:
    """Return float(v) or None if v cannot be converted."""
    try:
        f = float(v)
        import math
        return None if math.isnan(f) else f
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# PlotState — typed mirror of the App._vars dict
# ---------------------------------------------------------------------------
#
# MIGRATION GUIDE
# ===============
# The Tk app currently stores all UI state in ``App._vars: dict[str, tk.Variable]``
# with string keys and untyped tk.StringVar / tk.BooleanVar / tk.IntVar values.
# PlotState is a typed dataclass that mirrors every key in ``_VAR_DEFAULTS``
# (defined in refraction/app/main.py) with proper Python types.
#
# The intent is NOT to replace _vars in one giant refactor.  Instead, adopt
# PlotState incrementally using these steps:
#
# Phase A — Snapshot / restore (low-risk, immediate benefit)
# ----------------------------------------------------------
# 1. After _collect() builds the flat ``kw`` dict, construct a PlotState:
#        state = PlotState.from_var_dict(self._vars)
#    This gives you a typed, IDE-inspectable object for the current form.
#
# 2. Tab save/restore (TabState.vars_snapshot) can store a PlotState instead
#    of a raw dict.  Serialise with ``asdict(state)`` and reconstruct with
#    ``PlotState(**d)``.
#
# Phase B — Typed collect (medium effort)
# ----------------------------------------
# 3. Rewrite _collect_display / _collect_labels / _collect_stats to read
#    from a PlotState instead of raw ``self._vars[key].get()`` calls.
#    Example:
#        # Before:
#        kw["show_points"] = self._vars["show_points"].get()
#        # After:
#        state = PlotState.from_var_dict(self._vars)
#        kw["show_points"] = state.show_points
#
# Phase C — Single source of truth (larger refactor)
# ---------------------------------------------------
# 4. Replace ``App._vars`` with a single ``App._state: PlotState`` instance.
#    UI widgets bind to PlotState fields via a thin adapter that wraps each
#    field as a tk.Variable (similar to how _get_var auto-creates vars today).
#    This makes the complete set of state visible in one place and enables
#    static type checking across the entire codebase.
#
# PlotState field names exactly match the keys in _VAR_DEFAULTS so that
# ``PlotState.from_var_dict()`` and ``PlotState.to_var_values()`` can convert
# between the two representations without manual mapping.
# ---------------------------------------------------------------------------

@dataclass
class PlotState:
    """Typed representation of every UI variable in _VAR_DEFAULTS.

    Field names match the string keys used in App._vars so conversion is
    mechanical.  All defaults match the values in _VAR_DEFAULTS.
    """

    # ── File / sheet ──────────────────────────────────────────────────────
    excel_path: str = ""
    sheet: str = ""

    # ── Data tab ──────────────────────────────────────────────────────────
    error: str = "SEM (Standard Error)"
    show_points: bool = True
    show_n_labels: bool = False
    show_value_labels: bool = False
    color: str = "Default"
    title: str = ""
    xlabel: str = ""
    ytitle: str = ""
    jitter_amount: str = "0"
    error_below_bar: bool = False

    # ── Axes tab ──────────────────────────────────────────────────────────
    yscale: str = "Linear"
    ylim_lo: str = ""
    ylim_hi: str = ""
    figw: str = ""
    figh: str = ""
    font_size: str = "12"
    ref_line_y: str = "0"
    ref_line_enabled: bool = False
    ylim_data_min: bool = False
    ylim_none: bool = True
    ylim_mode: int = 0        # 0=Auto, 1=Data min, 2=Manual
    xlim_mode: int = 0        # 0=Auto, 1=Manual
    xlim_lo: str = ""
    xlim_hi: str = ""
    gridlines: bool = False
    open_points: bool = False
    grid_style: str = "None"
    horizontal: bool = False
    show_median: bool = False
    bar_alpha: str = "0.85"
    xscale: str = "Linear"
    ref_line_label: str = ""
    bar_width: str = "0.6"
    line_width: str = "1.5"
    marker_style: str = "Different Markers"
    marker_size: str = "7"
    notch_box: bool = False

    # ── Stats tab (shared) ────────────────────────────────────────────────
    show_stats: bool = False
    show_ns: bool = False
    show_p_values: bool = False
    show_effect_size: bool = False
    show_test_name: bool = False
    show_normality_warning: bool = True
    p_sig_threshold: str = "0.05"
    bracket_style: str = "Lines"
    stats_test: str = "Parametric"
    n_permutations: str = ""
    mc_correction: str = "Holm-Bonferroni"
    posthoc: str = "Tukey HSD"
    control: str = ""

    # ── Stacked bar ───────────────────────────────────────────────────────
    stacked_horizontal: bool = False
    stacked_mode: str = "absolute"
    stacked_value_labels: bool = False
    xtick_labels_str: str = ""
    twin_y_series_str: str = ""

    # ── Reference V-line ──────────────────────────────────────────────────
    ref_vline_enabled: bool = False
    ref_vline_x: str = "0"
    ref_vline_label: str = ""

    # ── Scatter-specific ──────────────────────────────────────────────────
    show_regression: bool = False
    show_ci_band: bool = False
    show_prediction_band: bool = False
    show_correlation: bool = False
    correlation_type: str = "Pearson"
    show_regression_table: bool = False
    one_sample_mu0: str = "0"

    # ── Kaplan-Meier ──────────────────────────────────────────────────────
    show_ci: bool = True
    show_censors: bool = True
    show_at_risk: bool = False

    # ── Heatmap ───────────────────────────────────────────────────────────
    annotate: bool = False
    cluster_rows: bool = False
    cluster_cols: bool = False
    robust: bool = False
    heatmap_fmt: str = ""
    heatmap_vmin: str = ""
    heatmap_vmax: str = ""
    heatmap_center: str = ""

    # ── Two-way ANOVA ─────────────────────────────────────────────────────
    show_posthoc: bool = False

    # ── Grouped bar ───────────────────────────────────────────────────────
    show_anova_per_group: bool = False

    # ── Histogram ─────────────────────────────────────────────────────────
    hist_bins: str = "0"
    hist_density: bool = False
    hist_overlay_normal: bool = False

    # ── Curve fit ─────────────────────────────────────────────────────────
    curve_model: str = "4PL Sigmoidal (EC50/IC50)"
    cf_show_ci: bool = True
    cf_show_residuals: bool = False
    cf_show_equation: bool = True
    cf_show_r2: bool = True
    cf_show_params: bool = True

    # ── Column stats ──────────────────────────────────────────────────────
    cs_show_normality: bool = True
    cs_show_ci: bool = True
    cs_show_cv: bool = True

    # ── Contingency ───────────────────────────────────────────────────────
    ct_show_pct: bool = True
    ct_show_expected: bool = False

    # ── Repeated measures ─────────────────────────────────────────────────
    rm_show_lines: bool = True
    rm_test_type: str = "Parametric"

    # ── Priority-1 styling (axes tab) ─────────────────────────────────────
    axis_style: str = "Open (default)"
    tick_dir: str = "Outward (default)"
    minor_ticks: bool = False
    point_size: str = "6"
    point_alpha: str = "0.80"
    cap_size: str = "4"
    legend_pos: str = "Upper right"
    spine_width: str = "0.8"

    # ── Chi-square GoF ────────────────────────────────────────────────────
    gof_expected_equal: bool = True

    # ── Bubble chart ──────────────────────────────────────────────────────
    bubble_scale: str = "1.0"
    bubble_show_labels: bool = False

    # ── Dot plot ──────────────────────────────────────────────────────────
    dp_show_mean: bool = True
    dp_show_median: bool = False

    # ── Bland-Altman ──────────────────────────────────────────────────────
    ba_show_ci: bool = True

    # ── Forest plot ───────────────────────────────────────────────────────
    fp_ref_value: str = "0"
    fp_show_weights: bool = True
    fp_show_summary: bool = True

    # ── Tick intervals ────────────────────────────────────────────────────
    ytick_interval: str = ""
    xtick_interval: str = ""

    # ── Figure background ─────────────────────────────────────────────────
    fig_bg: str = "White"

    # ── Comparison mode (not in _VAR_DEFAULTS but used by stats) ─────────
    comparison_mode: int = 0  # 0=all-pairs, 1=vs-ctrl

    # ------------------------------------------------------------------
    # Conversion helpers
    # ------------------------------------------------------------------

    @classmethod
    def from_var_dict(cls, vars_dict: dict) -> "PlotState":
        """Build a PlotState from the App._vars dict.

        Each entry in vars_dict is expected to be a tk.Variable (StringVar,
        BooleanVar, IntVar) whose ``.get()`` returns the current value.
        Keys that don't match a PlotState field are silently ignored.

        Usage in the app:
            state = PlotState.from_var_dict(self._vars)
        """
        import dataclasses as _dc
        known = {f.name for f in _dc.fields(cls)}
        kw: Dict[str, Any] = {}
        for key, var in vars_dict.items():
            if key not in known:
                continue
            try:
                kw[key] = var.get()
            except Exception:
                pass  # skip broken / destroyed tk vars
        return cls(**kw)

    def to_var_values(self) -> Dict[str, Any]:
        """Return a plain dict of {field_name: python_value}.

        Suitable for restoring into App._vars via:
            for key, val in state.to_var_values().items():
                if key in self._vars:
                    self._vars[key].set(val)
        """
        return asdict(self)

    def to_flat_kwargs(self) -> Dict[str, Any]:
        """Convert to the flat kwargs dict consumed by spec builders.

        This applies the same mapping transforms that _collect_display,
        _collect_labels, and _collect_stats currently perform (e.g.
        "Linear" -> "linear", "SEM (Standard Error)" -> "sem").
        For now returns raw values; the mapping layer can be added
        incrementally as _collect methods are migrated.
        """
        return asdict(self)
