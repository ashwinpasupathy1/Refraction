"""Builds a Plotly figure spec for a bubble chart (XY + size)."""

import pandas as pd
from plotter_plotly_theme import PRISM_TEMPLATE, PRISM_PALETTE
from plotter_spec_helpers import extract_common_kw, read_excel_or_error, spec_error


def build_bubble_spec(kw: dict) -> str:
    import plotly.graph_objects as go
    import numpy as np

    ck = extract_common_kw(kw)
    df, err = read_excel_or_error(ck["excel_path"], ck["sheet"])
    if err:
        return err

    if df.shape[1] < 3:
        return spec_error("Bubble chart requires at least 3 columns: X, Y, Size.")

    col_names = df.columns.tolist()
    x_label = ck["xlabel"] or str(col_names[0])
    y_label = ck["ytitle"] or str(col_names[1])
    size_label = str(col_names[2])

    x = pd.to_numeric(df.iloc[:, 0], errors="coerce")
    y = pd.to_numeric(df.iloc[:, 1], errors="coerce")
    s = pd.to_numeric(df.iloc[:, 2], errors="coerce")

    mask = x.notna() & y.notna() & s.notna()
    x, y, s = x[mask].values, y[mask].values, s[mask].values

    if len(s) > 0:
        s_min, s_max = s.min(), s.max()
        if s_max > s_min:
            sizes = 10 + (s - s_min) / (s_max - s_min) * 50
        else:
            sizes = np.full_like(s, 30.0)
    else:
        sizes = s

    color = PRISM_PALETTE[0]

    traces = [go.Scatter(
        x=x.tolist(),
        y=y.tolist(),
        mode="markers",
        marker=dict(
            size=sizes.tolist(),
            color=color,
            opacity=0.7,
            line=dict(width=1, color="white"),
            sizemode="diameter",
        ),
        text=[f"{size_label}: {v:.3g}" for v in s],
        hovertemplate=f"{x_label}: %{{x}}<br>{y_label}: %{{y}}<br>%{{text}}<extra></extra>",
        name="",
    )]

    fig = go.Figure(data=traces, layout=go.Layout(
        template=PRISM_TEMPLATE,
        title=dict(text=ck["title"]),
        xaxis=dict(title=x_label),
        yaxis=dict(title=y_label),
    ))
    return fig.to_json()
