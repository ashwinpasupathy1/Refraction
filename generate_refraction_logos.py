#!/usr/bin/env python3
"""
generate_refraction_logos.py — Refraction macOS app icon generator

Generates three icon variants:
  assets/logo_refraction_bars.png   — Spectrum bar chart (recommended)
  assets/logo_refraction_prism.png  — Prism dispersing light
  assets/icon.png                — Overwrites the active app icon (bars variant)
  assets/AppIcon.icns            — macOS .icns bundle (bars variant, macOS only)

Requires: Pillow  (pip install Pillow)
"""

import math
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ASSETS_DIR = Path(__file__).parent / "assets"
SIZE = 1024
CORNER_R = 220

# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------
DARK_BG   = (11, 17, 32)        # #0B1120 — deep navy
VIOLET    = (123, 47, 190)      # #7B2FBE
BLUE      = (34, 116, 165)      # #2274A5
TEAL      = (0, 168, 120)       # #00A878
AMBER     = (245, 166, 35)      # #F5A623
CORAL     = (232, 69, 60)       # #E8453C
WHITE     = (255, 255, 255)


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------

def hex_rgb(h: str):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def draw_rounded_rect(draw, x0, y0, x1, y1, radius, fill):
    from PIL import ImageDraw  # noqa
    r = int(radius)
    draw.rectangle([x0 + r, y0, x1 - r, y1], fill=fill)
    draw.rectangle([x0, y0 + r, x1, y1 - r], fill=fill)
    draw.ellipse([x0,        y0,        x0 + 2*r, y0 + 2*r], fill=fill)
    draw.ellipse([x1 - 2*r,  y0,        x1,        y0 + 2*r], fill=fill)
    draw.ellipse([x0,        y1 - 2*r,  x0 + 2*r,  y1     ], fill=fill)
    draw.ellipse([x1 - 2*r,  y1 - 2*r,  x1,        y1     ], fill=fill)


def draw_bar_rounded_top(draw, x0, x1, y_top, y_bot, fill, corner_r=14):
    """Bar with rounded top only."""
    r = corner_r
    # Body
    draw.rectangle([x0, y_top + r, x1, y_bot], fill=fill)
    # Top cap
    draw.rectangle([x0 + r, y_top, x1 - r, y_top + 2*r], fill=fill)
    draw.ellipse([x0,       y_top, x0 + 2*r, y_top + 2*r], fill=fill)
    draw.ellipse([x1 - 2*r, y_top, x1,       y_top + 2*r], fill=fill)


# ---------------------------------------------------------------------------
# Logo A — Spectrum Bar Chart
# ---------------------------------------------------------------------------

