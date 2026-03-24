"""Builds a Plotly figure spec for grouped bar charts."""

import logging
from refraction.specs.theme import PRISM_TEMPLATE, PRISM_PALETTE
from refraction.specs.helpers import extract_common_kw, read_excel_or_error

_log = logging.getLogger(__name__)


def build_grouped_bar_spec(kw: dict) -> str:
    """Read Excel grouped bar data and return a Plotly figure as JSON string.

    Args:
        kw: The same kwargs dict passed to prism_grouped_barplot().

    Returns:
        JSON string of a plotly.graph_objects.Figure.
    """
    import plotly.graph_objects as go

    ck = extract_common_kw(kw)
    df, err = read_excel_or_error(ck["excel_path"], ck["sheet"], header=[0, 1])
    if err:
        return err

    # df has a MultiIndex column: (category, subgroup)
    categories = df.columns.get_level_values(0).unique().tolist()
    subgroups = df.columns.get_level_values(1).unique().tolist()

    traces = []
    for j, sg in enumerate(subgroups):
        y_vals = []
        for cat in categories:
            try:
                col_data = df[(cat, sg)].dropna()
                y_vals.append(col_data.mean() if len(col_data) > 0 else 0)
            except KeyError:
                _log.warning("Missing column (%s, %s) in grouped bar data — using 0", cat, sg)
                y_vals.append(0)
        traces.append(go.Bar(
            name=sg,
            x=categories,
            y=y_vals,
            marker_color=PRISM_PALETTE[j % len(PRISM_PALETTE)],
        ))

    fig = go.Figure(data=traces, layout=go.Layout(
        template=PRISM_TEMPLATE,
        barmode="group",
        title=dict(text=ck["title"]),
        xaxis=dict(title=ck["xlabel"]),
        yaxis=dict(title=ck["ytitle"]),
    ))
    return fig.to_json()
