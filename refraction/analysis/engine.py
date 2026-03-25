"""Renderer-independent analysis engine.

``analyze(chart_type, excel_path, config)`` reads data from an Excel file,
computes descriptive statistics (means, medians, errors) and runs the
requested statistical tests.  The return value is a plain dict that any
renderer can consume -- no Plotly, matplotlib, or UI dependencies.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Any

from refraction.core.chart_helpers import (
    _calc_error,
    _run_stats,
    _p_to_stars,
    PRISM_PALETTE,
)


def analyze(
    chart_type: str,
    excel_path: str,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run analysis for *chart_type* on *excel_path*.

    Parameters
    ----------
    chart_type : str
        One of the 29 known chart type keys (e.g. ``"bar"``, ``"box"``).
    excel_path : str
        Path to an ``.xlsx`` / ``.xls`` / ``.csv`` file.
    config : dict, optional
        Extra configuration.  Recognised keys:

        * ``sheet`` -- sheet name or 0-based index (default ``0``)
        * ``error_type`` -- ``"sem"`` | ``"sd"`` | ``"ci95"`` (default ``"sem"``)
        * ``stats_test`` -- ``"parametric"`` | ``"nonparametric"`` | ``"paired"`` |
          ``"permutation"`` | ``"one_sample"`` | ``"none"`` (default ``"none"``)
        * ``posthoc`` -- posthoc method string (default ``"Tukey HSD"``)
        * ``mc_correction`` -- multiple-comparisons correction (default
          ``"Holm-Bonferroni"``)
        * ``control`` -- control group name for Dunnett / vs-control tests
        * ``title``, ``x_label``, ``y_label`` -- forwarded in the result

    Returns
    -------
    dict
        Always contains ``"ok": True`` on success or ``"ok": False`` with
        ``"error"`` on failure.  On success the dict also contains:

        * ``chart_type`` -- echo of the requested type
        * ``groups`` -- list of ``{"name", "values", "mean", "median",
          "sd", "sem", "ci95", "n", "error", "error_type", "color"}`` dicts
        * ``comparisons`` -- list of ``{"group_a", "group_b", "p_value",
          "stars"}`` dicts (empty when ``stats_test`` is ``"none"``)
        * ``title``, ``x_label``, ``y_label``
    """
    cfg = config or {}

    # ------------------------------------------------------------------
    # Dispatch to dedicated analyzers for chart types that have them
    # ------------------------------------------------------------------
    if chart_type in _DEDICATED_ANALYZERS:
        try:
            kw = dict(cfg)
            kw["excel_path"] = excel_path
            spec = _DEDICATED_ANALYZERS[chart_type](kw)
            result = spec.to_dict()
            result["ok"] = True
            result["chart_type"] = chart_type
            # Ensure backward-compatible top-level 'groups' key
            if "groups" not in result and "data" in result:
                data = result["data"]
                if "groups" in data:
                    result["groups"] = data["groups"]
            return result
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # Generic analysis path (for chart types without dedicated analyzers)
    # ------------------------------------------------------------------
    sheet = cfg.get("sheet", 0)
    error_type = cfg.get("error_type", "sem")
    stats_test = cfg.get("stats_test", "none")
    posthoc = cfg.get("posthoc", "Tukey HSD")
    mc_correction = cfg.get("mc_correction", "Holm-Bonferroni")
    control = cfg.get("control", None)
    title = cfg.get("title", "")
    x_label = cfg.get("x_label", cfg.get("xlabel", ""))
    y_label = cfg.get("y_label", cfg.get("ytitle", ""))

    # ------------------------------------------------------------------
    # Read data
    # ------------------------------------------------------------------
    try:
        if excel_path.endswith(".csv"):
            df = pd.read_csv(excel_path)
        else:
            df = pd.read_excel(excel_path, sheet_name=sheet)
    except Exception as exc:
        return {"ok": False, "error": f"Failed to read file: {exc}"}

    # ------------------------------------------------------------------
    # Build groups (columns = groups, rows = observations)
    # ------------------------------------------------------------------
    try:
        groups_dict: dict[str, np.ndarray] = {}
        for col in df.columns:
            vals = pd.to_numeric(df[col], errors="coerce").dropna().values
            if len(vals) > 0:
                groups_dict[str(col)] = vals

        if not groups_dict:
            return {"ok": False, "error": "No numeric data found in file."}
    except Exception as exc:
        return {"ok": False, "error": f"Failed to parse data: {exc}"}

    # ------------------------------------------------------------------
    # Descriptive statistics per group
    # ------------------------------------------------------------------
    group_results = []
    for i, (name, vals) in enumerate(groups_dict.items()):
        mean_val, err_val = _calc_error(vals, error_type)
        sd = float(np.std(vals, ddof=1)) if len(vals) > 1 else 0.0
        sem = sd / np.sqrt(len(vals)) if len(vals) > 0 else 0.0
        from scipy import stats as sp_stats
        ci95 = sp_stats.t.ppf(0.975, df=len(vals) - 1) * sem if len(vals) > 1 else float("nan")

        group_results.append({
            "name": name,
            "values": vals.tolist(),
            "mean": float(np.mean(vals)),
            "median": float(np.median(vals)),
            "sd": sd,
            "sem": sem,
            "ci95": ci95,
            "n": len(vals),
            "error": err_val,
            "error_type": error_type,
            "color": PRISM_PALETTE[i % len(PRISM_PALETTE)],
        })

    # ------------------------------------------------------------------
    # Statistical comparisons
    # ------------------------------------------------------------------
    comparisons = []
    if stats_test != "none" and len(groups_dict) >= 2:
        try:
            raw = _run_stats(
                groups_dict,
                test_type=stats_test,
                posthoc=posthoc,
                mc_correction=mc_correction,
                control=control,
            )
            for tup in raw:
                comparisons.append({
                    "group_a": tup[0],
                    "group_b": tup[1],
                    "p_value": float(tup[2]),
                    "stars": tup[3],
                })
        except Exception as exc:
            comparisons = [{"error": str(exc)}]

    return {
        "ok": True,
        "chart_type": chart_type,
        "groups": group_results,
        "comparisons": comparisons,
        "title": title,
        "x_label": x_label,
        "y_label": y_label,
    }


