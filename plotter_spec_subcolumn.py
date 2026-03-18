"""Builds a Plotly figure spec for Subcolumn Scatter charts."""

import json
import numpy as np
import pandas as pd
from plotter_plotly_theme import PRISM_TEMPLATE, PRISM_PALETTE


def build_subcolumn_spec(kw: dict) -> str:
    import plotly.graph_objects as go

    excel_path = kw.get("excel_path", "")
    sheet = kw.get("sheet", 0)
    title = kw.get("title", "")
    xlabel = kw.get("xlabel", "")
    ytitle = kw.get("ytitle", "")
    jitter_width = 0.15

    try:
        df = pd.read_excel(excel_path, sheet_name=sheet, header=0)
    except Exception as e:
        return json.dumps({"error": str(e)})

    groups = list(df.columns)
    traces = []

    rng = np.random.default_rng(42)

    for g_idx, group in enumerate(groups):
        color = PRISM_PALETTE[g_idx % len(PRISM_PALETTE)]
        vals = pd.to_numeric(df[group], errors="coerce").dropna().values
        if len(vals) == 0:
            continue

        jitter = rng.uniform(-jitter_width, jitter_width, size=len(vals))
        x_vals = [g_idx + j for j in jitter]

        # Individual points
        traces.append(go.Scatter(
            x=x_vals,
            y=vals.tolist(),
            mode="markers",
            marker=dict(color=color, size=7, opacity=0.7),
            name=group,
            legendgroup=group,
            showlegend=True,
        ))

        # Horizontal mean line
        mean_val = float(vals.mean())
        traces.append(go.Scatter(
            x=[g_idx - jitter_width * 2, g_idx + jitter_width * 2],
            y=[mean_val, mean_val],
            mode="lines",
            line=dict(color=color, width=2.5),
            legendgroup=group,
            showlegend=False,
            hovertemplate=f"{group} mean: {mean_val:.3g}<extra></extra>",
        ))

    fig = go.Figure(data=traces, layout=go.Layout(
        template=PRISM_TEMPLATE,
        title=dict(text=title),
        xaxis=dict(
            title=xlabel,
            tickvals=list(range(len(groups))),
            ticktext=groups,
        ),
        yaxis=dict(title=ytitle),
    ))
    return fig.to_json()
