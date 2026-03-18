"""Builds a Plotly figure spec for a heatmap."""

import json
import pandas as pd
from plotter_plotly_theme import PRISM_TEMPLATE, PRISM_PALETTE


def build_heatmap_spec(kw: dict) -> str:
    import plotly.graph_objects as go

    excel_path = kw.get("excel_path", "")
    sheet = kw.get("sheet", 0)
    title = kw.get("title", "")
    xlabel = kw.get("xlabel", "")
    ytitle = kw.get("ytitle", "")

    try:
        df = pd.read_excel(excel_path, sheet_name=sheet, header=None)
    except Exception as e:
        return json.dumps({"error": str(e)})

    # Row 0: blank, then column labels. Rows 1+: row label, then values.
    col_labels = [str(c) for c in df.iloc[0, 1:].tolist()]
    row_labels = [str(r) for r in df.iloc[1:, 0].tolist()]
    z = df.iloc[1:, 1:].apply(pd.to_numeric, errors="coerce").values.tolist()

    # Build text annotations
    text = []
    for row in z:
        text.append([f"{v:.2g}" if v is not None and pd.notna(v) else "" for v in row])

    traces = [go.Heatmap(
        z=z,
        x=col_labels,
        y=row_labels,
        colorscale="RdBu_r",
        text=text,
        texttemplate="%{text}",
        textfont=dict(size=11),
        hoverongaps=False,
    )]

    fig = go.Figure(data=traces, layout=go.Layout(
        template=PRISM_TEMPLATE,
        title=dict(text=title),
        xaxis=dict(title=xlabel),
        yaxis=dict(title=ytitle, autorange="reversed"),
    ))
    return fig.to_json()
