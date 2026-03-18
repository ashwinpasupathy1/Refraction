"""Builds a Plotly figure spec for column descriptive statistics (table)."""

import json
import pandas as pd
from plotter_plotly_theme import PRISM_TEMPLATE, PRISM_PALETTE


def build_column_stats_spec(kw: dict) -> str:
    import plotly.graph_objects as go
    import numpy as np

    excel_path = kw.get("excel_path", "")
    sheet = kw.get("sheet", 0)
    title = kw.get("title", "Column Statistics")

    try:
        df = pd.read_excel(excel_path, sheet_name=sheet, header=0)
    except Exception as e:
        return json.dumps({"error": str(e)})

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
            return f"{v:.4g}" if pd.notna(v) else "—"

        rows["n"].append(str(n))
        rows["Mean"].append(fmt(mean))
        rows["SD"].append(fmt(sd))
        rows["SEM"].append(fmt(sem))
        rows["Min"].append(fmt(mn))
        rows["Median"].append(fmt(med))
        rows["Max"].append(fmt(mx))

    cell_values = [rows[s] for s in stat_names]
    # Transpose: go.Table expects column-major data
    transposed = list(map(list, zip(*cell_values)))
    # transposed[0] = first column (stat names), etc.
    # go.Table header = col_headers, cells per column
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
        title=dict(text=title),
    ))
    return fig.to_json()
