"""Builds a Plotly figure spec for Subcolumn Scatter charts."""

import numpy as np
import pandas as pd
from refraction.specs.theme import PRISM_TEMPLATE, PRISM_PALETTE
from refraction.specs.helpers import extract_common_kw, read_excel_or_error


def build_subcolumn_spec(kw: dict) -> str:
    import plotly.graph_objects as go

    ck = extract_common_kw(kw)
    jitter_width = 0.15

    df, err = read_excel_or_error(ck["excel_path"], ck["sheet"])
    if err:
        return err

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
        title=dict(text=ck["title"]),
        xaxis=dict(
            title=ck["xlabel"],
            tickvals=list(range(len(groups))),
            ticktext=groups,
        ),
        yaxis=dict(title=ck["ytitle"]),
    ))
    return fig.to_json()
