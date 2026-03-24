"""Builds a Plotly figure spec for a forest plot."""

import pandas as pd
from plotter_plotly_theme import PRISM_TEMPLATE, PRISM_PALETTE
from plotter_spec_helpers import extract_common_kw, read_excel_or_error, spec_error


def build_forest_plot_spec(kw: dict) -> str:
    import plotly.graph_objects as go

    ck = extract_common_kw(kw, title="Forest Plot", xlabel="Effect Size")
    df, err = read_excel_or_error(ck["excel_path"], ck["sheet"])
    if err:
        return err

    required = ["Study", "Effect", "Lower CI", "Upper CI"]
    for col in required:
        if col not in df.columns:
            return spec_error(f"Missing column: {col}")

    studies = df["Study"].astype(str).tolist()
    effects = pd.to_numeric(df["Effect"], errors="coerce").tolist()
    lower = pd.to_numeric(df["Lower CI"], errors="coerce").tolist()
    upper = pd.to_numeric(df["Upper CI"], errors="coerce").tolist()

    # Y positions: one per study, top-to-bottom
    y_positions = list(range(len(studies) - 1, -1, -1))
    error_x_minus = [e - l if pd.notna(e) and pd.notna(l) else 0
                     for e, l in zip(effects, lower)]
    error_x_plus = [u - e if pd.notna(e) and pd.notna(u) else 0
                    for e, u in zip(effects, upper)]

    color = PRISM_PALETTE[0]

    traces = [go.Scatter(
        x=effects,
        y=y_positions,
        mode="markers",
        marker=dict(symbol="square", size=10, color=color),
        error_x=dict(
            type="data",
            symmetric=False,
            array=error_x_plus,
            arrayminus=error_x_minus,
            color=color,
            thickness=2,
            width=6,
        ),
        name="Effect (95% CI)",
    )]

    fig = go.Figure(data=traces, layout=go.Layout(
        template=PRISM_TEMPLATE,
        title=dict(text=ck["title"]),
        xaxis=dict(title=ck["xlabel"]),
        yaxis=dict(
            title=ck["ytitle"],
            tickvals=y_positions,
            ticktext=studies,
            showgrid=False,
        ),
    ))

    # Vertical reference line at x=0 (null effect)
    fig.add_vline(x=0, line=dict(color="#888888", width=1, dash="dot"))

    return fig.to_json()
