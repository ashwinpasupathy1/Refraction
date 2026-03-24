"""Builds a Plotly figure spec for a contingency table (grouped bar chart)."""

import pandas as pd
from refraction.specs.theme import PRISM_TEMPLATE, PRISM_PALETTE
from refraction.specs.helpers import extract_common_kw, read_excel_or_error


def build_contingency_spec(kw: dict) -> str:
    import plotly.graph_objects as go

    ck = extract_common_kw(kw, ytitle="Count")
    df, err = read_excel_or_error(ck["excel_path"], ck["sheet"], header=None)
    if err:
        return err

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
        title=dict(text=ck["title"]),
        xaxis=dict(title=ck["xlabel"]),
        yaxis=dict(title=ck["ytitle"]),
        barmode="group",
    ))
    return fig.to_json()
