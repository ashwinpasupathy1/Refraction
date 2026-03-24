"""Builds a Plotly figure spec for box plots from plotter kwargs."""

from refraction.specs.theme import PRISM_TEMPLATE
from refraction.specs.helpers import extract_common_kw, read_excel_or_error, resolve_colors


def build_box_spec(kw: dict) -> str:
    import plotly.graph_objects as go

    ck = extract_common_kw(kw)
    df, err = read_excel_or_error(ck["excel_path"], ck["sheet"])
    if err:
        return err

    groups = list(df.columns)
    colors = resolve_colors(ck["color"], len(groups))

    traces = []
    for i, g in enumerate(groups):
        vals = df[g].dropna().tolist()
        c = colors[i % len(colors)]
        traces.append(go.Box(
            y=vals,
            name=g,
            marker_color=c,
            line_color=c,
            boxpoints="all",
            jitter=0.3,
            pointpos=0,
            marker=dict(size=5, opacity=0.6, color=c),
            showlegend=False,
        ))

    layout = go.Layout(
        template=PRISM_TEMPLATE,
        title=dict(text=ck["title"], font=dict(size=14)),
        xaxis=dict(title=ck["xlabel"]),
        yaxis=dict(title=ck["ytitle"]),
    )
    fig = go.Figure(data=traces, layout=layout)

    # Attach linked results
    import json as _json
    from refraction.analysis.results import build_results_section
    values = {g: df[g].dropna().tolist() for g in groups}
    results = build_results_section(values)
    spec = _json.loads(fig.to_json())
    spec["results"] = results
    return _json.dumps(spec)
