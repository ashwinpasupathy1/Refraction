"""Builds a Plotly figure spec for a Bland-Altman agreement plot."""

import pandas as pd
from plotter_plotly_theme import PRISM_TEMPLATE, PRISM_PALETTE
from plotter_spec_helpers import extract_common_kw, read_excel_or_error, spec_error


def build_bland_altman_spec(kw: dict) -> str:
    import plotly.graph_objects as go
    import numpy as np

    ck = extract_common_kw(kw, title="Bland-Altman Plot",
                           xlabel="Mean of Methods", ytitle="Difference (A - B)")
    df, err = read_excel_or_error(ck["excel_path"], ck["sheet"])
    if err:
        return err

    cols = df.columns.tolist()
    if len(cols) < 2:
        return spec_error("Bland-Altman requires at least 2 columns.")

    a = pd.to_numeric(df.iloc[:, 0], errors="coerce").dropna()
    b = pd.to_numeric(df.iloc[:, 1], errors="coerce").dropna()
    n = min(len(a), len(b))
    a, b = a.iloc[:n].values, b.iloc[:n].values

    means = (a + b) / 2
    diffs = a - b
    mean_diff = float(np.mean(diffs))
    sd_diff = float(np.std(diffs, ddof=1))
    upper_loa = mean_diff + 1.96 * sd_diff
    lower_loa = mean_diff - 1.96 * sd_diff

    color = PRISM_PALETTE[0]

    traces = [go.Scatter(
        x=means.tolist(),
        y=diffs.tolist(),
        mode="markers",
        marker=dict(color=color, size=8, opacity=0.8),
        name="Observations",
    )]

    fig = go.Figure(data=traces, layout=go.Layout(
        template=PRISM_TEMPLATE,
        title=dict(text=ck["title"]),
        xaxis=dict(title=ck["xlabel"]),
        yaxis=dict(title=ck["ytitle"]),
    ))

    line_style = dict(color="#333333", width=1.5, dash="dash")
    fig.add_hline(y=mean_diff, line=dict(color="#333333", width=2),
                  annotation_text=f"Mean diff: {mean_diff:.3g}")
    fig.add_hline(y=upper_loa, line=line_style,
                  annotation_text=f"+1.96 SD: {upper_loa:.3g}")
    fig.add_hline(y=lower_loa, line=line_style,
                  annotation_text=f"-1.96 SD: {lower_loa:.3g}")

    return fig.to_json()
