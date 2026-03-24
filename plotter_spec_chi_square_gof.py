"""Builds a Plotly figure spec for Chi-Square goodness-of-fit (observed vs expected)."""

import pandas as pd
from plotter_plotly_theme import PRISM_TEMPLATE, PRISM_PALETTE
from plotter_spec_helpers import extract_common_kw, read_excel_or_error


def build_chi_square_gof_spec(kw: dict) -> str:
    import plotly.graph_objects as go

    ck = extract_common_kw(kw, title="Chi-Square Goodness of Fit",
                           xlabel="Category", ytitle="Count")
    df, err = read_excel_or_error(ck["excel_path"], ck["sheet"], header=None)
    if err:
        return err

    # Row 0: category names. Row 1: observed counts. Row 2 (optional): expected.
    categories = [str(c) for c in df.iloc[0].tolist()]
    observed = pd.to_numeric(df.iloc[1], errors="coerce").fillna(0).tolist()

    if df.shape[0] >= 3:
        expected = pd.to_numeric(df.iloc[2], errors="coerce").tolist()
        # Fill missing expected with uniform distribution
        total_obs = sum(observed)
        n_cats = len(categories)
        expected = [
            e if pd.notna(e) else (total_obs / n_cats if n_cats > 0 else 0)
            for e in expected
        ]
    else:
        total_obs = sum(observed)
        n_cats = len(categories)
        uniform = total_obs / n_cats if n_cats > 0 else 0
        expected = [uniform] * n_cats

    color_obs = PRISM_PALETTE[0]
    color_exp = PRISM_PALETTE[1]

    traces = [
        go.Bar(
            name="Observed",
            x=categories,
            y=observed,
            marker_color=color_obs,
        ),
        go.Bar(
            name="Expected",
            x=categories,
            y=expected,
            marker_color=color_exp,
            marker_pattern_shape="/",
        ),
    ]

    fig = go.Figure(data=traces, layout=go.Layout(
        template=PRISM_TEMPLATE,
        title=dict(text=ck["title"]),
        xaxis=dict(title=ck["xlabel"]),
        yaxis=dict(title=ck["ytitle"]),
        barmode="group",
    ))
    return fig.to_json()
