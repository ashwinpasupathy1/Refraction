"""
test_canvas_renderer.py
=======================
Unit tests for prism_canvas_renderer — bar scene builder, coordinate
transforms, RescaleHandle, and CanvasRenderer (using a mock canvas so
no display is required).

Run standalone:  python3 test_canvas_renderer.py
Or via harness:  python3 run_all.py canvas_renderer
"""

import sys, os, math, tempfile, warnings
import numpy as np
import pandas as pd
from unittest.mock import MagicMock, call, patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prism_test_harness as _h
from prism_test_harness import ok, fail, run, section, summarise

from prism_canvas_renderer import (
    _hex_to_rgb, _rgb_to_hex, _darken_hex, _rgba_to_hex, _blend_alpha,
    _fmt_tick_label, _calc_error_plain, _prism_palette_n,
    build_bar_scene,
    BarElement, BarScene,
    CoordTransform,
    RescaleHandle,
    CanvasRenderer,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

RNG = np.random.default_rng(42)


def _make_excel(groups: dict, path: str = None) -> str:
    """Write a flat-header Excel file and return its path."""
    if path is None:
        tf = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
        tf.close()
        path = tf.name
    max_n = max(len(v) for v in groups.values())
    data  = {}
    for name, vals in groups.items():
        col = list(vals) + [np.nan] * (max_n - len(vals))
        data[name] = col
    pd.DataFrame(data).to_excel(path, index=False)
    return path


def _make_kw(groups: dict, **extra) -> dict:
    """Build a minimal kwargs dict for build_bar_scene."""
    path = _make_excel(groups)
    kw = {
        "excel_path": path,
        "sheet": 0,
        "error": "sem",
        "bar_width": 0.6,
        "show_points": True,
        "font_size": 12.0,
        "alpha": 0.85,
        "title": "Test",
        "xlabel": "Group",
        "ytitle": "Value",
        "color": None,
    }
    kw.update(extra)
    return kw


def _mock_canvas():
    """Return a MagicMock that records canvas method calls."""
    canvas = MagicMock()
    # find_overlapping returns iterable; gettags returns list
    canvas.find_overlapping.return_value = []
    canvas.gettags.return_value = []
    # create_* methods return unique increasing item ids
    _counter = [0]
    def _next_id(*args, **kwargs):
        _counter[0] += 1
        return _counter[0]
    canvas.create_rectangle.side_effect = _next_id
    canvas.create_line.side_effect      = _next_id
    canvas.create_text.side_effect      = _next_id
    canvas.create_oval.side_effect      = _next_id
    canvas.winfo_width.return_value     = 560
    canvas.winfo_height.return_value    = 480
    return canvas


def _simple_scene(n_groups: int = 3, canvas_w: int = 560, canvas_h: int = 480) -> BarScene:
    groups = {f"G{i+1}": RNG.normal(5 * (i + 1), 1, 8) for i in range(n_groups)}
    kw = _make_kw(groups)
    try:
        scene = build_bar_scene(kw, canvas_w, canvas_h)
    finally:
        try:
            os.unlink(kw["excel_path"])
        except Exception:
            pass
    return scene


# ═════════════════════════════════════════════════════════════════════════════
# Section 1 — Colour helpers
# ═════════════════════════════════════════════════════════════════════════════
section("Colour helpers")


def test_hex_to_rgb_full():
    assert _hex_to_rgb("#e8453c") == (0xe8, 0x45, 0x3c)
run("_hex_to_rgb: full 6-digit hex", test_hex_to_rgb_full)


def test_hex_to_rgb_short():
    assert _hex_to_rgb("#f0a") == (0xff, 0x00, 0xaa)
run("_hex_to_rgb: 3-digit shorthand", test_hex_to_rgb_short)


def test_rgb_to_hex_roundtrip():
    for (r, g, b) in [(0, 0, 0), (255, 255, 255), (18, 100, 200)]:
        h = _rgb_to_hex(r, g, b)
        assert _hex_to_rgb(h) == (r, g, b), f"roundtrip failed for {r},{g},{b}"
run("_rgb_to_hex / _hex_to_rgb roundtrip", test_rgb_to_hex_roundtrip)


def test_darken_hex_black():
    assert _darken_hex("#000000", 0.5) == "#000000"
run("_darken_hex: black stays black", test_darken_hex_black)


def test_darken_hex_white():
    r, g, b = _hex_to_rgb(_darken_hex("#ffffff", 0.5))
    assert r == 127 and g == 127 and b == 127
run("_darken_hex: white → mid grey at factor=0.5", test_darken_hex_white)


def test_darken_hex_prism_red():
    result = _darken_hex("#E8453C", 0.65)
    r, g, b = _hex_to_rgb(result)
    # Should be significantly darker
    assert r < 0xE8 and g < 0x45 and b < 0x3C
run("_darken_hex: prism red darkens correctly", test_darken_hex_prism_red)


def test_rgba_to_hex_string():
    assert _rgba_to_hex("#2274A5") == "#2274A5"
run("_rgba_to_hex: passes through hex string", test_rgba_to_hex_string)


def test_rgba_to_hex_float_tuple():
    h = _rgba_to_hex((1.0, 0.0, 0.0))
    assert h.lower() == "#ff0000"
run("_rgba_to_hex: float RGB tuple", test_rgba_to_hex_float_tuple)


def test_blend_alpha_opaque():
    # Alpha=1 → colour unchanged
    result = _blend_alpha("#ff0000", 1.0, "#ffffff")
    assert _hex_to_rgb(result)[0] == 255
run("_blend_alpha: alpha=1.0 preserves colour", test_blend_alpha_opaque)


def test_blend_alpha_transparent():
    # Alpha=0 → background colour
    result = _blend_alpha("#ff0000", 0.0, "#ffffff")
    assert result.lower() == "#ffffff"
run("_blend_alpha: alpha=0.0 returns background", test_blend_alpha_transparent)


# ═════════════════════════════════════════════════════════════════════════════
# Section 2 — Tick label formatter
# ═════════════════════════════════════════════════════════════════════════════
section("Tick label formatter")


def test_fmt_zero():
    assert _fmt_tick_label(0.0) == "0"
run("_fmt_tick_label: zero", test_fmt_zero)


def test_fmt_integer():
    assert _fmt_tick_label(5.0) == "5"
    assert _fmt_tick_label(100.0) == "100"
run("_fmt_tick_label: integers", test_fmt_integer)


def test_fmt_decimal():
    assert "." in _fmt_tick_label(2.5)
run("_fmt_tick_label: decimals contain dot", test_fmt_decimal)


def test_fmt_large():
    label = _fmt_tick_label(1_000_000.0)
    assert "e" in label.lower()
run("_fmt_tick_label: large numbers use scientific notation", test_fmt_large)


def test_fmt_small():
    label = _fmt_tick_label(0.0001)
    assert "e" in label.lower()
run("_fmt_tick_label: very small numbers use scientific notation", test_fmt_small)


# ═════════════════════════════════════════════════════════════════════════════
# Section 3 — _calc_error_plain
# ═════════════════════════════════════════════════════════════════════════════
section("_calc_error_plain statistics")


def test_calc_error_sem_known():
    vals = np.array([2.0, 4.0, 6.0, 8.0])   # mean=5, sd=2.581…, sem=1.291…
    m, err = _calc_error_plain(vals, "sem")
    assert abs(m - 5.0) < 1e-9
    expected_sem = float(np.std(vals, ddof=1)) / math.sqrt(len(vals))
    assert abs(err - expected_sem) < 1e-9
run("_calc_error_plain: SEM matches manual computation", test_calc_error_sem_known)


def test_calc_error_sd_known():
    vals = np.array([1.0, 3.0, 5.0, 7.0, 9.0])
    m, err = _calc_error_plain(vals, "sd")
    assert abs(m - 5.0) < 1e-9
    assert abs(err - float(np.std(vals, ddof=1))) < 1e-9
run("_calc_error_plain: SD matches manual computation", test_calc_error_sd_known)


def test_calc_error_ci95_wider_than_sem():
    vals = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    _, sem = _calc_error_plain(vals, "sem")
    _, ci  = _calc_error_plain(vals, "ci95")
    assert ci > sem, f"CI95 ({ci:.4f}) should be wider than SEM ({sem:.4f})"
run("_calc_error_plain: CI95 wider than SEM", test_calc_error_ci95_wider_than_sem)


def test_calc_error_single_val():
    vals = np.array([5.0])
    m, err = _calc_error_plain(vals, "sem")
    assert m == 5.0 and err == 0.0
run("_calc_error_plain: single value → error=0", test_calc_error_single_val)


# ═════════════════════════════════════════════════════════════════════════════
# Section 4 — BarScene builder
# ═════════════════════════════════════════════════════════════════════════════
section("build_bar_scene")


def test_scene_element_count():
    n = 4
    groups = {f"G{i}": RNG.normal(i, 1, 6) for i in range(1, n + 1)}
    kw  = _make_kw(groups)
    try:
        scene = build_bar_scene(kw, 500, 450)
        assert len(scene.elements) == n
    finally:
        os.unlink(kw["excel_path"])
run("build_bar_scene: element count matches group count", test_scene_element_count)


def test_scene_y_min_zero():
    groups = {"A": RNG.normal(10, 1, 8), "B": RNG.normal(15, 1, 8)}
    kw = _make_kw(groups)
    try:
        scene = build_bar_scene(kw, 500, 450)
        assert scene.y_min == 0.0
    finally:
        os.unlink(kw["excel_path"])
run("build_bar_scene: y_min is always 0", test_scene_y_min_zero)


def test_scene_y_max_headroom():
    groups = {"A": np.array([10.0] * 8)}
    kw = _make_kw(groups)
    try:
        scene = build_bar_scene(kw, 500, 450)
        assert scene.y_max > 10.0, "y_max must add headroom above the mean"
    finally:
        os.unlink(kw["excel_path"])
run("build_bar_scene: y_max includes headroom above data", test_scene_y_max_headroom)


def test_scene_bar_tags_unique():
    groups = {f"G{i}": RNG.normal(5, 1, 6) for i in range(5)}
    kw = _make_kw(groups)
    try:
        scene = build_bar_scene(kw, 500, 450)
        tags = [e.bar_tag for e in scene.elements]
        assert len(set(tags)) == len(tags), "bar_tags must be unique"
    finally:
        os.unlink(kw["excel_path"])
run("build_bar_scene: bar_tags are all unique", test_scene_bar_tags_unique)


def test_scene_colors_are_hex():
    groups = {"A": RNG.normal(5, 1, 6), "B": RNG.normal(8, 1, 6)}
    kw = _make_kw(groups)
    try:
        scene = build_bar_scene(kw, 500, 450)
        for el in scene.elements:
            assert el.color.startswith("#"), f"{el.color!r} not hex"
            assert el.edge_color.startswith("#"), f"{el.edge_color!r} not hex"
    finally:
        os.unlink(kw["excel_path"])
run("build_bar_scene: all element colours are hex strings", test_scene_colors_are_hex)


def test_scene_means_match_data():
    vals_a = np.array([1.0, 3.0, 5.0])
    vals_b = np.array([2.0, 4.0, 6.0])
    groups = {"A": vals_a, "B": vals_b}
    kw = _make_kw(groups)
    try:
        scene = build_bar_scene(kw, 500, 450)
        assert abs(scene.elements[0].mean - 3.0) < 1e-9
        assert abs(scene.elements[1].mean - 4.0) < 1e-9
    finally:
        os.unlink(kw["excel_path"])
run("build_bar_scene: element means match data means", test_scene_means_match_data)


# ═════════════════════════════════════════════════════════════════════════════
# Section 5 — CoordTransform
# ═════════════════════════════════════════════════════════════════════════════
section("CoordTransform")


def _make_tf(y_min=0.0, y_max=10.0, n=3, w=600, h=500,
             ml=60, mr=20, mt=40, mb=60):
    """Build a minimal BarScene + CoordTransform for geometry tests."""
    # Build fake elements
    elements = [
        BarElement(group=f"G{i}", index=i, mean=5.0, error=1.0,
                   color="#ff0000", edge_color="#800000",
                   points=np.array([4.0, 5.0, 6.0]),
                   bar_tag=f"bar_{i}", err_tag=f"err_{i}", pts_tag=f"pts_{i}")
        for i in range(n)
    ]
    scene = BarScene(
        elements=elements, group_order=[f"G{i}" for i in range(n)],
        title="", xlabel="", ylabel="",
        error_type="sem", bar_width=0.6, show_points=False,
        font_size=12.0, alpha=0.85,
        y_min=y_min, y_max=y_max,
        canvas_w=w, canvas_h=h,
        margin_left=ml, margin_right=mr, margin_top=mt, margin_bottom=mb,
    )
    return CoordTransform(scene)


def test_transform_y_min_at_bottom():
    tf = _make_tf(y_min=0.0, y_max=10.0, h=500, mt=40, mb=60)
    cy = tf.y(0.0)
    assert cy == 500 - 60, f"y_min should map to bottom pixel, got {cy}"
run("CoordTransform.y: y_min maps to bottom of plot area", test_transform_y_min_at_bottom)


def test_transform_y_max_at_top():
    tf = _make_tf(y_min=0.0, y_max=10.0, h=500, mt=40, mb=60)
    cy = tf.y(10.0)
    assert cy == 40, f"y_max should map to top of plot area, got {cy}"
run("CoordTransform.y: y_max maps to top of plot area", test_transform_y_max_at_top)


def test_transform_y_midpoint():
    tf = _make_tf(y_min=0.0, y_max=10.0, h=500, mt=40, mb=60)
    cy = tf.y(5.0)
    expected = 40 + (500 - 40 - 60) // 2    # midpoint of plot area
    assert abs(cy - expected) <= 1, f"midpoint mismatch: {cy} vs {expected}"
run("CoordTransform.y: midpoint data value maps to centre pixel", test_transform_y_midpoint)


def test_transform_x_first_group_centred():
    tf = _make_tf(n=4, w=600, ml=60, mr=20)
    # Cell width = (600 - 60 - 20) / 4 = 130
    # Centre of first cell = 60 + 130*0.5 = 125
    cx = tf.x(0)
    assert cx == 60 + int(130 * 0.5), f"x(0) = {cx}"
run("CoordTransform.x: first group centred in first cell", test_transform_x_first_group_centred)


def test_transform_y_zero_at_bottom():
    tf = _make_tf(y_min=0.0, y_max=10.0, h=500, mt=40, mb=60)
    assert tf.y_zero() == 500 - 60
run("CoordTransform.y_zero: baseline at bottom for y_min=0", test_transform_y_zero_at_bottom)


def test_transform_bar_half_w_positive():
    tf = _make_tf(n=3, w=600, ml=60, mr=20)
    assert tf.bar_half_w() > 0
run("CoordTransform.bar_half_w: positive value", test_transform_bar_half_w_positive)


def test_transform_canvas_to_group():
    tf = _make_tf(n=3, w=600, ml=60, mr=20)
    # Cell width = (600 - 60 - 20) / 3 ≈ 173.3
    # First cell centre ≈ 60 + 86 = 146
    g = tf.canvas_to_group(146)
    assert g == 0, f"Expected group 0 at x=146, got {g}"
run("CoordTransform.canvas_to_group: click maps to correct group", test_transform_canvas_to_group)


def test_transform_canvas_to_group_out_of_bounds():
    tf = _make_tf(n=3, w=600, ml=60, mr=20)
    assert tf.canvas_to_group(10) is None    # left of margin
    assert tf.canvas_to_group(595) is None   # right of margin
run("CoordTransform.canvas_to_group: returns None outside plot area", test_transform_canvas_to_group_out_of_bounds)


# ═════════════════════════════════════════════════════════════════════════════
# Section 6 — RescaleHandle
# ═════════════════════════════════════════════════════════════════════════════
section("RescaleHandle")


def _make_handle(**kw) -> RescaleHandle:
    defaults = dict(y_min=0.0, y_max=10.0, canvas_w=600, canvas_h=500,
                    margin_left=60, margin_right=20, margin_top=40,
                    margin_bottom=60, n_groups=3)
    defaults.update(kw)
    return RescaleHandle(**defaults)


def test_rh_y_fraction_zero():
    rh = _make_handle(y_min=0.0, y_max=10.0)
    assert rh.y_fraction(0.0) == 0.0
run("RescaleHandle.y_fraction: y_min → 0.0", test_rh_y_fraction_zero)


def test_rh_y_fraction_max():
    rh = _make_handle(y_min=0.0, y_max=10.0)
    assert rh.y_fraction(10.0) == 1.0
run("RescaleHandle.y_fraction: y_max → 1.0", test_rh_y_fraction_max)


def test_rh_y_fraction_mid():
    rh = _make_handle(y_min=0.0, y_max=10.0)
    assert abs(rh.y_fraction(5.0) - 0.5) < 1e-9
run("RescaleHandle.y_fraction: midpoint → 0.5", test_rh_y_fraction_mid)


def test_rh_to_canvas_y_bottom():
    rh = _make_handle(y_min=0.0, y_max=10.0, canvas_h=500, margin_bottom=60)
    cy = rh.to_canvas_y(0.0)
    assert cy == 500 - 60
run("RescaleHandle.to_canvas_y: y_min at bottom", test_rh_to_canvas_y_bottom)


def test_rh_to_canvas_y_top():
    rh = _make_handle(y_min=0.0, y_max=10.0, canvas_h=500, margin_top=40)
    cy = rh.to_canvas_y(10.0)
    assert cy == 40
run("RescaleHandle.to_canvas_y: y_max at top", test_rh_to_canvas_y_top)


def test_rh_set_y_range_immutable():
    rh1 = _make_handle(y_min=0.0, y_max=10.0)
    rh2 = rh1.set_y_range(2.0, 8.0)
    assert rh1.y_min == 0.0 and rh1.y_max == 10.0, "original unchanged"
    assert rh2.y_min == 2.0 and rh2.y_max == 8.0, "new handle correct"
run("RescaleHandle.set_y_range: immutable — original unchanged", test_rh_set_y_range_immutable)


def test_rh_set_canvas_size():
    rh1 = _make_handle(canvas_w=600, canvas_h=500)
    rh2 = rh1.set_canvas_size(800, 700)
    assert rh1.canvas_w == 600 and rh1.canvas_h == 500, "original unchanged"
    assert rh2.canvas_w == 800 and rh2.canvas_h == 700
run("RescaleHandle.set_canvas_size: immutable update", test_rh_set_canvas_size)


def test_rh_nice_ticks_count():
    rh = _make_handle(y_min=0.0, y_max=10.0)
    ticks = rh.nice_y_ticks(n_ticks=5)
    assert 3 <= len(ticks) <= 8, f"Expected 3–8 ticks, got {len(ticks)}: {ticks}"
run("RescaleHandle.nice_y_ticks: returns reasonable number of ticks", test_rh_nice_ticks_count)


def test_rh_nice_ticks_within_range():
    rh = _make_handle(y_min=0.0, y_max=10.0)
    ticks = rh.nice_y_ticks()
    for t in ticks:
        assert rh.y_min - 1e-9 <= t <= rh.y_max + 1e-9, f"tick {t} outside [{rh.y_min}, {rh.y_max}]"
run("RescaleHandle.nice_y_ticks: all ticks within y range", test_rh_nice_ticks_within_range)


def test_rh_from_scene():
    scene = _simple_scene(n_groups=3)
    rh = RescaleHandle.from_scene(scene)
    assert rh.y_min == scene.y_min
    assert rh.y_max == scene.y_max
    assert rh.canvas_w == scene.canvas_w
    assert rh.n_groups == scene.n_groups
run("RescaleHandle.from_scene: matches BarScene geometry", test_rh_from_scene)


# ═════════════════════════════════════════════════════════════════════════════
# Section 7 — CanvasRenderer (mocked canvas)
# ═════════════════════════════════════════════════════════════════════════════
section("CanvasRenderer (mock canvas)")


def test_renderer_render_calls_delete_all():
    scene    = _simple_scene(n_groups=2)
    canvas   = _mock_canvas()
    renderer = CanvasRenderer(canvas, scene)
    renderer.render()
    canvas.delete.assert_called_with("all")
run("CanvasRenderer.render: calls canvas.delete('all')", test_renderer_render_calls_delete_all)


def test_renderer_render_creates_rectangles():
    n_groups = 3
    scene    = _simple_scene(n_groups=n_groups)
    canvas   = _mock_canvas()
    renderer = CanvasRenderer(canvas, scene)
    renderer.render()
    rect_calls = canvas.create_rectangle.call_count
    # At least n_groups bars + 1 background rect
    assert rect_calls >= n_groups, f"Expected ≥{n_groups} rectangles, got {rect_calls}"
run("CanvasRenderer.render: creates at least n_groups rectangles", test_renderer_render_creates_rectangles)


def test_renderer_hit_test_returns_tag():
    scene  = _simple_scene(n_groups=3)
    canvas = _mock_canvas()

    # Simulate overlapping items with bar tag
    _item_tags = {99: ["bar_1"]}
    canvas.find_overlapping.return_value = [99]
    canvas.gettags.side_effect = lambda iid: _item_tags.get(iid, [])

    renderer = CanvasRenderer(canvas, scene)
    renderer.render()

    result = renderer.hit_test(200, 200)
    assert result == "bar_1", f"Expected 'bar_1', got {result!r}"
run("CanvasRenderer.hit_test: returns bar_tag from overlapping items", test_renderer_hit_test_returns_tag)


def test_renderer_hit_test_miss():
    scene  = _simple_scene(n_groups=2)
    canvas = _mock_canvas()
    canvas.find_overlapping.return_value = []

    renderer = CanvasRenderer(canvas, scene)
    renderer.render()

    result = renderer.hit_test(5, 5)
    assert result is None
run("CanvasRenderer.hit_test: returns None when no bar found", test_renderer_hit_test_miss)


def test_renderer_recolor():
    scene  = _simple_scene(n_groups=2)
    canvas = _mock_canvas()
    renderer = CanvasRenderer(canvas, scene)
    renderer.render()

    # Manually register bar_0 rect so recolor can find it
    fake_id = 42
    renderer._bar_rects["bar_0"] = fake_id

    renderer.recolor("bar_0", "#00ff00")
    canvas.itemconfig.assert_called_once()
    call_args = canvas.itemconfig.call_args
    assert call_args[0][0] == fake_id, "itemconfig called with wrong item id"
    # fill kwarg should contain the new colour
    kwargs = call_args[1]
    assert "fill" in kwargs, "itemconfig not called with fill keyword"
run("CanvasRenderer.recolor: calls canvas.itemconfig with correct item and fill", test_renderer_recolor)


def test_renderer_recolor_tracks_color():
    scene  = _simple_scene(n_groups=2)
    canvas = _mock_canvas()
    renderer = CanvasRenderer(canvas, scene)
    renderer.render()

    renderer._bar_rects["bar_1"] = 77
    renderer.recolor("bar_1", "#123456")
    assert renderer.current_color("bar_1") == "#123456"
run("CanvasRenderer.recolor: tracks current colour via current_color()", test_renderer_recolor_tracks_color)


def test_renderer_recolor_nonexistent_tag():
    """Recoloring an unknown tag should silently do nothing."""
    scene  = _simple_scene(n_groups=2)
    canvas = _mock_canvas()
    renderer = CanvasRenderer(canvas, scene)
    renderer.render()
    renderer.recolor("bar_999", "#ff0000")   # should not raise
    canvas.itemconfig.assert_not_called()
run("CanvasRenderer.recolor: unknown tag is silently ignored", test_renderer_recolor_nonexistent_tag)


def test_renderer_rescale_handle_set_after_render():
    scene  = _simple_scene(n_groups=3)
    canvas = _mock_canvas()
    renderer = CanvasRenderer(canvas, scene)
    assert renderer.rescale_handle is None, "handle should be None before render"
    renderer.render()
    assert renderer.rescale_handle is not None, "handle should exist after render"
run("CanvasRenderer.rescale_handle: None before render, set after", test_renderer_rescale_handle_set_after_render)


def test_renderer_rescale_preserves_colors():
    scene  = _simple_scene(n_groups=2)
    canvas = _mock_canvas()
    renderer = CanvasRenderer(canvas, scene)
    renderer.render()

    renderer._bar_rects["bar_0"] = 10
    renderer.recolor("bar_0", "#aabbcc")

    # Rescale with updated Y range
    rh = renderer.rescale_handle.set_y_range(0.0, 50.0)
    renderer.rescale(rh)

    # After rescale the color should have been re-applied
    assert renderer.current_color("bar_0") == "#aabbcc"
run("CanvasRenderer.rescale: reapplies user-set colours after rescale", test_renderer_rescale_preserves_colors)


# ═════════════════════════════════════════════════════════════════════════════
# Section 8 — BarElement helpers
# ═════════════════════════════════════════════════════════════════════════════
section("BarElement helpers")


def test_bar_element_n():
    vals = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    el = BarElement(group="A", index=0, mean=3.0, error=1.0,
                    color="#ff0000", edge_color="#800000", points=vals,
                    bar_tag="bar_0", err_tag="err_0", pts_tag="pts_0")
    assert el.n == 5
run("BarElement.n: returns correct point count", test_bar_element_n)


def test_bar_element_y_top():
    el = BarElement(group="A", index=0, mean=5.0, error=2.0,
                    color="#ff0000", edge_color="#800000",
                    points=np.array([5.0]),
                    bar_tag="bar_0", err_tag="err_0", pts_tag="pts_0")
    assert el.y_top == 7.0
run("BarElement.y_top: mean + error", test_bar_element_y_top)


def test_bar_element_y_bot_floor():
    el = BarElement(group="A", index=0, mean=1.0, error=5.0,
                    color="#ff0000", edge_color="#800000",
                    points=np.array([1.0]),
                    bar_tag="bar_0", err_tag="err_0", pts_tag="pts_0")
    assert el.y_bot == 0.0, "y_bot must not go negative"
run("BarElement.y_bot: floored at 0 when mean < error", test_bar_element_y_bot_floor)


def test_scene_element_by_tag():
    scene = _simple_scene(n_groups=3)
    el = scene.element_by_tag("bar_2")
    assert el is not None and el.bar_tag == "bar_2"
    assert scene.element_by_tag("bar_99") is None
run("BarScene.element_by_tag: lookup and None for missing", test_scene_element_by_tag)


# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────

# ═════════════════════════════════════════════════════════════════════════════
# Section 9 — ClickResult
# ═════════════════════════════════════════════════════════════════════════════
section("ClickResult")

from prism_canvas_renderer import ClickResult

def test_clickresult_defaults():
    cr = ClickResult()
    assert cr.kind is None
    assert cr.bar_tag is None
run("ClickResult: default kind and bar_tag are None", test_clickresult_defaults)

def test_clickresult_bar():
    cr = ClickResult(kind="bar", bar_tag="bar_2")
    assert cr.kind == "bar"
    assert cr.bar_tag == "bar_2"
run("ClickResult: stores kind and bar_tag", test_clickresult_bar)

def test_clickresult_y_drag():
    cr = ClickResult(kind="y_drag_start")
    assert cr.kind == "y_drag_start"
    assert cr.bar_tag is None
run("ClickResult: y_drag_start has no bar_tag", test_clickresult_y_drag)

def test_clickresult_barwidth():
    cr = ClickResult(kind="barwidth_drag_start")
    assert cr.kind == "barwidth_drag_start"
run("ClickResult: barwidth_drag_start", test_clickresult_barwidth)


# ═════════════════════════════════════════════════════════════════════════════
# Section 10 — RescaleHandle set_bar_width (P11-c)
# ═════════════════════════════════════════════════════════════════════════════
section("RescaleHandle.set_bar_width (P11-c)")

def test_rh_set_bar_width_basic():
    rh1 = _make_handle()
    rh2 = rh1.set_bar_width(0.8)
    assert rh1.bar_width == 0.6, "original unchanged"
    assert abs(rh2.bar_width - 0.8) < 1e-9
run("RescaleHandle.set_bar_width: immutable update", test_rh_set_bar_width_basic)

def test_rh_set_bar_width_clamp_low():
    rh = _make_handle()
    assert rh.set_bar_width(0.0).bar_width == 0.05
run("RescaleHandle.set_bar_width: clamps to 0.05 minimum", test_rh_set_bar_width_clamp_low)

def test_rh_set_bar_width_clamp_high():
    rh = _make_handle()
    assert rh.set_bar_width(2.0).bar_width == 1.0
run("RescaleHandle.set_bar_width: clamps to 1.0 maximum", test_rh_set_bar_width_clamp_high)


# ═════════════════════════════════════════════════════════════════════════════
# Section 11 — BarScene.with_geometry
# ═════════════════════════════════════════════════════════════════════════════
section("BarScene.with_geometry")

def test_with_geometry_y_range():
    scene = _simple_scene(n_groups=2)
    s2    = scene.with_geometry(y_min=1.0, y_max=20.0)
    assert s2.y_min == 1.0 and s2.y_max == 20.0
    assert scene.y_min == 0.0, "original unchanged"
run("BarScene.with_geometry: updates y_min/y_max", test_with_geometry_y_range)

def test_with_geometry_bar_width():
    scene = _simple_scene(n_groups=2)
    s2    = scene.with_geometry(bar_width=0.9)
    assert abs(s2.bar_width - 0.9) < 1e-9
    # elements list is shared (same objects)
    assert s2.elements is scene.elements
run("BarScene.with_geometry: updates bar_width, shares elements", test_with_geometry_bar_width)


# ═════════════════════════════════════════════════════════════════════════════
# Section 12 — CanvasRenderer P11 features (mock canvas)
# ═════════════════════════════════════════════════════════════════════════════
section("CanvasRenderer P11 (mock canvas)")

def _renderer_with_items():
    """Return a renderer with render() called and known item IDs registered."""
    scene    = _simple_scene(n_groups=3)
    canvas   = _mock_canvas()
    renderer = CanvasRenderer(canvas, scene)
    renderer.render()
    return renderer, canvas, scene


def test_renderer_y_drag_handle_created():
    renderer, canvas, scene = _renderer_with_items()
    # The polygon call for the Y-drag handle should have been made
    assert canvas.create_polygon.call_count >= 1, (
        "create_polygon not called (no Y-drag handle drawn)")
    assert renderer._y_drag_id is not None
run("CanvasRenderer: Y-drag handle drawn after render()", test_renderer_y_drag_handle_created)


def test_renderer_bw_handles_created():
    n = 3
    renderer, canvas, scene = _renderer_with_items()
    # One BW handle rect per group (on top of the bar rects)
    assert len(renderer._bw_handles) == n, (
        f"Expected {n} BW handles, got {len(renderer._bw_handles)}")
run("CanvasRenderer: bar-width handles created for each group", test_renderer_bw_handles_created)


def test_renderer_err_stems_created():
    n = 3
    renderer, canvas, scene = _renderer_with_items()
    assert len(renderer._err_stems) == n
    assert len(renderer._err_top_caps) == n
    assert len(renderer._err_bot_caps) == n
run("CanvasRenderer: separate stem/top-cap/bot-cap IDs stored", test_renderer_err_stems_created)


def test_renderer_pts_ovals_created():
    n_groups = 2
    scene    = _simple_scene(n_groups=n_groups)
    canvas   = _mock_canvas()
    renderer = CanvasRenderer(canvas, scene)
    renderer.render()
    assert len(renderer._pts_ovals) == n_groups
    for tag, ovals in renderer._pts_ovals.items():
        assert len(ovals) > 0, f"no ovals registered for {tag}"
run("CanvasRenderer: jitter oval IDs stored per group", test_renderer_pts_ovals_created)


def test_on_press_returns_clickresult():
    renderer, canvas, _ = _renderer_with_items()
    event = type("E", (), {"x": 5, "y": 5})()   # outside plot area
    canvas.find_overlapping.return_value = []
    canvas.gettags.return_value = []
    result = renderer.on_press(event)
    assert isinstance(result, ClickResult)
    assert result.kind is None
run("CanvasRenderer.on_press: returns ClickResult(None) on background click",
    test_on_press_returns_clickresult)


def test_on_press_returns_bar_click():
    renderer, canvas, _ = _renderer_with_items()
    # Simulate a click that overlaps bar_1
    canvas.find_overlapping.return_value = [55]
    canvas.gettags.return_value = ["bar_1", "bar"]
    event = type("E", (), {"x": 200, "y": 200})()
    result = renderer.on_press(event)
    assert result.kind == "bar"
    assert result.bar_tag == "bar_1"
run("CanvasRenderer.on_press: returns ClickResult('bar') when bar clicked",
    test_on_press_returns_bar_click)


def test_on_press_y_drag_near_handle():
    renderer, canvas, scene = _renderer_with_items()
    # Simulate click exactly on Y-drag handle position
    hx = scene.margin_left
    hy = scene.margin_top - 6    # _Y_HANDLE_H // 2
    event = type("E", (), {"x": hx, "y": hy})()
    # Y drag handle must not be a "bwh_" or "bar_" tag
    canvas.find_overlapping.return_value = []
    canvas.gettags.return_value = []
    result = renderer.on_press(event)
    assert result.kind == "y_drag_start", (
        f"Expected y_drag_start at ({hx},{hy}), got {result.kind!r}")
run("CanvasRenderer.on_press: returns y_drag_start when near Y handle",
    test_on_press_y_drag_near_handle)


def test_on_motion_y_drag_calls_incremental():
    """on_motion during y_drag should update scene y_max."""
    renderer, canvas, scene = _renderer_with_items()
    # Start a Y drag
    renderer._drag = {"kind": "y_drag"}

    # Simulate dragging to near the top of the plot area
    # cy = margin_top means y_max → infinity (data above top)
    # cy = canvas_h - margin_bottom means y_max → 0
    # Use cy = margin_top + 10 (near top) so new_ymax >> current
    cy = scene.margin_top + 10
    event = type("E", (), {"x": scene.margin_left, "y": cy})()

    old_ymax = renderer._scene.y_max
    renderer.on_motion(event)
    # y_max should have changed
    new_ymax = renderer._scene.y_max
    assert new_ymax != old_ymax, "y_max unchanged after y_drag on_motion"
run("CanvasRenderer.on_motion: y_drag changes scene.y_max incrementally",
    test_on_motion_y_drag_calls_incremental)


def test_on_motion_barwidth_drag():
    """on_motion during barwidth_drag should change scene.bar_width."""
    renderer, canvas, scene = _renderer_with_items()
    old_bw = scene.bar_width
    renderer._drag = {
        "kind":      "barwidth_drag",
        "cx_start":  200,
        "bw_start":  old_bw,
    }
    # Drag 40px to the right → bar_width increases
    event = type("E", (), {"x": 240, "y": 300})()
    renderer.on_motion(event)
    assert renderer._scene.bar_width != old_bw, (
        "bar_width unchanged after barwidth_drag on_motion")
run("CanvasRenderer.on_motion: barwidth_drag changes scene.bar_width",
    test_on_motion_barwidth_drag)


def test_on_release_clears_drag():
    renderer, canvas, _ = _renderer_with_items()
    renderer._drag = {"kind": "y_drag"}
    event = type("E", (), {"x": 0, "y": 0})()
    renderer.on_release(event)
    assert renderer._drag is None
run("CanvasRenderer.on_release: clears drag state", test_on_release_clears_drag)


def test_incremental_rescale_y_calls_coords():
    """_incremental_rescale_y must call canvas.coords() for each bar rect."""
    renderer, canvas, scene = _renderer_with_items()
    n = scene.n_groups
    # Register fake rect IDs
    for i, el in enumerate(scene.elements):
        renderer._bar_rects[el.bar_tag] = i + 100

    canvas.coords.reset_mock()
    renderer._incremental_rescale_y(0.0, scene.y_max * 2)
    # At minimum one coords call per bar rect
    assert canvas.coords.call_count >= n, (
        f"Expected ≥{n} coords() calls, got {canvas.coords.call_count}")
run("CanvasRenderer._incremental_rescale_y: calls canvas.coords() per bar",
    test_incremental_rescale_y_calls_coords)


def test_incremental_rescale_bw_calls_coords():
    renderer, canvas, scene = _renderer_with_items()
    n = scene.n_groups
    for i, el in enumerate(scene.elements):
        renderer._bar_rects[el.bar_tag] = i + 200
    canvas.coords.reset_mock()
    renderer._incremental_rescale_bw(0.4)
    assert canvas.coords.call_count >= n
run("CanvasRenderer._incremental_rescale_bw: calls canvas.coords() per bar",
    test_incremental_rescale_bw_calls_coords)


def test_rescale_routes_incremental_for_y_only():
    """rescale() with only Y changed must NOT call canvas.delete('all')."""
    renderer, canvas, scene = _renderer_with_items()
    canvas.delete.reset_mock()
    rh = renderer.rescale_handle.set_y_range(0.0, scene.y_max * 1.5)
    renderer.rescale(rh)
    # Full redraw would call delete("all"); incremental must not
    for c in canvas.delete.call_args_list:
        assert c.args != ("all",), "Incremental rescale called delete('all')"
run("CanvasRenderer.rescale: Y-only change is incremental (no delete('all'))",
    test_rescale_routes_incremental_for_y_only)


def test_rescale_full_on_size_change():
    """rescale() with canvas size change must call delete('all') for full redraw."""
    renderer, canvas, scene = _renderer_with_items()
    canvas.delete.reset_mock()
    rh = renderer.rescale_handle.set_canvas_size(
        scene.canvas_w + 100, scene.canvas_h + 80)
    renderer.rescale(rh)
    delete_all_calls = [c for c in canvas.delete.call_args_list
                        if c.args == ("all",)]
    assert len(delete_all_calls) >= 1, (
        "Full rescale (size change) should call delete('all')")
run("CanvasRenderer.rescale: size change triggers full redraw",
    test_rescale_full_on_size_change)


def test_snapshot_png_returns_none_gracefully():
    """snapshot_png() must not raise even when PIL isn't available / no display."""
    renderer, canvas, _ = _renderer_with_items()
    # Don't call update_idletasks / winfo_rootx on mock canvas — it'll MagicMock
    # Just verify the method exists and returns None or bytes without raising
    try:
        result = renderer.snapshot_png()
        assert result is None or isinstance(result, bytes)
    except Exception as e:
        raise AssertionError(f"snapshot_png() raised: {e}")
run("CanvasRenderer.snapshot_png: returns None or bytes, never raises",
    test_snapshot_png_returns_none_gracefully)



# ═════════════════════════════════════════════════════════════════════════════
# Section 13 — GroupedBarScene builder
# ═════════════════════════════════════════════════════════════════════════════
section("GroupedBarScene builder")

from prism_canvas_renderer import (
    GroupedBarGroup, GroupedBarScene,
    build_grouped_bar_scene,
    GroupedCoordTransform,
    GroupedCanvasRenderer,
)


def _make_grouped_excel(cats, subs, data_dict, path=None):
    """
    Write a grouped-bar Excel.
    data_dict: {(cat, sub): [values]}
    Layout: row0=categories, row1=subgroups, rows2+=values.
    """
    if path is None:
        tf = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
        tf.close(); path = tf.name

    # Build column list: one column per (cat,sub) combo
    cols = [(c, s) for c in cats for s in subs]
    max_n = max(len(data_dict.get(k, [])) for k in cols) if cols else 0

    rows = [[c for c, _ in cols], [s for _, s in cols]]
    for ri in range(max_n):
        row = []
        for k in cols:
            vals = data_dict.get(k, [])
            row.append(vals[ri] if ri < len(vals) else np.nan)
        rows.append(row)
    pd.DataFrame(rows).to_excel(path, index=False, header=False)
    return path


def _make_grouped_kw(cats, subs, data_dict, **extra):
    path = _make_grouped_excel(cats, subs, data_dict)
    kw = {
        "excel_path": path, "sheet": 0,
        "error": "sem", "bar_width": 0.6,
        "show_points": True, "font_size": 12.0,
        "alpha": 0.85, "title": "Grouped", "xlabel": "Category",
        "ytitle": "Value", "color": None,
    }
    kw.update(extra)
    return kw


def _simple_grouped_scene(n_cats=3, n_subs=2, canvas_w=620, canvas_h=480):
    cats = [f"Cat{i}" for i in range(n_cats)]
    subs = [f"Sub{j}" for j in range(n_subs)]
    data = {(c, s): RNG.normal(5, 1, 6) for c in cats for s in subs}
    kw = _make_grouped_kw(cats, subs, data)
    try:
        scene = build_grouped_bar_scene(kw, canvas_w, canvas_h)
    finally:
        try: os.unlink(kw["excel_path"])
        except Exception: pass
    return scene


def test_grouped_scene_group_count():
    scene = _simple_grouped_scene(n_cats=3, n_subs=2)
    assert len(scene.groups) == 6
    assert scene.n_cats == 3
    assert scene.n_subs == 2
run("build_grouped_bar_scene: group count = n_cats × n_subs", test_grouped_scene_group_count)


def test_grouped_scene_categories_order():
    cats = ["Alpha", "Beta", "Gamma"]
    subs = ["Male", "Female"]
    data = {(c, s): RNG.normal(5, 1, 5) for c in cats for s in subs}
    kw = _make_grouped_kw(cats, subs, data)
    try:
        scene = build_grouped_bar_scene(kw, 600, 480)
        assert scene.categories == cats, f"Categories order wrong: {scene.categories}"
        assert scene.subgroups  == subs, f"Subgroups order wrong: {scene.subgroups}"
    finally:
        os.unlink(kw["excel_path"])
run("build_grouped_bar_scene: category and subgroup order preserved", test_grouped_scene_categories_order)


def test_grouped_scene_y_min_zero():
    scene = _simple_grouped_scene()
    assert scene.y_min == 0.0
run("build_grouped_bar_scene: y_min is always 0.0", test_grouped_scene_y_min_zero)


def test_grouped_scene_y_max_headroom():
    scene = _simple_grouped_scene()
    max_data = max(g.y_top for g in scene.groups)
    assert scene.y_max > max_data
run("build_grouped_bar_scene: y_max > max data top", test_grouped_scene_y_max_headroom)


def test_grouped_scene_bar_tags_unique():
    scene = _simple_grouped_scene(n_cats=3, n_subs=3)
    tags = [g.bar_tag for g in scene.groups]
    assert len(set(tags)) == len(tags)
run("build_grouped_bar_scene: bar_tags are unique", test_grouped_scene_bar_tags_unique)


def test_grouped_scene_colors_are_hex():
    scene = _simple_grouped_scene(n_cats=2, n_subs=2)
    for g in scene.groups:
        assert g.color.startswith("#"), f"{g.color!r} not hex"
        assert g.edge_color.startswith("#"), f"{g.edge_color!r} not hex"
run("build_grouped_bar_scene: all colours are hex strings", test_grouped_scene_colors_are_hex)


def test_grouped_scene_group_by_tag():
    scene = _simple_grouped_scene(n_cats=2, n_subs=2)
    g = scene.group_by_tag("gbar_1_0")
    assert g is not None and g.bar_tag == "gbar_1_0"
    assert scene.group_by_tag("gbar_99_99") is None
run("GroupedBarScene.group_by_tag: lookup and None for missing", test_grouped_scene_group_by_tag)


def test_grouped_scene_with_geometry():
    scene = _simple_grouped_scene()
    s2    = scene.with_geometry(y_max=100.0, bar_width=0.4)
    assert s2.y_max == 100.0
    assert abs(s2.bar_width - 0.4) < 1e-9
    assert scene.y_max != 100.0, "original unchanged"
    assert scene.groups is s2.groups, "groups list shared"
run("GroupedBarScene.with_geometry: immutable update, shares groups", test_grouped_scene_with_geometry)


# ═════════════════════════════════════════════════════════════════════════════
# Section 14 — GroupedCoordTransform
# ═════════════════════════════════════════════════════════════════════════════
section("GroupedCoordTransform")


def test_grouped_tf_bar_cx_increases_with_cat():
    scene = _simple_grouped_scene(n_cats=3, n_subs=2)
    tf = GroupedCoordTransform(scene)
    cx0 = tf.bar_cx(0, 0)
    cx1 = tf.bar_cx(1, 0)
    cx2 = tf.bar_cx(2, 0)
    assert cx0 < cx1 < cx2, "Category centres should increase left-to-right"
run("GroupedCoordTransform.bar_cx: increases with cat_index", test_grouped_tf_bar_cx_increases_with_cat)


def test_grouped_tf_bar_cx_subs_within_cluster():
    scene = _simple_grouped_scene(n_cats=2, n_subs=3)
    tf = GroupedCoordTransform(scene)
    cxs = [tf.bar_cx(0, si) for si in range(3)]
    assert cxs[0] < cxs[1] < cxs[2], "Sub bars must be left-to-right within cluster"
run("GroupedCoordTransform.bar_cx: sub bars ordered within cluster", test_grouped_tf_bar_cx_subs_within_cluster)


def test_grouped_tf_y_min_at_bottom():
    scene = _simple_grouped_scene()
    tf = GroupedCoordTransform(scene)
    cy = tf.y(scene.y_min)
    assert cy == scene.canvas_h - scene.margin_bottom
run("GroupedCoordTransform.y: y_min at bottom pixel", test_grouped_tf_y_min_at_bottom)


def test_grouped_tf_cat_cx_centred():
    scene = _simple_grouped_scene(n_cats=4)
    tf = GroupedCoordTransform(scene)
    # Category cluster centres should be evenly spaced and inside plot area
    cxs = [tf.cat_cx(i) for i in range(4)]
    gaps = [cxs[i+1] - cxs[i] for i in range(3)]
    assert max(gaps) - min(gaps) <= 2, "Cluster centres not evenly spaced"
run("GroupedCoordTransform.cat_cx: evenly spaced cluster centres", test_grouped_tf_cat_cx_centred)


# ═════════════════════════════════════════════════════════════════════════════
# Section 15 — GroupedCanvasRenderer (mock canvas)
# ═════════════════════════════════════════════════════════════════════════════
section("GroupedCanvasRenderer (mock canvas)")


def _grouped_renderer(n_cats=3, n_subs=2):
    scene  = _simple_grouped_scene(n_cats=n_cats, n_subs=n_subs)
    canvas = _mock_canvas()
    rend   = GroupedCanvasRenderer(canvas, scene)
    rend.render()
    return rend, canvas, scene


def test_grouped_renderer_render_calls_delete_all():
    rend, canvas, _ = _grouped_renderer()
    canvas.delete.assert_called_with("all")
run("GroupedCanvasRenderer.render: calls canvas.delete('all')", test_grouped_renderer_render_calls_delete_all)


def test_grouped_renderer_bar_rect_count():
    n_cats, n_subs = 3, 2
    rend, canvas, _ = _grouped_renderer(n_cats, n_subs)
    assert len(rend._bar_rects) == n_cats * n_subs
run("GroupedCanvasRenderer: one bar_rect per (cat,sub) pair", test_grouped_renderer_bar_rect_count)


def test_grouped_renderer_err_stems_count():
    n_cats, n_subs = 2, 3
    rend, canvas, _ = _grouped_renderer(n_cats, n_subs)
    assert len(rend._err_stems) == n_cats * n_subs
run("GroupedCanvasRenderer: one error stem per bar", test_grouped_renderer_err_stems_count)


def test_grouped_renderer_y_drag_handle():
    rend, canvas, _ = _grouped_renderer()
    assert rend._y_drag_id is not None
    assert canvas.create_polygon.call_count >= 1
run("GroupedCanvasRenderer: Y-drag handle drawn", test_grouped_renderer_y_drag_handle)


def test_grouped_renderer_rescale_handle_after_render():
    rend, _, _ = _grouped_renderer()
    assert rend.rescale_handle is not None
    assert rend.rescale_handle.y_min == 0.0
run("GroupedCanvasRenderer: rescale_handle set after render()", test_grouped_renderer_rescale_handle_after_render)


def test_grouped_renderer_hit_test_returns_gbar_tag():
    rend, canvas, _ = _grouped_renderer()
    canvas.find_overlapping.return_value = [77]
    canvas.gettags.return_value = ["gbar_1_0", "gbar"]
    result = rend.hit_test(300, 200)
    assert result == "gbar_1_0"
run("GroupedCanvasRenderer.hit_test: returns gbar_N_M tag", test_grouped_renderer_hit_test_returns_gbar_tag)


def test_grouped_renderer_hit_test_miss():
    rend, canvas, _ = _grouped_renderer()
    canvas.find_overlapping.return_value = []
    assert rend.hit_test(5, 5) is None
run("GroupedCanvasRenderer.hit_test: returns None on miss", test_grouped_renderer_hit_test_miss)


def test_grouped_renderer_recolor():
    rend, canvas, _ = _grouped_renderer()
    fake_id = 55
    rend._bar_rects["gbar_0_1"] = fake_id
    rend.recolor("gbar_0_1", "#00ff88")
    canvas.itemconfig.assert_called_once()
    assert canvas.itemconfig.call_args[0][0] == fake_id
    assert rend.current_color("gbar_0_1") == "#00ff88"
run("GroupedCanvasRenderer.recolor: patches item and tracks colour", test_grouped_renderer_recolor)


def test_grouped_renderer_on_press_bar_click():
    rend, canvas, _ = _grouped_renderer()
    canvas.find_overlapping.return_value = [88]
    canvas.gettags.return_value = ["gbar_2_1", "gbar"]
    event = type("E", (), {"x": 300, "y": 200})()
    result = rend.on_press(event)
    assert result.kind == "bar"
    assert result.bar_tag == "gbar_2_1"
run("GroupedCanvasRenderer.on_press: returns ClickResult('bar') on bar click", test_grouped_renderer_on_press_bar_click)


def test_grouped_renderer_on_press_y_drag():
    rend, canvas, scene = _grouped_renderer()
    canvas.find_overlapping.return_value = []
    canvas.gettags.return_value = []
    hx = scene.margin_left
    hy = scene.margin_top - 6
    event = type("E", (), {"x": hx, "y": hy})()
    result = rend.on_press(event)
    assert result.kind == "y_drag_start"
run("GroupedCanvasRenderer.on_press: y_drag_start near Y handle", test_grouped_renderer_on_press_y_drag)


def test_grouped_renderer_on_motion_y_drag():
    rend, canvas, scene = _grouped_renderer()
    rend._drag = {"kind": "y_drag"}
    cy    = scene.margin_top + 15
    event = type("E", (), {"x": scene.margin_left, "y": cy})()
    old_ymax = rend._scene.y_max
    rend.on_motion(event)
    assert rend._scene.y_max != old_ymax
run("GroupedCanvasRenderer.on_motion: y_drag updates y_max", test_grouped_renderer_on_motion_y_drag)


def test_grouped_renderer_incremental_y_calls_coords():
    n_cats, n_subs = 3, 2
    rend, canvas, scene = _grouped_renderer(n_cats, n_subs)
    for i, g in enumerate(scene.groups):
        rend._bar_rects[g.bar_tag] = i + 200
    canvas.coords.reset_mock()
    rend._incremental_rescale_y(0.0, scene.y_max * 2)
    assert canvas.coords.call_count >= n_cats * n_subs
run("GroupedCanvasRenderer._incremental_rescale_y: calls canvas.coords() per bar",
    test_grouped_renderer_incremental_y_calls_coords)


def test_grouped_renderer_rescale_calls_full_redraw_on_size():
    rend, canvas, scene = _grouped_renderer()
    canvas.delete.reset_mock()
    rh = rend.rescale_handle.set_canvas_size(scene.canvas_w + 100, scene.canvas_h + 80)
    rend.rescale(rh)
    calls = [c for c in canvas.delete.call_args_list if c.args == ("all",)]
    assert len(calls) >= 1
run("GroupedCanvasRenderer.rescale: size change triggers full redraw", test_grouped_renderer_rescale_calls_full_redraw_on_size)


def test_grouped_renderer_legend_drawn():
    """Legend should appear when n_subs > 1."""
    rend, canvas, _ = _grouped_renderer(n_cats=2, n_subs=3)
    legend_ids = rend._items.get("legend", [])
    # One rect + one label per subgroup → at least 2*n_subs items
    assert len(legend_ids) >= 2 * 3, f"Expected ≥6 legend items, got {len(legend_ids)}"
run("GroupedCanvasRenderer: legend drawn when n_subs > 1", test_grouped_renderer_legend_drawn)


# ═════════════════════════════════════════════════════════════════════════════
# Section 16 — GroupedBarGroup helpers
# ═════════════════════════════════════════════════════════════════════════════
section("GroupedBarGroup helpers")


def test_grouped_bar_group_n():
    pts = np.array([1.0, 2.0, 3.0])
    g   = GroupedBarGroup("Cat", "Sub", 0, 0, 2.0, 0.5, "#ff0000", "#800000",
                          pts, "gbar_0_0", "gerr_0_0", "gpts_0_0")
    assert g.n == 3
run("GroupedBarGroup.n: returns correct count", test_grouped_bar_group_n)


def test_grouped_bar_group_y_top():
    g = GroupedBarGroup("Cat", "Sub", 0, 0, 5.0, 1.5, "#ff0000", "#800000",
                        np.array([5.0]), "gbar_0_0", "gerr_0_0", "gpts_0_0")
    assert g.y_top == 6.5
run("GroupedBarGroup.y_top: mean + error", test_grouped_bar_group_y_top)


def test_grouped_bar_group_y_bot_floor():
    g = GroupedBarGroup("Cat", "Sub", 0, 0, 1.0, 5.0, "#ff0000", "#800000",
                        np.array([1.0]), "gbar_0_0", "gerr_0_0", "gpts_0_0")
    assert g.y_bot == 0.0
run("GroupedBarGroup.y_bot: floored at 0", test_grouped_bar_group_y_bot_floor)


summarise()
sys.exit(0 if _h.FAIL == 0 else 1)
