"""Builds a Plotly figure spec for violin plots from plotter kwargs."""

import json
import pandas as pd
from plotter_plotly_theme import PRISM_TEMPLATE, PRISM_PALETTE


def build_violin_spec(kw: dict) -> str:
    import plotly.graph_objects as go

    excel_path = kw.get("excel_path", "")
    sheet = kw.get("sheet", 0)
    color = kw.get("color", None)
    title = kw.get("title", "")
    xlabel = kw.get("xlabel", "")
    ytitle = kw.get("ytitle", "")

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
        vals = df[g].dropna().tolist()
        c = colors[i % len(colors)]
        traces.append(go.Violin(
            y=vals,
            name=g,
            box_visible=True,
            meanline_visible=True,
            points="all",
            jitter=0.3,
            pointpos=0,
            line_color=c,
            fillcolor=c,
            opacity=0.7,
            marker=dict(size=4, opacity=0.5, color=c),
            showlegend=False,
        ))

    layout = go.Layout(
        template=PRISM_TEMPLATE,
        title=dict(text=title, font=dict(size=14)),
        xaxis=dict(title=xlabel),
        yaxis=dict(title=ytitle),
    )
    fig = go.Figure(data=traces, layout=layout)
    return fig.to_json()
