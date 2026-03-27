"""Dedicated analyzer for XY chart types (scatter, line, area, curve_fit, bubble).

Reads XY layout: Column 0 = X values, Columns 1+ = Y series with optional
sub-columns for replicates. Series names come from row 0 header.

Returns ChartSpec with per-point replicate-aware structure:
  data.series[].points[].{x, y_mean, y_error, y_raw, n}
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Any
from collections import OrderedDict

from refraction.analysis.schema import AxisSpec, ChartSpec, StyleSpec
from refraction.analysis.helpers import extract_config
from refraction.core.config import PRISM_PALETTE


def analyze_xy(kw: dict[str, Any]) -> ChartSpec:
    """Analyze XY data with optional replicates."""
    cfg = extract_config(kw)
    excel_path = cfg["excel_path"]
    sheet = cfg["sheet"]
    error_type = cfg.get("error_type", "sem")
    chart_type = kw.get("_chart_type", "scatter")

    # Read without headers to handle replicate sub-columns
    if "_df" in cfg:
        # Inline data — re-read without header interpretation
        inline = cfg["_df"]
        # Reconstruct with header row as first data row
        import io
        csv_str = inline.to_csv(index=False)
        df = pd.read_csv(io.StringIO(csv_str), header=None)
    elif excel_path.endswith(".csv"):
        df = pd.read_csv(excel_path, header=None)
    else:
        df = pd.read_excel(excel_path, sheet_name=sheet, header=None)

    if len(df) < 2 or len(df.columns) < 2:
        raise ValueError("XY data needs at least 2 rows and 2 columns (X + 1 Y series)")

    # Row 0 = headers: X label, then series names (repeated for replicates)
    headers = [str(v) if pd.notna(v) else "" for v in df.iloc[0].values]
    x_label = headers[0]

    # Group columns by series name (repeated names = replicates)
    series_cols: OrderedDict[str, list[int]] = OrderedDict()
    for col_idx in range(1, len(headers)):
        name = headers[col_idx].strip()
        if not name:
            name = f"Series {len(series_cols) + 1}"
        if name not in series_cols:
            series_cols[name] = []
        series_cols[name].append(col_idx)

    # Data rows (skip header)
    data_rows = df.iloc[1:]

    # Extract X values
    x_raw = pd.to_numeric(data_rows.iloc[:, 0], errors="coerce")
    x_values = x_raw.dropna().values.tolist()
    x_indices = x_raw.dropna().index.tolist()

    if not x_values:
        raise ValueError("No valid X values found in column 0")

    # Build series with per-point replicates
    series_list = []
    for si, (series_name, col_indices) in enumerate(series_cols.items()):
        points = []
        for xi, x_idx in enumerate(x_indices):
            x_val = x_values[xi]

            # Collect replicate Y values at this X
            y_reps = []
            for ci in col_indices:
                val = data_rows.iloc[x_idx - data_rows.index[0], ci]
                v = pd.to_numeric(val, errors="coerce")
                if pd.notna(v):
                    y_reps.append(float(v))

            if not y_reps:
                continue

            y_arr = np.array(y_reps)
            y_mean = float(np.mean(y_arr))
            n = len(y_reps)

            if n > 1:
                sd = float(np.std(y_arr, ddof=1))
                sem = sd / np.sqrt(n)
                if error_type == "sd":
                    y_error = sd
                elif error_type == "ci95":
                    from scipy import stats as sp_stats
                    y_error = sp_stats.t.ppf(0.975, df=n - 1) * sem
                else:
                    y_error = sem
            else:
                y_error = 0.0

            points.append({
                "x": x_val,
                "y_mean": y_mean,
                "y_error": float(y_error),
                "y_raw": y_reps,
                "n": n,
            })

        color = PRISM_PALETTE[si % len(PRISM_PALETTE)]
        series_list.append({
            "name": series_name,
            "points": points,
            "color": color,
            "n_points": len(points),
        })

    if not series_list:
        raise ValueError("No valid Y series found")

    return ChartSpec(
        chart_type=chart_type,
        title=cfg["title"],
        x_axis=AxisSpec(label=x_label),
        y_axis=AxisSpec(
            label=cfg["ytitle"],
            scale=cfg.get("yscale", "linear"),
        ),
        style=StyleSpec(
            colors=[s["color"] for s in series_list],
        ),
        data={
            "x_values": x_values,
            "series": series_list,
            "error_type": error_type,
        },
    )
