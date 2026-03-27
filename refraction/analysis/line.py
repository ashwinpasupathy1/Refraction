"""Line graph analyzer — renderer-independent.

Reads XY Excel data (first column = X, remaining columns = Y series)
and produces a ChartSpec with per-series x and y arrays connected by lines.
"""

from __future__ import annotations

from refraction.analysis.schema import AxisSpec, ChartSpec, StyleSpec
from refraction.analysis.helpers import read_data, resolve_colors, extract_config


def analyze_line(kw: dict) -> ChartSpec:
    """Analyze line graph data and return a ChartSpec.

    Data payload keys:
        x_label: str — name of the X column
        series: list[dict] — per-series data with keys:
            name: str — series/column name
            x: list[float] — X values
            y: list[float] — Y values
    """
    cfg = extract_config(kw)
    df = read_data(cfg["excel_path"], cfg["sheet"], df=cfg.get("_df"))

    if df.shape[1] < 2:
        raise ValueError("Line graph requires at least 2 columns (X, Y)")

    x_col = df.columns[0]
    y_cols = df.columns[1:]
    x_vals = df[x_col].dropna().astype(float).tolist()
    colors = resolve_colors(cfg["color"], len(y_cols))

    series = []
    for col in y_cols:
        y_vals = df[col].dropna().astype(float).tolist()
        n = min(len(x_vals), len(y_vals))
        series.append({
            "name": str(col),
            "x": x_vals[:n],
            "y": y_vals[:n],
        })

    return ChartSpec(
        chart_type="line",
        title=cfg["title"],
        x_axis=AxisSpec(label=cfg["xlabel"] or str(x_col)),
        y_axis=AxisSpec(
            label=cfg["ytitle"],
            scale=cfg["yscale"],
            limits=cfg["ylim"],
        ),
        style=StyleSpec(
            colors=colors,
            line_width=cfg["line_width"],
            point_size=cfg["point_size"],
            font_size=cfg["font_size"],
            axis_style=cfg["axis_style"],
            gridlines=cfg["gridlines"],
        ),
        data={
            "x_label": str(x_col),
            "series": series,
        },
    )
