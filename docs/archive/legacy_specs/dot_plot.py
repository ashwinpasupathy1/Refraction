"""Builds a Plotly figure spec for dot/strip plots from plotter kwargs."""

import random
from refraction.specs.theme import PRISM_TEMPLATE
from refraction.specs.helpers import extract_common_kw, read_excel_or_error, resolve_colors


def build_dot_plot_spec(kw: dict) -> str:
    import plotly.graph_objects as go

    ck = extract_common_kw(kw)
    jitter_width = kw.get("jitter", 0.15)

    df, err = read_excel_or_error(ck["excel_path"], ck["sheet"])
    if err:
        return err

    groups = list(df.columns)
    colors = resolve_colors(ck["color"], len(groups))

    rng = random.Random(42)
    traces = []
    for i, g in enumerate(groups):
        vals = df[g].dropna().tolist()
        c = colors[i % len(colors)]
        x_jitter = [i + rng.uniform(-jitter_width, jitter_width) for _ in vals]
        traces.append(go.Scatter(
            x=x_jitter,
            y=vals,
            mode="markers",
            name=g,
            marker=dict(color=c, size=7, opacity=0.75, line=dict(width=0.5, color="white")),
            showlegend=False,
        ))

    layout = go.Layout(
        template=PRISM_TEMPLATE,
        title=dict(text=ck["title"], font=dict(size=14)),
        xaxis=dict(
            title=ck["xlabel"],
            tickmode="array",
            tickvals=list(range(len(groups))),
            ticktext=groups,
        ),
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
