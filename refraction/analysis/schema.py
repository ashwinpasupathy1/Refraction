"""ChartSpec — renderer-independent chart specification schema.

A ChartSpec is a plain-data description of a fully-analyzed chart:
groups, summary stats, error bars, axis metadata, style hints, and
statistical annotations.  Any renderer (Plotly, matplotlib, Canvas,
SVG exporter) can consume a ChartSpec without re-running analysis.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


SCHEMA_VERSION = "1.0"


@dataclass
class GroupData:
    """Summary statistics and optional raw values for one data group."""
    name: str
    mean: float
    error: float                     # half-width (SEM, SD, or CI95)
    error_type: str = "SEM"          # "SEM" | "SD" | "CI95"
    n: int = 0
    color: str = "#E8453C"
    raw_points: Optional[List[float]] = None   # only when show_points=True


@dataclass
class Bracket:
    """One significance bracket between two groups."""
    group_a: str
    group_b: str
    p_value: float
    stars: str                       # "ns" | "*" | "**" | "***" | "****"
    effect_size: Optional[float] = None       # Cohen's d
    stacking_order: int = 0          # 0 = lowest, drawn first


@dataclass
class NormalityResult:
    """Shapiro-Wilk normality test result for one group."""
    group: str
    statistic: Optional[float]
    p_value: Optional[float]
    is_normal: Optional[bool]
    warning: Optional[str] = None


@dataclass
class Annotations:
    """All statistical annotations for the chart."""
    brackets: List[Bracket] = field(default_factory=list)
    normality: List[NormalityResult] = field(default_factory=list)


@dataclass
class Axes:
    """Axis configuration."""
    xlabel: str = ""
    ylabel: str = ""
    title: str = ""
    suggested_range: Optional[List[float]] = None   # [y_min, y_max]


@dataclass
class Style:
    """Visual style hints (renderer interprets as it sees fit)."""
    show_points: bool = False
    point_size: float = 6.0
    point_alpha: float = 0.80
    error_bar_type: str = "SEM"
    axis_style: str = "open"


@dataclass
class ChartSpec:
    """Top-level renderer-independent chart specification."""
    schema_version: str = SCHEMA_VERSION
    chart_type: str = ""
    data: Dict[str, Any] = field(default_factory=lambda: {"groups": []})
    axes: Axes = field(default_factory=Axes)
    style: Style = field(default_factory=Style)
    annotations: Annotations = field(default_factory=Annotations)

    def to_dict(self) -> dict:
        """Return a JSON-serializable plain dict."""
        d = asdict(self)
        return d
