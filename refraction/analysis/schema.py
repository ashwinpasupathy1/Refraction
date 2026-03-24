"""ChartSpec — renderer-independent chart description.

A ChartSpec is a pure-data object that fully describes a chart's content
without referencing any rendering library (no Plotly, no matplotlib).
Renderers consume a ChartSpec and produce visual output.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
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
    effect_size: float = 0.0       # Cohen's d or similar


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

    chart_type: str = ""
    title: str = ""
    schema_version: str = "1.0"
    x_axis: AxisSpec = field(default_factory=AxisSpec)
    y_axis: AxisSpec = field(default_factory=AxisSpec)
    style: StyleSpec = field(default_factory=StyleSpec)
    data: dict[str, Any] = field(default_factory=dict)
    stats: list[StatsBracket] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def axes(self):
        """Proxy: provides .axes.title, .axes.xlabel, .axes.ylabel, .axes.suggested_range."""
        return _AxesProxy(self)

    @property
    def annotations(self):
        """Proxy: provides .annotations.brackets and .annotations.normality."""
        return _AnnotationsProxy(self.stats, self.data.get("normality"))

    def to_dict(self) -> dict[str, Any]:
        """Convert to a JSON-serializable dict with canonical key names."""
        d = asdict(self)
        # Provide canonical aliases expected by consumers
        d["axes"] = {"x": d.pop("x_axis", {}), "y": d.pop("y_axis", {})}
        d["annotations"] = d.pop("stats", [])
        return d


class _AxesProxy:
    """Proxy allowing spec.axes.title, spec.axes.xlabel, etc."""

    def __init__(self, spec: ChartSpec):
        self._spec = spec
        self.x = spec.x_axis
        self.y = spec.y_axis

    @property
    def title(self) -> str:
        return self._spec.title

    @property
    def xlabel(self) -> str:
        return self._spec.x_axis.label

    @property
    def ylabel(self) -> str:
        return self._spec.y_axis.label

    @property
    def suggested_range(self):
        """Returns (min, max) suggested y-range from data, or None."""
        data = self._spec.data
        groups = data.get("groups", [])
        if not groups:
            return None
        all_vals = []
        for g in groups:
            if isinstance(g, dict):
                m = g.get("mean", 0)
                e = g.get("error", 0)
                all_vals.append(m + e)
                all_vals.append(m - e)
                for pt in g.get("raw_points", []):
                    all_vals.append(pt)
        if not all_vals:
            return None
        lo = min(all_vals)
        hi = max(all_vals)
        # Pad by 10%
        margin = (hi - lo) * 0.1 if hi != lo else abs(hi) * 0.1
        return (min(0, lo - margin), hi + margin)


class _NormalityResult:
    """Simple container for normality test result."""
    def __init__(self, d: dict):
        self.group = d.get("group", "")
        self.is_normal = d.get("is_normal", True)
        self.p = d.get("p", 1.0)


class _AnnotationsProxy:
    """Proxy allowing spec.annotations.brackets and spec.annotations.normality."""

    def __init__(self, brackets: list[StatsBracket], normality=None):
        self.brackets = brackets
        if normality is not None:
            self.normality = [_NormalityResult(d) if isinstance(d, dict) else d for d in normality]
        else:
            self.normality = None


# Schema version for compatibility tracking
SCHEMA_VERSION = "1.0"

# Backward-compatible aliases
Axes = AxisSpec
Style = StyleSpec
Annotations = StatsBracket
