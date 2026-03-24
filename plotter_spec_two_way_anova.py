"""Builds a Plotly figure spec for a Two-Way ANOVA interaction plot."""

import pandas as pd
from plotter_plotly_theme import PRISM_TEMPLATE, PRISM_PALETTE
from plotter_spec_helpers import extract_common_kw, read_excel_or_error, spec_error


def build_two_way_anova_spec(kw: dict) -> str:
    import plotly.graph_objects as go

    ck = extract_common_kw(kw, title="Two-Way ANOVA Interaction Plot", ytitle="Mean")
    df, err = read_excel_or_error(ck["excel_path"], ck["sheet"])
    if err:
        return err

    required = ["Factor_A", "Factor_B", "Value"]
    for col in required:
        if col not in df.columns:
            return spec_error(f"Missing column: {col}")

    df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
    df = df.dropna(subset=["Value"])

    # Compute cell means: Factor_A x Factor_B
    grouped = df.groupby(["Factor_A", "Factor_B"])["Value"].mean().reset_index()

    factor_a_levels = grouped["Factor_A"].unique().tolist()
    factor_b_levels = sorted(grouped["Factor_B"].unique().tolist(), key=str)
    x_label = ck["xlabel"] or "Factor B"

    traces = []
    for i, level_a in enumerate(factor_a_levels):
        subset = grouped[grouped["Factor_A"] == level_a].copy()
        subset = subset.set_index("Factor_B").reindex(factor_b_levels)
        color = PRISM_PALETTE[i % len(PRISM_PALETTE)]
        traces.append(go.Scatter(
            x=[str(b) for b in factor_b_levels],
            y=subset["Value"].tolist(),
            mode="lines+markers",
            name=str(level_a),
            line=dict(color=color, width=2),
            marker=dict(color=color, size=8),
        ))

    fig = go.Figure(data=traces, layout=go.Layout(
        template=PRISM_TEMPLATE,
        title=dict(text=ck["title"]),
        xaxis=dict(title=x_label),
        yaxis=dict(title=ck["ytitle"]),
    ))
    return fig.to_json()
