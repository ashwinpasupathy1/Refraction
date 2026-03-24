"""Builds a Plotly figure spec for Repeated Measures charts."""

import pandas as pd
from refraction.specs.theme import PRISM_TEMPLATE, PRISM_PALETTE
from refraction.specs.helpers import extract_common_kw, read_excel_or_error
from refraction.core.stats import calc_mean, calc_sem


def build_repeated_measures_spec(kw: dict) -> str:
    import plotly.graph_objects as go

    ck = extract_common_kw(kw)
    df, err = read_excel_or_error(ck["excel_path"], ck["sheet"])
    if err:
        return err

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
        col = pd.to_numeric(df[t], errors="coerce").dropna().values.tolist()
        means.append(calc_mean(col))
        sems.append(calc_sem(col))

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
        name="Mean \u00b1 SEM",
        showlegend=True,
    ))

    fig = go.Figure(data=traces, layout=go.Layout(
        template=PRISM_TEMPLATE,
        title=dict(text=ck["title"]),
        xaxis=dict(
            title=ck["xlabel"],
            tickvals=x_positions,
            ticktext=timepoints,
        ),
        yaxis=dict(title=ck["ytitle"]),
    ))
    return fig.to_json()
