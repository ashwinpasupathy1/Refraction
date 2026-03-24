"""Builds a Plotly figure spec for column descriptive statistics (table)."""

import pandas as pd
from refraction.specs.theme import PRISM_TEMPLATE, PRISM_PALETTE
from refraction.specs.helpers import extract_common_kw, read_excel_or_error
from refraction.core.stats import descriptive_stats


def build_column_stats_spec(kw: dict) -> str:
    import plotly.graph_objects as go

    ck = extract_common_kw(kw, title="Column Statistics")
    df, err = read_excel_or_error(ck["excel_path"], ck["sheet"])
    if err:
        return err

    stat_names = ["n", "Mean", "SD", "SEM", "Min", "Median", "Max"]
    col_headers = ["Statistic"] + df.columns.tolist()

    rows = {s: [s] for s in stat_names}

    for col in df.columns:
        vals = pd.to_numeric(df[col], errors="coerce").dropna().values
        ds = descriptive_stats(vals)

        def fmt(v):
            return f"{v:.4g}" if pd.notna(v) else "\u2014"

        rows["n"].append(str(ds["n"]))
        rows["Mean"].append(fmt(ds["mean"]))
        rows["SD"].append(fmt(ds["sd"]))
        rows["SEM"].append(fmt(ds["sem"]))
        rows["Min"].append(fmt(ds["min"]))
        rows["Median"].append(fmt(ds["median"]))
        rows["Max"].append(fmt(ds["max"]))

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
