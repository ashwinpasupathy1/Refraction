"""Journal-quality figure export presets for Refraction.

Provides dimension presets for Nature, Science, and Cell journals.
The actual rendering is handled by the SwiftUI/Charts frontend;
this module supplies the dimensional constants and helpers.

Journal dimension sources
-------------------------
Nature:  https://www.nature.com/nature/for-authors/formatting-guide
Science: https://www.science.org/content/page/instructions-preparing-initial-manuscript
Cell:    https://www.cell.com/figureguidelines

All three journals require:
  - Arial or Helvetica font
  - Minimum 7 pt font size
  - Minimum 300 DPI for raster images (600 DPI for line art)
  - RGB colour (not CMYK)
"""
from __future__ import annotations

from typing import Optional

# -- Conversion ----------------------------------------------------------------
_MM_PER_IN = 25.4


def _mm_to_in(mm: float) -> float:
    return mm / _MM_PER_IN


# -- Journal presets -----------------------------------------------------------
JOURNAL_PRESETS: dict[str, dict] = {
    "Nature": {
        "columns": {
            "Single column (89 mm)":  89,
            "Double column (183 mm)": 183,
        },
        "max_h_mm": 247,
        "min_font": 7,
        "dpi": 300,
        "font": "Arial",
    },
    "Science": {
        "columns": {
            "Single column (55 mm)":       55,
            "1.5 columns (120 mm)":        120,
            "Double column (182 mm)":      182,
        },
        "max_h_mm": 245,
        "min_font": 7,
        "dpi": 300,
        "font": "Arial",
    },
    "Cell": {
        "columns": {
            "Single column (85 mm)":  85,
            "Double column (174 mm)": 174,
        },
        "max_h_mm": 235,
        "min_font": 7,
        "dpi": 300,
        "font": "Arial",
    },
}


def dims_from_preset(
    journal: str, col_label: str
) -> tuple[float, float, int, int, str]:
    """Return (width_in, height_in, dpi, min_font, font_family) for a preset."""
    p = JOURNAL_PRESETS[journal]
    w_mm = p["columns"][col_label]
    w_in = _mm_to_in(w_mm)
    h_in = min(w_in / 1.618, _mm_to_in(p["max_h_mm"]))
    return w_in, h_in, p["dpi"], p["min_font"], p["font"]
