"""Kaplan-Meier survival curve analyzer — renderer-independent.

Reads paired time/event columns from Excel (each group has two columns:
Time and Event where Event is 0=censored, 1=event) and produces a
ChartSpec with step-function survival curves and censoring marks.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from refraction.analysis.schema import AxisSpec, ChartSpec, StyleSpec
from refraction.analysis.helpers import read_data, resolve_colors, extract_config
from refraction.core.chart_helpers import _logrank_test


def _kaplan_meier_curve(times: np.ndarray, events: np.ndarray):
    """Compute Kaplan-Meier survival function S(t) = product(1 - d_i/n_i).

    Returns (sorted_times, survival_probs, censored_times, censored_probs).
    """
    order = np.argsort(times)
    times = times[order]
    events = events[order]

    unique_times = np.unique(times)
    n_at_risk = len(times)
    survival = 1.0

    curve_times = [0.0]
    curve_survival = [1.0]
    censored_t = []
    censored_s = []

    for t in unique_times:
        mask = times == t
        d_i = int(events[mask].sum())      # deaths at time t
        c_i = int((~events.astype(bool))[mask].sum())  # censored at time t

        if d_i > 0:
            survival *= (1 - d_i / n_at_risk)

        curve_times.append(float(t))
        curve_survival.append(survival)

        if c_i > 0:
            censored_t.append(float(t))
            censored_s.append(survival)

        n_at_risk -= (d_i + c_i)
        if n_at_risk <= 0:
            break

    return curve_times, curve_survival, censored_t, censored_s


def analyze_kaplan_meier(kw: dict) -> ChartSpec:
    """Analyze Kaplan-Meier survival data and return a ChartSpec.

    Data payload keys:
        curves: list[dict] — per-group survival curves with keys:
            name, times, survival, censored_times, censored_survival, n
    """
    cfg = extract_config(kw)
    df = read_data(cfg["excel_path"], cfg["sheet"], header=None, df=cfg.get("_df"))

    # Parse KM layout: Row 0 = group names (each spans 2 cols),
    # Row 1 = "Time", "Event" headers, Rows 2+ = data
    header_row = df.iloc[0].tolist()
    sub_header = df.iloc[1].tolist()
    data_rows = df.iloc[2:]

    # Identify groups from header (non-empty cells, spanning 2 cols)
    group_names = []
    group_cols = []
    i = 0
    while i < len(header_row):
        name = str(header_row[i]).strip()
        if name and name.lower() not in ("nan", "none", ""):
            group_names.append(name)
            group_cols.append(i)
        i += 2 if i + 1 < len(header_row) else 1

    colors = resolve_colors(cfg["color"], len(group_names))

    curves = []
    for gi, (name, col_start) in enumerate(zip(group_names, group_cols)):
        time_col = pd.to_numeric(data_rows.iloc[:, col_start], errors="coerce")
        event_col = pd.to_numeric(data_rows.iloc[:, col_start + 1], errors="coerce")

        # Prism convention: rows with a valid time are included.
        # Empty/NaN event values are treated as censored (0).
        valid_mask = time_col.notna()
        times = time_col[valid_mask].values
        events = event_col[valid_mask].fillna(0).values

        # Clamp events to 0/1 (anything > 0 is an event)
        events = (events > 0).astype(float)

        n = len(times)
        if n == 0:
            curves.append({
                "name": name,
                "times": [],
                "survival": [],
                "censored_times": [],
                "censored_survival": [],
                "n": 0,
                "color": colors[gi],
            })
            continue

        curve_t, curve_s, cens_t, cens_s = _kaplan_meier_curve(times, events)

        curves.append({
            "name": name,
            "times": curve_t,
            "survival": curve_s,
            "censored_times": cens_t,
            "censored_survival": cens_s,
            "n": n,
            "color": colors[gi],
        })

    # Log-rank (Mantel-Cox) pairwise tests between groups
    comparisons = []
    non_empty = [(c["name"], i) for i, c in enumerate(curves) if c["n"] > 0]
    if len(non_empty) >= 2:
        # Build groups_dict for _logrank_test: {name: (times, events)}
        lr_groups = {}
        for gi, (name, col_start) in enumerate(zip(group_names, group_cols)):
            time_col = data_rows.iloc[:, col_start]
            event_col = data_rows.iloc[:, col_start + 1]
            t = pd.to_numeric(time_col, errors="coerce").dropna().values
            e = pd.to_numeric(event_col, errors="coerce").dropna().values
            n = min(len(t), len(e))
            if n > 0:
                lr_groups[name] = (t[:n].astype(float), e[:n].astype(float))
        if len(lr_groups) >= 2:
            comparisons = [
                {"group_a": a, "group_b": b, "p_value": p, "stars": s}
                for a, b, p, s in _logrank_test(lr_groups)
            ]

    return ChartSpec(
        chart_type="kaplan_meier",
        title=cfg["title"],
        x_axis=AxisSpec(label=cfg["xlabel"] or "Time"),
        y_axis=AxisSpec(
            label=cfg["ytitle"] or "Survival Probability",
            scale="linear",
            limits=(0.0, 1.05),
        ),
        style=StyleSpec(
            colors=colors,
            alpha=cfg["alpha"],
            line_width=cfg["line_width"],
            font_size=cfg["font_size"],
            axis_style=cfg["axis_style"],
            gridlines=cfg["gridlines"],
        ),
        data={
            "curves": curves,
            "comparisons": comparisons,
        },
    )
