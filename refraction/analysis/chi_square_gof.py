"""Chi-square goodness-of-fit analyzer — renderer-independent.

Reads category names (row 0), observed counts (row 1), and optional expected
counts (row 2) from Excel.  Produces a ChartSpec with chi-square statistic,
p-value, and Cramér's V / phi effect size.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats as sp_stats

from refraction.analysis.schema import AxisSpec, ChartSpec, StyleSpec
from refraction.analysis.helpers import read_data, resolve_colors, extract_config


def analyze_chi_square_gof(kw: dict) -> ChartSpec:
    """Analyze chi-square goodness-of-fit data and return a ChartSpec."""
    cfg = extract_config(kw)
    df = read_data(cfg["excel_path"], cfg["sheet"], header=None)

    if len(df) < 2:
        return ChartSpec(
            chart_type="chi_square_gof",
            title=cfg["title"],
            warnings=["Need at least 2 rows: categories and observed counts."],
        )

    categories = [str(v) for v in df.iloc[0].tolist() if str(v).lower() not in ("nan", "none", "")]
    k = len(categories)

    if k < 2:
        return ChartSpec(
            chart_type="chi_square_gof",
            title=cfg["title"],
            warnings=["Need at least 2 categories."],
        )

    observed = pd.to_numeric(df.iloc[1].iloc[:k], errors="coerce").fillna(0).values.astype(float)

    # Expected: from row 2, or uniform (equal expected)
    if len(df) >= 3:
        expected = pd.to_numeric(df.iloc[2].iloc[:k], errors="coerce").fillna(0).values.astype(float)
        # If expected sums to ~1, treat as proportions
        if 0.99 <= expected.sum() <= 1.01:
            expected = expected * observed.sum()
    else:
        expected = np.full(k, observed.sum() / k)

    warnings_list = []
    if np.any(expected < 5):
        warnings_list.append(
            "Some expected counts < 5; chi-square approximation may be unreliable."
        )

    # Chi-square test
    chi2, p_val = sp_stats.chisquare(observed, f_exp=expected)

    # Effect size: Cramér's V (reduces to phi for k=2)
    n_total = observed.sum()
    cramers_v = float(np.sqrt(chi2 / (n_total * max(k - 1, 1)))) if n_total > 0 else 0.0

    colors = resolve_colors(cfg["color"], k)

    return ChartSpec(
        chart_type="chi_square_gof",
        title=cfg["title"],
        x_axis=AxisSpec(label=cfg["xlabel"] or "Category"),
        y_axis=AxisSpec(label=cfg["ytitle"] or "Count"),
        style=StyleSpec(colors=colors, font_size=cfg["font_size"],
                        axis_style=cfg["axis_style"], gridlines=cfg["gridlines"]),
        data={
            "categories": categories,
            "observed": observed.tolist(),
            "expected": expected.tolist(),
            "chi2": round(float(chi2), 4),
            "chi2_p": float(p_val),
            "dof": k - 1,
            "cramers_v": round(cramers_v, 4),
            "n": int(n_total),
        },
        warnings=warnings_list,
    )
