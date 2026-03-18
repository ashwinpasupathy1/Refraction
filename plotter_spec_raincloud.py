"""Builds a Plotly figure spec for raincloud plots from plotter kwargs."""

import json
import random
import pandas as pd
from plotter_plotly_theme import PRISM_TEMPLATE, PRISM_PALETTE


def build_raincloud_spec(kw: dict) -> str:
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

    rng = random.Random(42)
    traces = []

    for i, g in enumerate(groups):
        vals = df[g].dropna().tolist()
        c = colors[i % len(colors)]

        # Half violin (positive/right side only)
        traces.append(go.Violin(
            x=[g] * len(vals),
            y=vals,
            name=g,
            side="positive",
            line_color=c,
            fillcolor=c,
            opacity=0.6,
            box_visible=False,
            meanline_visible=False,
            points=False,
            showlegend=False,
            width=0.8,
        ))

        # Box overlay (narrow)
        traces.append(go.Box(
            x=[g] * len(vals),
            y=vals,
            name=g,
            marker_color=c,
            line_color=c,
            boxpoints=False,
            width=0.08,
            showlegend=False,
        ))

        # Jittered scatter (rain drops)
        x_jitter = [g + rng.uniform(0.05, 0.25) for _ in vals]
        traces.append(go.Scatter(
            x=x_jitter,
            y=vals,
            mode="markers",
            name=g,
            marker=dict(color=c, size=5, opacity=0.55, line=dict(width=0)),
            showlegend=False,
        ))

    layout = go.Layout(
        template=PRISM_TEMPLATE,
        title=dict(text=title, font=dict(size=14)),
        xaxis=dict(title=xlabel),
        yaxis=dict(title=ytitle),
        violinmode="overlay",
        boxmode="overlay",
    )
    fig = go.Figure(data=traces, layout=layout)
    return fig.to_json()
