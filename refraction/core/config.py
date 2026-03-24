"""
refraction/core/config.py
--------------------------
Canonical source for all style constants, palettes, and default parameters.

Other modules should import from here rather than defining their own copies.
For backward compatibility, chart_helpers.py and specs/theme.py re-export
the constants they previously owned.

Usage:
    from refraction.core.config import DEFAULT_CONFIG, PRISM_PALETTE
    # or access individual values:
    DEFAULT_CONFIG.dpi   # 144
    DEFAULT_CONFIG.font  # "Arial"
"""

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# The 10-color Prism palette -- defined once, imported everywhere
# ---------------------------------------------------------------------------

PRISM_PALETTE: list[str] = [
    "#E8453C", "#2274A5", "#32936F", "#F18F01", "#A846A0",
    "#6B4226", "#048A81", "#D4AC0D", "#3B1F2B", "#44BBA4",
]


# ---------------------------------------------------------------------------
# UI-facing lookup dicts
# ---------------------------------------------------------------------------

AXIS_STYLES: dict[str, str] = {
    "Open (default)": "open",
    "Closed box":     "closed",
    "Floating":       "floating",
    "None":           "none",
}

TICK_DIRS: dict[str, str] = {
    "Outward (default)": "out",
    "Inward":            "in",
    "Both":              "inout",
    "None":              "",
}

LEGEND_POSITIONS: dict[str, str] = {
    "Auto (best fit)": "best",
    "Upper right":     "upper right",
    "Upper left":      "upper left",
    "Lower right":     "lower right",
    "Lower left":      "lower left",
    "Outside right":   "outside",
    "None (hidden)":   "none",
}

MARKER_CYCLE: list[str] = ["o", "s", "^", "D", "v", "*", "P", "X", "h"]


# ---------------------------------------------------------------------------
# Plot parameter defaults -- used by _style_kwargs() and UI reset
# ---------------------------------------------------------------------------

PLOT_PARAM_DEFAULTS: dict = {
    # Axis / tick style
    "axis_style":     "open",
    "tick_dir":       "out",
    "minor_ticks":    False,
    # Data point style
    "point_size":     6.0,
    "point_alpha":    0.80,
    # Error bar style
    "cap_size":       4.0,
    # Legend
    "legend_pos":     "upper right",
    # Tick intervals (0 = auto)
    "ytick_interval": 0.0,
    "xtick_interval": 0.0,
    # Background color
    "fig_bg":         "white",
    # Spine / tick width
    "spine_width":    0.8,
    # Grid style
    "grid_style":     "none",
    # Bracket style
    "bracket_style":  "lines",
    # Layout
    "figsize":        (5, 5),
    "font_size":      12.0,
    # Labels
    "title":          "",
    "xlabel":         "",
    "ytitle":         "",
    "yscale":         "linear",
    "ylim":           None,
    "ref_line":       None,
    "ref_line_label": "",
}


# ---------------------------------------------------------------------------
# PlotConfig dataclass -- groups all rendering constants in one place
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PlotConfig:
    """Immutable container for all rendering/style constants.

    Access the singleton via ``DEFAULT_CONFIG``.  Individual fields are
    documented inline.
    """

    # Resolution
    dpi: int = 144

    # Typography
    font: str = "Arial"

    # Line widths
    lw_axis: float = 0.8
    lw_err: float = 1.0
    lw_grid: float = 0.6
    lw_ref: float = 1.0

    # Error bars
    cap_size: int = 4

    # Padding (pts)
    label_pad: int = 6
    title_pad: int = 8
    tight_pad: float = 1.2

    # Alpha values
    alpha_bar: float = 0.85
    alpha_point: float = 0.80
    alpha_ci: float = 0.15
    alpha_line: float = 0.55

    # Point style
    pt_size: int = 18
    pt_lw: float = 1.2

    # Color manipulation
    darken: float = 0.65

    # Annotation colors
    color_annot: str = "dimgray"
    color_warn: str = "darkorange"
    color_subj: str = "#aaaaaa"
    color_box: str = "#444444"
    color_anno_subtle: str = "#888888"
    color_hdr: str = "#2274A5"
    color_warn_fill: str = "#FFA50055"
    color_bg: str = "white"

    # Paired / subcolumn drawing constants
    mean_tick_half: float = 0.18
    mean_tick_lw: float = 2.5
    pair_err_lw: float = 1.8
    pair_cap_size: int = 6
    subj_line_lw: float = 0.8
    subj_line_alpha: float = 0.55

    # Palette (not frozen-safe as list, but treated as immutable)
    palette: tuple[str, ...] = (
        "#E8453C", "#2274A5", "#32936F", "#F18F01", "#A846A0",
        "#6B4226", "#048A81", "#D4AC0D", "#3B1F2B", "#44BBA4",
    )

    # Marker cycle for multi-series XY charts
    marker_cycle: tuple[str, ...] = ("o", "s", "^", "D", "v", "*", "P", "X", "h")


# The default configuration instance -- import this in other modules
DEFAULT_CONFIG = PlotConfig()
