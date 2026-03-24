"""Bar chart analyzer — produces a ChartSpec from raw data.

Reads an Excel file (flat header layout) and computes group summaries,
error bars, axis ranges, and optional statistical annotations.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from refraction.analysis.schema import (
    Annotations, Axes, ChartSpec, GroupData, Style,
)
from refraction.analysis.helpers import resolve_colors, extract_config
from refraction.analysis import stats_annotator


def _calc_error(vals: np.ndarray, error_type: str) -> float:
    """Return the half-width of the error bar for *vals*."""
    clean = vals[~np.isnan(vals)]
    n = len(clean)
    if n < 2:
        return 0.0
    sd = float(np.std(clean, ddof=1))
    if error_type == "SD":
        return sd
    if error_type == "CI95":
        from scipy import stats as sp_stats
        se = sd / math.sqrt(n)
        t_crit = sp_stats.t.ppf(0.975, df=n - 1)
        return se * t_crit
    # default: SEM
    return sd / math.sqrt(n)


def analyze_bar(excel_path: str, **kw) -> ChartSpec:
    """Analyze bar-chart data and return a renderer-independent ChartSpec.

    Parameters
    ----------
    excel_path : path to .xlsx with flat header layout
    **kw : optional overrides (sheet, color, title, xlabel, ytitle,
           error_type, show_points, stats_test, ...)
    """
    cfg = extract_config(kw)
    sheet = cfg.get("sheet", 0)
    color = cfg.get("color", None)
    error_type = cfg.get("error_type", "SEM")
    show_points = cfg.get("show_points", False)
    stats_test = cfg.get("stats_test", None)

    # ── Read data ─────────────────────────────────────────────────────────────
    df = pd.read_excel(excel_path, sheet_name=sheet, header=None)
    headers = [str(c).strip() for c in df.iloc[0]]
    n_groups = len(headers)
    colors = resolve_colors(color, n_groups)

    groups_dict: Dict[str, np.ndarray] = {}
    group_data_list: List[dict] = []

    for i, name in enumerate(headers):
        raw = pd.to_numeric(df.iloc[1:, i], errors="coerce")
        vals = np.array(raw.dropna(), dtype=float)
        groups_dict[name] = vals

        mean_val = float(np.nanmean(vals)) if len(vals) > 0 else 0.0
        err = _calc_error(vals, error_type)

        gd = {
            "name": name,
            "mean": mean_val,
            "error": err,
            "error_type": error_type,
            "n": len(vals),
            "color": colors[i],
        }
        if show_points:
            gd["raw_points"] = [float(v) for v in vals]
        group_data_list.append(gd)

    # ── Axis range ────────────────────────────────────────────────────────────
    all_means = [g["mean"] for g in group_data_list]
    all_errors = [g["error"] for g in group_data_list]
    if all_means:
        y_min = min(m - e for m, e in zip(all_means, all_errors))
        y_max = max(m + e for m, e in zip(all_means, all_errors))
        suggested_range = [min(0.0, y_min), y_max * 1.15]
    else:
        suggested_range = [0.0, 1.0]

    # ── Stats ─────────────────────────────────────────────────────────────────
    brackets, normality = stats_annotator.annotate(
        groups_dict, stats_test=stats_test,
    )

    # ── Assemble spec ─────────────────────────────────────────────────────────
    spec = ChartSpec(
        chart_type="bar",
        data={"groups": group_data_list},
        axes=Axes(
            xlabel=cfg.get("xlabel", ""),
            ylabel=cfg.get("ylabel", ""),
            title=cfg.get("title", ""),
            suggested_range=suggested_range,
        ),
        style=Style(
            show_points=show_points,
            error_bar_type=error_type,
        ),
        annotations=Annotations(
            brackets=brackets,
            normality=normality,
        ),
    )
    return spec
