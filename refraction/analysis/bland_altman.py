"""Bland-Altman agreement analyzer — renderer-independent.

Reads paired measurements from two methods (2 columns) and produces a
ChartSpec with mean difference, limits of agreement (±1.96 SD), and 95%
confidence intervals on the LOA.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats as sp_stats

from refraction.analysis.schema import AxisSpec, ChartSpec, StyleSpec
from refraction.analysis.helpers import read_data, resolve_colors, extract_config


def analyze_bland_altman(kw: dict) -> ChartSpec:
    """Analyze Bland-Altman agreement data and return a ChartSpec."""
    cfg = extract_config(kw)
    df = read_data(cfg["excel_path"], cfg["sheet"], df=cfg.get("_df"))

    cols = list(df.columns)
    if len(cols) < 2:
        return ChartSpec(
            chart_type="bland_altman",
            title=cfg["title"],
            warnings=["Bland-Altman requires exactly 2 columns (Method A, Method B)."],
        )

    method_a_name = str(cols[0])
    method_b_name = str(cols[1])

    a_raw = pd.to_numeric(df[cols[0]], errors="coerce")
    b_raw = pd.to_numeric(df[cols[1]], errors="coerce")
    valid = a_raw.notna() & b_raw.notna()
    a_vals = a_raw[valid].values
    b_vals = b_raw[valid].values
    n = len(a_vals)

    if n < 3:
        return ChartSpec(
            chart_type="bland_altman",
            title=cfg["title"],
            warnings=["Need at least 3 paired observations."],
        )

    means = (a_vals + b_vals) / 2.0
    diffs = a_vals - b_vals

    mean_diff = float(np.mean(diffs))
    sd_diff = float(np.std(diffs, ddof=1))

    loa_upper = mean_diff + 1.96 * sd_diff
    loa_lower = mean_diff - 1.96 * sd_diff

    # 95% CI on mean difference
    se_mean = sd_diff / np.sqrt(n)
    t_crit = float(sp_stats.t.ppf(0.975, df=n - 1))
    mean_ci = [mean_diff - t_crit * se_mean, mean_diff + t_crit * se_mean]

    # 95% CI on LOA (Bland & Altman 1986 formula)
    # SE of LOA = sqrt(3 * s² / n)
    se_loa = np.sqrt(3.0 * sd_diff ** 2 / n)
    loa_upper_ci = [loa_upper - t_crit * se_loa, loa_upper + t_crit * se_loa]
    loa_lower_ci = [loa_lower - t_crit * se_loa, loa_lower + t_crit * se_loa]

    colors = resolve_colors(cfg["color"], 1)

    return ChartSpec(
        chart_type="bland_altman",
        title=cfg["title"],
        x_axis=AxisSpec(label=cfg["xlabel"] or f"Mean of {method_a_name} and {method_b_name}"),
        y_axis=AxisSpec(label=cfg["ytitle"] or f"{method_a_name} − {method_b_name}"),
        style=StyleSpec(colors=colors, font_size=cfg["font_size"],
                        axis_style=cfg["axis_style"], gridlines=cfg["gridlines"]),
        data={
            "method_a": method_a_name,
            "method_b": method_b_name,
            "means": means.tolist(),
            "diffs": diffs.tolist(),
            "n": n,
            "mean_diff": round(mean_diff, 6),
            "sd_diff": round(sd_diff, 6),
            "loa_upper": round(loa_upper, 6),
            "loa_lower": round(loa_lower, 6),
            "mean_ci": [round(v, 6) for v in mean_ci],
            "loa_upper_ci": [round(v, 6) for v in loa_upper_ci],
            "loa_lower_ci": [round(v, 6) for v in loa_lower_ci],
        },
    )
