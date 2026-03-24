"""Builds a Plotly figure spec for Population Pyramid charts."""

import pandas as pd
from refraction.specs.theme import PRISM_TEMPLATE, PRISM_PALETTE
from refraction.specs.helpers import extract_common_kw, read_excel_or_error, spec_error


def build_pyramid_spec(kw: dict) -> str:
    import plotly.graph_objects as go

    ck = extract_common_kw(kw)
    df, err = read_excel_or_error(ck["excel_path"], ck["sheet"])
    if err:
        return err

    cols = list(df.columns)
    if len(cols) < 3:
        return spec_error("Pyramid chart needs 3 columns: Category, Left series, Right series.")

    cat_col, left_col, right_col = cols[0], cols[1], cols[2]

    categories = df[cat_col].astype(str).tolist()
    left_vals = pd.to_numeric(df[left_col], errors="coerce").fillna(0).tolist()
    right_vals = pd.to_numeric(df[right_col], errors="coerce").fillna(0).tolist()

    # Left bars are plotted as negative values
    left_neg = [-abs(v) for v in left_vals]

    traces = [
        go.Bar(
            name=str(left_col),
            x=left_neg,
            y=categories,
            orientation="h",
            marker_color=PRISM_PALETTE[0],
            hovertemplate="%{customdata:.3g}<extra>" + str(left_col) + "</extra>",
            customdata=left_vals,
        ),
        go.Bar(
            name=str(right_col),
            x=right_vals,
            y=categories,
            orientation="h",
            marker_color=PRISM_PALETTE[1],
            hovertemplate="%{x:.3g}<extra>" + str(right_col) + "</extra>",
        ),
    ]

    # Symmetric x-axis ticks using absolute values
    max_val = max(abs(v) for v in left_vals + right_vals) if (left_vals or right_vals) else 1

    fig = go.Figure(data=traces, layout=go.Layout(
        template=PRISM_TEMPLATE,
        barmode="relative",
        title=dict(text=ck["title"]),
        xaxis=dict(
            title=ck["xlabel"],
            tickvals=[-max_val, -max_val / 2, 0, max_val / 2, max_val],
            ticktext=[str(int(max_val)), str(int(max_val / 2)), "0",
                      str(int(max_val / 2)), str(int(max_val))],
        ),
        yaxis=dict(title=ck["ytitle"] if ck["ytitle"] else str(cat_col)),
        legend=dict(title=dict(text="")),
    ))
    return fig.to_json()
