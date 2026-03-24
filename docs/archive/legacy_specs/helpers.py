"""Shared helpers for Plotly spec builders — eliminates boilerplate."""

import json
import pandas as pd
from refraction.specs.theme import PRISM_PALETTE


def spec_error(msg) -> str:
    """Return a JSON string with an error message."""
    return json.dumps({"error": str(msg)})


def extract_common_kw(kw, *, xlabel="", ytitle="", title=""):
    """Extract common kwargs from the plotter kw dict.

    Returns a dict with: excel_path, sheet, title, xlabel, ytitle, color.
    Callers can override the defaults for xlabel/ytitle/title.
    """
    return {
        "excel_path": kw.get("excel_path", ""),
        "sheet": kw.get("sheet", 0),
        "title": kw.get("title", title),
        "xlabel": kw.get("xlabel", xlabel),
        "ytitle": kw.get("ytitle", ytitle),
        "color": kw.get("color", None),
    }


def read_excel_or_error(excel_path, sheet, *, header=0):
    """Read an Excel file and return (df, None) or (None, error_json_str)."""
    try:
        df = pd.read_excel(excel_path, sheet_name=sheet, header=header)
        return df, None
    except Exception as e:
        return None, spec_error(e)


def resolve_colors(color, n):
    """Resolve a color argument to a list of n colors.

    Handles: list of colors, single color string, or None (uses PRISM_PALETTE).
    """
    if isinstance(color, list):
        return color
    elif isinstance(color, str):
        return [color] * n
    else:
        return PRISM_PALETTE[:n]
