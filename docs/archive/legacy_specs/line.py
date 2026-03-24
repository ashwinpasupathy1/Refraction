"""Builds a Plotly figure spec for line graphs."""

from refraction.specs.theme import PRISM_TEMPLATE, PRISM_PALETTE
from refraction.specs.helpers import extract_common_kw, read_excel_or_error, spec_error


def build_line_spec(kw: dict) -> str:
    """Read Excel line data and return a Plotly figure as JSON string.

    Args:
        kw: The same kwargs dict passed to prism_linegraph().

    Returns:
        JSON string of a plotly.graph_objects.Figure.
    """
    import plotly.graph_objects as go

    ck = extract_common_kw(kw)
    df, err = read_excel_or_error(ck["excel_path"], ck["sheet"])
    if err:
        return err

    if df.shape[1] < 2:
        return spec_error("Need at least 2 columns (X, Y1)")

    x_col = df.columns[0]
    y_cols = df.columns[1:]

    traces = []
    for i, col in enumerate(y_cols):
        # Drop rows where either X or Y is NaN to keep arrays aligned
        pair = df[[x_col, col]].dropna()
        x_vals = pair[x_col].tolist()
        y_vals = pair[col].tolist()
        traces.append(go.Scatter(
            x=x_vals,
            y=y_vals,
            mode="lines+markers",
            name=str(col),
            line=dict(color=PRISM_PALETTE[i % len(PRISM_PALETTE)], width=2),
            marker=dict(size=6),
        ))

    fig = go.Figure(data=traces, layout=go.Layout(
        template=PRISM_TEMPLATE,
        title=dict(text=ck["title"]),
        xaxis=dict(title=ck["xlabel"]),
        yaxis=dict(title=ck["ytitle"]),
    ))
    return fig.to_json()
