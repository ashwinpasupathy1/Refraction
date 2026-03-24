"""Builds a Plotly figure spec for raincloud plots from plotter kwargs."""

import random
from refraction.specs.theme import PRISM_TEMPLATE
from refraction.specs.helpers import extract_common_kw, read_excel_or_error, resolve_colors


def build_raincloud_spec(kw: dict) -> str:
    import plotly.graph_objects as go

    ck = extract_common_kw(kw)
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

        # Half violin (positive/right side only)
        traces.append(go.Violin(
            x=[g] * len(vals),
            y=vals,
            name=g,
            side="positive",
            line_color=c,
            fillcolor=c,
            opacity=0.6,
            box_visible=False,
            meanline_visible=False,
            points=False,
            showlegend=False,
            width=0.8,
        ))

        # Box overlay (narrow)
        traces.append(go.Box(
            x=[g] * len(vals),
            y=vals,
            name=g,
            marker_color=c,
            line_color=c,
            boxpoints=False,
            width=0.08,
            showlegend=False,
        ))

        # Jittered scatter (rain drops)
        x_jitter = [g + rng.uniform(0.05, 0.25) for _ in vals]
        traces.append(go.Scatter(
            x=x_jitter,
            y=vals,
            mode="markers",
            name=g,
            marker=dict(color=c, size=5, opacity=0.55, line=dict(width=0)),
            showlegend=False,
        ))

    layout = go.Layout(
        template=PRISM_TEMPLATE,
        title=dict(text=ck["title"], font=dict(size=14)),
        xaxis=dict(title=ck["xlabel"]),
        yaxis=dict(title=ck["ytitle"]),
        violinmode="overlay",
        boxmode="overlay",
    )
    fig = go.Figure(data=traces, layout=layout)
    return fig.to_json()
