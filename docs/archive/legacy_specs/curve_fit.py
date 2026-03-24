"""Builds a Plotly figure spec for scatter + polynomial curve fit."""

import pandas as pd
from refraction.specs.theme import PRISM_TEMPLATE, PRISM_PALETTE
from refraction.specs.helpers import extract_common_kw, read_excel_or_error, spec_error


def build_curve_fit_spec(kw: dict) -> str:
    import plotly.graph_objects as go
    import numpy as np

    ck = extract_common_kw(kw)
    poly_degree = int(kw.get("poly_degree", 1))

    df, err = read_excel_or_error(ck["excel_path"], ck["sheet"])
    if err:
        return err

    if df.shape[1] < 2:
        return spec_error("Curve fit requires at least 2 columns: X, Y.")

    col_names = df.columns.tolist()
    x_label = ck["xlabel"] or str(col_names[0])
    y_label = ck["ytitle"] or str(col_names[1])

    x = pd.to_numeric(df.iloc[:, 0], errors="coerce")
    y = pd.to_numeric(df.iloc[:, 1], errors="coerce")
    mask = x.notna() & y.notna()
    x, y = x[mask].values, y[mask].values

    if len(x) < 2:
        return spec_error("Not enough data points for curve fit.")

    color_scatter = PRISM_PALETTE[0]
    color_fit = PRISM_PALETTE[1]

    traces = [go.Scatter(
        x=x.tolist(),
        y=y.tolist(),
        mode="markers",
        marker=dict(color=color_scatter, size=8, opacity=0.8),
        name="Data",
    )]

    coeffs = np.polyfit(x, y, poly_degree)
    x_fit = np.linspace(x.min(), x.max(), 200)
    y_fit = np.polyval(coeffs, x_fit)

    # Compute R-squared
    y_pred = np.polyval(coeffs, x)
    ss_res = float(np.sum((y - y_pred) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")

    degree_label = {1: "Linear", 2: "Quadratic", 3: "Cubic"}.get(poly_degree, f"Degree-{poly_degree}")
    traces.append(go.Scatter(
        x=x_fit.tolist(),
        y=y_fit.tolist(),
        mode="lines",
        line=dict(color=color_fit, width=2),
        name=f"{degree_label} fit (R²={r2:.4f})",
    ))

    fig = go.Figure(data=traces, layout=go.Layout(
        template=PRISM_TEMPLATE,
        title=dict(text=ck["title"]),
        xaxis=dict(title=x_label),
        yaxis=dict(title=y_label),
        annotations=[dict(
            x=0.05, y=0.95,
            xref="paper", yref="paper",
            text=f"R² = {r2:.4f}",
            showarrow=False,
            font=dict(size=13),
            bgcolor="rgba(255,255,255,0.7)",
        )],
    ))
    return fig.to_json()
