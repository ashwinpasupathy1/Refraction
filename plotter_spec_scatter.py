"""Builds a Plotly figure spec for scatter plots."""

from plotter_plotly_theme import PRISM_TEMPLATE, PRISM_PALETTE
from plotter_spec_helpers import extract_common_kw, read_excel_or_error, spec_error


def build_scatter_spec(kw: dict) -> str:
    """Read Excel scatter data and return a Plotly figure as JSON string.

    Args:
        kw: The same kwargs dict passed to prism_scatterplot().

    Returns:
        JSON string of a plotly.graph_objects.Figure.
    """
    import plotly.graph_objects as go

    ck = extract_common_kw(kw)
    df, err = read_excel_or_error(ck["excel_path"], ck["sheet"])
    if err:
        return err

    if df.shape[1] < 2:
        return spec_error("Need at least 2 columns (X, Y)")

    x_col = df.columns[0]
    y_cols = df.columns[1:]
    x_vals = df[x_col].dropna().tolist()

    traces = []
    for i, col in enumerate(y_cols):
        y_vals = df[col].tolist()
        traces.append(go.Scatter(
            x=x_vals,
            y=y_vals,
            mode="markers",
            name=str(col),
            marker=dict(
                color=PRISM_PALETTE[i % len(PRISM_PALETTE)],
                size=8,
                opacity=0.8,
            ),
        ))

    fig = go.Figure(data=traces, layout=go.Layout(
        template=PRISM_TEMPLATE,
        title=dict(text=ck["title"]),
        xaxis=dict(title=ck["xlabel"]),
        yaxis=dict(title=ck["ytitle"]),
    ))
    return fig.to_json()
