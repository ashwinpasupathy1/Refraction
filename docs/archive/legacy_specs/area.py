"""Builds a Plotly figure spec for Area charts."""

import pandas as pd
from refraction.specs.theme import PRISM_TEMPLATE, PRISM_PALETTE
from refraction.specs.helpers import extract_common_kw, read_excel_or_error, spec_error


def build_area_spec(kw: dict) -> str:
    import plotly.graph_objects as go

    ck = extract_common_kw(kw)
    df, err = read_excel_or_error(ck["excel_path"], ck["sheet"])
    if err:
        return err

    cols = list(df.columns)
    if len(cols) < 2:
        return spec_error("Area chart needs at least 2 columns (X + one Y series).")

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
            fillcolor=color,
            opacity=0.6,
        ))

    fig = go.Figure(data=traces, layout=go.Layout(
        template=PRISM_TEMPLATE,
        title=dict(text=ck["title"]),
        xaxis=dict(title=ck["xlabel"] if ck["xlabel"] else str(x_col)),
        yaxis=dict(title=ck["ytitle"]),
        legend=dict(title=dict(text="")),
    ))
    return fig.to_json()
