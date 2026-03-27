"""Violin plot analyzer — renderer-independent.

Reads columnar Excel data (one column per group, values in rows)
and produces a ChartSpec with per-group KDE curves, box statistics,
optional raw data points, and stats brackets.
"""

from __future__ import annotations

import numpy as np

from refraction.analysis.schema import AxisSpec, ChartSpec, StyleSpec
from refraction.analysis.helpers import read_data, resolve_colors, extract_config
from refraction.analysis.stats_annotator import build_stats_brackets
from refraction.analysis.results import build_results_section


def _violin_stats(vals: list[float], kde_points: int = 100) -> dict:
    """Compute violin plot statistics for a single group.

    Returns KDE curve data plus inner box statistics.
    """
    arr = np.array(vals)

    # Box stats
    q1 = float(np.percentile(arr, 25))
    median = float(np.median(arr))
    q3 = float(np.percentile(arr, 75))

    # KDE
    try:
        from scipy.stats import gaussian_kde
        kde = gaussian_kde(arr)
        # Evaluate KDE over the data range with some padding
        data_min, data_max = float(arr.min()), float(arr.max())
        pad = (data_max - data_min) * 0.1 if data_max > data_min else 1.0
        kde_y = np.linspace(data_min - pad, data_max + pad, kde_points)
        kde_x = kde(kde_y)
        kde_x_list = kde_x.tolist()
        kde_y_list = kde_y.tolist()
    except (ImportError, np.linalg.LinAlgError):
        # Fallback: no KDE available
        kde_x_list = []
        kde_y_list = []

    return {
        "q1": q1,
        "median": median,
        "q3": q3,
        "kde_x": kde_x_list,   # density values
        "kde_y": kde_y_list,   # data values along the range
    }


def analyze_violin(kw: dict) -> ChartSpec:
    """Analyze violin plot data and return a ChartSpec.

    Data payload keys:
        groups: list[str] — group names
        violin_stats: list[dict] — per-group stats with keys:
            q1, median, q3, kde_x, kde_y
        raw_points: list[list[float]] | None — per-group raw values
    """
    cfg = extract_config(kw)
    df = read_data(cfg["excel_path"], cfg["sheet"], df=cfg.get("_df"))

    groups = list(df.columns)
    values = {g: df[g].dropna().astype(float).tolist() for g in groups}
    colors = resolve_colors(cfg["color"], len(groups))

    stats_list = []
    group_data = []
    for i, g in enumerate(groups):
        vals = values[g]
        if len(vals) >= 2:
            stats_list.append(_violin_stats(vals))
        else:
            stats_list.append({
                "q1": 0.0, "median": 0.0, "q3": 0.0,
                "kde_x": [], "kde_y": [],
            })
        m = float(np.mean(vals)) if vals else 0.0
        med = float(np.median(vals)) if vals else 0.0
        sd = float(np.std(vals, ddof=1)) if len(vals) > 1 else 0.0
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

    # Optional raw points
    raw_points = None
    if cfg["show_points"]:
        raw_points = [values[g] for g in groups]

    # Stats brackets
    brackets = build_stats_brackets(
        values, cfg["stats_test"], cfg["posthoc"], cfg["correction"]
    )

    # Results section
    results = build_results_section(values)

    return ChartSpec(
        chart_type="violin",
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
            "violin_stats": stats_list,
            "raw_points": raw_points,
            "results": results,
        },
        stats=brackets,
    )
