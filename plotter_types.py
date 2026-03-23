"""plotter_types.py — Typed dataclasses for Refract plot requests."""

import json
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple, Union


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
# ChartData — parsed chart data passed between the parse layer, Plotly
# spec builders, and matplotlib export functions.
#
# Design rationale
# ----------------
# Every chart function and every Plotly spec builder previously called
# pd.read_excel() independently, so a single render caused multiple disk
# reads.  ChartData is parsed ONCE per render in _do_run and then shared
# across all consumers (Plotly spec builder for display, matplotlib for
# export-only).
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
