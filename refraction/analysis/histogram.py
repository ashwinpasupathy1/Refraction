"""Histogram analyzer — renderer-independent.

Reads columnar Excel data (one column per group, values in rows)
and produces a ChartSpec with per-group bin edges and counts.
"""

from __future__ import annotations

import numpy as np

from refraction.analysis.schema import AxisSpec, ChartSpec, StyleSpec
from refraction.analysis.helpers import read_data, resolve_colors, extract_config
from refraction.analysis.results import build_results_section


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

    df = read_data(cfg["excel_path"], cfg["sheet"], df=cfg.get("_df"))

    groups = list(df.columns)
    values = {g: df[g].dropna().astype(float).tolist() for g in groups}
    colors = resolve_colors(cfg["color"], len(groups))

    histograms = []
    group_data = []
    for i, g in enumerate(groups):
        vals = values[g]
        if vals:
            counts, bin_edges = np.histogram(vals, bins=n_bins)
            histograms.append({
                "bin_edges": bin_edges.tolist(),
                "counts": counts.tolist(),
            })
            m = float(np.mean(vals))
            med = float(np.median(vals))
            sd = float(np.std(vals, ddof=1)) if len(vals) > 1 else 0.0
        else:
            histograms.append({"bin_edges": [], "counts": []})
            m = 0.0
            med = 0.0
            sd = 0.0
        group_data.append({
            "name": g,
            "values": vals,
            "mean": m,
            "median": med,
            "sd": sd,
            "sem": sd / len(vals) ** 0.5 if vals else 0.0,
            "n": len(vals),
            "color": colors[i],
        })

    # Results section
    results = build_results_section(values)

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
            "groups": group_data,
            "histograms": histograms,
            "hist_mode": hist_mode,
            "results": results,
        },
    )
