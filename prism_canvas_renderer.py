"""
prism_canvas_renderer.py
========================
Canvas-based bar chart renderer for Claude Prism  (Session 11 / v11).

Replaces the matplotlib Agg *screen* path with a tk.Canvas scene graph.

  P11-a  Live Y-axis drag  — ▲ handle above the Y spine; drag to rescale
  P11-b  Incremental rescale — canvas.coords() moves instead of destroy+recreate
  P11-c  Bar-width drag  — blue-grey strip on right edge of each bar
  P11-d  snapshot_png()  — PIL ImageGrab of live canvas (captures recolors)

Export (PNG / TIFF / SVG) still uses the matplotlib Figure held by the App.

Public API
----------
    build_bar_scene(kw, canvas_w, canvas_h) -> BarScene

    CanvasRenderer(canvas, scene)
        .render()                           full initial draw
        .on_press(event)  -> ClickResult    call from <Button-1>
        .on_motion(event)                   call from <B1-Motion>
        .on_release(event)                  call from <ButtonRelease-1>
        .hit_test(cx, cy) -> tag | None
        .recolor(tag, hex)                  O(1) in-place colour change
        .rescale(handle)                    incremental update
        .rescale_handle   -> RescaleHandle
        .snapshot_png()   -> bytes | None

    ClickResult
        .kind     "bar" | "y_drag_start" | "barwidth_drag_start" | None
        .bar_tag  str | None

    RescaleHandle (immutable value object)
        .set_y_range(lo, hi)   -> RescaleHandle
        .set_canvas_size(w, h) -> RescaleHandle
        .set_bar_width(bw)     -> RescaleHandle
        .to_canvas_y(val)      -> int
        .to_canvas_x(idx, n)   -> int
        .y_fraction(val)       -> float
        .nice_y_ticks(n)       -> List[float]
"""

from __future__ import annotations

import io
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


# ─────────────────────────────────────────────────────────────────────────────
# Colour helpers  (no matplotlib dependency)
# ─────────────────────────────────────────────────────────────────────────────

def _hex_to_rgb(h: str) -> Tuple[int, int, int]:
    """Convert a CSS hex colour string (#RRGGBB or #RGB) to an (R, G, B) int tuple."""
    h = h.strip().lstrip("#")
    if len(h) == 3:
        h = h[0]*2 + h[1]*2 + h[2]*2
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert integer (R, G, B) components to a lowercase hex colour string."""
    return f"#{r:02x}{g:02x}{b:02x}"


def _darken_hex(h: str, factor: float = 0.65) -> str:
    """Return a darkened version of hex colour h by multiplying each channel by factor."""
    try:
        r, g, b = _hex_to_rgb(h)
        return _rgb_to_hex(int(r * factor), int(g * factor), int(b * factor))
    except Exception:
        return "#000000"


def _rgba_to_hex(color) -> str:
    """Accept any colour spec (hex string, float tuple, named colour) and return #RRGGBB."""
    if isinstance(color, str):
        if color.startswith("#"):
            return color[:7]
        try:
            import matplotlib.colors as mc
            r, g, b, _ = mc.to_rgba(color)
            return _rgb_to_hex(int(r*255), int(g*255), int(b*255))
        except Exception:
            return "#888888"
    if hasattr(color, "__len__") and len(color) >= 3:
        r, g, b = color[0], color[1], color[2]
        scale = 255 if max(r, g, b) > 1.0 else 1.0
        return _rgb_to_hex(int(r * (255/scale if scale != 255 else 1)),
                           int(g * (255/scale if scale != 255 else 1)),
                           int(b * (255/scale if scale != 255 else 1)))
    return "#888888"


