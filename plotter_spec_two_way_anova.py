"""Builds a Plotly figure spec for a Two-Way ANOVA interaction plot."""

import json
import pandas as pd
from plotter_plotly_theme import PRISM_TEMPLATE, PRISM_PALETTE


def build_two_way_anova_spec(kw: dict) -> str:
    import plotly.graph_objects as go

    excel_path = kw.get("excel_path", "")
    sheet = kw.get("sheet", 0)
    title = kw.get("title", "Two-Way ANOVA Interaction Plot")
    xlabel = kw.get("xlabel", "")
    ytitle = kw.get("ytitle", "Mean")

    try:
        df = pd.read_excel(excel_path, sheet_name=sheet, header=0)
    except Exception as e:
        return json.dumps({"error": str(e)})

    required = ["Factor_A", "Factor_B", "Value"]
    for col in required:
        if col not in df.columns:
            return json.dumps({"error": f"Missing column: {col}"})

    df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
    df = df.dropna(subset=["Value"])

    # Compute cell means: Factor_A x Factor_B
    grouped = df.groupby(["Factor_A", "Factor_B"])["Value"].mean().reset_index()

    factor_a_levels = grouped["Factor_A"].unique().tolist()
    factor_b_levels = sorted(grouped["Factor_B"].unique().tolist(), key=str)
    x_label = xlabel or "Factor B"

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
        title=dict(text=title),
        xaxis=dict(title=x_label),
        yaxis=dict(title=ytitle),
    ))
    return fig.to_json()
