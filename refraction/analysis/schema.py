"""ChartSpec — renderer-independent chart description.

A ChartSpec is a pure-data object that fully describes a chart's content
without referencing any rendering library (no Plotly, no matplotlib).
Renderers consume a ChartSpec and produce visual output.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AxisSpec:
    """Describes a single axis."""

    label: str = ""
    scale: str = "linear"          # "linear" | "log"
    limits: tuple | None = None    # (min, max) or None for auto
    tick_interval: float = 0.0     # 0 = auto


@dataclass
class StyleSpec:
    """Visual style parameters (renderer interprets these)."""

    colors: list[str] = field(default_factory=list)
    alpha: float = 0.85
    point_size: float = 6.0
    point_alpha: float = 0.80
    line_width: float = 2.0
    bar_width: float = 0.8
    font_size: float = 12.0
    axis_style: str = "open"       # "open" | "closed" | "floating" | "none"
    gridlines: bool = False


@dataclass
class StatsBracket:
    """A single statistical comparison bracket."""

    group_a: str
    group_b: str
    p_value: float
    label: str                     # e.g. "***", "ns", "p=0.023"
    stacking_order: int = 0        # vertical ordering hint


@dataclass
class ChartSpec:
    """Complete renderer-independent chart description.

    Attributes:
        chart_type: Registry key (e.g. "bar", "box", "scatter").
        title: Chart title string.
        x_axis: X-axis specification.
        y_axis: Y-axis specification.
        style: Visual style parameters.
        data: Chart-type-specific data payload (dict).
        stats: Optional list of stats brackets.
        warnings: Optional list of warning strings.
    """

    chart_type: str
    title: str = ""
    x_axis: AxisSpec = field(default_factory=AxisSpec)
    y_axis: AxisSpec = field(default_factory=AxisSpec)
    style: StyleSpec = field(default_factory=StyleSpec)
    data: dict[str, Any] = field(default_factory=dict)
    stats: list[StatsBracket] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
