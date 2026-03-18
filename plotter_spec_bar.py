"""Builds a Plotly figure spec for bar charts from plotter kwargs."""

import json
import pandas as pd
from plotter_plotly_theme import PRISM_TEMPLATE, PRISM_PALETTE, apply_open_spine


def build_bar_spec(kw: dict) -> str:
    """Read Excel data and return a Plotly figure as JSON string.

    Args:
        kw: The same kwargs dict passed to prism_barplot().

    Returns:
        JSON string of a plotly.graph_objects.Figure.
    """
    import plotly.graph_objects as go

    excel_path = kw.get("excel_path", "")
    sheet = kw.get("sheet", 0)
    color = kw.get("color", None)
    title = kw.get("title", "")
    xlabel = kw.get("xlabel", "")
    ytitle = kw.get("ytitle", "")

    # Read data
    try:
        df = pd.read_excel(excel_path, sheet_name=sheet, header=0)
    except Exception as e:
        return json.dumps({"error": str(e)})

    groups = list(df.columns)
    values = {g: df[g].dropna().tolist() for g in groups}
    means = [sum(v) / len(v) if v else 0 for v in values.values()]

    # Colors
    if isinstance(color, list):
        colors = color
    elif isinstance(color, str):
        colors = [color] * len(groups)
    else:
        colors = PRISM_PALETTE[:len(groups)]

    # Build traces
    traces = []
    for i, (g, mean) in enumerate(zip(groups, means)):
        vals = values[g]
        sem = (sum((x - mean) ** 2 for x in vals) / len(vals)) ** 0.5 / (len(vals) ** 0.5) if len(vals) > 1 else 0
        traces.append(go.Bar(
            x=[g],
            y=[mean],
            name=g,
            marker_color=colors[i % len(colors)],
            error_y=dict(type="data", array=[sem], visible=True),
            showlegend=False,
        ))

    layout = go.Layout(
        template=PRISM_TEMPLATE,
        title=dict(text=title, font=dict(size=14)),
        xaxis=dict(title=xlabel),
        yaxis=dict(title=ytitle),
    )
    apply_open_spine(layout.to_plotly_json())

    fig = go.Figure(data=traces, layout=layout)
    return fig.to_json()
