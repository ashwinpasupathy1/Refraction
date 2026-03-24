"""Analysis engine — dispatches chart type to the correct analyzer.

Usage:
    from refraction.analysis import analyze
    spec = analyze("bar", kw)
"""

from __future__ import annotations

from typing import Callable

from refraction.analysis.schema import ChartSpec

# Lazy imports — each analyzer is imported only when first requested.
_ANALYZERS: dict[str, Callable[[dict], ChartSpec]] = {}


def _ensure_analyzers() -> None:
    """Populate _ANALYZERS on first call (lazy to avoid circular imports)."""
    if _ANALYZERS:
        return

    from refraction.analysis.bar import analyze_bar
    from refraction.analysis.box import analyze_box
    from refraction.analysis.scatter import analyze_scatter
    from refraction.analysis.line import analyze_line
    from refraction.analysis.grouped_bar import analyze_grouped_bar
    from refraction.analysis.violin import analyze_violin
    from refraction.analysis.histogram import analyze_histogram
    from refraction.analysis.before_after import analyze_before_after

    _ANALYZERS.update({
        "bar": analyze_bar,
        "box": analyze_box,
        "scatter": analyze_scatter,
        "line": analyze_line,
        "grouped_bar": analyze_grouped_bar,
        "violin": analyze_violin,
        "histogram": analyze_histogram,
        "before_after": analyze_before_after,
    })


def analyze(chart_type: str, kw: dict) -> ChartSpec:
    """Analyze data for *chart_type* and return a ChartSpec.

    Args:
        chart_type: Registry key (e.g. "bar", "box", "scatter").
        kw: The same kwargs dict used by the plotter functions.

    Returns:
        A fully populated ChartSpec instance.

    Raises:
        KeyError: If *chart_type* is not registered.
    """
    _ensure_analyzers()
    if chart_type not in _ANALYZERS:
        raise KeyError(
            f"Unknown chart type {chart_type!r}. "
            f"Available: {sorted(_ANALYZERS)}"
        )
    return _ANALYZERS[chart_type](kw)
