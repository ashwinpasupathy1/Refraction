"""Builds a Plotly figure spec for Q-Q plots from plotter kwargs."""

from refraction.specs.theme import PRISM_TEMPLATE
from refraction.specs.helpers import extract_common_kw, read_excel_or_error, resolve_colors


def build_qq_spec(kw: dict) -> str:
    import plotly.graph_objects as go
    from scipy import stats as scipy_stats

    ck = extract_common_kw(kw, title="Q-Q Plot", xlabel="Theoretical Quantiles",
                           ytitle="Sample Quantiles")
    df, err = read_excel_or_error(ck["excel_path"], ck["sheet"])
    if err:
        return err

    groups = list(df.columns)
    colors = resolve_colors(ck["color"], len(groups))

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
        title=dict(text=ck["title"], font=dict(size=14)),
        xaxis=dict(title=ck["xlabel"]),
        yaxis=dict(title=ck["ytitle"]),
    )
    fig = go.Figure(data=traces, layout=layout)
    return fig.to_json()