def _blend_alpha(hex_color: str, alpha: float, bg: str = "#ffffff") -> str:
    """Alpha-composite hex_color at alpha over bg and return the opaque result."""
    rf, gf, bf = _hex_to_rgb(hex_color)
    rb, gb, bb = _hex_to_rgb(bg)
    return _rgb_to_hex(
        int(rf*alpha + rb*(1-alpha)),
        int(gf*alpha + gb*(1-alpha)),
        int(bf*alpha + bb*(1-alpha)),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Data model
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class BarElement:
    """Single bar and its associated data and render state."""
    group:      str
    index:      int
    mean:       float
    error:      float
    color:      str
    edge_color: str
    points:     np.ndarray
    bar_tag:    str
    err_tag:    str
    pts_tag:    str

    @property
    def n(self) -> int:
        return len(self.points)

    @property
    def y_top(self) -> float:
        return self.mean + self.error

    @property
    def y_bot(self) -> float:
        return max(0.0, self.mean - self.error)


@dataclass
class BarScene:
    """Immutable, matplotlib-free description of a bar chart."""
    elements:      List[BarElement]
    group_order:   List[str]
    title:         str
    xlabel:        str
    ylabel:        str
    error_type:    str
    bar_width:     float
    show_points:   bool
    font_size:     float
    alpha:         float
    y_min:         float
    y_max:         float
    canvas_w:      int
    canvas_h:      int
    margin_left:   int = 60
    margin_right:  int = 20
    margin_top:    int = 40
    margin_bottom: int = 60

    @property
    def n_groups(self) -> int:
        return len(self.elements)

    def element_by_tag(self, tag: str) -> Optional[BarElement]:
        for e in self.elements:
            if e.bar_tag == tag:
                return e
        return None

    def with_geometry(self, **kw) -> "BarScene":
        """Return a shallow copy with the given fields replaced."""
        d = {
            "elements": self.elements, "group_order": self.group_order,
            "title": self.title, "xlabel": self.xlabel, "ylabel": self.ylabel,
            "error_type": self.error_type, "bar_width": self.bar_width,
            "show_points": self.show_points, "font_size": self.font_size,
            "alpha": self.alpha, "y_min": self.y_min, "y_max": self.y_max,
            "canvas_w": self.canvas_w, "canvas_h": self.canvas_h,
            "margin_left": self.margin_left, "margin_right": self.margin_right,
            "margin_top": self.margin_top, "margin_bottom": self.margin_bottom,
        }
        d.update(kw)
        return BarScene(**d)


# ─────────────────────────────────────────────────────────────────────────────
# ClickResult
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ClickResult:
    """Result returned by CanvasRenderer.on_press(); describes what the user clicked."""
    kind:    Optional[str] = None   # "bar"|"y_drag_start"|"barwidth_drag_start"|None
    bar_tag: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# Coordinate transform
# ─────────────────────────────────────────────────────────────────────────────

class CoordTransform:
    """Maps data values to canvas pixel coordinates and back for a BarScene."""
    def __init__(self, scene: BarScene) -> None:
        self._s = scene

    @property
    def plot_w(self) -> int:
        return self._s.canvas_w - self._s.margin_left - self._s.margin_right

    @property
    def plot_h(self) -> int:
        return self._s.canvas_h - self._s.margin_top - self._s.margin_bottom

    @property
    def cell_w(self) -> float:
        return self.plot_w / max(self._s.n_groups, 1)

    def x(self, group_index: float) -> int:
        return int(self._s.margin_left + (group_index + 0.5) * self.cell_w)

    def y(self, data_val: float) -> int:
        s    = self._s
        span = s.y_max - s.y_min
        frac = (data_val - s.y_min) / span if span > 0 else 0.0
        return int(s.canvas_h - s.margin_bottom - frac * self.plot_h)

    def y_zero(self) -> int:
        return self.y(max(self._s.y_min, 0.0))

    def bar_half_w(self) -> int:
        return max(2, int(self.cell_w * self._s.bar_width * 0.5))

    def cap_half_w(self) -> int:
        return max(1, self.bar_half_w() // 3)

    def canvas_to_group(self, cx: int) -> Optional[int]:
        s = self._s
        if cx < s.margin_left or cx > s.canvas_w - s.margin_right:
            return None
        return min(int((cx - s.margin_left) / self.cell_w), s.n_groups - 1)

    def canvas_to_y(self, cy: int) -> float:
        s    = self._s
        frac = (s.canvas_h - s.margin_bottom - cy) / max(self.plot_h, 1)
        return s.y_min + frac * (s.y_max - s.y_min)


# ─────────────────────────────────────────────────────────────────────────────
# RescaleHandle
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class RescaleHandle:
    """
    Immutable value object for the current coordinate mapping.
    Mutation methods return new handles; the original is never changed.
    """
    y_min:         float
    y_max:         float
    canvas_w:      int
    canvas_h:      int
    margin_left:   int
    margin_right:  int
    margin_top:    int
    margin_bottom: int
    n_groups:      int   = 1
    bar_width:     float = 0.6

    @property
    def plot_w(self) -> int:
        return self.canvas_w - self.margin_left - self.margin_right

    @property
    def plot_h(self) -> int:
        return self.canvas_h - self.margin_top - self.margin_bottom

    def set_y_range(self, new_min: float, new_max: float) -> "RescaleHandle":
        import copy as _c; rh = _c.copy(self)
        rh.y_min = new_min; rh.y_max = new_max
        return rh

    def set_canvas_size(self, w: int, h: int) -> "RescaleHandle":
        import copy as _c; rh = _c.copy(self)
        rh.canvas_w = w; rh.canvas_h = h
        return rh

    def set_bar_width(self, bw: float) -> "RescaleHandle":
        import copy as _c; rh = _c.copy(self)
        rh.bar_width = max(0.05, min(1.0, bw))
        return rh

    def y_fraction(self, data_val: float) -> float:
        span = self.y_max - self.y_min
        return (data_val - self.y_min) / span if span > 0 else 0.0

    def to_canvas_y(self, data_val: float) -> int:
        return int(self.canvas_h - self.margin_bottom
                   - self.y_fraction(data_val) * self.plot_h)

    def to_canvas_x(self, group_index: float,
                    n_groups: Optional[int] = None) -> int:
        n      = n_groups if n_groups is not None else max(self.n_groups, 1)
        cell_w = self.plot_w / n
        return int(self.margin_left + (group_index + 0.5) * cell_w)

    def nice_y_ticks(self, n_ticks: int = 5) -> List[float]:
        span = self.y_max - self.y_min
        if span <= 0:
            return [self.y_min]
        raw_step  = span / max(n_ticks - 1, 1)
        magnitude = 10 ** math.floor(math.log10(raw_step))
        nice      = [1, 2, 2.5, 5, 10]
        step = magnitude * min(nice, key=lambda x: abs(x - raw_step/magnitude))
        start = math.ceil(self.y_min / step) * step
        ticks, v = [], start
        while v <= self.y_max + step * 1e-6:
            ticks.append(round(v, 10)); v += step
        return ticks

    @classmethod
    def from_scene(cls, scene: BarScene) -> "RescaleHandle":
        return cls(
            y_min=scene.y_min,    y_max=scene.y_max,
            canvas_w=scene.canvas_w, canvas_h=scene.canvas_h,
            margin_left=scene.margin_left, margin_right=scene.margin_right,
            margin_top=scene.margin_top,   margin_bottom=scene.margin_bottom,
            n_groups=scene.n_groups,       bar_width=scene.bar_width,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Scene builder
# ─────────────────────────────────────────────────────────────────────────────

def _calc_error_plain(vals: np.ndarray,
                      error_type: str) -> Tuple[float, float]:
    """Pure-numpy SEM/SD/CI95 calculation — no scipy import required."""
    n = len(vals)
    m = float(np.mean(vals))
    s = float(np.std(vals, ddof=1)) if n > 1 else 0.0
    if error_type == "sd":
        return m, s
    if error_type == "ci95":
        try:
            from scipy import stats as _st
            t = float(_st.t.ppf(0.975, max(n-1, 1)))
        except ImportError:
            t = 1.96
        return m, t * s / math.sqrt(max(n, 1))
    return m, s / math.sqrt(n) if n > 0 else 0.0   # sem


def _read_bar_groups(excel_path: str,
                     sheet) -> Tuple[List[str], Dict[str, np.ndarray]]:
    """Read a flat-header Excel file and return (group_order, {group: values}) dict."""
    raw         = pd.read_excel(excel_path, sheet_name=sheet, header=0)
    group_order = list(raw.columns)
    groups: Dict[str, np.ndarray] = {}
    for col in group_order:
        vals = pd.to_numeric(raw[col], errors="coerce").dropna().values
        if len(vals) == 0:
            raise ValueError(f"Column '{col}' has no numeric data")
        groups[col] = vals
    return group_order, groups


def _prism_palette_n(n: int, color_spec) -> List[str]:
    """Return n hex colours from a palette spec, mirroring prism_functions._assign_colors."""
    _PAL = ["#E8453C","#2274A5","#32936F","#F18F01","#A846A0",
            "#6B4226","#048A81","#D4AC0D","#3B1F2B","#44BBA4"]
    if color_spec is None:
        return [_PAL[i % len(_PAL)] for i in range(n)]
    if isinstance(color_spec, str):
        try:
            import prism_functions as _pf
            return [_rgba_to_hex(c) for c in _pf._assign_colors(n, color_spec)]
        except Exception:
            return [color_spec] * n
    c = [_rgba_to_hex(x) for x in list(color_spec)]
    while len(c) < n: c += c
    return c[:n]


def build_bar_scene(kw: dict, canvas_w: int, canvas_h: int) -> BarScene:
    """Build a BarScene from plot kwargs.  Reads Excel, no matplotlib."""
    excel_path  = kw["excel_path"]
    sheet       = kw.get("sheet", 0)
    error_type  = kw.get("error", "sem")
    bar_width   = float(kw.get("bar_width", 0.6))
    show_points = bool(kw.get("show_points", True))
    font_size   = float(kw.get("font_size", 12.0))
    alpha       = float(kw.get("alpha", 0.85))
    title       = kw.get("title", "") or ""
    xlabel      = kw.get("xlabel", "") or ""
    ylabel      = kw.get("ytitle", "") or kw.get("ylabel", "") or ""
    color_spec  = kw.get("color", None)

    group_order, groups = _read_bar_groups(excel_path, sheet)
    hex_colors = _prism_palette_n(len(group_order), color_spec)
    elements: List[BarElement] = []
    all_tops: List[float] = []

    for i, g in enumerate(group_order):
        vals = groups[g]
        m, err = _calc_error_plain(vals, error_type)
        raw_fill     = hex_colors[i] if i < len(hex_colors) else "#888888"
        fill_hex     = _rgba_to_hex(raw_fill)
        fill_blended = _blend_alpha(fill_hex, alpha)
        edge_hex     = _darken_hex(fill_hex, 0.65)
        elements.append(BarElement(
            group=g, index=i, mean=m, error=err,
            color=fill_blended, edge_color=edge_hex, points=vals,
            bar_tag=f"bar_{i}", err_tag=f"err_{i}", pts_tag=f"pts_{i}",
        ))
        all_tops.append(m + err)

    y_min   = 0.0
    raw_top = max(all_tops) if all_tops else 1.0
    y_max   = raw_top * 1.15 if raw_top > 0 else 1.0
    ml      = max(55, int(font_size * 4.5))
    mb      = max(55, int(font_size * 4.5))

    return BarScene(
        elements=elements, group_order=group_order,
        title=title, xlabel=xlabel, ylabel=ylabel,
        error_type=error_type, bar_width=bar_width,
        show_points=show_points, font_size=font_size, alpha=alpha,
        y_min=y_min, y_max=y_max,
        canvas_w=canvas_w, canvas_h=canvas_h,
        margin_left=ml, margin_right=25, margin_top=45, margin_bottom=mb,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Tick label formatter
# ─────────────────────────────────────────────────────────────────────────────

def _fmt_tick_label(v: float) -> str:
    """Format a Y-axis tick value compactly (integers, decimals, or scientific notation)."""
    if v == 0:
        return "0"
    if abs(v) >= 10_000 or (abs(v) < 0.01 and v != 0):
        return f"{v:.2e}"
    if v == int(v):
        return str(int(v))
    for dp in (1, 2, 3, 4):
        s = f"{v:.{dp}f}"
        if float(s) == v or dp == 4:
            return s
    return f"{v:.3g}"


# ─────────────────────────────────────────────────────────────────────────────
# Visual constants for drag handles
# ─────────────────────────────────────────────────────────────────────────────

_Y_HANDLE_H   = 12    # px height of ▲ triangle
_Y_HANDLE_W   = 8     # px half-width of ▲
_Y_HANDLE_PAD = 6     # px hit-test slack
_BW_HANDLE_W  = 6     # px width of bar-width drag strip
_BW_HANDLE_CLR = "#8899cc"   # blue-grey colour for the strip


# ─────────────────────────────────────────────────────────────────────────────
# CanvasRenderer
# ─────────────────────────────────────────────────────────────────────────────

class CanvasRenderer:
    """
    Renders a BarScene onto a tk.Canvas widget.

    Item-ID tracking
    ----------------
    _bar_rects        {bar_tag: rect_id}
    _err_stems        {err_tag: line_id}
    _err_top_caps     {err_tag: line_id}
    _err_bot_caps     {err_tag: line_id}
    _pts_ovals        {pts_tag: [oval_id, …]}
    _bw_handles       {bar_tag: rect_id}     bar-width drag strip
    _y_spine_id       int                    left spine line
    _y_drag_id        int                    ▲ Y-drag handle
    _items            {tag: [id, …]}         general registry
    """

    _FONT_FACE = "Helvetica Neue"

    def __init__(self, canvas, scene: BarScene) -> None:
        self._canvas = canvas
        self._scene  = scene
        self._tf     = CoordTransform(scene)
        self._rh: Optional[RescaleHandle] = None

        # item registries
        self._items:        Dict[str, List[int]] = {}
        self._bar_rects:    Dict[str, int] = {}
        self._bar_colors:   Dict[str, str] = {}
        self._err_stems:    Dict[str, int] = {}
        self._err_top_caps: Dict[str, int] = {}
        self._err_bot_caps: Dict[str, int] = {}
        self._pts_ovals:    Dict[str, List[int]] = {}
        self._bw_handles:   Dict[str, int] = {}
        self._y_spine_id:   Optional[int] = None
        self._y_drag_id:    Optional[int] = None

        # active drag state (None when not dragging)
        self._drag: Optional[dict] = None

    # ── public: lifecycle ────────────────────────────────────────────────────

    @property
    def rescale_handle(self) -> Optional[RescaleHandle]:
        return self._rh

    def render(self) -> None:
        """Full redraw — clears canvas, draws all elements."""
        c = self._canvas
        c.delete("all")
        for d in (self._items, self._bar_rects, self._bar_colors,
                  self._err_stems, self._err_top_caps, self._err_bot_caps,
                  self._pts_ovals, self._bw_handles):
            d.clear()
        self._y_spine_id = None
        self._y_drag_id  = None

        self._draw_background()
        self._draw_axes()
        self._draw_y_drag_handle()
        self._draw_y_ticks()
        self._draw_x_labels()
        for el in self._scene.elements:
            self._draw_bar(el)
            self._draw_error_bar(el)
            self._draw_bw_handle(el)
        if self._scene.show_points:
            for el in self._scene.elements:
                self._draw_jitter_points(el)
        self._draw_axis_labels()
        self._draw_title()
        self._rh = RescaleHandle.from_scene(self._scene)

    # ── public: mouse events ─────────────────────────────────────────────────

    def on_press(self, event) -> ClickResult:
        """
        Call from <Button-1>.  Returns a ClickResult.
        kind "bar"                 → App should open colour picker
        kind "y_drag_start"        → drag begun; nothing else needed
        kind "barwidth_drag_start" → drag begun; nothing else needed
        kind None                  → background click; ignore
        """
        cx, cy    = event.x, event.y
        self._drag = None

        # 1. Y drag handle (highest priority)
        if self._y_drag_id is not None and self._near_y_handle(cx, cy):
            self._drag = {"kind": "y_drag"}
            return ClickResult(kind="y_drag_start")

        # 2. Bar-width drag strip
        bw_tag = self._hit_bw_handle(cx, cy)
        if bw_tag is not None:
            el = self._scene.element_by_tag(bw_tag)
            self._drag = {
                "kind":      "barwidth_drag",
                "cx_start":  cx,
                "bw_start":  self._scene.bar_width,
            }
            return ClickResult(kind="barwidth_drag_start")

        # 3. Bar body
        bar_tag = self.hit_test(cx, cy)
        if bar_tag is not None:
            return ClickResult(kind="bar", bar_tag=bar_tag)

        return ClickResult()

    def on_motion(self, event) -> None:
        """Call from <B1-Motion>."""
        if self._drag is None:
            return
        cx, cy = event.x, event.y
        kind   = self._drag["kind"]

        if kind == "y_drag":
            new_ymax = self._tf.canvas_to_y(cy)
            max_data = max((el.y_top for el in self._scene.elements), default=1.0)
            new_ymax = max(new_ymax, max_data * 1.02,
                           self._scene.y_min + 0.01)
            self._incremental_rescale_y(self._scene.y_min, new_ymax)

        elif kind == "barwidth_drag":
            dx      = cx - self._drag["cx_start"]
            new_bw  = float(np.clip(
                self._drag["bw_start"] + 2.0 * dx / max(self._tf.cell_w, 1),
                0.05, 1.0))
            if abs(new_bw - self._scene.bar_width) > 0.005:
                self._incremental_rescale_bw(new_bw)

    def on_release(self, event) -> None:
        """Call from <ButtonRelease-1>."""
        self._drag = None

    # ── public: existing API (unchanged) ────────────────────────────────────

    def hit_test(self, canvas_x: int, canvas_y: int) -> Optional[str]:
        items = self._canvas.find_overlapping(
            canvas_x-2, canvas_y-2, canvas_x+2, canvas_y+2)
        for iid in reversed(items):
            for tag in self._canvas.gettags(iid):
                if tag.startswith("bar_"):
                    return tag
        return None

    def recolor(self, bar_tag: str, new_color: str) -> None:
        iid = self._bar_rects.get(bar_tag)
        if iid is None:
            return
        new_hex = _rgba_to_hex(new_color) if not new_color.startswith("#") else new_color
        self._canvas.itemconfig(iid, fill=new_hex,
                                 outline=_darken_hex(new_hex, 0.65))
        self._bar_colors[bar_tag] = new_hex

    def current_color(self, bar_tag: str) -> Optional[str]:
        return self._bar_colors.get(bar_tag)

    def rescale(self, handle: RescaleHandle) -> None:
        """
        Apply an updated RescaleHandle.

        Routes to incremental update when only Y or bar_width changed.
        Falls back to full render() when canvas size changes.
        """
        if self._rh is None:
            self._full_rescale(handle); return

        sz_changed = (handle.canvas_w != self._rh.canvas_w or
                      handle.canvas_h != self._rh.canvas_h)
        if sz_changed:
            self._full_rescale(handle); return

        y_changed  = (handle.y_min != self._rh.y_min or
                      handle.y_max != self._rh.y_max)
        bw_changed = handle.bar_width != self._rh.bar_width

        if y_changed:
            self._incremental_rescale_y(handle.y_min, handle.y_max)
        if bw_changed:
            self._incremental_rescale_bw(handle.bar_width)
        if not y_changed and not bw_changed:
            self._rh = handle

    # ── public: P11-d snapshot ───────────────────────────────────────────────

    def snapshot_png(self) -> Optional[bytes]:
        """
        Return PNG bytes of the live canvas (including user recolors).

        Tries PIL.ImageGrab first (macOS/Win screen capture); falls back
        to canvas.postscript() + PIL (requires Ghostscript).
        Returns None if both fail.
        """
        c = self._canvas
        try:
            c.update_idletasks()
            x0 = c.winfo_rootx();  y0 = c.winfo_rooty()
            x1 = x0 + c.winfo_width(); y1 = y0 + c.winfo_height()
            from PIL import ImageGrab
            img = ImageGrab.grab(bbox=(x0, y0, x1, y1))
            buf = io.BytesIO(); img.save(buf, format="PNG")
            return buf.getvalue()
        except Exception:
            pass
        try:
            ps  = c.postscript(colormode="color")
            buf = io.BytesIO(ps.encode("latin-1"))
            from PIL import Image
            img = Image.open(buf)
            out = io.BytesIO(); img.save(out, format="PNG")
            return out.getvalue()
        except Exception:
            return None

    # ── private: full rescale ────────────────────────────────────────────────

    def _full_rescale(self, handle: RescaleHandle) -> None:
        saved     = dict(self._bar_colors)
        new_scene = self._scene.with_geometry(
            y_min=handle.y_min,       y_max=handle.y_max,
            canvas_w=handle.canvas_w, canvas_h=handle.canvas_h,
            bar_width=handle.bar_width,
            margin_left=handle.margin_left,   margin_right=handle.margin_right,
            margin_top=handle.margin_top,     margin_bottom=handle.margin_bottom,
        )
        self._scene = new_scene
        self._tf    = CoordTransform(new_scene)
        self.render()
        for tag, col in saved.items():
            self.recolor(tag, col)
        self._rh = handle

    # ── private: incremental Y rescale (P11-a / P11-b) ──────────────────────

    def _incremental_rescale_y(self, new_y_min: float, new_y_max: float) -> None:
        """
        Move all Y-dependent items via canvas.coords() — no destroy/create.
        O(n_groups × n_points) calls; 60fps-safe for typical data sizes.
        """
        new_scene   = self._scene.with_geometry(y_min=new_y_min, y_max=new_y_max)
        self._scene = new_scene
        self._tf    = CoordTransform(new_scene)
        c           = self._canvas
        tf          = self._tf
        y_zero      = tf.y_zero()

        for el in new_scene.elements:
            cx = tf.x(el.index)
            hw = tf.bar_half_w()
            cw = tf.cap_half_w()

            # Bar rectangle top
            rect_id = self._bar_rects.get(el.bar_tag)
            if rect_id is not None:
                y_t = tf.y(max(el.mean, 0.0))
                y_b = y_zero
                if y_t > y_b: y_t, y_b = y_b, y_t
                c.coords(rect_id, cx-hw, y_t, cx+hw, y_b)

            # Error stem
            if (sid := self._err_stems.get(el.err_tag)) is not None:
                c.coords(sid, cx, tf.y(el.y_bot), cx, tf.y(el.y_top))

            # Error caps
            cy_top = tf.y(el.y_top)
            cy_bot = tf.y(el.y_bot)
            if (tid := self._err_top_caps.get(el.err_tag)) is not None:
                c.coords(tid, cx-cw, cy_top, cx+cw, cy_top)
            if (bid := self._err_bot_caps.get(el.err_tag)) is not None:
                c.coords(bid, cx-cw, cy_bot, cx+cw, cy_bot)

            # Jitter ovals
            r   = max(2, int(new_scene.font_size * 0.35))
            rng = np.random.default_rng(seed=el.index)
            js  = max(4, hw // 2)
            jitter = rng.uniform(-js, js, len(el.points))
            for oid, v, jx in zip(self._pts_ovals.get(el.pts_tag, []),
                                   el.points, jitter):
                px = cx + int(jx); py = tf.y(float(v))
                c.coords(oid, px-r, py-r, px+r, py+r)

            # BW handle Y (bar top changes)
            bwh_id = self._bw_handles.get(el.bar_tag)
            if bwh_id is not None:
                y_t2 = tf.y(max(el.mean, 0.0)); y_b2 = y_zero
                if y_t2 > y_b2: y_t2, y_b2 = y_b2, y_t2
                c.coords(bwh_id, cx+hw-_BW_HANDLE_W, y_t2, cx+hw, y_b2)

        # Y ticks: values and labels may change → delete + recreate
        for iid in (self._items.pop("tick_y", [])
                    + self._items.pop("ticklabel_y", [])):
            c.delete(iid)
        self._draw_y_ticks()

        # Y spine top
        if self._y_spine_id is not None:
            s = new_scene
            c.coords(self._y_spine_id,
                     s.margin_left, s.margin_top,
                     s.margin_left, s.canvas_h - s.margin_bottom)

        # Y drag handle position
        self._move_y_drag_handle()

        self._rh = RescaleHandle.from_scene(new_scene)

    # ── private: incremental bar-width rescale (P11-c) ───────────────────────

    def _incremental_rescale_bw(self, new_bw: float) -> None:
        """Resize bars and caps horizontally; no Y changes needed."""
        new_scene   = self._scene.with_geometry(bar_width=new_bw)
        self._scene = new_scene
        self._tf    = CoordTransform(new_scene)
        c           = self._canvas
        tf          = self._tf
        y_zero      = tf.y_zero()

        for el in new_scene.elements:
            cx = tf.x(el.index)
            hw = tf.bar_half_w()
            cw = tf.cap_half_w()

            rect_id = self._bar_rects.get(el.bar_tag)
            if rect_id is not None:
                y_t = tf.y(max(el.mean, 0.0)); y_b = y_zero
                if y_t > y_b: y_t, y_b = y_b, y_t
                c.coords(rect_id, cx-hw, y_t, cx+hw, y_b)

            cy_top = tf.y(el.y_top);  cy_bot = tf.y(el.y_bot)
            if (tid := self._err_top_caps.get(el.err_tag)) is not None:
                c.coords(tid, cx-cw, cy_top, cx+cw, cy_top)
            if (bid := self._err_bot_caps.get(el.err_tag)) is not None:
                c.coords(bid, cx-cw, cy_bot, cx+cw, cy_bot)

            bwh_id = self._bw_handles.get(el.bar_tag)
            if bwh_id is not None:
                y_t2 = tf.y(max(el.mean, 0.0)); y_b2 = y_zero
                if y_t2 > y_b2: y_t2, y_b2 = y_b2, y_t2
                c.coords(bwh_id, cx+hw-_BW_HANDLE_W, y_t2, cx+hw, y_b2)

        if self._rh is not None:
            self._rh = self._rh.set_bar_width(new_bw)

    # ── private: drag hit helpers ────────────────────────────────────────────

    def _near_y_handle(self, cx: int, cy: int) -> bool:
        s  = self._scene
        hx = s.margin_left
        hy = s.margin_top - _Y_HANDLE_H // 2
        return (abs(cx - hx) <= _Y_HANDLE_W + _Y_HANDLE_PAD
                and abs(cy - hy) <= _Y_HANDLE_H + _Y_HANDLE_PAD)

    def _hit_bw_handle(self, cx: int, cy: int) -> Optional[str]:
        items = self._canvas.find_overlapping(cx-2, cy-2, cx+2, cy+2)
        for iid in reversed(items):
            for tag in self._canvas.gettags(iid):
                if tag.startswith("bwh_"):
                    return tag.replace("bwh_", "bar_", 1)
        return None

    # ── private: draw primitives ─────────────────────────────────────────────

    def _font(self, delta: int = 0, bold: bool = False) -> tuple:
        sz    = max(7, int(self._scene.font_size + delta))
        style = "bold" if bold else ""
        return (self._FONT_FACE, sz, style) if style else (self._FONT_FACE, sz)

    def _add(self, tag: str, iid: int) -> None:
        self._items.setdefault(tag, []).append(iid)

    def _draw_background(self) -> None:
        s = self._scene
        self._canvas.configure(bg="white")
        iid = self._canvas.create_rectangle(
            s.margin_left, s.margin_top,
            s.canvas_w - s.margin_right, s.canvas_h - s.margin_bottom,
            fill="white", outline="", tags=("bg_plot",))
        self._add("bg_plot", iid)

    def _draw_axes(self) -> None:
        s  = self._scene
        ax = "#333333"
        lw = max(1, int(s.font_size * 0.065))

        iid = self._canvas.create_line(
            s.margin_left, s.canvas_h - s.margin_bottom,
            s.canvas_w - s.margin_right, s.canvas_h - s.margin_bottom,
            fill=ax, width=lw, tags=("axis_x",))
        self._add("axis_x", iid)

        iid = self._canvas.create_line(
            s.margin_left, s.margin_top,
            s.margin_left, s.canvas_h - s.margin_bottom,
            fill=ax, width=lw, tags=("axis_y",))
        self._add("axis_y", iid)
        self._y_spine_id = iid

    def _draw_y_drag_handle(self) -> None:
        """▲ triangle just above the top of the Y spine (P11-a grab point)."""
        s  = self._scene
        hx = s.margin_left
        hy = s.margin_top - _Y_HANDLE_H
        pts = [hx, hy,
               hx - _Y_HANDLE_W, hy + _Y_HANDLE_H,
               hx + _Y_HANDLE_W, hy + _Y_HANDLE_H]
        iid = self._canvas.create_polygon(
            pts, fill="#2274A5", outline="#2274A5",
            tags=("y_drag_handle",))
        self._add("y_drag_handle", iid)
        self._y_drag_id = iid

    def _move_y_drag_handle(self) -> None:
        if self._y_drag_id is None:
            return
        s  = self._scene
        hx = s.margin_left
        hy = s.margin_top - _Y_HANDLE_H
        self._canvas.coords(self._y_drag_id,
            hx, hy,
            hx - _Y_HANDLE_W, hy + _Y_HANDLE_H,
            hx + _Y_HANDLE_W, hy + _Y_HANDLE_H)

    def _draw_y_ticks(self) -> None:
        rh = RescaleHandle.from_scene(self._scene)
        tf = self._tf; s = self._scene; ax = "#333333"
        for v in rh.nice_y_ticks():
            cy = tf.y(v)
            if cy < s.margin_top or cy > s.canvas_h - s.margin_bottom:
                continue
            iid = self._canvas.create_line(
                s.margin_left-5, cy, s.margin_left, cy,
                fill=ax, width=1, tags=("tick_y",))
            self._add("tick_y", iid)
            iid = self._canvas.create_text(
                s.margin_left-9, cy, text=_fmt_tick_label(v),
                anchor="e", font=self._font(-2), fill="#333333",
                tags=("ticklabel_y",))
            self._add("ticklabel_y", iid)

    def _draw_x_labels(self) -> None:
        s = self._scene; tf = self._tf; ax = "#333333"
        y = s.canvas_h - s.margin_bottom + 8
        for el in s.elements:
            cx = tf.x(el.index)
            iid = self._canvas.create_line(
                cx, s.canvas_h - s.margin_bottom,
                cx, s.canvas_h - s.margin_bottom + 5,
                fill=ax, width=1, tags=("tick_x",))
            self._add("tick_x", iid)
            label = f"{el.group}\nn={el.n}" if s.show_points else el.group
            iid = self._canvas.create_text(
                cx, y, text=label, anchor="n",
                font=self._font(-1, bold=True), fill="#333333",
                tags=("ticklabel_x",))
            self._add("ticklabel_x", iid)

    def _draw_bar(self, el: BarElement) -> None:
        tf = self._tf; cx = tf.x(el.index); hw = tf.bar_half_w()
        y_t = tf.y(max(el.mean, 0.0)); y_b = tf.y_zero()
        if y_t > y_b: y_t, y_b = y_b, y_t
        iid = self._canvas.create_rectangle(
            cx-hw, y_t, cx+hw, y_b,
            fill=el.color, outline=el.edge_color, width=1,
            tags=(el.bar_tag, "bar"))
        self._add(el.bar_tag, iid)
        self._bar_rects[el.bar_tag]  = iid
        self._bar_colors[el.bar_tag] = el.color

    def _draw_error_bar(self, el: BarElement) -> None:
        tf = self._tf; cx = tf.x(el.index); cw = tf.cap_half_w()
        ytop = tf.y(el.y_top); ybot = tf.y(el.y_bot); ec = "#222222"

        stem = self._canvas.create_line(cx, ybot, cx, ytop,
            fill=ec, width=1, tags=(el.err_tag, "errbar"))
        self._add(el.err_tag, stem)
        self._err_stems[el.err_tag] = stem

        tcap = self._canvas.create_line(cx-cw, ytop, cx+cw, ytop,
            fill=ec, width=1, tags=(el.err_tag, "errcap"))
        self._add(el.err_tag, tcap)
        self._err_top_caps[el.err_tag] = tcap

        bcap = self._canvas.create_line(cx-cw, ybot, cx+cw, ybot,
            fill=ec, width=1, tags=(el.err_tag, "errcap"))
        self._add(el.err_tag, bcap)
        self._err_bot_caps[el.err_tag] = bcap

    def _draw_bw_handle(self, el: BarElement) -> None:
        """Blue-grey strip on right edge of bar — grab here to resize width."""
        tf = self._tf; cx = tf.x(el.index); hw = tf.bar_half_w()
        y_t = tf.y(max(el.mean, 0.0)); y_b = tf.y_zero()
        if y_t > y_b: y_t, y_b = y_b, y_t
        bwh_tag = el.bar_tag.replace("bar_", "bwh_", 1)
        iid = self._canvas.create_rectangle(
            cx+hw-_BW_HANDLE_W, y_t, cx+hw, y_b,
            fill=_BW_HANDLE_CLR, outline="", width=0,
            tags=(bwh_tag, "bw_handle"))
        self._add(bwh_tag, iid)
        self._bw_handles[el.bar_tag] = iid

    def _draw_jitter_points(self, el: BarElement) -> None:
        tf  = self._tf; cx = tf.x(el.index)
        r   = max(2, int(self._scene.font_size * 0.35))
        rng = np.random.default_rng(seed=el.index)
        js  = max(4, tf.bar_half_w() // 2)
        jitter = rng.uniform(-js, js, len(el.points))
        ovals: List[int] = []
        for v, jx in zip(el.points, jitter):
            px = cx + int(jx); py = tf.y(float(v))
            iid = self._canvas.create_oval(
                px-r, py-r, px+r, py+r,
                fill=el.edge_color, outline=el.edge_color,
                tags=(el.pts_tag, "point"))
            self._add(el.pts_tag, iid)
            ovals.append(iid)
        self._pts_ovals[el.pts_tag] = ovals

    def _draw_axis_labels(self) -> None:
        s = self._scene
        if s.ylabel:
            lx = max(14, s.margin_left // 3)
            ly = s.margin_top + (s.canvas_h-s.margin_top-s.margin_bottom)//2
            try:
                iid = self._canvas.create_text(
                    lx, ly, text=s.ylabel,
                    font=self._font(1, bold=True), fill="#333333",
                    angle=90, anchor="center", tags=("label_y",))
            except Exception:
                iid = self._canvas.create_text(
                    4, ly, text=s.ylabel,
                    font=self._font(-1, bold=True), fill="#333333",
                    anchor="w", tags=("label_y",))
            self._add("label_y", iid)
        if s.xlabel:
            lx = s.margin_left + (s.canvas_w-s.margin_left-s.margin_right)//2
            iid = self._canvas.create_text(
                lx, s.canvas_h-8, text=s.xlabel,
                font=self._font(1, bold=True), fill="#333333",
                anchor="s", tags=("label_x",))
            self._add("label_x", iid)

    def _draw_title(self) -> None:
        s = self._scene
        if not s.title: return
        lx = s.margin_left + (s.canvas_w-s.margin_left-s.margin_right)//2
        iid = self._canvas.create_text(
            lx, max(4, s.margin_top//2), text=s.title,
            font=self._font(4, bold=True), fill="#111111",
            anchor="center", tags=("label_title",))
        self._add("label_title", iid)


# ─────────────────────────────────────────────────────────────────────────────
# App integration helper (unchanged API)
# ─────────────────────────────────────────────────────────────────────────────

def embed_canvas_renderer(
    plot_frame,
    kw: dict,
    canvas_w: Optional[int] = None,
    canvas_h: Optional[int] = None,
) -> Tuple[CanvasRenderer, RescaleHandle]:
    """Build scene, create Canvas, render, return (renderer, handle)."""
    import tkinter as tk
    w = canvas_w or max(400, plot_frame.winfo_width()  or 560)
    h = canvas_h or max(360, plot_frame.winfo_height() or 520)
    scene    = build_bar_scene(kw, w, h)
    canvas   = tk.Canvas(plot_frame, width=w, height=h,
                          bg="white", highlightthickness=0)
    canvas.pack(padx=8, pady=(2, 8))
    renderer = CanvasRenderer(canvas, scene)
    renderer.render()
    return renderer, renderer.rescale_handle


# ─────────────────────────────────────────────────────────────────────────────
# Grouped-bar canvas renderer  (P12)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class GroupedBarGroup:
    """One (category, subgroup) cell in a grouped bar chart."""
    category:   str       # e.g. "Control"
    subgroup:   str       # e.g. "Male"
    cat_index:  int       # 0-based category position
    sub_index:  int       # 0-based subgroup position within category
    mean:       float
    error:      float
    color:      str       # hex fill
    edge_color: str       # hex edge
    points:     np.ndarray
    bar_tag:    str       # "gbar_0_1" → cat 0, sub 1
    err_tag:    str
    pts_tag:    str

    @property
    def n(self) -> int:
        return len(self.points)

    @property
    def y_top(self) -> float:
        return self.mean + self.error

    @property
    def y_bot(self) -> float:
        return max(0.0, self.mean - self.error)


@dataclass
class GroupedBarScene:
    """
    Immutable, matplotlib-free description of a grouped bar chart.

    Excel layout expected (mirrors prism_grouped_barplot):
      Row 0 (header=None, row index 0): category names  (e.g. Control, Drug A)
      Row 1 (row index 1):              subgroup names  (e.g. Male, Female)
      Rows 2+:                          numeric values
    """
    groups:        List[GroupedBarGroup]
    categories:    List[str]         # unique, ordered
    subgroups:     List[str]         # unique, ordered
    title:         str
    xlabel:        str
    ylabel:        str
    error_type:    str
    bar_width:     float             # per-bar width as fraction of sub-cell
    show_points:   bool
    font_size:     float
    alpha:         float
    y_min:         float
    y_max:         float
    canvas_w:      int
    canvas_h:      int
    margin_left:   int = 65
    margin_right:  int = 20
    margin_top:    int = 45
    margin_bottom: int = 65

    @property
    def n_cats(self) -> int:
        return len(self.categories)

    @property
    def n_subs(self) -> int:
        return len(self.subgroups)

    def group_by_tag(self, tag: str) -> Optional[GroupedBarGroup]:
        for g in self.groups:
            if g.bar_tag == tag:
                return g
        return None

    def with_geometry(self, **kw) -> "GroupedBarScene":
        d = {f: getattr(self, f) for f in self.__dataclass_fields__}
        d.update(kw)
        return GroupedBarScene(**d)


def _read_grouped_groups(
    excel_path: str, sheet
) -> Tuple[List[str], List[str], Dict[Tuple[str,str], np.ndarray]]:
    """
    Read a grouped-bar Excel file (row 0 = categories, row 1 = subgroups).
    Returns (categories, subgroups, {(cat, sub): values}).
    """
    raw = pd.read_excel(excel_path, sheet_name=sheet, header=None)
    row0 = [str(h) if pd.notna(h) else "" for h in raw.iloc[0]]
    row1 = [str(h) if pd.notna(h) else "" for h in raw.iloc[1]]
    data = raw.iloc[2:].reset_index(drop=True)
    n_cols = raw.shape[1]

    categories = list(dict.fromkeys(c for c in row0 if c))
    subgroups  = list(dict.fromkeys(s for s in row1 if s))

    col_map: Dict[Tuple[str,str], List[int]] = {}
    for ci in range(n_cols):
        cat, sub = row0[ci], row1[ci]
        if cat and sub:
            col_map.setdefault((cat, sub), []).append(ci)

    vals: Dict[Tuple[str,str], np.ndarray] = {}
    for cat in categories:
        for sub in subgroups:
            idxs = col_map.get((cat, sub), [])
            if idxs:
                flat = pd.to_numeric(
                    data.iloc[:, idxs].values.flatten(), errors="coerce"
                ).astype(float)
                vals[(cat, sub)] = flat[~np.isnan(flat)]
            else:
                vals[(cat, sub)] = np.array([])
    return categories, subgroups, vals


def build_grouped_bar_scene(
    kw: dict, canvas_w: int, canvas_h: int
) -> GroupedBarScene:
    """
    Build a GroupedBarScene from plot kwargs.  No matplotlib needed.
    """
    excel_path  = kw["excel_path"]
    sheet       = kw.get("sheet", 0)
    error_type  = kw.get("error", "sem")
    bar_width   = float(kw.get("bar_width", 0.6))
    show_points = bool(kw.get("show_points", True))
    font_size   = float(kw.get("font_size", 12.0))
    alpha       = float(kw.get("alpha", 0.85))
    title       = kw.get("title", "") or ""
    xlabel      = kw.get("xlabel", "") or ""
    ylabel      = kw.get("ytitle", "") or kw.get("ylabel", "") or ""
    color_spec  = kw.get("color", None)

    categories, subgroups, vals = _read_grouped_groups(excel_path, sheet)
    n_subs = len(subgroups)
    hex_colors = _prism_palette_n(n_subs, color_spec)

    groups: List[GroupedBarGroup] = []
    all_tops: List[float] = []

    for ci, cat in enumerate(categories):
        for si, sub in enumerate(subgroups):
            v = vals.get((cat, sub), np.array([]))
            if len(v) == 0:
                m, err = 0.0, 0.0
            else:
                m, err = _calc_error_plain(v, error_type)
            fill_raw     = hex_colors[si % len(hex_colors)]
            fill_hex     = _rgba_to_hex(fill_raw)
            fill_blended = _blend_alpha(fill_hex, alpha)
            edge_hex     = _darken_hex(fill_hex, 0.65)
            groups.append(GroupedBarGroup(
                category=cat, subgroup=sub,
                cat_index=ci, sub_index=si,
                mean=m, error=err,
                color=fill_blended, edge_color=edge_hex, points=v,
                bar_tag=f"gbar_{ci}_{si}",
                err_tag=f"gerr_{ci}_{si}",
                pts_tag=f"gpts_{ci}_{si}",
            ))
            all_tops.append(m + err)

    y_min   = 0.0
    raw_top = max(all_tops) if all_tops else 1.0
    y_max   = raw_top * 1.15 if raw_top > 0 else 1.0
    ml      = max(60, int(font_size * 4.5))
    mb      = max(60, int(font_size * 4.5))

    return GroupedBarScene(
        groups=groups, categories=categories, subgroups=subgroups,
        title=title, xlabel=xlabel, ylabel=ylabel,
        error_type=error_type, bar_width=bar_width,
        show_points=show_points, font_size=font_size, alpha=alpha,
        y_min=y_min, y_max=y_max,
        canvas_w=canvas_w, canvas_h=canvas_h,
        margin_left=ml, margin_right=25, margin_top=45, margin_bottom=mb,
    )


class GroupedCoordTransform:
    """
    Coordinate transform for grouped bar charts.

    Layout:
      The plot area is divided into n_cats equal *cluster* cells.
      Each cluster is divided into n_subs equal *bar* cells.
      A gap of `gap_frac` of cluster_w is added between clusters.
    """

    GAP_FRAC = 0.25   # fraction of cluster_w used as inter-cluster gap

    def __init__(self, scene: GroupedBarScene) -> None:
        self._s = scene

    @property
    def plot_w(self) -> int:
        return self._s.canvas_w - self._s.margin_left - self._s.margin_right

    @property
    def plot_h(self) -> int:
        return self._s.canvas_h - self._s.margin_top - self._s.margin_bottom

    @property
    def cluster_w(self) -> float:
        return self.plot_w / max(self._s.n_cats, 1)

    @property
    def bar_cell_w(self) -> float:
        """Width of one bar cell within a cluster (accounts for gap)."""
        usable = self.cluster_w * (1 - self.GAP_FRAC)
        return usable / max(self._s.n_subs, 1)

    def bar_cx(self, cat_idx: int, sub_idx: int) -> int:
        """Centre X pixel of bar (cat_idx, sub_idx)."""
        s          = self._s
        gap_half   = self.cluster_w * self.GAP_FRAC / 2
        cluster_cx = s.margin_left + (cat_idx + 0.5) * self.cluster_w
        # sub bars are left-aligned within the cluster's usable width
        usable     = self.cluster_w * (1 - self.GAP_FRAC)
        x_left     = cluster_cx - usable / 2
        return int(x_left + (sub_idx + 0.5) * self.bar_cell_w)

    def bar_half_w(self) -> int:
        return max(2, int(self.bar_cell_w * self._s.bar_width * 0.5))

    def cap_half_w(self) -> int:
        return max(1, self.bar_half_w() // 3)

    def cat_cx(self, cat_idx: int) -> int:
        """Centre X of an entire category cluster (for x-axis label)."""
        return int(self._s.margin_left + (cat_idx + 0.5) * self.cluster_w)

    def y(self, data_val: float) -> int:
        s    = self._s
        span = s.y_max - s.y_min
        frac = (data_val - s.y_min) / span if span > 0 else 0.0
        return int(s.canvas_h - s.margin_bottom - frac * self.plot_h)

    def y_zero(self) -> int:
        return self.y(max(self._s.y_min, 0.0))

    def canvas_to_y(self, cy: int) -> float:
        s    = self._s
        frac = (s.canvas_h - s.margin_bottom - cy) / max(self.plot_h, 1)
        return s.y_min + frac * (s.y_max - s.y_min)


class GroupedCanvasRenderer:
    """
    Renders a GroupedBarScene onto a tk.Canvas.

    Supports:
      • Hit testing  — click a bar to get (category, subgroup)
      • Live recolor — per-bar colour change via recolor(tag, hex)
      • Y-axis drag  — ▲ handle above Y spine, drag to rescale (same as CanvasRenderer)
      • Legend       — drawn in top-right margin
    """

    _FONT_FACE = "Helvetica Neue"

    def __init__(self, canvas, scene: GroupedBarScene) -> None:
        self._canvas    = canvas
        self._scene     = scene
        self._tf        = GroupedCoordTransform(scene)
        self._rh: Optional[RescaleHandle] = None

        self._bar_rects:    Dict[str, int] = {}
        self._bar_colors:   Dict[str, str] = {}
        self._err_stems:    Dict[str, int] = {}
        self._err_top_caps: Dict[str, int] = {}
        self._err_bot_caps: Dict[str, int] = {}
        self._pts_ovals:    Dict[str, List[int]] = {}
        self._items:        Dict[str, List[int]] = {}
        self._y_spine_id:   Optional[int] = None
        self._y_drag_id:    Optional[int] = None
        self._drag:         Optional[dict] = None

    @property
    def rescale_handle(self) -> Optional[RescaleHandle]:
        return self._rh

    def render(self) -> None:
        c = self._canvas
        c.delete("all")
        for d in (self._bar_rects, self._bar_colors, self._err_stems,
                  self._err_top_caps, self._err_bot_caps, self._pts_ovals,
                  self._items):
            d.clear()
        self._y_spine_id = self._y_drag_id = None

        self._draw_background()
        self._draw_axes()
        self._draw_y_drag_handle()
        self._draw_y_ticks()
        self._draw_x_labels()
        for g in self._scene.groups:
            self._draw_bar(g)
            self._draw_error_bar(g)
        if self._scene.show_points:
            for g in self._scene.groups:
                self._draw_jitter_points(g)
        self._draw_legend()
        self._draw_axis_labels()
        self._draw_title()

        # Build a RescaleHandle from scene geometry for compatibility
        self._rh = RescaleHandle(
            y_min=self._scene.y_min, y_max=self._scene.y_max,
            canvas_w=self._scene.canvas_w, canvas_h=self._scene.canvas_h,
            margin_left=self._scene.margin_left, margin_right=self._scene.margin_right,
            margin_top=self._scene.margin_top,   margin_bottom=self._scene.margin_bottom,
            n_groups=self._scene.n_cats * self._scene.n_subs,
            bar_width=self._scene.bar_width,
        )

    # ── Mouse events ─────────────────────────────────────────────────────────

    def on_press(self, event) -> ClickResult:
        self._drag = None
        cx, cy = event.x, event.y

        # Y-drag handle
        if self._y_drag_id is not None and self._near_y_handle(cx, cy):
            self._drag = {"kind": "y_drag"}
            return ClickResult(kind="y_drag_start")

        # Bar hit
        tag = self.hit_test(cx, cy)
        if tag:
            return ClickResult(kind="bar", bar_tag=tag)
        return ClickResult()

    def on_motion(self, event) -> None:
        if self._drag is None:
            return
        if self._drag["kind"] == "y_drag":
            new_ymax = self._tf.canvas_to_y(event.y)
            max_data = max((g.y_top for g in self._scene.groups), default=1.0)
            new_ymax = max(new_ymax, max_data * 1.02, self._scene.y_min + 0.01)
            self._incremental_rescale_y(self._scene.y_min, new_ymax)

    def on_release(self, event) -> None:
        self._drag = None

    def hit_test(self, cx: int, cy: int) -> Optional[str]:
        items = self._canvas.find_overlapping(cx-2, cy-2, cx+2, cy+2)
        for iid in reversed(items):
            for tag in self._canvas.gettags(iid):
                if tag.startswith("gbar_"):
                    return tag
        return None

    def recolor(self, bar_tag: str, new_color: str) -> None:
        iid = self._bar_rects.get(bar_tag)
        if iid is None:
            return
        new_hex = (_rgba_to_hex(new_color)
                   if not new_color.startswith("#") else new_color)
        self._canvas.itemconfig(iid, fill=new_hex,
                                 outline=_darken_hex(new_hex, 0.65))
        self._bar_colors[bar_tag] = new_hex

    def current_color(self, bar_tag: str) -> Optional[str]:
        return self._bar_colors.get(bar_tag)

    def rescale(self, handle: RescaleHandle) -> None:
        """Full redraw with new geometry (grouped bars always do full redraw)."""
        saved = dict(self._bar_colors)
        new_s = self._scene.with_geometry(
            y_min=handle.y_min, y_max=handle.y_max,
            canvas_w=handle.canvas_w, canvas_h=handle.canvas_h,
            bar_width=handle.bar_width,
        )
        self._scene = new_s
        self._tf    = GroupedCoordTransform(new_s)
        self.render()
        for tag, col in saved.items():
            self.recolor(tag, col)
        self._rh = handle

    # ── Incremental Y rescale ────────────────────────────────────────────────

    def _incremental_rescale_y(self, new_y_min: float, new_y_max: float) -> None:
        new_s       = self._scene.with_geometry(y_min=new_y_min, y_max=new_y_max)
        self._scene = new_s
        self._tf    = GroupedCoordTransform(new_s)
        c           = self._canvas
        y_zero      = self._tf.y_zero()

        for g in new_s.groups:
            cx = self._tf.bar_cx(g.cat_index, g.sub_index)
            hw = self._tf.bar_half_w()
            cw = self._tf.cap_half_w()

            rect_id = self._bar_rects.get(g.bar_tag)
            if rect_id is not None:
                y_t = self._tf.y(max(g.mean, 0.0)); y_b = y_zero
                if y_t > y_b: y_t, y_b = y_b, y_t
                c.coords(rect_id, cx-hw, y_t, cx+hw, y_b)

            if (sid := self._err_stems.get(g.err_tag)) is not None:
                c.coords(sid, cx, self._tf.y(g.y_bot), cx, self._tf.y(g.y_top))

            cy_top = self._tf.y(g.y_top); cy_bot = self._tf.y(g.y_bot)
            if (tid := self._err_top_caps.get(g.err_tag)) is not None:
                c.coords(tid, cx-cw, cy_top, cx+cw, cy_top)
            if (bid := self._err_bot_caps.get(g.err_tag)) is not None:
                c.coords(bid, cx-cw, cy_bot, cx+cw, cy_bot)

            r   = max(2, int(new_s.font_size * 0.35))
            rng = np.random.default_rng(seed=g.cat_index * 100 + g.sub_index)
            js  = max(4, hw // 2)
            jitter = rng.uniform(-js, js, len(g.points))
            for oid, v, jx in zip(self._pts_ovals.get(g.pts_tag, []),
                                   g.points, jitter):
                px = cx + int(jx); py = self._tf.y(float(v))
                c.coords(oid, px-r, py-r, px+r, py+r)

        for iid in (self._items.pop("tick_y", [])
                    + self._items.pop("ticklabel_y", [])):
            c.delete(iid)
        self._draw_y_ticks()

        if self._y_spine_id is not None:
            s = new_s
            c.coords(self._y_spine_id,
                     s.margin_left, s.margin_top,
                     s.margin_left, s.canvas_h - s.margin_bottom)
        self._move_y_drag_handle()

        self._rh = RescaleHandle(
            y_min=new_y_min, y_max=new_y_max,
            canvas_w=new_s.canvas_w, canvas_h=new_s.canvas_h,
            margin_left=new_s.margin_left, margin_right=new_s.margin_right,
            margin_top=new_s.margin_top,   margin_bottom=new_s.margin_bottom,
            n_groups=new_s.n_cats * new_s.n_subs,
            bar_width=new_s.bar_width,
        )

    # ── Drag helpers ─────────────────────────────────────────────────────────

    def _near_y_handle(self, cx: int, cy: int) -> bool:
        s  = self._scene
        hx = s.margin_left; hy = s.margin_top - _Y_HANDLE_H // 2
        return (abs(cx - hx) <= _Y_HANDLE_W + _Y_HANDLE_PAD
                and abs(cy - hy) <= _Y_HANDLE_H + _Y_HANDLE_PAD)

    # ── Drawing primitives ───────────────────────────────────────────────────

    def _font(self, delta: int = 0, bold: bool = False) -> tuple:
        sz    = max(7, int(self._scene.font_size + delta))
        style = "bold" if bold else ""
        return (self._FONT_FACE, sz, style) if style else (self._FONT_FACE, sz)

    def _add(self, tag: str, iid: int) -> None:
        self._items.setdefault(tag, []).append(iid)

    def _draw_background(self) -> None:
        s = self._scene
        self._canvas.configure(bg="white")
        iid = self._canvas.create_rectangle(
            s.margin_left, s.margin_top,
            s.canvas_w - s.margin_right, s.canvas_h - s.margin_bottom,
            fill="white", outline="", tags=("bg_plot",))
        self._add("bg_plot", iid)

    def _draw_axes(self) -> None:
        s = self._scene; ax = "#333333"
        lw = max(1, int(s.font_size * 0.065))
        iid = self._canvas.create_line(
            s.margin_left, s.canvas_h - s.margin_bottom,
            s.canvas_w - s.margin_right, s.canvas_h - s.margin_bottom,
            fill=ax, width=lw, tags=("axis_x",))
        self._add("axis_x", iid)
        iid = self._canvas.create_line(
            s.margin_left, s.margin_top,
            s.margin_left, s.canvas_h - s.margin_bottom,
            fill=ax, width=lw, tags=("axis_y",))
        self._add("axis_y", iid)
        self._y_spine_id = iid

    def _draw_y_drag_handle(self) -> None:
        s  = self._scene
        hx = s.margin_left; hy = s.margin_top - _Y_HANDLE_H
        iid = self._canvas.create_polygon(
            hx, hy,
            hx - _Y_HANDLE_W, hy + _Y_HANDLE_H,
            hx + _Y_HANDLE_W, hy + _Y_HANDLE_H,
            fill="#2274A5", outline="#2274A5", tags=("y_drag_handle",))
        self._add("y_drag_handle", iid)
        self._y_drag_id = iid

    def _move_y_drag_handle(self) -> None:
        if self._y_drag_id is None: return
        s  = self._scene; hx = s.margin_left; hy = s.margin_top - _Y_HANDLE_H
        self._canvas.coords(self._y_drag_id,
            hx, hy, hx-_Y_HANDLE_W, hy+_Y_HANDLE_H, hx+_Y_HANDLE_W, hy+_Y_HANDLE_H)

    def _draw_y_ticks(self) -> None:
        rh = RescaleHandle(
            y_min=self._scene.y_min, y_max=self._scene.y_max,
            canvas_w=self._scene.canvas_w, canvas_h=self._scene.canvas_h,
            margin_left=self._scene.margin_left, margin_right=self._scene.margin_right,
            margin_top=self._scene.margin_top,   margin_bottom=self._scene.margin_bottom,
        )
        s = self._scene; ax = "#333333"
        for v in rh.nice_y_ticks():
            cy = self._tf.y(v)
            if cy < s.margin_top or cy > s.canvas_h - s.margin_bottom: continue
            iid = self._canvas.create_line(s.margin_left-5, cy, s.margin_left, cy,
                fill=ax, width=1, tags=("tick_y",))
            self._add("tick_y", iid)
            iid = self._canvas.create_text(s.margin_left-9, cy, text=_fmt_tick_label(v),
                anchor="e", font=self._font(-2), fill="#333333", tags=("ticklabel_y",))
            self._add("ticklabel_y", iid)

    def _draw_x_labels(self) -> None:
        s = self._scene; ax = "#333333"
        y = s.canvas_h - s.margin_bottom + 8
        for ci, cat in enumerate(s.categories):
            cx = self._tf.cat_cx(ci)
            iid = self._canvas.create_line(cx, s.canvas_h-s.margin_bottom,
                cx, s.canvas_h-s.margin_bottom+5, fill=ax, width=1, tags=("tick_x",))
            self._add("tick_x", iid)
            iid = self._canvas.create_text(cx, y, text=cat, anchor="n",
                font=self._font(-1, bold=True), fill="#333333", tags=("ticklabel_x",))
            self._add("ticklabel_x", iid)

    def _draw_bar(self, g: GroupedBarGroup) -> None:
        cx = self._tf.bar_cx(g.cat_index, g.sub_index)
        hw = self._tf.bar_half_w()
        y_t = self._tf.y(max(g.mean, 0.0)); y_b = self._tf.y_zero()
        if y_t > y_b: y_t, y_b = y_b, y_t
        iid = self._canvas.create_rectangle(
            cx-hw, y_t, cx+hw, y_b,
            fill=g.color, outline=g.edge_color, width=1,
            tags=(g.bar_tag, "gbar"))
        self._add(g.bar_tag, iid)
        self._bar_rects[g.bar_tag]  = iid
        self._bar_colors[g.bar_tag] = g.color

    def _draw_error_bar(self, g: GroupedBarGroup) -> None:
        cx   = self._tf.bar_cx(g.cat_index, g.sub_index)
        cw   = self._tf.cap_half_w()
        ytop = self._tf.y(g.y_top); ybot = self._tf.y(g.y_bot); ec = "#222222"

        stem = self._canvas.create_line(cx, ybot, cx, ytop,
            fill=ec, width=1, tags=(g.err_tag, "gerrbar"))
        self._add(g.err_tag, stem); self._err_stems[g.err_tag] = stem

        tcap = self._canvas.create_line(cx-cw, ytop, cx+cw, ytop,
            fill=ec, width=1, tags=(g.err_tag, "gerrcap"))
        self._add(g.err_tag, tcap); self._err_top_caps[g.err_tag] = tcap

        bcap = self._canvas.create_line(cx-cw, ybot, cx+cw, ybot,
            fill=ec, width=1, tags=(g.err_tag, "gerrcap"))
        self._add(g.err_tag, bcap); self._err_bot_caps[g.err_tag] = bcap

    def _draw_jitter_points(self, g: GroupedBarGroup) -> None:
        if len(g.points) == 0: return
        cx  = self._tf.bar_cx(g.cat_index, g.sub_index)
        r   = max(2, int(self._scene.font_size * 0.3))
        rng = np.random.default_rng(seed=g.cat_index * 100 + g.sub_index)
        js  = max(3, self._tf.bar_half_w() // 2)
        jitter = rng.uniform(-js, js, len(g.points))
        ovals: List[int] = []
        for v, jx in zip(g.points, jitter):
            px = cx + int(jx); py = self._tf.y(float(v))
            iid = self._canvas.create_oval(px-r, py-r, px+r, py+r,
                fill=g.edge_color, outline=g.edge_color, tags=(g.pts_tag, "gpoint"))
            self._add(g.pts_tag, iid); ovals.append(iid)
        self._pts_ovals[g.pts_tag] = ovals

    def _draw_legend(self) -> None:
        """Draw a compact colour-swatch legend for subgroups (top-right)."""
        s    = self._scene
        if s.n_subs <= 1: return
        # Collect one colour per subgroup (from first category that has data)
        sub_colors: Dict[str, str] = {}
        for g in s.groups:
            if g.subgroup not in sub_colors:
                sub_colors[g.subgroup] = g.color
            if len(sub_colors) == s.n_subs:
                break

        sw = 12; sh = 12; pad = 4
        x0 = s.canvas_w - s.margin_right - 8
        y0 = s.margin_top + 6

        for si, sub in enumerate(s.subgroups):
            col = sub_colors.get(sub, "#888888")
            y   = y0 + si * (sh + pad + 2)
            # Swatch
            iid = self._canvas.create_rectangle(
                x0 - sw, y, x0, y + sh,
                fill=col, outline=_darken_hex(col, 0.65), width=1,
                tags=("legend",))
            self._add("legend", iid)
            # Label
            iid = self._canvas.create_text(
                x0 - sw - 4, y + sh//2, text=sub,
                anchor="e", font=self._font(-3), fill="#333333",
                tags=("legend",))
            self._add("legend", iid)

    def _draw_axis_labels(self) -> None:
        s = self._scene
        if s.ylabel:
            lx = max(14, s.margin_left // 3)
            ly = s.margin_top + (s.canvas_h - s.margin_top - s.margin_bottom) // 2
            try:
                iid = self._canvas.create_text(lx, ly, text=s.ylabel,
                    font=self._font(1, bold=True), fill="#333333",
                    angle=90, anchor="center", tags=("label_y",))
            except Exception:
                iid = self._canvas.create_text(4, ly, text=s.ylabel,
                    font=self._font(-1, bold=True), fill="#333333",
                    anchor="w", tags=("label_y",))
            self._add("label_y", iid)
        if s.xlabel:
            lx = s.margin_left + (s.canvas_w - s.margin_left - s.margin_right)//2
            iid = self._canvas.create_text(lx, s.canvas_h-8, text=s.xlabel,
                font=self._font(1, bold=True), fill="#333333",
                anchor="s", tags=("label_x",))
            self._add("label_x", iid)

    def _draw_title(self) -> None:
        s = self._scene
        if not s.title: return
        lx = s.margin_left + (s.canvas_w - s.margin_left - s.margin_right)//2
        iid = self._canvas.create_text(
            lx, max(4, s.margin_top//2), text=s.title,
            font=self._font(4, bold=True), fill="#111111",
            anchor="center", tags=("label_title",))
        self._add("label_title", iid)
