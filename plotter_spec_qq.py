"""Builds a Plotly figure spec for Q-Q plots from plotter kwargs."""

import json
import pandas as pd
from plotter_plotly_theme import PRISM_TEMPLATE, PRISM_PALETTE


def build_qq_spec(kw: dict) -> str:
    import plotly.graph_objects as go
    from scipy import stats as scipy_stats

    excel_path = kw.get("excel_path", "")
    sheet = kw.get("sheet", 0)
    color = kw.get("color", None)
    title = kw.get("title", "Q-Q Plot")
    xlabel = kw.get("xlabel", "Theoretical Quantiles")
    ytitle = kw.get("ytitle", "Sample Quantiles")

    try:
        df = pd.read_excel(excel_path, sheet_name=sheet, header=0)
    except Exception as e:
        return json.dumps({"error": str(e)})

    groups = list(df.columns)

    if isinstance(color, list):
        colors = color
    elif isinstance(color, str):
        colors = [color] * len(groups)
    else:
        colors = PRISM_PALETTE[:len(groups)]

    traces = []

    for i, g in enumerate(groups):
        vals = sorted(df[g].dropna().tolist())
        n = len(vals)
        if n < 2:
            continue
        c = colors[i % len(colors)]

        # Theoretical quantiles from standard normal
        probs = [(j - 0.5) / n for j in range(1, n + 1)]
        theoretical = [scipy_stats.norm.ppf(p) for p in probs]

        traces.append(go.Scatter(
            x=theoretical,
            y=vals,
            mode="markers",
            name=g,
            marker=dict(color=c, size=6, opacity=0.8),
            showlegend=len(groups) > 1,
        ))

    # 45-degree reference line across the full theoretical range
    if traces:
        all_x = [x for t in traces for x in t.x]
        all_y = [y for t in traces for y in t.y]
        x_min, x_max = min(all_x), max(all_x)
        y_min, y_max = min(all_y), max(all_y)
        traces.append(go.Scatter(
            x=[x_min, x_max],
            y=[y_min, y_max],
            mode="lines",
            name="Reference",
            line=dict(color="#888888", width=1.5, dash="dash"),
            showlegend=False,
        ))

    layout = go.Layout(
        template=PRISM_TEMPLATE,
        title=dict(text=title, font=dict(size=14)),
        xaxis=dict(title=xlabel),
        yaxis=dict(title=ytitle),
    )
    fig = go.Figure(data=traces, layout=layout)
    return fig.to_json()
