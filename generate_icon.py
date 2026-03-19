#!/usr/bin/env python3
"""
generate_icon.py — Spectra macOS app icon generator

Generates:
  assets/icon.png   — 1024x1024 PNG (primary blue bg + white bar chart)
  assets/icon.icns  — macOS .icns bundle (macOS only, via sips + iconutil)

Requires: Pillow (pip install Pillow)
"""

import os
import sys
import shutil
import subprocess
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

ASSETS_DIR = Path(__file__).parent / "assets"
OUT_PNG    = ASSETS_DIR / "icon.png"
OUT_ICNS   = ASSETS_DIR / "icon.icns"

SIZE       = 1024            # canvas size
BG_COLOR   = "#2274A5"       # primary blue (from _DS.PRIMARY in plotter_widgets.py)
FG_COLOR   = "#FFFFFF"       # white bars
CORNER_R   = 224             # rounded-corner radius (~22% of 1024, matches Apple HIG)

# Bar chart geometry (relative to 1024 px canvas)
# Four bars of increasing then decreasing height — classic "bar chart" silhouette
BARS = [
    # (x_center_frac, height_frac)
    (0.22, 0.40),
    (0.38, 0.62),
    (0.54, 0.82),
    (0.70, 0.55),
]
BAR_WIDTH_FRAC = 0.11    # bar width as fraction of canvas
BAR_BOTTOM_Y   = 0.77    # baseline Y as fraction of canvas (higher = lower on screen)
BAR_CAP_R      = 0.012   # top-corner radius as fraction of canvas


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------

def hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def draw_rounded_rect(draw, x0, y0, x1, y1, radius, fill):
    """Draw a filled rounded rectangle using PIL.ImageDraw primitives."""
    from PIL import ImageDraw  # noqa — already imported by caller

    r = radius
    # Main body (cross shape avoids double-painting the rounded corners)
    draw.rectangle([x0 + r, y0, x1 - r, y1], fill=fill)
    draw.rectangle([x0, y0 + r, x1, y1 - r], fill=fill)
    # Four corner circles
    draw.ellipse([x0,      y0,      x0 + 2*r, y0 + 2*r], fill=fill)
    draw.ellipse([x1 - 2*r, y0,      x1,       y0 + 2*r], fill=fill)
    draw.ellipse([x0,      y1 - 2*r, x0 + 2*r, y1      ], fill=fill)
    draw.ellipse([x1 - 2*r, y1 - 2*r, x1,       y1      ], fill=fill)


def draw_bar(draw, cx_frac, h_frac, canvas_size, bar_w, baseline_y, cap_r):
    """Draw a single rounded-top bar."""
    s = canvas_size
    cx    = cx_frac * s
    bw    = bar_w * s
    bh    = h_frac * s
    bl    = baseline_y * s          # baseline Y in pixels
    x0    = cx - bw / 2
    x1    = cx + bw / 2
    y_top = bl - bh
    y_bot = bl
    cr    = cap_r * s               # top-corner radius

    # Rounded top, flat bottom: draw body + top-rounded rect
    # Body (full height, flat everywhere — we'll paint the rounded top over it)
    draw.rectangle([x0, y_top + cr, x1, y_bot], fill=FG_COLOR)
    # Top rounded cap
    draw.rectangle([x0 + cr, y_top, x1 - cr, y_top + cr * 2], fill=FG_COLOR)
    draw.ellipse([x0,      y_top,      x0 + 2*cr, y_top + 2*cr], fill=FG_COLOR)
    draw.ellipse([x1 - 2*cr, y_top,    x1,         y_top + 2*cr], fill=FG_COLOR)


def generate_png(path: Path, size: int = SIZE) -> None:
    """Render the icon as a PNG using Pillow."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        sys.exit(
            "ERROR: Pillow is required.\n"
            "Install it with:  pip install Pillow\n"
        )

    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background rounded rectangle
    bg   = hex_to_rgb(BG_COLOR)
    r    = int(CORNER_R * size / SIZE)
    draw_rounded_rect(draw, 0, 0, size - 1, size - 1, r, bg + (255,))

    # Draw bars
    for cx_frac, h_frac in BARS:
        draw_bar(
            draw,
            cx_frac,
            h_frac,
            size,
            BAR_WIDTH_FRAC,
            BAR_BOTTOM_Y,
            BAR_CAP_R,
        )

    # Subtle baseline rule under the bars
    bl_y   = int(BAR_BOTTOM_Y * size)
    rule_h = max(2, int(0.006 * size))  # ~6px at 1024
    left_x = int(0.13 * size)
    right_x = int(0.82 * size)
    draw.rectangle([left_x, bl_y, right_x, bl_y + rule_h], fill=FG_COLOR + (200,))

    img.save(path, "PNG")
    print(f"  Saved {path}  ({size}x{size})")


# ---------------------------------------------------------------------------
# macOS .icns generation
# ---------------------------------------------------------------------------

ICNS_SIZES = [16, 32, 64, 128, 256, 512, 1024]


def generate_icns(png_path: Path, icns_path: Path) -> bool:
    """
    Build a .icns file from the source PNG using sips + iconutil.
    Returns True on success, False if the tools aren't available.
    """
    if not shutil.which("sips") or not shutil.which("iconutil"):
        print("  Skipping .icns — sips/iconutil not found (not macOS?)")
        return False

    with tempfile.TemporaryDirectory() as tmp:
        iconset = Path(tmp) / "AppIcon.iconset"
        iconset.mkdir()

        # sips can resize PNGs natively on macOS
        for px in ICNS_SIZES:
            for scale, suffix in [(1, ""), (2, "@2x")]:
                actual = px * scale
                if actual > 1024:
                    continue
                dest = iconset / f"icon_{px}x{px}{suffix}.png"
                subprocess.run(
                    ["sips", "-z", str(actual), str(actual), str(png_path),
                     "--out", str(dest)],
                    check=True,
                    capture_output=True,
                )

        subprocess.run(
            ["iconutil", "-c", "icns", str(iconset), "-o", str(icns_path)],
            check=True,
            capture_output=True,
        )

    print(f"  Saved {icns_path}")
    return True


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    print("Spectra — icon generator")
    print(f"  Output dir: {ASSETS_DIR}")

    # 1. Generate 1024x1024 PNG
    print("\n[1] Generating PNG…")
    generate_png(OUT_PNG, size=SIZE)

    # 2. Generate .icns (macOS only)
    print("\n[2] Generating ICNS…")
    generate_icns(OUT_PNG, OUT_ICNS)

    print("\nDone.")


if __name__ == "__main__":
    main()
