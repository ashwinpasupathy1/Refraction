"""Forest plot analyzer — renderer-independent.

Reads tabular data with columns: Study, Effect, CI_lo, CI_hi (and optional
Weight) and produces a ChartSpec with study names, effect sizes, confidence
intervals, and a null reference line.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from refraction.analysis.schema import AxisSpec, ChartSpec, StyleSpec
from refraction.analysis.helpers import read_data, resolve_colors, extract_config


def analyze_forest_plot(kw: dict) -> ChartSpec:
    """Analyze forest plot data and return a ChartSpec.

    Data payload keys:
        studies: list[dict] — per-study data with keys:
            name, effect, ci_lo, ci_hi, weight (optional)
        null_value: float — reference line (typically 0 or 1)
        summary_effect: float | None — pooled estimate
        summary_ci: [float, float] | None — pooled CI
    """
    cfg = extract_config(kw)
    df = read_data(cfg["excel_path"], cfg["sheet"])

    # Expected columns: Study, Effect, CI_lo, CI_hi, (optional Weight)
    cols = list(df.columns)
    if len(cols) < 4:
        return ChartSpec(
            chart_type="forest_plot",
            title=cfg["title"],
            warnings=["Forest plot requires at least 4 columns: Study, Effect, CI_lo, CI_hi"],
        )

    study_col = cols[0]
    effect_col = cols[1]
    ci_lo_col = cols[2]
    ci_hi_col = cols[3]
    weight_col = cols[4] if len(cols) > 4 else None

    studies = []
    effects = []
    for _, row in df.iterrows():
        name = str(row[study_col])
        effect = float(row[effect_col])
        ci_lo = float(row[ci_lo_col])
        ci_hi = float(row[ci_hi_col])
        weight = float(row[weight_col]) if weight_col and pd.notna(row.get(weight_col)) else None

        studies.append({
            "name": name,
            "effect": effect,
            "ci_lo": ci_lo,
            "ci_hi": ci_hi,
            "weight": weight,
        })
        effects.append(effect)

    # Compute pooled summary (inverse-variance weighted mean)
    summary_effect = None
    summary_ci = None
    heterogeneity = None
    if len(studies) >= 2:
        effs = np.array([s["effect"] for s in studies])
        ci_widths = np.array([s["ci_hi"] - s["ci_lo"] for s in studies])
        # Approximate SE from CI width: SE ~ (CI_hi - CI_lo) / (2 * 1.96)
        ses = ci_widths / (2 * 1.96)
        ses = np.where(ses > 0, ses, 1.0)
        weights = 1.0 / (ses ** 2)
        summary_effect = float(np.sum(weights * effs) / np.sum(weights))
        summary_se = float(1.0 / np.sqrt(np.sum(weights)))
        summary_ci = [
            round(summary_effect - 1.96 * summary_se, 6),
            round(summary_effect + 1.96 * summary_se, 6),
        ]
        summary_effect = round(summary_effect, 6)

        # Cochran's Q and I² heterogeneity statistics
        k = len(effs)
        Q = float(np.sum(weights * (effs - summary_effect) ** 2))
        from scipy import stats as sp_stats
        Q_p = float(sp_stats.chi2.sf(Q, df=max(k - 1, 1)))
        I2 = max(0.0, (Q - (k - 1)) / Q) * 100.0 if Q > 0 else 0.0
        heterogeneity = {
            "Q": round(Q, 4),
            "Q_p": round(Q_p, 6),
            "I2": round(I2, 2),
            "df": k - 1,
        }

    # Determine null reference value (0 for mean differences, 1 for ratios)
    null_value = kw.get("null_value", 0.0)

    colors = resolve_colors(cfg["color"], len(studies))

    return ChartSpec(
        chart_type="forest_plot",
        title=cfg["title"],
        x_axis=AxisSpec(label=cfg["xlabel"] or "Effect Size"),
        y_axis=AxisSpec(label=cfg["ytitle"]),
        style=StyleSpec(
            colors=colors,
            alpha=cfg["alpha"],
            font_size=cfg["font_size"],
            axis_style=cfg["axis_style"],
            gridlines=cfg["gridlines"],
        ),
        data={
            "studies": studies,
            "null_value": null_value,
            "summary_effect": summary_effect,
            "summary_ci": summary_ci,
            "heterogeneity": heterogeneity,
        },
    )
