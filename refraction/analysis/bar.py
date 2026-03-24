"""Bar chart analyzer — renderer-independent.

Reads columnar Excel data (one column per group, values in rows)
and produces a ChartSpec with per-group means, error bars, and
optional raw data points and stats brackets.
"""

from __future__ import annotations

import numpy as np

from refraction.analysis.schema import AxisSpec, ChartSpec, StyleSpec
from refraction.analysis.helpers import read_data, resolve_colors, extract_config
from refraction.analysis.stats_annotator import build_stats_brackets


def _calc_error(vals: list[float], error_type: str) -> float:
    """Return the half-width of the error bar for *vals*."""
    if len(vals) < 2:
        return 0.0
    arr = np.array(vals)
    if error_type == "sd":
        return float(np.std(arr, ddof=1))
    if error_type == "ci95":
        se = float(np.std(arr, ddof=1) / np.sqrt(len(arr)))
        return se * 1.96
    # default: SEM
    return float(np.std(arr, ddof=1) / np.sqrt(len(arr)))


def analyze_bar(kw: dict) -> ChartSpec:
    """Analyze bar chart data and return a ChartSpec.

    Data payload keys:
        groups: list[str] — group names
        means: list[float] — mean per group
        errors: list[float] — error bar half-width per group
        error_type: str — "sem", "sd", or "ci95"
        raw_points: list[list[float]] | None — per-group raw values
    """
    cfg = extract_config(kw)
    df = read_data(cfg["excel_path"], cfg["sheet"])

    groups = list(df.columns)
    values = {g: df[g].dropna().astype(float).tolist() for g in groups}
    colors = resolve_colors(cfg["color"], len(groups))

    means = []
    errors = []
    for g in groups:
        vals = values[g]
        m = float(np.mean(vals)) if vals else 0.0
        means.append(m)
        errors.append(_calc_error(vals, cfg["error_type"]))

    # Optional raw points
    raw_points = None
    if cfg["show_points"]:
        raw_points = [values[g] for g in groups]

    # Stats brackets
    brackets = build_stats_brackets(
        values, cfg["stats_test"], cfg["posthoc"], cfg["correction"]
    )

    return ChartSpec(
        chart_type="bar",
        title=cfg["title"],
        x_axis=AxisSpec(label=cfg["xlabel"]),
        y_axis=AxisSpec(
            label=cfg["ytitle"],
            scale=cfg["yscale"],
            limits=cfg["ylim"],
        ),
        style=StyleSpec(
            colors=colors,
            alpha=cfg["alpha"],
            point_size=cfg["point_size"],
            point_alpha=cfg["point_alpha"],
            bar_width=cfg["bar_width"],
            font_size=cfg["font_size"],
            axis_style=cfg["axis_style"],
            gridlines=cfg["gridlines"],
        ),
        data={
            "groups": groups,
            "means": means,
            "errors": errors,
            "error_type": cfg["error_type"],
            "raw_points": raw_points,
        },
        stats=brackets,
    )
