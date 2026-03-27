"""Shared helpers for analysis modules."""

from __future__ import annotations

import pandas as pd

from refraction.core.config import PRISM_PALETTE


def read_data(excel_path: str, sheet=0, *, header=0, df: pd.DataFrame | None = None) -> pd.DataFrame:
    """Read an Excel/CSV file and return a DataFrame.

    If *df* is provided, return it directly (for inline data from the Swift app).
    Raises FileNotFoundError or ValueError on failure.
    """
    if df is not None:
        return df
    path = str(excel_path)
    if path.endswith(".csv"):
        return pd.read_csv(path, header=header)
    return pd.read_excel(path, sheet_name=sheet, header=header)


def resolve_colors(color, n: int) -> list[str]:
    """Resolve a color argument to a list of *n* hex strings.

    Accepts: list[str], single str, or None (falls back to PRISM_PALETTE).
    """
    if isinstance(color, list):
        # Cycle the provided list to reach n entries
        if len(color) >= n:
            return color[:n]
        return [color[i % len(color)] for i in range(n)]
    if isinstance(color, str):
        return [color] * n
    return [PRISM_PALETTE[i % len(PRISM_PALETTE)] for i in range(n)]


def extract_config(kw: dict) -> dict:
    """Pull common configuration keys from the plotter kwargs dict.

    Returns a flat dict with normalised keys that every analyzer needs.
    """
    ytitle_val = kw.get("ytitle", kw.get("ylabel", ""))
    result = {
        "excel_path": kw.get("excel_path", ""),
        "sheet": kw.get("sheet", 0),
        "title": kw.get("title", ""),
        "xlabel": kw.get("xlabel", ""),
        "ytitle": ytitle_val,
        "ylabel": ytitle_val,   # alias for backward compatibility
        "color": kw.get("color", None),
        "yscale": kw.get("yscale", "linear"),
        "ylim": kw.get("ylim", None),
        "figsize": kw.get("figsize", (5, 5)),
        "font_size": kw.get("font_size", 12.0),
        "axis_style": kw.get("axis_style", "open"),
        "gridlines": kw.get("gridlines", False),
        "error_type": kw.get("error_type", "SEM"),
        "show_points": kw.get("show_points", False),
        "point_size": kw.get("point_size", 6.0),
        "point_alpha": kw.get("point_alpha", 0.80),
        "bar_width": kw.get("bar_width", 0.8),
        "alpha": kw.get("alpha", 0.85),
        "line_width": kw.get("line_width", 2.0),
        "stats_test": kw.get("stats_test", None),
        "posthoc": kw.get("posthoc", ""),
        "correction": kw.get("correction", ""),
    }
    # Pass through inline DataFrame if provided
    if "_df" in kw:
        result["_df"] = kw["_df"]
    return result
