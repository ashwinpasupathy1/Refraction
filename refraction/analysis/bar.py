"""Bar chart analyzer — renderer-independent.

Reads columnar Excel data (one column per group, values in rows)
and produces a ChartSpec with per-group means, error bars, and
optional raw data points and stats brackets.
"""

from __future__ import annotations

import numpy as np

from refraction.analysis.schema import AxisSpec, ChartSpec, StyleSpec
from refraction.analysis.helpers import read_data, resolve_colors, extract_config
from refraction.analysis.stats_annotator import build_stats_brackets, check_normality, _cohens_d


def _calc_error(vals: list[float], error_type: str) -> float:
    """Return the half-width of the error bar for *vals*."""
    if len(vals) < 2:
        return 0.0
    arr = np.array(vals)
    et = error_type.lower() if isinstance(error_type, str) else "sem"
    if et == "sd":
        return float(np.std(arr, ddof=1))
    if et == "ci95":
        se = float(np.std(arr, ddof=1) / np.sqrt(len(arr)))
        try:
            from scipy.stats import t as t_dist
            t_crit = float(t_dist.ppf(0.975, df=len(arr) - 1))
        except ImportError:
            t_crit = 1.96
        return se * t_crit
    # default: SEM
    return float(np.std(arr, ddof=1) / np.sqrt(len(arr)))


def analyze_bar(kw_or_path=None, **kwargs) -> ChartSpec:
    """Analyze bar chart data and return a ChartSpec.

    Accepts either a dict of kwargs or a path string plus keyword args:
        analyze_bar({"excel_path": "...", "error_type": "sem"})
        analyze_bar("/path/to/data.xlsx", error_type="sem")

    Data payload keys:
        groups: list[str] — group names
        means: list[float] — mean per group
        errors: list[float] — error bar half-width per group
        error_type: str — "sem", "sd", or "ci95"
        raw_points: list[list[float]] | None — per-group raw values
    """
    if isinstance(kw_or_path, str):
        kw = {"excel_path": kw_or_path, **kwargs}
    elif kw_or_path is None:
        kw = kwargs
    else:
        kw = dict(kw_or_path)
        kw.update(kwargs)
    cfg = extract_config(kw)
    df = read_data(cfg["excel_path"], cfg["sheet"])

    groups = list(df.columns)
    values = {g: df[g].dropna().astype(float).tolist() for g in groups}
    colors = resolve_colors(cfg["color"], len(groups))

    group_data = []
    for i, g in enumerate(groups):
        vals = values[g]
        m = float(np.mean(vals)) if vals else 0.0
        err = _calc_error(vals, cfg["error_type"])
        entry: dict = {
            "name": g,
            "mean": m,
            "error": err,
            "n": len(vals),
            "color": colors[i],
        }
        if cfg["show_points"]:
            entry["raw_points"] = vals
        group_data.append(entry)

    # Stats
    raw_test = cfg["stats_test"] or ""
    # Map "parametric" to appropriate test based on group count
    if raw_test.lower() == "parametric":
        stats_test = "t-test" if len(groups) == 2 else "anova"
    else:
        stats_test = raw_test

    brackets = build_stats_brackets(
        values, stats_test, cfg["posthoc"], cfg["correction"]
    )

    # Normality and effect sizes when stats requested
    normality_data = None
    if stats_test:
        normality_data = []
        for g in groups:
            is_normal, p = check_normality(values[g])
            normality_data.append({"group": g, "is_normal": is_normal, "p": p})
        # Add effect sizes to brackets
        for br in brackets:
            a_vals = values.get(br.group_a, [])
            b_vals = values.get(br.group_b, [])
            if a_vals and b_vals:
                br.effect_size = _cohens_d(a_vals, b_vals)  # type: ignore[attr-defined]

    chart_data: dict = {
        "groups": group_data,
        "error_type": cfg["error_type"],
    }
    if normality_data is not None:
        chart_data["normality"] = normality_data

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
        data=chart_data,
        stats=brackets,
    )
