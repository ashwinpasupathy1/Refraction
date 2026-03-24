"""Shared helpers for analysis modules."""

from __future__ import annotations

import pandas as pd

from refraction.specs.theme import PRISM_PALETTE


def read_data(excel_path: str, sheet=0, *, header=0) -> pd.DataFrame:
    """Read an Excel/CSV file and return a DataFrame.

    Raises FileNotFoundError or ValueError on failure.
    """
    path = str(excel_path)
    if path.endswith(".csv"):
        return pd.read_csv(path, header=header)
    return pd.read_excel(path, sheet_name=sheet, header=header)


def resolve_colors(color, n: int) -> list[str]:
    """Resolve a color argument to a list of *n* hex strings.

    Accepts: list[str], single str, or None (falls back to PRISM_PALETTE).
    """
    if isinstance(color, list):
        # Extend with palette if too short
        while len(color) < n:
            color.append(PRISM_PALETTE[len(color) % len(PRISM_PALETTE)])
        return color[:n]
    if isinstance(color, str):
        return [color] * n
    return [PRISM_PALETTE[i % len(PRISM_PALETTE)] for i in range(n)]


def extract_config(kw: dict) -> dict:
    """Pull common configuration keys from the plotter kwargs dict.

    Returns a flat dict with normalised keys that every analyzer needs.
    """
    return {
        "excel_path": kw.get("excel_path", ""),
        "sheet": kw.get("sheet", 0),
        "title": kw.get("title", ""),
        "xlabel": kw.get("xlabel", ""),
        "ytitle": kw.get("ytitle", ""),
        "color": kw.get("color", None),
        "yscale": kw.get("yscale", "linear"),
        "ylim": kw.get("ylim", None),
        "figsize": kw.get("figsize", (5, 5)),
        "font_size": kw.get("font_size", 12.0),
        "axis_style": kw.get("axis_style", "open"),
        "gridlines": kw.get("gridlines", False),
        "error_type": kw.get("error_type", "sem"),
        "show_points": kw.get("show_points", False),
        "point_size": kw.get("point_size", 6.0),
        "point_alpha": kw.get("point_alpha", 0.80),
        "bar_width": kw.get("bar_width", 0.8),
        "alpha": kw.get("alpha", 0.85),
        "line_width": kw.get("line_width", 2.0),
        "stats_test": kw.get("stats_test", ""),
        "posthoc": kw.get("posthoc", ""),
        "correction": kw.get("correction", ""),
    }
