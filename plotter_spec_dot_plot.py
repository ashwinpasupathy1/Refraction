"""Builds a Plotly figure spec for dot/strip plots from plotter kwargs."""

import json
import random
import pandas as pd
from plotter_plotly_theme import PRISM_TEMPLATE, PRISM_PALETTE


def build_dot_plot_spec(kw: dict) -> str:
    import plotly.graph_objects as go

    excel_path = kw.get("excel_path", "")
    sheet = kw.get("sheet", 0)
    color = kw.get("color", None)
    title = kw.get("title", "")
    xlabel = kw.get("xlabel", "")
    ytitle = kw.get("ytitle", "")
    jitter_width = kw.get("jitter", 0.15)

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
        x_jitter = [i + rng.uniform(-jitter_width, jitter_width) for _ in vals]
        traces.append(go.Scatter(
            x=x_jitter,
            y=vals,
            mode="markers",
            name=g,
            marker=dict(color=c, size=7, opacity=0.75, line=dict(width=0.5, color="white")),
            showlegend=False,
        ))

    layout = go.Layout(
        template=PRISM_TEMPLATE,
        title=dict(text=title, font=dict(size=14)),
        xaxis=dict(
            title=xlabel,
            tickmode="array",
            tickvals=list(range(len(groups))),
            ticktext=groups,
        ),
        yaxis=dict(title=ytitle),
    )
    fig = go.Figure(data=traces, layout=layout)
    return fig.to_json()
