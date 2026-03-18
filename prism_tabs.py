"""
prism_tabs.py
=============
Tab system for Claude Prism.

Three classes:
  TabState    — dataclass holding per-tab identity and form state
  TabManager  — create/close/reorder tabs; save/restore form state on switch
  TabBar      — tk.Canvas horizontal tab strip (visual only, fires callbacks)

Also exports:
  draw_tab_icon(canvas, x, y, key, size) — shared icon drawing used by both
                                            the sidebar and the tab bar.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import tkinter as tk
from tkinter import ttk
import uuid


# ── TabState ─────────────────────────────────────────────────────────────────

@dataclass
class TabState:
    """Per-tab state container.  One instance per open plot tab."""

    tab_id:         str         # unique hex UUID
    chart_type:     str         # registry key e.g. "bar", "scatter"
    chart_type_idx: int         # index in _REGISTRY_SPECS / sidebar position
    label:          str         # display name; defaults to "Untitled"
    vars_snapshot:  dict        # saved copy of all form tk-var values
    file_path:      str         # absolute path to excel file, or ""
    sheet_name:     str         # sheet name or ""
    validated:      bool        # whether spreadsheet passed validation
    plot_frame:     Any         # ttk.Frame — stable container; NEVER replaced

    fig:            Any = None  # matplotlib Figure; kept for export
    canvas_widget:  Any = None  # FigureCanvasTkAgg (Agg path)
    render_job_id:  str = None  # UUID hex; superseded-job guard


# ── TabManager ────────────────────────────────────────────────────────────────

class TabManager:
    """
    Manages the list of TabState objects.

    Responsibilities:
      • create / close / reorder tabs
      • save outgoing form state and restore incoming form state on switch
      • sync sidebar highlight (silent — no chart-type reset)
      • suppress live preview during var restore
    """

    def __init__(self, app, tab_bar: "TabBar", plot_canvas: tk.Canvas):
        self._app         = app
        self._tab_bar     = tab_bar
        self._plot_canvas = plot_canvas
        self._tabs:       list[TabState] = []
        self._active_idx: int            = -1

    # ── Public API ─────────────────────────────────────────────────────────────

    def new_tab(self, chart_type: str = "bar") -> TabState:
        """Create a new tab, add it to the bar, switch to it."""
        try:
            from prism_registry import _REGISTRY_SPECS as _specs
        except ImportError:
            _specs = []
        idx = next((i for i, s in enumerate(_specs) if s.key == chart_type), 0)

        tab_id     = uuid.uuid4().hex
        plot_frame = ttk.Frame(self._plot_canvas)

        # Keep scrollregion in sync whenever this frame's content changes
        plot_frame.bind(
            "<Configure>",
            lambda e: self._plot_canvas.configure(
                scrollregion=self._plot_canvas.bbox("all")),
        )

        tab = TabState(
            tab_id=tab_id,
            chart_type=chart_type,
            chart_type_idx=idx,
            label="Untitled",
            vars_snapshot={},
            file_path="",
            sheet_name="",
            validated=False,
            plot_frame=plot_frame,
        )
        self._tabs.append(tab)
        self._tab_bar.set_tabs(self._tabs)
        self.switch_to(tab_id)

        # New tabs always start with a clean form
        self._app._reset_chart_type_state()
        return tab

    def close_tab(self, tab_id: str) -> None:
        """Close tab, destroy its plot_frame, activate nearest neighbour."""
        tab = self.get_tab(tab_id)
        if tab is None:
            return

        idx       = self._tabs.index(tab)
        is_active = (self._active_idx == idx)

        tab.plot_frame.place_forget()
        tab.plot_frame.destroy()

        if tab.fig is not None:
            try:
                import matplotlib.pyplot as _plt
                _plt.close(tab.fig)
            except Exception:
                pass

        self._tabs.pop(idx)

        if not self._tabs:
            self._active_idx = -1
            self.new_tab("bar")
            return

        if is_active:
            new_idx          = min(idx, len(self._tabs) - 1)
            self._active_idx = -1   # force switch_to to proceed
            self.switch_to(self._tabs[new_idx].tab_id)
        elif self._active_idx > idx:
            self._active_idx -= 1

        self._tab_bar.set_tabs(self._tabs)
        if self.active:
            self._tab_bar.set_active(self.active.tab_id)

    def switch_to(self, tab_id: str) -> None:
        """Save outgoing state, swap frames, restore incoming state."""
        outgoing = self.active
        incoming = self.get_tab(tab_id)
        if incoming is None or incoming is outgoing:
            return

        # 1. Save outgoing form state
        if outgoing is not None:
            outgoing.vars_snapshot = {
                k: v.get() for k, v in self._app._vars.items()
            }
            outgoing.file_path  = (self._app._vars.get("excel_path")
                                   or _NullVar()).get()
            outgoing.sheet_name = (self._app._vars.get("sheet")
                                   or _NullVar()).get()
            outgoing.validated  = self._app._validated
            outgoing.plot_frame.place_forget()

        # 2. Suppress live preview during var restore (prevents ~694 spurious re-renders)
        self._app._live_preview_enabled = False
        self._app._switching_tabs       = True

        # 3. Restore incoming form state
        for k, v in self._app._vars.items():
            if k in incoming.vars_snapshot:
                try:
                    v.set(incoming.vars_snapshot[k])
                except Exception:
                    pass

        # 4. Re-enable live preview; cancel any pending preview that fired during restore
        self._app._live_preview_enabled = True
        self._app._switching_tabs       = False
        if getattr(self._app, "_preview_after_id", None):
            try:
                self._app.after_cancel(self._app._preview_after_id)
            except Exception:
                pass
            self._app._preview_after_id = None

        # 5. Restore file/validation state
        self._app._file_selected = bool(incoming.file_path)
        self._app._validated     = incoming.validated

        # 6. Show incoming plot frame; update app references
        incoming.plot_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._app._plot_frame    = incoming.plot_frame
        self._app._canvas_widget = incoming.canvas_widget
        self._app._fig           = incoming.fig

        # 7. Sync sidebar highlight (silent — no chart-type reset)
        self._app._sb_select_silent(incoming.chart_type_idx)

        # 8. Update active pointer and tab bar
        self._active_idx = self._tabs.index(incoming)
        self._tab_bar.set_active(tab_id)

        # 9. Unlock/lock form to match incoming tab state
        if incoming.validated:
            self._app._unlock_form()
            self._app._run_btn.config(state="normal")
        else:
            self._app._lock_form()
            self._app._run_btn.config(state="disabled")

    def reorder(self, from_idx: int, to_idx: int) -> None:
        """Move tab in list and redraw tab bar."""
        if from_idx == to_idx:
            return
        n = len(self._tabs)
        if not (0 <= from_idx < n and 0 <= to_idx < n):
            return

        active = self.active
        tab    = self._tabs.pop(from_idx)
        self._tabs.insert(to_idx, tab)

        if active is not None:
            self._active_idx = self._tabs.index(active)

        self._tab_bar.set_tabs(self._tabs)
        if active:
            self._tab_bar.set_active(active.tab_id)

    def get_tab(self, tab_id: str) -> "TabState | None":
        """Return TabState by id, or None if not found."""
        return next((t for t in self._tabs if t.tab_id == tab_id), None)

    def update_label(self, tab_id: str, label: str) -> None:
        """Update tab label and redraw that tab in the bar."""
        tab = self.get_tab(tab_id)
        if tab is not None:
            tab.label = label
            self._tab_bar.update_label(tab_id, label)

    @property
    def active(self) -> "TabState | None":
        if 0 <= self._active_idx < len(self._tabs):
            return self._tabs[self._active_idx]
        return None

    @property
    def all_tabs(self) -> list[TabState]:
        return list(self._tabs)


class _NullVar:
    """Fallback for missing vars."""
    def get(self):      return ""
    def set(self, v):   pass


# ── Icon drawing ──────────────────────────────────────────────────────────────

def draw_tab_icon(canvas: tk.Canvas, x: int, y: int,
                  key: str, size: int = 14, color: str = "#2274A5"):
    """
    Draw a miniature chart icon on *canvas* at pixel (x, y).

    Used by both the tab bar and (optionally) the sidebar.  All drawing is
    done with primitive canvas shapes so no images or fonts are required.
    """
    s = size

    if key in ("bar", "grouped_bar", "stacked_bar", "column_stats",
               "subcolumn_scatter", "dot_plot"):
        for bx, bh in ((1, 8), (5, 11), (9, 6)):
            canvas.create_rectangle(
                x + bx, y + s - bh, x + bx + 3, y + s,
                fill=color, outline="")

    elif key in ("line", "curve_fit"):
        pts = [x + 1, y + s - 3, x + 4, y + 4, x + 8, y + 8, x + s - 1, y + 2]
        canvas.create_line(pts, fill=color, width=2, smooth=True)

    elif key in ("scatter", "bubble", "bland_altman"):
        for dx, dy in ((2, 10), (6, 5), (10, 8), (4, 2)):
            canvas.create_oval(
                x + dx, y + dy, x + dx + 2, y + dy + 2,
                fill=color, outline="")

    elif key == "box":
        canvas.create_rectangle(
            x + 2, y + 3, x + s - 2, y + s - 3, outline=color, fill="")
        canvas.create_line(x + s // 2, y,     x + s // 2, y + 3,     fill=color)
        canvas.create_line(x + s // 2, y + s - 3, x + s // 2, y + s, fill=color)

    elif key == "violin":
        pts = [x + s // 2, y + 1,
               x + s - 2, y + s // 2,
               x + s // 2, y + s - 1,
               x + 2,     y + s // 2]
        canvas.create_polygon(pts, outline=color, fill="", smooth=True)

    elif key == "heatmap":
        shades = [color, "#aaaaaa", "#dddddd"]
        for row in range(3):
            for col in range(3):
                shade = shades[(row * 3 + col) % 3]
                canvas.create_rectangle(
                    x + col * 4 + 1, y + row * 4 + 1,
                    x + col * 4 + 4, y + row * 4 + 4,
                    fill=shade, outline="")

    elif key == "kaplan_meier":
        pts = [x + 1, y + 1,
               x + 4, y + 1, x + 4, y + 6,
               x + 8, y + 6, x + 8, y + 11,
               x + s, y + 11]
        canvas.create_line(pts, fill=color, width=2)

    elif key == "histogram":
        for bx, bh in ((1, 5), (4, 9), (7, 12), (10, 7)):
            canvas.create_rectangle(
                x + bx, y + s - bh, x + bx + 3, y + s,
                fill=color, outline="")

    elif key == "forest_plot":
        canvas.create_line(x + s // 2, y + 1, x + s // 2, y + s - 1,
                           fill=color, width=1, dash=(2, 2))
        for row in (3, 7, 11):
            canvas.create_line(x + 2, y + row, x + s - 2, y + row,
                               fill=color, width=2)

    elif key == "before_after":
        for px, py in ((3, 10), (3, 4), (10, 8), (10, 3)):
            canvas.create_oval(x + px, y + py, x + px + 2, y + py + 2,
                               fill=color, outline="")
        canvas.create_line(x + 4, y + 11, x + 11, y + 9, fill=color, dash=(2, 2))
        canvas.create_line(x + 4, y + 5,  x + 11, y + 4, fill=color, dash=(2, 2))

    elif key == "waterfall":
        for bx, bh, up in ((1, 5, True), (4, 7, True), (7, 3, False), (10, 9, True)):
            fill = color if up else "#aaaaaa"
            canvas.create_rectangle(
                x + bx, y + s - bh, x + bx + 2, y + s,
                fill=fill, outline="")

    elif key in ("contingency", "chi_square_gof", "repeated_measures"):
        for col in range(3):
            for row in range(3):
                shade = color if (col + row) % 2 == 0 else "#cccccc"
                canvas.create_rectangle(
                    x + col * 4 + 1, y + row * 4 + 1,
                    x + col * 4 + 4, y + row * 4 + 4,
                    fill=shade, outline="")

    else:
        # Fallback: generic bar icon
        for bx, bh in ((1, 8), (5, 11), (9, 6)):
            canvas.create_rectangle(
                x + bx, y + s - bh, x + bx + 3, y + s,
                fill=color, outline="")


# ── TabBar ────────────────────────────────────────────────────────────────────

class TabBar(tk.Canvas):
    """
    Horizontal tab bar rendered on a tk.Canvas.

    Visual only — fires callbacks (on_select, on_close, on_new, on_reorder)
    and owns no state itself.  All state lives in TabManager.

    Layout (per tab):  [chart-icon 14px]  [label, max 17 chars]  [× 18px]
    """

    _H       = 32   # total height
    _TAB_MIN = 100  # minimum tab width
    _TAB_MAX = 200  # maximum tab width
    _PAD_X   = 8    # left padding inside each tab
    _ICON_W  = 14   # icon square size
    _CLOSE_W = 18   # close button width
    _NEW_W   = 28   # "+ new tab" button width

    def __init__(self, parent, on_select, on_close, on_new, on_reorder,
                 height=32, **kwargs):
        super().__init__(parent, height=height, highlightthickness=0,
                         bg="#e8eaed", **kwargs)
        self._on_select  = on_select
        self._on_close   = on_close
        self._on_new     = on_new
        self._on_reorder = on_reorder

        self._tabs:      list[TabState] = []
        self._active_id: str | None     = None
        self._rects:     list[dict]     = []   # [{tab_id, x1, x2, close_x1}]
        self._new_x1:    int            = 0
        self._new_x2:    int            = 0
        self._drag_x:    int | None     = None
        self._drag_id:   str | None     = None

        self.bind("<Button-1>",        self._on_click)
        self.bind("<B1-Motion>",       self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Configure>",       lambda e: self._redraw())

    # ── Public ─────────────────────────────────────────────────────────────────

    def set_tabs(self, tabs: list) -> None:
        """Full redraw from tab list."""
        self._tabs = list(tabs)
        self._redraw()

    def set_active(self, tab_id: str) -> None:
        """Highlight the active tab."""
        self._active_id = tab_id
        self._redraw()

    def update_label(self, tab_id: str, label: str) -> None:
        """Update one tab's label text and redraw."""
        for t in self._tabs:
            if t.tab_id == tab_id:
                t.label = label
                break
        self._redraw()

    # ── Drawing ─────────────────────────────────────────────────────────────────

    def _redraw(self):
        self.delete("all")
        self._rects = []

        if not self._tabs:
            self._draw_new_btn(4)
            return

        total_w = self.winfo_width() or 400
        n       = len(self._tabs)
        avail   = max(0, total_w - self._NEW_W - 4)
        tab_w   = max(self._TAB_MIN, min(self._TAB_MAX, avail // max(n, 1)))

        x = 0
        for tab in self._tabs:
            self._draw_tab(tab, x, tab_w)
            x += tab_w

        # Bottom border across full width
        self.create_line(0, self._H - 1, total_w, self._H - 1, fill="#c0c0c0")

        # Active tab erases its segment of the bottom border
        for r in self._rects:
            if r["tab_id"] == self._active_id:
                self.create_line(r["x1"] + 1, self._H - 1,
                                 r["x2"] - 1, self._H - 1,
                                 fill="white")
                break

        self._draw_new_btn(x + 4)

    def _draw_tab(self, tab: TabState, x: int, w: int):
        h      = self._H
        active = (tab.tab_id == self._active_id)
        bg     = "white"    if active else "#f0f2f5"
        fg     = "#1a1a1a"  if active else "#555555"
        accent = "#2274A5"  if active else fg

        self.create_rectangle(x, 0, x + w, h, fill=bg, outline="#c0c0c0")

        # Icon
        ix = x + self._PAD_X
        iy = (h - self._ICON_W) // 2
        draw_tab_icon(self, ix, iy, tab.chart_type, self._ICON_W, accent)

        # Label (truncated to 17 chars + ellipsis)
        lbl      = (tab.label[:16] + "…") if len(tab.label) > 17 else tab.label
        close_x1 = x + w - self._CLOSE_W - 4
        text_x   = ix + self._ICON_W + 4
        self.create_text(text_x, h // 2, text=lbl, anchor="w",
                         fill=fg, font=("Helvetica Neue", 11))

        # Close ×
        cx = close_x1 + self._CLOSE_W // 2
        self.create_text(cx, h // 2, text="×",
                         fill=fg, font=("Helvetica Neue", 13))

        self._rects.append({
            "tab_id":   tab.tab_id,
            "x1":       x,
            "x2":       x + w,
            "close_x1": close_x1,
        })

    def _draw_new_btn(self, x: int):
        self._new_x1 = x
        self._new_x2 = x + self._NEW_W
        self.create_text(
            x + self._NEW_W // 2, self._H // 2,
            text="+", fill="#555555",
            font=("Helvetica Neue", 15, "bold"))

    # ── Events ─────────────────────────────────────────────────────────────────

    def _on_click(self, event):
        x = event.x

        if self._new_x1 <= x <= self._new_x2:
            self._on_new()
            return

        for r in self._rects:
            if r["x1"] <= x <= r["x2"]:
                self._drag_x  = event.x
                self._drag_id = r["tab_id"]
                if x >= r["close_x1"]:
                    self._on_close(r["tab_id"])
                elif r["tab_id"] != self._active_id:
                    self._on_select(r["tab_id"])
                return

    def _on_drag(self, event):
        if self._drag_id is None or self._drag_x is None:
            return
        if abs(event.x - self._drag_x) < 10:
            return

        src = next((i for i, r in enumerate(self._rects)
                    if r["tab_id"] == self._drag_id), None)
        tgt = next((i for i, r in enumerate(self._rects)
                    if r["x1"] <= event.x <= r["x2"]), None)

        if src is not None and tgt is not None and tgt != src:
            self._on_reorder(src, tgt)
            self._drag_x  = event.x
            self._drag_id = None   # release drag after reorder to avoid double-move

    def _on_release(self, event):
        self._drag_x  = None
        self._drag_id = None
