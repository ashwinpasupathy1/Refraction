"""Chi-square goodness-of-fit analyzer -- renderer-independent.

Reads category names (row 0), observed counts (row 1), and optional expected
counts (row 2) from Excel.  Also accepts contingency-table layout (row 0 has
a blank first cell + outcome labels; rows 1+ have group labels + counts) and
collapses it by summing columns.

Produces a ChartSpec with chi-square statistic, p-value, and Cramer's V / phi
effect size.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats as sp_stats

from refraction.analysis.schema import AxisSpec, ChartSpec, StyleSpec
from refraction.analysis.helpers import read_data, resolve_colors, extract_config


# ------------------------------------------------------------------
# Layout detection helpers
# ------------------------------------------------------------------

def _detect_contingency_layout(df: pd.DataFrame) -> bool:
    """Return True if *df* looks like a contingency table.

    Contingency layout: row 0 has a blank/NaN in column 0 with text labels
    in cols 1+; rows 1+ have text labels in column 0 and numeric counts in
    cols 1+.
    """
    if df.shape[1] < 2 or df.shape[0] < 2:
        return False
    top_left = str(df.iloc[0, 0]).lower()
    if top_left not in ("nan", "none", ""):
        return False
    # Column 0 in data rows should be non-numeric (group labels)
    col0_vals = df.iloc[1:, 0]
    numeric_col0 = pd.to_numeric(col0_vals, errors="coerce")
    if numeric_col0.notna().all():
        return False
    return True


def _collapse_contingency_to_gof(df: pd.DataFrame):
    """Convert a contingency table into GoF categories + observed counts.

    The column headers (row 0, cols 1+) become the categories, and
    observed counts are the column sums of the numeric body.
    """
    categories = [
        str(v) for v in df.iloc[0, 1:].tolist()
        if str(v).lower() not in ("nan", "none", "")
    ]
    k = len(categories)
    body = df.iloc[1:, 1:1 + k]
    observed = body.apply(pd.to_numeric, errors="coerce").sum(axis=0).values.astype(float)
    return categories, observed


# ------------------------------------------------------------------
# Main analyzer
# ------------------------------------------------------------------

def analyze_chi_square_gof(kw: dict) -> ChartSpec:
    """Analyze chi-square goodness-of-fit data and return a ChartSpec."""
    cfg = extract_config(kw)
    df = read_data(cfg["excel_path"], cfg["sheet"], header=None, df=cfg.get("_df"))

    if len(df) < 2:
        return ChartSpec(
            chart_type="chi_square_gof",
            title=cfg["title"],
            warnings=["Need at least 2 rows: categories and observed counts."],
        )

    # ----------------------------------------------------------
    # Parse categories and observed counts from whichever layout
    # ----------------------------------------------------------
    expected = None

    if _detect_contingency_layout(df):
        # Contingency-table layout -- collapse by summing columns
        categories, observed = _collapse_contingency_to_gof(df)
        k = len(categories)
        # Uniform expected (no explicit expected row in this layout)
        expected = np.full(k, observed.sum() / k)
    else:
        # Standard GoF layout: row 0 = categories, row 1 = observed,
        # optional row 2 = expected counts / proportions
        categories = [
            str(v) for v in df.iloc[0].tolist()
            if str(v).lower() not in ("nan", "none", "")
        ]
        k = len(categories)

        if k >= 2:
            observed = (
                pd.to_numeric(df.iloc[1].iloc[:k], errors="coerce")
                .fillna(0)
                .values.astype(float)
            )

            if len(df) >= 3:
                expected = (
                    pd.to_numeric(df.iloc[2].iloc[:k], errors="coerce")
                    .fillna(0)
                    .values.astype(float)
                )
                # Treat proportions that sum to ~1 as relative weights
                if 0.99 <= expected.sum() <= 1.01:
                    expected = expected * observed.sum()
            else:
                expected = np.full(k, observed.sum() / k)

    if k < 2:
        return ChartSpec(
            chart_type="chi_square_gof",
            title=cfg["title"],
            warnings=["Need at least 2 categories."],
        )

    # ----------------------------------------------------------
    # Warnings
    # ----------------------------------------------------------
    warnings_list: list[str] = []
    if np.any(expected < 5):
        warnings_list.append(
            "Some expected counts < 5; chi-square approximation may be unreliable."
        )

    # ----------------------------------------------------------
    # Chi-square test
    # ----------------------------------------------------------
    chi2, p_val = sp_stats.chisquare(observed, f_exp=expected)

    # Effect size: Cramer's V (reduces to phi for k=2)
    n_total = observed.sum()
    cramers_v = (
        float(np.sqrt(chi2 / (n_total * max(k - 1, 1)))) if n_total > 0 else 0.0
    )

    colors = resolve_colors(cfg["color"], k)

    return ChartSpec(
        chart_type="chi_square_gof",
        title=cfg["title"],
        x_axis=AxisSpec(label=cfg["xlabel"] or "Category"),
        y_axis=AxisSpec(label=cfg["ytitle"] or "Count"),
        style=StyleSpec(
            colors=colors,
            font_size=cfg["font_size"],
            axis_style=cfg["axis_style"],
            gridlines=cfg["gridlines"],
        ),
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
