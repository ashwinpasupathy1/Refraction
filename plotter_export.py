"""
plotter_export.py — Journal-quality figure export for Refraction.

Provides dimension presets for Nature, Science, and Cell journals.
Uses Plotly + kaleido for all raster/vector export.

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

import os
from typing import Optional

# ── Conversion ────────────────────────────────────────────────────────────────
_MM_PER_IN = 25.4


def _mm_to_in(mm: float) -> float:
    return mm / _MM_PER_IN


# ── Journal presets ───────────────────────────────────────────────────────────
# Keys in each entry:
#   columns  : dict mapping column label → width in mm
#   max_h_mm : maximum figure height (mm)
#   min_font : minimum font size in points
#   dpi      : minimum recommended DPI for raster output

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

# Column label → mm for quick lookup
_COL_WIDTHS_MM: dict[str, int] = {
    label: mm
    for preset in JOURNAL_PRESETS.values()
    for label, mm in preset["columns"].items()
}


def _dims_from_preset(journal: str, col_label: str) -> tuple[float, float, int]:
    """Return (width_in, height_in, dpi) for a journal + column label."""
    p = JOURNAL_PRESETS[journal]
    w_mm = p["columns"][col_label]
    w_in = _mm_to_in(w_mm)
    # Default height: golden-ratio proportion of width, capped at journal max.
    h_in = min(w_in / 1.618, _mm_to_in(p["max_h_mm"]))
    return w_in, h_in, p["dpi"]


# ── Plotly / kaleido export ───────────────────────────────────────────────────

def export_plotly(
    spec_json: str,
    path: str,
    journal: Optional[str] = None,
    col_label: Optional[str] = None,
    dpi: int = 300,
    width_px: Optional[int] = None,
    height_px: Optional[int] = None,
) -> None:
    """Export a Plotly JSON spec to a file using kaleido or write_html.

    Parameters
    ----------
    spec_json  : JSON string returned by ``_build_spec()``
    path       : output file path; extension sets format (.png/.svg/.pdf/.html)
    journal    : one of "Nature", "Science", "Cell" — or None for custom size
    col_label  : column width label matching the journal preset (e.g.
                 "Single column (89 mm)"); ignored when journal is None
    dpi        : DPI for raster export (PNG); overridden by journal preset
    width_px   : explicit pixel width when journal is None
    height_px  : explicit pixel height when journal is None

    Raises
    ------
    ImportError  if plotly or kaleido are not installed
    """
    import plotly.io as pio

    ext = os.path.splitext(path)[1].lower()

    # ── HTML: no kaleido needed ────────────────────────────────────────────────
    if ext == ".html":
        fig = pio.from_json(spec_json)
        fig.write_html(path, include_plotlyjs="cdn")
        return

    # ── Raster / vector via kaleido ────────────────────────────────────────────
    if journal and journal in JOURNAL_PRESETS and col_label:
        w_in, h_in, _dpi = _dims_from_preset(journal, col_label)
        # Enforce minimum font size for journal compliance.
        min_font = JOURNAL_PRESETS[journal]["min_font"]
        font_family = JOURNAL_PRESETS[journal]["font"]
    else:
        w_in  = (width_px  / dpi) if width_px  else 7.0
        h_in  = (height_px / dpi) if height_px else 5.0
        _dpi  = dpi
        min_font   = 7
        font_family = "Arial"

    # Plotly layout dimensions are in logical pixels at 72 lpi (screen).
    # kaleido `scale` multiplies that to reach the target DPI.
    scale  = _dpi / 72.0
    w_logi = w_in * 72.0
    h_logi = h_in * 72.0

    fig = pio.from_json(spec_json)

    # Apply journal font requirements to layout.
    existing_size = (fig.layout.font.size or 12)
    fig.update_layout(
        width=w_logi,
        height=h_logi,
        font=dict(
            family=font_family,
            size=max(min_font, existing_size),
        ),
    )

    pio.write_image(fig, path, scale=scale)


# ── Kaleido availability check ────────────────────────────────────────────────

def kaleido_available() -> bool:
    """Return True if kaleido is installed and functional."""
    try:
        import kaleido  # noqa: F401
        return True
    except ImportError:
        return False
