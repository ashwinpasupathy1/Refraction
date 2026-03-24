"""Builds a Plotly figure spec for histograms from plotter kwargs."""

from plotter_plotly_theme import PRISM_TEMPLATE
from plotter_spec_helpers import extract_common_kw, read_excel_or_error, resolve_colors


def build_histogram_spec(kw: dict) -> str:
    import plotly.graph_objects as go

    ck = extract_common_kw(kw, ytitle="Frequency")
    hist_mode = kw.get("hist_mode", "overlay")

    df, err = read_excel_or_error(ck["excel_path"], ck["sheet"])
    if err:
        return err

    groups = list(df.columns)
    colors = resolve_colors(ck["color"], len(groups))

    opacity = 0.7 if hist_mode == "overlay" else 1.0

    traces = []
    for i, g in enumerate(groups):
        vals = df[g].dropna().tolist()
        c = colors[i % len(colors)]
        traces.append(go.Histogram(
            x=vals,
            name=g,
            marker_color=c,
            opacity=opacity,
            showlegend=len(groups) > 1,
        ))

    layout = go.Layout(
        template=PRISM_TEMPLATE,
        title=dict(text=ck["title"], font=dict(size=14)),
        xaxis=dict(title=ck["xlabel"]),
        yaxis=dict(title=ck["ytitle"]),
        barmode=hist_mode if hist_mode in ("overlay", "stack") else "overlay",
    )
    fig = go.Figure(data=traces, layout=layout)
    return fig.to_json()
