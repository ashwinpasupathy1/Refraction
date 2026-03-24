"""Analysis engine dispatcher.

Routes ``analyze(chart_type, excel_path, **kw)`` to the appropriate
chart-specific analyzer and returns a :class:`ChartSpec`.
"""

from __future__ import annotations

from typing import List

from refraction.analysis.schema import ChartSpec


_ANALYZERS = {
    "bar": "refraction.analysis.bar:analyze_bar",
}


def available_chart_types() -> List[str]:
    """Return the list of chart types the engine can analyze."""
    return sorted(_ANALYZERS.keys())


def analyze(chart_type: str, excel_path: str, **kw) -> ChartSpec:
    """Run analysis for *chart_type* and return a ChartSpec.

    Raises
    ------
    ValueError
        If *chart_type* is not supported.  The error message lists the
        available chart types.
    """
    entry = _ANALYZERS.get(chart_type)
    if entry is None:
        avail = ", ".join(available_chart_types())
        raise ValueError(
            f"Unknown chart type {chart_type!r}. "
            f"Available types: {avail}"
        )

    module_path, func_name = entry.rsplit(":", 1)
    import importlib
    mod = importlib.import_module(module_path)
    fn = getattr(mod, func_name)
    return fn(excel_path, **kw)