def generate_bars(size: int = SIZE) -> "Image":
    from PIL import Image, ImageDraw
    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background
    cr = int(CORNER_R * size / SIZE)
    draw_rounded_rect(draw, 0, 0, size - 1, size - 1, cr, DARK_BG + (255,))

    # Layout (all fractions of SIZE)
    baseline = int(0.74 * size)
    bar_w    = int(0.105 * size)
    gap      = int(0.039 * size)

    # 5 bars: (colour, height_frac)
    bars_data = [
        (VIOLET, 0.255),
        (BLUE,   0.375),
        (TEAL,   0.500),
        (AMBER,  0.415),
        (CORAL,  0.315),
    ]

    total_w = len(bars_data) * bar_w + (len(bars_data) - 1) * gap
    left    = (size - total_w) // 2

    for i, (colour, h_frac) in enumerate(bars_data):
        x0    = left + i * (bar_w + gap)
        x1    = x0 + bar_w
        bh    = int(h_frac * size)
        y_top = baseline - bh
        draw_bar_rounded_top(draw, x0, x1, y_top, baseline, colour + (255,), corner_r=14)

        # Error bar cap
        cap_x0 = x0 + bar_w // 4
        cap_x1 = x0 + 3 * bar_w // 4
        cap_y  = y_top - int(0.006 * size)
        draw.rectangle([cap_x0, cap_y, cap_x1, cap_y + max(3, int(0.005 * size))],
                       fill=WHITE + (160,))

    # Baseline rule
    rule_h = max(3, int(0.006 * size))
    draw.rectangle([left - bar_w // 2, baseline,
                    left + total_w + bar_w // 2, baseline + rule_h],
                   fill=WHITE + (55,))

    return img


# ---------------------------------------------------------------------------
# Logo B — Prism dispersing light
# ---------------------------------------------------------------------------

def _fill_polygon(draw, points, fill):
    """Filled convex polygon using ImageDraw."""
    from PIL import ImageDraw  # noqa
    draw.polygon(points, fill=fill)


def generate_prism(size: int = SIZE) -> "Image":
    from PIL import Image, ImageDraw
    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    s = size

    # Background
    cr = int(CORNER_R * s / SIZE)
    draw_rounded_rect(draw, 0, 0, s - 1, s - 1, cr, DARK_BG + (255,))

    # Prism triangle: top (0.37*s, 0.225*s) → bottom (0.37*s, 0.775*s) → apex (0.606*s, 0.5*s)
    tri_x1, tri_y_top  = int(0.370 * s), int(0.225 * s)
    tri_x2, tri_y_bot  = int(0.370 * s), int(0.775 * s)
    apex_x, apex_y     = int(0.606 * s), int(0.500 * s)

    # Incoming beam (left)
    beam_y1 = int(0.481 * s)
    beam_y2 = int(0.519 * s)
    draw.rectangle([int(0.095 * s), beam_y1, tri_x1, beam_y2], fill=WHITE + (215,))

    # Prism face
    _fill_polygon(draw, [(tri_x1, tri_y_top), (tri_x2, tri_y_bot), (apex_x, apex_y)],
                  (26, 47, 74, 242))
    draw.polygon([(tri_x1, tri_y_top), (tri_x2, tri_y_bot), (apex_x, apex_y)],
                 outline=WHITE + (200,), width=max(4, int(0.009 * s)))

    # Dispersed beams — fan from apex
    far = int(0.92 * s)
    beam_colours = [VIOLET, BLUE, TEAL, AMBER, (240, 123, 27), CORAL]
    # Y positions of far endpoints (top to bottom)
    far_y_tops    = [0.200, 0.318, 0.440, 0.538, 0.645, 0.775]
    far_y_bottoms = [0.318, 0.440, 0.538, 0.645, 0.775, 0.830]

    for colour, yt_frac, yb_frac in zip(beam_colours, far_y_tops, far_y_bottoms):
        yt = int(yt_frac * s)
        yb = int(yb_frac * s)
        mid_apex_y = apex_y
        poly = [(apex_x, mid_apex_y - 6), (apex_x, mid_apex_y + 6), (far, yb), (far, yt)]
        _fill_polygon(draw, poly, colour + (220,))

    # Glow at apex
    ax, ay = apex_x, apex_y
    for r, alpha in [(28, 45), (14, 90)]:
        draw.ellipse([ax - r, ay - r, ax + r, ay + r], fill=WHITE + (alpha,))

    return img


# ---------------------------------------------------------------------------
# .icns generation
# ---------------------------------------------------------------------------

ICNS_SIZES = [16, 32, 64, 128, 256, 512, 1024]


def generate_icns(png_path: Path, icns_path: Path) -> bool:
    if not shutil.which("sips") or not shutil.which("iconutil"):
        print("  Skipping .icns — sips/iconutil not found (not macOS?)")
        return False
    with tempfile.TemporaryDirectory() as tmp:
        iconset = Path(tmp) / "AppIcon.iconset"
        iconset.mkdir()
        for px in ICNS_SIZES:
            for scale, suffix in [(1, ""), (2, "@2x")]:
                actual = px * scale
                if actual > 1024:
                    continue
                dest = iconset / f"icon_{px}x{px}{suffix}.png"
                subprocess.run(
                    ["sips", "-z", str(actual), str(actual), str(png_path), "--out", str(dest)],
                    check=True, capture_output=True,
                )
        subprocess.run(
            ["iconutil", "-c", "icns", str(iconset), "-o", str(icns_path)],
            check=True, capture_output=True,
        )
    print(f"  Saved {icns_path}")
    return True


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    try:
        from PIL import Image
    except ImportError:
        sys.exit("ERROR: Pillow is required.\nInstall with:  pip install Pillow\n")

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    print("Refraction — logo generator\n")

    # Logo A: Spectrum Bars (used as the active app icon)
    print("[1] Generating spectrum-bars icon…")
    bars_img = generate_bars(SIZE)
    bars_path = ASSETS_DIR / "logo_refraction_bars.png"
    bars_img.save(bars_path, "PNG")
    print(f"  Saved {bars_path}")

    # Copy as active icon
    active_png = ASSETS_DIR / "icon.png"
    bars_img.save(active_png, "PNG")
    print(f"  Copied to {active_png} (active app icon)")

    # Logo B: Prism
    print("\n[2] Generating prism icon…")
    prism_img  = generate_prism(SIZE)
    prism_path = ASSETS_DIR / "logo_refraction_prism.png"
    prism_img.save(prism_path, "PNG")
    print(f"  Saved {prism_path}")

    # macOS .icns (bars variant)
    print("\n[3] Generating macOS .icns (bars variant)…")
    generate_icns(active_png, ASSETS_DIR / "AppIcon.icns")

    print("\nDone. Preview all variants:\n"
          f"  {ASSETS_DIR}/logo_refraction_bars.png\n"
          f"  {ASSETS_DIR}/logo_refraction_prism.png\n"
          f"  {ASSETS_DIR}/AppIcon.icns\n\n"
          "SVG sources (editable in Figma/Sketch/Inkscape):\n"
          f"  {ASSETS_DIR}/logo_refraction_bars.svg\n"
          f"  {ASSETS_DIR}/logo_refraction_prism.svg\n"
          f"  {ASSETS_DIR}/logo_refraction_s.svg\n")


if __name__ == "__main__":
    main()
