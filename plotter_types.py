"""plotter_types.py — Typed dataclasses for Spectra plot requests."""

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
