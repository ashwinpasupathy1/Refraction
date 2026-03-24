"""Histogram analyzer — renderer-independent.

Reads columnar Excel data (one column per group, values in rows)
and produces a ChartSpec with per-group bin edges and counts.
"""

from __future__ import annotations

import numpy as np

from refraction.analysis.schema import AxisSpec, ChartSpec, StyleSpec
from refraction.analysis.helpers import read_data, resolve_colors, extract_config


def analyze_histogram(kw: dict) -> ChartSpec:
    """Analyze histogram data and return a ChartSpec.

    Data payload keys:
        groups: list[str] — group names
        histograms: list[dict] — per-group histogram data with keys:
            bin_edges: list[float] — N+1 bin edge values
            counts: list[float] — N bin counts
        hist_mode: str — "overlay" or "stack"
    """
    cfg = extract_config(kw)
    hist_mode = kw.get("hist_mode", "overlay")
    n_bins = kw.get("bins", "auto")

    df = read_data(cfg["excel_path"], cfg["sheet"])

    groups = list(df.columns)
    values = {g: df[g].dropna().astype(float).tolist() for g in groups}
    colors = resolve_colors(cfg["color"], len(groups))

    histograms = []
    for g in groups:
        vals = values[g]
        if vals:
            counts, bin_edges = np.histogram(vals, bins=n_bins)
            histograms.append({
                "bin_edges": bin_edges.tolist(),
                "counts": counts.tolist(),
            })
        else:
            histograms.append({"bin_edges": [], "counts": []})

    return ChartSpec(
        chart_type="histogram",
        title=cfg["title"],
        x_axis=AxisSpec(label=cfg["xlabel"]),
        y_axis=AxisSpec(
            label=cfg["ytitle"] or "Frequency",
            scale=cfg["yscale"],
            limits=cfg["ylim"],
        ),
        style=StyleSpec(
            colors=colors,
            alpha=0.7 if hist_mode == "overlay" else 1.0,
            font_size=cfg["font_size"],
            axis_style=cfg["axis_style"],
            gridlines=cfg["gridlines"],
        ),
        data={
            "groups": groups,
            "histograms": histograms,
            "hist_mode": hist_mode,
        },
    )
