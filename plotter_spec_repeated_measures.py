"""Builds a Plotly figure spec for Repeated Measures charts."""

import json
import numpy as np
import pandas as pd
from plotter_plotly_theme import PRISM_TEMPLATE, PRISM_PALETTE


def build_repeated_measures_spec(kw: dict) -> str:
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

    timepoints = list(df.columns)
    x_positions = list(range(len(timepoints)))
    traces = []

    # One line per subject
    for i, row in df.iterrows():
        vals = [row[t] for t in timepoints]
        if all(pd.isna(v) for v in vals):
            continue
        traces.append(go.Scatter(
            x=x_positions,
            y=vals,
            mode="lines+markers",
            line=dict(color="grey", width=1),
            marker=dict(color="grey", size=5),
            opacity=0.35,
            showlegend=False,
            hoverinfo="skip",
        ))

    # Mean line with SEM error bars
    means, sems = [], []
    for t in timepoints:
        col = pd.to_numeric(df[t], errors="coerce").dropna()
        means.append(col.mean() if len(col) > 0 else float("nan"))
        sems.append(col.sem() if len(col) > 1 else 0.0)

    traces.append(go.Scatter(
        x=x_positions,
        y=means,
        mode="lines+markers",
        line=dict(color=PRISM_PALETTE[0], width=2),
        marker=dict(color=PRISM_PALETTE[0], size=10),
        error_y=dict(
            type="data",
            array=sems,
            visible=True,
            color=PRISM_PALETTE[0],
            thickness=1.5,
        ),
        name="Mean ± SEM",
        showlegend=True,
    ))

    fig = go.Figure(data=traces, layout=go.Layout(
        template=PRISM_TEMPLATE,
        title=dict(text=title),
        xaxis=dict(
            title=xlabel,
            tickvals=x_positions,
            ticktext=timepoints,
        ),
        yaxis=dict(title=ytitle),
    ))
    return fig.to_json()
