"""Builds a Plotly figure spec for Stacked Bar charts."""

import json
import pandas as pd
from plotter_plotly_theme import PRISM_TEMPLATE, PRISM_PALETTE


def build_stacked_bar_spec(kw: dict) -> str:
    import plotly.graph_objects as go

    excel_path = kw.get("excel_path", "")
    sheet = kw.get("sheet", 0)
    title = kw.get("title", "")
    xlabel = kw.get("xlabel", "")
    ytitle = kw.get("ytitle", "")

    try:
        df = pd.read_excel(excel_path, sheet_name=sheet, header=[0, 1])
    except Exception as e:
        return json.dumps({"error": str(e)})

    # MultiIndex columns: level 0 = category, level 1 = subgroup
    categories = df.columns.get_level_values(0).unique().tolist()
    subgroups = df.columns.get_level_values(1).unique().tolist()

    # Build means per (category, subgroup)
    # df shape: rows = replicates, cols = MultiIndex
    means = {}
    for cat in categories:
        means[cat] = {}
        for sg in subgroups:
            try:
                col = pd.to_numeric(df[(cat, sg)], errors="coerce").dropna()
                means[cat][sg] = float(col.mean()) if len(col) > 0 else 0.0
            except KeyError:
                means[cat][sg] = 0.0

    traces = []
    for sg_idx, sg in enumerate(subgroups):
        color = PRISM_PALETTE[sg_idx % len(PRISM_PALETTE)]
        y_vals = [means[cat][sg] for cat in categories]
        traces.append(go.Bar(
            name=sg,
            x=categories,
            y=y_vals,
            marker_color=color,
        ))

    fig = go.Figure(data=traces, layout=go.Layout(
        template=PRISM_TEMPLATE,
        barmode="stack",
        title=dict(text=title),
        xaxis=dict(title=xlabel),
        yaxis=dict(title=ytitle),
        legend=dict(title=dict(text="")),
    ))
    return fig.to_json()
