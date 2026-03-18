"""Builds a Plotly figure spec for Waterfall charts."""

import json
import pandas as pd
from plotter_plotly_theme import PRISM_TEMPLATE, PRISM_PALETTE


def build_waterfall_spec(kw: dict) -> str:
    import plotly.graph_objects as go

    excel_path = kw.get("excel_path", "")
    sheet = kw.get("sheet", 0)
    title = kw.get("title", "")
    xlabel = kw.get("xlabel", "")
    ytitle = kw.get("ytitle", "")

    try:
        df = pd.read_excel(excel_path, sheet_name=sheet, header=0)
    except Exception as e:
        return json.dumps({"error": str(e)})

    # Each column = one category; use column means as waterfall values
    categories = list(df.columns)
    values = []
    for cat in categories:
        col = pd.to_numeric(df[cat], errors="coerce").dropna()
        values.append(float(col.mean()) if len(col) > 0 else 0.0)

    # Determine increasing/decreasing colors
    inc_color = PRISM_PALETTE[1]   # blue for positive
    dec_color = PRISM_PALETTE[0]   # red for negative

    traces = [go.Waterfall(
        name="",
        orientation="v",
        measure=["relative"] * len(categories),
        x=categories,
        y=values,
        connector=dict(line=dict(color="#888888", width=1, dash="dot")),
        increasing=dict(marker=dict(color=inc_color)),
        decreasing=dict(marker=dict(color=dec_color)),
        totals=dict(marker=dict(color=PRISM_PALETTE[2])),
        textposition="outside",
        text=[f"{v:+.3g}" for v in values],
    )]

    fig = go.Figure(data=traces, layout=go.Layout(
        template=PRISM_TEMPLATE,
        title=dict(text=title),
        xaxis=dict(title=xlabel),
        yaxis=dict(title=ytitle),
        showlegend=False,
    ))
    return fig.to_json()
