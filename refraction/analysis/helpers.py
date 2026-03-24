"""Shared helpers for analysis engine — data reading and color resolution."""

from __future__ import annotations

import pandas as pd

PRISM_PALETTE = [
    "#E8453C", "#2274A5", "#32936F", "#F18F01", "#A846A0",
    "#6B4226", "#048A81", "#D4AC0D", "#3B1F2B", "#44BBA4",
]


def read_data(path: str, sheet: int | str = 0, *, header: int = 0) -> pd.DataFrame:
    """Read an Excel/CSV file and return a DataFrame.

    Raises ValueError with a descriptive message on failure.
    """
    ext = str(path).rsplit(".", 1)[-1].lower()
    try:
        if ext == "csv":
            return pd.read_csv(path, header=header)
        return pd.read_excel(path, sheet_name=sheet, header=header)
    except Exception as e:
        raise ValueError(f"Cannot read data file: {e}") from e


def resolve_colors(color: str | list[str] | None, n: int) -> list[str]:
    """Resolve a color argument to a list of n hex colors.

    - None → cycle through PRISM_PALETTE
    - Single string → repeat n times
    - List → use as-is (cycle if shorter than n)
    """
    if color is None:
        return [PRISM_PALETTE[i % len(PRISM_PALETTE)] for i in range(n)]
    if isinstance(color, str):
        return [color] * n
    # List of colors — cycle if needed
    return [color[i % len(color)] for i in range(n)]


def extract_config(kw: dict, **defaults: str) -> dict:
    """Extract common config keys from kwargs with defaults.

    Always returns: data_path, sheet, title, xlabel, ylabel, color.
    """
    return {
        "data_path": kw.get("excel_path", kw.get("data_path", "")),
        "sheet": kw.get("sheet", 0),
        "title": kw.get("title", defaults.get("title", "")),
        "xlabel": kw.get("xlabel", defaults.get("xlabel", "")),
        "ylabel": kw.get("ytitle", kw.get("ylabel", defaults.get("ylabel", ""))),
        "color": kw.get("color", None),
    }
