"""Builds a Plotly figure spec for bar charts from plotter kwargs."""

from refraction.specs.theme import PRISM_TEMPLATE, apply_open_spine
from refraction.specs.helpers import extract_common_kw, read_excel_or_error, resolve_colors
from refraction.core.stats import calc_mean, calc_sem


def build_bar_spec(kw: dict) -> str:
    """Read Excel data and return a Plotly figure as JSON string.

    Args:
        kw: The same kwargs dict passed to prism_barplot().

    Returns:
        JSON string of a plotly.graph_objects.Figure.
    """
    import plotly.graph_objects as go

    ck = extract_common_kw(kw)
    df, err = read_excel_or_error(ck["excel_path"], ck["sheet"])
    if err:
        return err

    groups = list(df.columns)
    values = {g: df[g].dropna().tolist() for g in groups}
    means = [calc_mean(v) if v else 0 for v in values.values()]

    colors = resolve_colors(ck["color"], len(groups))

    # Build traces
    traces = []
    for i, (g, mean) in enumerate(zip(groups, means)):
        vals = values[g]
        sem = calc_sem(vals)
        traces.append(go.Bar(
            x=[g],
            y=[mean],
            name=g,
            marker_color=colors[i % len(colors)],
            error_y=dict(type="data", array=[sem], visible=True),
            showlegend=False,
        ))

    layout = go.Layout(
        template=PRISM_TEMPLATE,
        title=dict(text=ck["title"], font=dict(size=14)),
        xaxis=dict(title=ck["xlabel"]),
        yaxis=dict(title=ck["ytitle"]),
    )
    apply_open_spine(layout.to_plotly_json())

    fig = go.Figure(data=traces, layout=layout)
    return fig.to_json()