# ------------------------------------------------------------------
# Dedicated analyzer dispatch table
# ------------------------------------------------------------------
def _lazy_load_analyzer(module_name: str, func_name: str):
    """Return a callable that lazily imports and calls the analyzer."""
    def _call(kw):
        import importlib
        mod = importlib.import_module(f"refraction.analysis.{module_name}")
        return getattr(mod, func_name)(kw)
    return _call


_DEDICATED_ANALYZERS = {
    "dot_plot": _lazy_load_analyzer("dot_plot", "analyze_dot_plot"),
    "kaplan_meier": _lazy_load_analyzer("kaplan_meier", "analyze_kaplan_meier"),
    "forest_plot": _lazy_load_analyzer("forest_plot", "analyze_forest_plot"),
    "raincloud": _lazy_load_analyzer("raincloud", "analyze_raincloud"),
    "contingency": _lazy_load_analyzer("contingency", "analyze_contingency"),
    "bland_altman": _lazy_load_analyzer("bland_altman", "analyze_bland_altman"),
    "chi_square_gof": _lazy_load_analyzer("chi_square_gof", "analyze_chi_square_gof"),
}


_ALL_CHART_TYPES = sorted([
    "bar", "grouped_bar", "line", "scatter",
    "box", "violin", "heatmap", "histogram",
    "kaplan_meier", "two_way_anova", "before_after",
    "subcolumn_scatter", "curve_fit", "column_stats",
    "contingency", "repeated_measures", "chi_square_gof",
    "stacked_bar", "bubble", "dot_plot", "bland_altman",
    "forest_plot", "area_chart", "raincloud", "qq_plot",
    "lollipop", "waterfall", "pyramid", "ecdf",
])


def available_chart_types() -> list[str]:
    """Return sorted list of all 29 supported chart type keys."""
    return list(_ALL_CHART_TYPES)
