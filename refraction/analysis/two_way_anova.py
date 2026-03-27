"""Dedicated analyzer for two-way ANOVA.

Reads long-format data with columns: Factor_A, Factor_B, Value.
Returns ChartSpec with interaction plot data and ANOVA table.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Any

from refraction.analysis.schema import AxisSpec, ChartSpec, StyleSpec
from refraction.analysis.helpers import extract_config
from refraction.core.chart_helpers import _twoway_anova
from refraction.core.config import PRISM_PALETTE


def analyze_two_way_anova(kw: dict[str, Any]) -> ChartSpec:
    """Analyze two-way ANOVA from long-format data."""
    cfg = extract_config(kw)
    excel_path = cfg["excel_path"]
    sheet = cfg["sheet"]

    if "_df" in cfg:
        df = cfg["_df"]
    elif excel_path.endswith(".csv"):
        df = pd.read_csv(excel_path)
    else:
        df = pd.read_excel(excel_path, sheet_name=sheet)

    # Expect 3 columns: Factor_A, Factor_B, Value
    if len(df.columns) < 3:
        raise ValueError("Two-way ANOVA requires at least 3 columns: Factor_A, Factor_B, Value")

    factor_a_col = str(df.columns[0])
    factor_b_col = str(df.columns[1])
    value_col = str(df.columns[2])

    # Run two-way ANOVA
    anova_result = _twoway_anova(df, value_col, factor_a_col, factor_b_col)

    # Compute cell means for interaction plot
    a_levels = sorted(df[factor_a_col].unique(), key=str)
    b_levels = sorted(df[factor_b_col].unique(), key=str)

    cell_means: dict[str, list[float]] = {}
    cell_sems: dict[str, list[float]] = {}

    for b_val in b_levels:
        means = []
        sems = []
        for a_val in a_levels:
            mask = (df[factor_a_col] == a_val) & (df[factor_b_col] == b_val)
            vals = df.loc[mask, value_col].dropna().astype(float)
            means.append(float(vals.mean()) if len(vals) > 0 else 0.0)
            sem = float(vals.std(ddof=1) / np.sqrt(len(vals))) if len(vals) > 1 else 0.0
            sems.append(sem)
        cell_means[str(b_val)] = means
        cell_sems[str(b_val)] = sems

    # Format ANOVA table for display
    # _twoway_anova returns keys matching column names + "interaction" + "residual"
    key_map = {
        factor_a_col: ("factor_a", factor_a_col),
        factor_b_col: ("factor_b", factor_b_col),
        "interaction": ("interaction", "Interaction"),
        "residual": ("residual", "Residual"),
    }
    anova_table = {}
    for raw_key, (out_key, label) in key_map.items():
        if raw_key in anova_result:
            r = anova_result[raw_key]
            anova_table[out_key] = {
                "label": label,
                "SS": round(r["SS"], 4),
                "df": r["df"],
                "MS": round(r["MS"], 4),
                "F": round(r["F"], 4) if r.get("F") else None,
                "p": round(r["p"], 6) if r.get("p") else None,
                "eta2_partial": round(r.get("eta2_partial", 0), 4),
            }

    colors = [PRISM_PALETTE[i % len(PRISM_PALETTE)] for i in range(len(b_levels))]

    return ChartSpec(
        chart_type="two_way_anova",
        title=cfg["title"],
        x_axis=AxisSpec(label=factor_a_col),
        y_axis=AxisSpec(label=value_col),
        style=StyleSpec(colors=colors),
        data={
            "factor_a": factor_a_col,
            "factor_b": factor_b_col,
            "a_levels": [str(v) for v in a_levels],
            "b_levels": [str(v) for v in b_levels],
            "cell_means": cell_means,
            "cell_sems": cell_sems,
            "anova_table": anova_table,
        },
    )
