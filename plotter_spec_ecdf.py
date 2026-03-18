"""Builds a Plotly figure spec for ECDF plots from plotter kwargs."""

import json
import pandas as pd
from plotter_plotly_theme import PRISM_TEMPLATE, PRISM_PALETTE


def build_ecdf_spec(kw: dict) -> str:
    import plotly.graph_objects as go

    excel_path = kw.get("excel_path", "")
    sheet = kw.get("sheet", 0)
    color = kw.get("color", None)
    title = kw.get("title", "ECDF")
    xlabel = kw.get("xlabel", "Value")
    ytitle = kw.get("ytitle", "Cumulative Proportion")

    try:
        df = pd.read_excel(excel_path, sheet_name=sheet, header=0)
    except Exception as e:
        return json.dumps({"error": str(e)})

    groups = list(df.columns)

    if isinstance(color, list):
        colors = color
    elif isinstance(color, str):
        colors = [color] * len(groups)
    else:
        colors = PRISM_PALETTE[:len(groups)]

    traces = []
    for i, g in enumerate(groups):
        vals = sorted(df[g].dropna().tolist())
        n = len(vals)
        if n == 0:
            continue
        c = colors[i % len(colors)]
        proportions = [(j + 1) / n for j in range(n)]
        traces.append(go.Scatter(
            x=vals,
            y=proportions,
            mode="lines",
            name=g,
            line=dict(color=c, width=2, shape="hv"),
            showlegend=len(groups) > 1,
        ))

    layout = go.Layout(
        template=PRISM_TEMPLATE,
        title=dict(text=title, font=dict(size=14)),
        xaxis=dict(title=xlabel),
        yaxis=dict(title=ytitle, range=[0, 1]),
    )
    fig = go.Figure(data=traces, layout=layout)
    return fig.to_json()
