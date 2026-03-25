"""Contingency table analyzer — renderer-independent.

Reads a contingency table from Excel (Row 0 = outcome labels in cols 1+,
Col 0 = group names in rows 1+, body = counts) and produces a ChartSpec
with chi-square test, Fisher's exact test (2x2), and standardized residuals.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats as sp_stats

from refraction.analysis.schema import AxisSpec, ChartSpec, StyleSpec
from refraction.analysis.helpers import read_data, resolve_colors, extract_config


def analyze_contingency(kw: dict) -> ChartSpec:
    """Analyze contingency table data and return a ChartSpec."""
    cfg = extract_config(kw)
    df = read_data(cfg["excel_path"], cfg["sheet"])

    cols = list(df.columns)
    if len(cols) < 2:
        return ChartSpec(
            chart_type="contingency",
            title=cfg["title"],
            warnings=["Contingency table requires at least 2 columns."],
        )

    group_col = cols[0]
    outcome_cols = cols[1:]
    groups = df[group_col].tolist()
    outcomes = [str(c) for c in outcome_cols]

    # Build observed count matrix
    observed = df[outcome_cols].apply(pd.to_numeric, errors="coerce").fillna(0).values.astype(float)

    n_rows, n_cols = observed.shape
    warnings_list = []

    # Chi-square test of independence
    chi2, p_chi2, dof, expected = sp_stats.chi2_contingency(observed)

    # Standardized residuals: (O - E) / sqrt(E)
    with np.errstate(divide="ignore", invalid="ignore"):
        std_residuals = np.where(expected > 0, (observed - expected) / np.sqrt(expected), 0.0)

    # Cramér's V effect size
    n_total = observed.sum()
    min_dim = min(n_rows, n_cols) - 1
    cramers_v = float(np.sqrt(chi2 / (n_total * min_dim))) if n_total > 0 and min_dim > 0 else 0.0

    # Fisher's exact test for 2x2 tables
    fisher_p = None
    fisher_or = None
    if n_rows == 2 and n_cols == 2:
        fisher_or_val, fisher_p_val = sp_stats.fisher_exact(observed.astype(int))
        fisher_p = float(fisher_p_val)
        fisher_or = float(fisher_or_val)
        # Warn if expected counts < 5 (chi-square approximation unreliable)
        if np.any(expected < 5):
            warnings_list.append(
                "Some expected counts < 5; Fisher's exact test is more reliable "
                "than chi-square for this table."
            )

    elif np.any(expected < 5):
        warnings_list.append(
            "Some expected counts < 5; chi-square approximation may be unreliable."
        )

    colors = resolve_colors(cfg["color"], len(groups))

    return ChartSpec(
        chart_type="contingency",
        title=cfg["title"],
        x_axis=AxisSpec(label=cfg["xlabel"] or "Outcome"),
        y_axis=AxisSpec(label=cfg["ytitle"] or "Group"),
        style=StyleSpec(colors=colors, font_size=cfg["font_size"],
                        axis_style=cfg["axis_style"], gridlines=cfg["gridlines"]),
        data={
            "groups": [str(g) for g in groups],
            "outcomes": outcomes,
            "observed": observed.tolist(),
            "expected": expected.tolist(),
            "std_residuals": std_residuals.tolist(),
            "chi2": round(float(chi2), 4),
            "chi2_p": float(p_chi2),
            "dof": int(dof),
            "cramers_v": round(cramers_v, 4),
            "fisher_p": fisher_p,
            "fisher_odds_ratio": fisher_or,
        },
        warnings=warnings_list,
    )
