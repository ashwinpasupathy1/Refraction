"""Builds a Plotly figure spec for Lollipop charts."""

import pandas as pd
from refraction.specs.theme import PRISM_TEMPLATE, PRISM_PALETTE
from refraction.specs.helpers import extract_common_kw, read_excel_or_error
from refraction.core.stats import calc_mean


def build_lollipop_spec(kw: dict) -> str:
    import plotly.graph_objects as go

    ck = extract_common_kw(kw)
    df, err = read_excel_or_error(ck["excel_path"], ck["sheet"])
    if err:
        return err

    groups = list(df.columns)
    x_positions = list(range(len(groups)))
    traces = []

    means = []
    for g in groups:
        col = pd.to_numeric(df[g], errors="coerce").dropna().tolist()
        means.append(calc_mean(col))

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
        title=dict(text=ck["title"]),
        xaxis=dict(
            title=ck["xlabel"],
            tickvals=x_positions,
            ticktext=groups,
        ),
        yaxis=dict(title=ck["ytitle"]),
    ))
    return fig.to_json()
