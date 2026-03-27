"""Dot plot analyzer — renderer-independent.

Reads columnar Excel data (one column per group, values in rows)
and produces a ChartSpec with jittered points and mean lines per group.
"""

from __future__ import annotations

import numpy as np

from refraction.analysis.schema import AxisSpec, ChartSpec, StyleSpec
from refraction.analysis.helpers import read_data, resolve_colors, extract_config
from refraction.analysis.stats_annotator import build_stats_brackets
from refraction.analysis.results import build_results_section


def analyze_dot_plot(kw: dict) -> ChartSpec:
    """Analyze dot plot data and return a ChartSpec.

    Data payload keys:
        groups: list[dict] — per-group data with keys:
            name, values, mean, median, n, color
    """
    cfg = extract_config(kw)
    df = read_data(cfg["excel_path"], cfg["sheet"], df=cfg.get("_df"))

    groups = list(df.columns)
    values = {g: df[g].dropna().astype(float).tolist() for g in groups}
    colors = resolve_colors(cfg["color"], len(groups))

    group_data = []
    for i, g in enumerate(groups):
        vals = values[g]
        m = float(np.mean(vals)) if vals else 0.0
        med = float(np.median(vals)) if vals else 0.0
        group_data.append({
            "name": g,
            "values": vals,
            "mean": m,
            "median": med,
            "n": len(vals),
            "color": colors[i],
        })

    # Stats brackets
    brackets = build_stats_brackets(
        values, cfg["stats_test"], cfg["posthoc"], cfg["correction"]
    )

    # Results section
    results = build_results_section(values)

    return ChartSpec(
        chart_type="dot_plot",
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
            font_size=cfg["font_size"],
            axis_style=cfg["axis_style"],
            gridlines=cfg["gridlines"],
        ),
        data={
            "groups": group_data,
            "results": results,
        },
        stats=brackets,
    )
