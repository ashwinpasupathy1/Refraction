"""Builds a Plotly figure spec for ECDF plots from plotter kwargs."""

from plotter_plotly_theme import PRISM_TEMPLATE
from plotter_spec_helpers import extract_common_kw, read_excel_or_error, resolve_colors


def build_ecdf_spec(kw: dict) -> str:
    import plotly.graph_objects as go

    ck = extract_common_kw(kw, title="ECDF", xlabel="Value",
                           ytitle="Cumulative Proportion")
    df, err = read_excel_or_error(ck["excel_path"], ck["sheet"])
    if err:
        return err

    groups = list(df.columns)
    colors = resolve_colors(ck["color"], len(groups))

    traces = []
    for i, g in enumerate(groups):
        vals = sorted(df[g].dropna().tolist())
        n = len(vals)
        if n == 0:
            continue
        c = colors[i % len(colors)]
        proportions = [(j + 1) / n for j in range(n)]
        traces.append(go.Scatter(
            x=vals,
            y=proportions,
            mode="lines",
            name=g,
            line=dict(color=c, width=2, shape="hv"),
            showlegend=len(groups) > 1,
        ))

    layout = go.Layout(
        template=PRISM_TEMPLATE,
        title=dict(text=ck["title"], font=dict(size=14)),
        xaxis=dict(title=ck["xlabel"]),
        yaxis=dict(title=ck["ytitle"], range=[0, 1]),
    )
    fig = go.Figure(data=traces, layout=layout)
    return fig.to_json()
