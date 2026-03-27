"""Grouped bar chart analyzer — renderer-independent.

Reads two-row-header Excel data (row 0 = categories, row 1 = subgroups)
and produces a ChartSpec with per-(category, subgroup) means.
"""

from __future__ import annotations

import numpy as np

from refraction.analysis.schema import AxisSpec, ChartSpec, StyleSpec
from refraction.analysis.helpers import read_data, resolve_colors, extract_config


def analyze_grouped_bar(kw: dict) -> ChartSpec:
    """Analyze grouped bar chart data and return a ChartSpec.

    Data payload keys:
        categories: list[str] — category names (from row 0)
        subgroups: list[str] — subgroup names (from row 1)
        means: dict[str, list[float]] — subgroup -> list of means per category
        errors: dict[str, list[float]] — subgroup -> list of SEM per category
        error_type: str
    """
    cfg = extract_config(kw)
    df = read_data(cfg["excel_path"], cfg["sheet"], header=[0, 1], df=cfg.get("_df"))

    categories = list(df.columns.get_level_values(0).unique())
    subgroups = list(df.columns.get_level_values(1).unique())
    colors = resolve_colors(cfg["color"], len(subgroups))

    means: dict[str, list[float]] = {}
    errors: dict[str, list[float]] = {}

    for sg in subgroups:
        sg_means = []
        sg_errors = []
        for cat in categories:
            try:
                col_data = df[(cat, sg)].dropna().astype(float).tolist()
            except KeyError:
                col_data = []

            if col_data:
                arr = np.array(col_data)
                sg_means.append(float(np.mean(arr)))
                if len(arr) > 1:
                    sg_errors.append(float(np.std(arr, ddof=1) / np.sqrt(len(arr))))
                else:
                    sg_errors.append(0.0)
            else:
                sg_means.append(0.0)
                sg_errors.append(0.0)

        means[sg] = sg_means
        errors[sg] = sg_errors

    return ChartSpec(
        chart_type=kw.get("_chart_type", "grouped_bar"),
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
            bar_width=cfg["bar_width"],
            font_size=cfg["font_size"],
            axis_style=cfg["axis_style"],
            gridlines=cfg["gridlines"],
        ),
        data={
            "categories": categories,
            "subgroups": subgroups,
            "means": means,
            "errors": errors,
            "error_type": cfg["error_type"],
        },
    )
