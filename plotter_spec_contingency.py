"""Builds a Plotly figure spec for a contingency table (grouped bar chart)."""

import json
import pandas as pd
from plotter_plotly_theme import PRISM_TEMPLATE, PRISM_PALETTE


def build_contingency_spec(kw: dict) -> str:
    import plotly.graph_objects as go

    excel_path = kw.get("excel_path", "")
    sheet = kw.get("sheet", 0)
    title = kw.get("title", "")
    xlabel = kw.get("xlabel", "")
    ytitle = kw.get("ytitle", "Count")

    try:
        df = pd.read_excel(excel_path, sheet_name=sheet, header=None)
    except Exception as e:
        return json.dumps({"error": str(e)})

    # Row 0: blank, then outcome labels. Rows 1+: group name, then counts.
    outcome_labels = [str(c) for c in df.iloc[0, 1:].tolist()]
    group_names = [str(r) for r in df.iloc[1:, 0].tolist()]
    count_matrix = df.iloc[1:, 1:].apply(pd.to_numeric, errors="coerce").fillna(0)

    traces = []
    for i, outcome in enumerate(outcome_labels):
        color = PRISM_PALETTE[i % len(PRISM_PALETTE)]
        counts = count_matrix.iloc[:, i].tolist() if i < count_matrix.shape[1] else [0] * len(group_names)
        traces.append(go.Bar(
            name=outcome,
            x=group_names,
            y=counts,
            marker_color=color,
        ))

    fig = go.Figure(data=traces, layout=go.Layout(
        template=PRISM_TEMPLATE,
        title=dict(text=title),
        xaxis=dict(title=xlabel),
        yaxis=dict(title=ytitle),
        barmode="group",
    ))
    return fig.to_json()
