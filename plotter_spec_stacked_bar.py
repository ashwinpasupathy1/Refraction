"""Builds a Plotly figure spec for Stacked Bar charts."""

import pandas as pd
from plotter_plotly_theme import PRISM_TEMPLATE, PRISM_PALETTE
from plotter_spec_helpers import extract_common_kw, read_excel_or_error


def build_stacked_bar_spec(kw: dict) -> str:
    import plotly.graph_objects as go

    ck = extract_common_kw(kw)
    df, err = read_excel_or_error(ck["excel_path"], ck["sheet"], header=[0, 1])
    if err:
        return err

    # MultiIndex columns: level 0 = category, level 1 = subgroup
    categories = df.columns.get_level_values(0).unique().tolist()
    subgroups = df.columns.get_level_values(1).unique().tolist()

    # Build means per (category, subgroup)
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
        title=dict(text=ck["title"]),
        xaxis=dict(title=ck["xlabel"]),
        yaxis=dict(title=ck["ytitle"]),
        legend=dict(title=dict(text="")),
    ))
    return fig.to_json()
