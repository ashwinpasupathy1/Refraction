"""Builds a Plotly figure spec for column descriptive statistics (table)."""

import pandas as pd
from plotter_plotly_theme import PRISM_TEMPLATE, PRISM_PALETTE
from plotter_spec_helpers import extract_common_kw, read_excel_or_error


def build_column_stats_spec(kw: dict) -> str:
    import plotly.graph_objects as go
    import numpy as np

    ck = extract_common_kw(kw, title="Column Statistics")
    df, err = read_excel_or_error(ck["excel_path"], ck["sheet"])
    if err:
        return err

    stat_names = ["n", "Mean", "SD", "SEM", "Min", "Median", "Max"]
    col_headers = ["Statistic"] + df.columns.tolist()

    rows = {s: [s] for s in stat_names}

    for col in df.columns:
        vals = pd.to_numeric(df[col], errors="coerce").dropna().values
        n = len(vals)
        mean = float(np.mean(vals)) if n > 0 else float("nan")
        sd = float(np.std(vals, ddof=1)) if n > 1 else float("nan")
        sem = sd / np.sqrt(n) if n > 1 else float("nan")
        mn = float(np.min(vals)) if n > 0 else float("nan")
        med = float(np.median(vals)) if n > 0 else float("nan")
        mx = float(np.max(vals)) if n > 0 else float("nan")

        def fmt(v):
            return f"{v:.4g}" if pd.notna(v) else "\u2014"

        rows["n"].append(str(n))
        rows["Mean"].append(fmt(mean))
        rows["SD"].append(fmt(sd))
        rows["SEM"].append(fmt(sem))
        rows["Min"].append(fmt(mn))
        rows["Median"].append(fmt(med))
        rows["Max"].append(fmt(mx))

    cell_values = [rows[s] for s in stat_names]
    # Transpose: go.Table expects column-major data
    col_data = list(map(list, zip(*[row for row in cell_values])))

    traces = [go.Table(
        header=dict(
            values=col_headers,
            fill_color=PRISM_PALETTE[1],
            font=dict(color="white", size=12),
            align="center",
        ),
        cells=dict(
            values=col_data,
            fill_color=[["#f5f5f5", "white"] * (len(stat_names) // 2 + 1)],
            align=["left"] + ["center"] * len(df.columns),
            font=dict(size=11),
        ),
    )]

    fig = go.Figure(data=traces, layout=go.Layout(
        template=PRISM_TEMPLATE,
        title=dict(text=ck["title"]),
    ))
    return fig.to_json()
