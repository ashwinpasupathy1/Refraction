"""ChartSpec schema — the renderer-independent output of the analysis engine.

A ChartSpec is a self-describing JSON-serializable dict containing everything
a renderer needs to draw a chart:
  - Computed data (means, errors, quartiles, curves)
  - Statistical results (p-values, test names, effect sizes)
  - Annotation instructions (brackets, reference lines)
  - Style tokens (colors, visibility flags)
  - Axis metadata (ranges, scale, labels)

A ChartSpec does NOT contain pixel coordinates, font sizes in points,
or any renderer-specific format.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


SCHEMA_VERSION = "1.0"


# ── Axis metadata ────────────────────────────────────────────────────────────

@dataclass
class AxisSpec:
    label: str = ""
    type: str = "categorical"  # "categorical" | "linear" | "log"
    categories: list[str] | None = None  # for categorical axes
    suggested_range: list[float] | None = None  # [min, max] suggestion

    def to_dict(self) -> dict:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None}


# ── Statistical comparison ───────────────────────────────────────────────────

@dataclass
class Comparison:
    group_a: str
    group_b: str
    p_raw: float
    p_adjusted: float
    stars: str
    effect_size: float | None = None
    effect_type: str | None = None


@dataclass
class NormalityResult:
    shapiro_p: float
    normal: bool


@dataclass
class StatsResult:
    test: str
    omnibus_p: float | None = None
    posthoc: str | None = None
    correction: str | None = None
    comparisons: list[Comparison] = field(default_factory=list)
    normality: dict[str, NormalityResult] = field(default_factory=dict)


# ── Bracket annotation ──────────────────────────────────────────────────────

@dataclass
class Bracket:
    group_a: str
    group_b: str
    label: str  # "**", "***", "ns", etc.
    p: float


# ── Reference line ───────────────────────────────────────────────────────────

@dataclass
class ReferenceLine:
    orientation: str  # "horizontal" | "vertical"
    value: float
    label: str = ""
    style: str = "dashed"  # "solid" | "dashed" | "dotted"


# ── Style tokens ─────────────────────────────────────────────────────────────

@dataclass
class StyleSpec:
    colors: list[str] = field(default_factory=list)
    show_points: bool = False
    show_error_bars: bool = True
    show_brackets: bool = True
    jitter: float = 0.15
    point_opacity: float = 0.8
    error_type: str = "sem"


# ── ChartSpec (top-level output) ─────────────────────────────────────────────

@dataclass
class ChartSpec:
    """Top-level analysis result. Fully describes a chart for any renderer."""

    chart_type: str
    data: dict[str, Any]  # chart-type-specific data payload
    axes: dict[str, Any] = field(default_factory=dict)
    statistics: StatsResult | None = None
    annotations: dict[str, Any] = field(default_factory=lambda: {
        "brackets": [], "reference_lines": []
    })
    style: StyleSpec = field(default_factory=StyleSpec)
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dict."""
        d: dict[str, Any] = {
            "schema_version": self.schema_version,
            "chart_type": self.chart_type,
            "data": self.data,
            "axes": self.axes,
        }
        if self.statistics:
            d["statistics"] = _stats_to_dict(self.statistics)
        raw_brackets = self.annotations.get("brackets", [])
        raw_reflines = self.annotations.get("reference_lines", [])
        d["annotations"] = {
            "brackets": [asdict(b) if hasattr(b, '__dataclass_fields__') else b
                         for b in raw_brackets],
            "reference_lines": [asdict(r) if hasattr(r, '__dataclass_fields__') else r
                                for r in raw_reflines],
        }
        d["style"] = asdict(self.style)
        return d


def _stats_to_dict(s: StatsResult) -> dict:
    d: dict[str, Any] = {"test": s.test}
    if s.omnibus_p is not None:
        d["omnibus_p"] = s.omnibus_p
    if s.posthoc:
        d["posthoc"] = s.posthoc
    if s.correction:
        d["correction"] = s.correction
    d["comparisons"] = [asdict(c) for c in s.comparisons]
    d["normality"] = {k: asdict(v) for k, v in s.normality.items()}
    return d
