"""Box plot analyzer — renderer-independent.

Reads columnar Excel data (one column per group, values in rows)
and produces a ChartSpec with per-group box statistics, outliers,
optional raw data points, and stats brackets.
"""

from __future__ import annotations

import numpy as np

from refraction.analysis.schema import AxisSpec, ChartSpec, StyleSpec
from refraction.analysis.helpers import read_data, resolve_colors, extract_config
from refraction.analysis.stats_annotator import build_stats_brackets
from refraction.analysis.results import build_results_section


def _box_stats(vals: list[float]) -> dict:
    """Compute box plot statistics for a single group."""
    arr = np.array(vals)
    q1 = float(np.percentile(arr, 25))
    median = float(np.median(arr))
    q3 = float(np.percentile(arr, 75))
    iqr = q3 - q1
    whisker_lo = float(max(arr.min(), q1 - 1.5 * iqr))
    whisker_hi = float(min(arr.max(), q3 + 1.5 * iqr))
    outliers = [float(v) for v in arr if v < whisker_lo or v > whisker_hi]
    return {
        "q1": q1,
        "median": median,
        "q3": q3,
        "whisker_lo": whisker_lo,
        "whisker_hi": whisker_hi,
        "outliers": outliers,
    }


def analyze_box(kw: dict) -> ChartSpec:
    """Analyze box plot data and return a ChartSpec.

    Data payload keys:
        groups: list[str] — group names
        box_stats: list[dict] — per-group box statistics with keys:
            q1, median, q3, whisker_lo, whisker_hi, outliers
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
        if vals:
            box = _box_stats(vals)
            stats_list.append(box)
            m = float(np.mean(vals))
            med = float(np.median(vals))
            sd = float(np.std(vals, ddof=1)) if len(vals) > 1 else 0.0
        else:
            stats_list.append({
                "q1": 0.0, "median": 0.0, "q3": 0.0,
                "whisker_lo": 0.0, "whisker_hi": 0.0, "outliers": [],
            })
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
        chart_type="box",
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
            "box_stats": stats_list,
            "raw_points": raw_points,
            "results": results,
        },
        stats=brackets,
    )
