"""Analysis engine — main entry point for renderer-independent chart analysis.

Usage:
    from refraction.analysis import analyze

    spec = analyze(
        data="path/to/data.xlsx",
        chart_type="bar",
        config={"error": "sem", "stats_test": "parametric"}
    )
"""

from __future__ import annotations

from refraction.analysis.schema import ChartSpec


# Registry of chart type → analyzer function (lazy imports)
_ANALYZERS: dict[str, tuple[str, str]] = {
    "bar": ("refraction.analysis.bar", "analyze_bar"),
    # Phase 2:
    # "box": ("refraction.analysis.box", "analyze_box"),
    # "scatter": ("refraction.analysis.scatter", "analyze_scatter"),
    # "line": ("refraction.analysis.line", "analyze_line"),
    # "grouped_bar": ("refraction.analysis.grouped_bar", "analyze_grouped_bar"),
    # "violin": ("refraction.analysis.violin", "analyze_violin"),
    # "histogram": ("refraction.analysis.histogram", "analyze_histogram"),
    # "before_after": ("refraction.analysis.before_after", "analyze_before_after"),
}


def analyze(data: str, chart_type: str, config: dict | None = None) -> dict:
    """Analyze data and return a renderer-independent ChartSpec dict.

    Args:
        data: path to an Excel/CSV file
        chart_type: one of the registered chart types (e.g., "bar")
        config: optional dict of chart config (error type, stats, labels, etc.)

    Returns:
        A JSON-serializable dict following the ChartSpec schema.

    Raises:
        ValueError: if chart_type is unknown or data cannot be read.
    """
    if chart_type not in _ANALYZERS:
        raise ValueError(
            f"Unknown chart type: {chart_type!r}. "
            f"Available: {sorted(_ANALYZERS.keys())}"
        )

    module_name, fn_name = _ANALYZERS[chart_type]
    import importlib
    mod = importlib.import_module(module_name)
    analyzer = getattr(mod, fn_name)

    cfg = dict(config or {})
    cfg.setdefault("excel_path", data)
    cfg.setdefault("data_path", data)

    spec: ChartSpec = analyzer(cfg)
    return spec.to_dict()


def available_chart_types() -> list[str]:
    """Return list of chart types the analysis engine supports."""
    return sorted(_ANALYZERS.keys())
