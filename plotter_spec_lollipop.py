"""Builds a Plotly figure spec for Lollipop charts."""

import json
import pandas as pd
from plotter_plotly_theme import PRISM_TEMPLATE, PRISM_PALETTE


def build_lollipop_spec(kw: dict) -> str:
    import plotly.graph_objects as go

    excel_path = kw.get("excel_path", "")
    sheet = kw.get("sheet", 0)
    title = kw.get("title", "")
    xlabel = kw.get("xlabel", "")
    ytitle = kw.get("ytitle", "")

    try:
        df = pd.read_excel(excel_path, sheet_name=sheet, header=0)
    except Exception as e:
        return json.dumps({"error": str(e)})

    groups = list(df.columns)
    x_positions = list(range(len(groups)))
    traces = []

    means = []
    for g in groups:
        col = pd.to_numeric(df[g], errors="coerce").dropna()
        means.append(float(col.mean()) if len(col) > 0 else float("nan"))

    # Stem traces: one per group (vertical line from 0 to mean)
    for i, (g, mean_val) in enumerate(zip(groups, means)):
        color = PRISM_PALETTE[i % len(PRISM_PALETTE)]
        traces.append(go.Scatter(
            x=[i, i],
            y=[0, mean_val],
            mode="lines",
            line=dict(color=color, width=2),
            showlegend=False,
            hoverinfo="skip",
        ))

    # Dot traces: one per group (marker at mean)
    for i, (g, mean_val) in enumerate(zip(groups, means)):
        color = PRISM_PALETTE[i % len(PRISM_PALETTE)]
        traces.append(go.Scatter(
            x=[i],
            y=[mean_val],
            mode="markers",
            marker=dict(color=color, size=12, line=dict(color="white", width=1.5)),
            name=g,
            showlegend=True,
            hovertemplate=f"{g}: {mean_val:.3g}<extra></extra>",
        ))

    fig = go.Figure(data=traces, layout=go.Layout(
        template=PRISM_TEMPLATE,
        title=dict(text=title),
        xaxis=dict(
            title=xlabel,
            tickvals=x_positions,
            ticktext=groups,
        ),
        yaxis=dict(title=ytitle),
    ))
    return fig.to_json()
