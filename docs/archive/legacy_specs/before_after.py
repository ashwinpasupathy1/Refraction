"""Builds a Plotly figure spec for Before/After (paired) charts."""

import pandas as pd
from refraction.specs.theme import PRISM_TEMPLATE, PRISM_PALETTE
from refraction.specs.helpers import extract_common_kw, read_excel_or_error


def build_before_after_spec(kw: dict) -> str:
    import plotly.graph_objects as go

    ck = extract_common_kw(kw)
    df, err = read_excel_or_error(ck["excel_path"], ck["sheet"])
    if err:
        return err

    groups = [c for c in df.columns]
    n_groups = len(groups)
    x_positions = list(range(n_groups))

    traces = []

    # One line+markers trace per subject (row)
    for i, row in df.iterrows():
        vals = [row[g] for g in groups]
        if all(pd.isna(v) for v in vals):
            continue
        traces.append(go.Scatter(
            x=x_positions,
            y=vals,
            mode="lines+markers",
            line=dict(color="grey", width=1),
            marker=dict(color="grey", size=6),
            opacity=0.4,
            showlegend=False,
            hoverinfo="skip",
        ))

    # Mean markers per group
    means = []
    for g in groups:
        col = pd.to_numeric(df[g], errors="coerce").dropna()
        means.append(col.mean() if len(col) > 0 else float("nan"))

    traces.append(go.Scatter(
        x=x_positions,
        y=means,
        mode="markers",
        marker=dict(color=PRISM_PALETTE[0], size=12, symbol="circle"),
        name="Mean",
        showlegend=True,
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
