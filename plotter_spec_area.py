"""Builds a Plotly figure spec for Area charts."""

import json
import pandas as pd
from plotter_plotly_theme import PRISM_TEMPLATE, PRISM_PALETTE


def build_area_spec(kw: dict) -> str:
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

    cols = list(df.columns)
    if len(cols) < 2:
        return json.dumps({"error": "Area chart needs at least 2 columns (X + one Y series)."})

    x_col = cols[0]
    y_cols = cols[1:]
    x_vals = pd.to_numeric(df[x_col], errors="coerce").tolist()

    traces = []
    for i, y_col in enumerate(y_cols):
        color = PRISM_PALETTE[i % len(PRISM_PALETTE)]
        y_vals = pd.to_numeric(df[y_col], errors="coerce").tolist()
        fill = "tozeroy" if i == 0 else "tonexty"
        traces.append(go.Scatter(
            x=x_vals,
            y=y_vals,
            mode="lines",
            name=str(y_col),
            fill=fill,
            line=dict(color=color, width=1.5),
            fillcolor=color.replace("#", "rgba(").rstrip(")") if False else color,
            opacity=0.6,
        ))

    fig = go.Figure(data=traces, layout=go.Layout(
        template=PRISM_TEMPLATE,
        title=dict(text=title),
        xaxis=dict(title=xlabel if xlabel else str(x_col)),
        yaxis=dict(title=ytitle),
        legend=dict(title=dict(text="")),
    ))
    return fig.to_json()
