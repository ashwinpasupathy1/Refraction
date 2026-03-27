"""Before/After (paired) chart analyzer — renderer-independent.

Reads columnar Excel data where columns = timepoints and each row = one
subject's values across timepoints. Produces a ChartSpec with subject
trajectories, per-timepoint means and SEM.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from refraction.analysis.schema import AxisSpec, ChartSpec, StyleSpec
from refraction.analysis.helpers import read_data, resolve_colors, extract_config
from refraction.analysis.stats_annotator import build_stats_brackets
from refraction.analysis.results import build_results_section


def analyze_before_after(kw: dict) -> ChartSpec:
    """Analyze before/after data and return a ChartSpec.

    Data payload keys:
        timepoints: list[str] — column names (timepoint labels)
        trajectories: list[list[float | None]] — per-subject value lists
        means: list[float] — mean per timepoint
        sems: list[float] — SEM per timepoint
    """
    cfg = extract_config(kw)
    df = read_data(cfg["excel_path"], cfg["sheet"], df=cfg.get("_df"))

    timepoints = [str(c) for c in df.columns]
    colors = resolve_colors(cfg["color"], len(timepoints))

    # Extract subject trajectories (one list per row)
    trajectories: list[list[float | None]] = []
    for _, row in df.iterrows():
        vals = []
        for tp in df.columns:
            v = row[tp]
            if pd.isna(v):
                vals.append(None)
            else:
                vals.append(float(v))
        # Skip entirely-NaN rows
        if any(v is not None for v in vals):
            trajectories.append(vals)

    # Per-timepoint means and SEM
    means: list[float] = []
    sems: list[float] = []
    for col in df.columns:
        col_data = pd.to_numeric(df[col], errors="coerce").dropna()
        arr = col_data.values
        if len(arr) > 0:
            means.append(float(np.mean(arr)))
            if len(arr) > 1:
                sems.append(float(np.std(arr, ddof=1) / np.sqrt(len(arr))))
            else:
                sems.append(0.0)
        else:
            means.append(float("nan"))
            sems.append(0.0)

    # Stats brackets (treat timepoints as groups for paired tests)
    values = {}
    for col in df.columns:
        col_data = pd.to_numeric(df[col], errors="coerce").dropna().tolist()
        values[str(col)] = col_data

    brackets = build_stats_brackets(
        values, cfg["stats_test"], cfg["posthoc"], cfg["correction"]
    )

    # Results section (paired)
    results = build_results_section(values, paired=True)

    return ChartSpec(
        chart_type="before_after",
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
            line_width=cfg["line_width"],
            font_size=cfg["font_size"],
            axis_style=cfg["axis_style"],
            gridlines=cfg["gridlines"],
        ),
        data={
            "timepoints": timepoints,
            "trajectories": trajectories,
            "means": means,
            "sems": sems,
            "results": results,
        },
        stats=brackets,
    )
