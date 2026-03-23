"""
plotter_widgets.py
==================
Design-system tokens, custom Tkinter widget classes, and shared UI helpers
for Refraction.

Everything in this module is *display-only* — no plot logic, no file I/O,
no scientific computation.  Import it from ``plotter_barplot_app`` so that
the App class stays focused on application logic.

Public surface
--------------
Design tokens
    _DS                  — colour/font constants used by all widgets

Widget classes (all inherit from tk.Frame)
    PButton              — styled push button with hover/press states
    PCheckbox            — checkmark toggle with canvas rendering
    PRadioGroup          — row of radio buttons sharing a variable
    PEntry               — flat-border text entry with focus highlight
    PCombobox            — styled combobox wrapping ttk.Combobox

UI helpers
    section_sep(parent, row, text)          — blue section band header
    _create_tooltip(widget, text)           — plain hover tooltip
    add_placeholder(entry, var, text)       — grey hint text in entries
    _bind_scroll_recursive(widget, handler) — safe subtree scroll binding

Metadata helpers
    LABELS        — human-readable names for field keys
    HINTS         — one-line tooltips for field keys
    label(key)    — LABELS lookup with key fallback
    hint(key)     — HINTS lookup with empty fallback
    tip(widget, key)   — attach hint-based tooltip

Utility
    _is_num(v)                             — float-castability test
    _non_numeric_values(series, max_shown) — extract bad cells for validators
    _scipy_summary(fn, max_chars)          — one-line scipy function summary
    _sys_bg(parent)                        — detect system background colour
"""

from __future__ import annotations

# Tkinter is optional here so the pure-Python helpers can be imported and tested
# in headless environments (CI, unit-test runners without a display).
_TK_AVAILABLE = False
try:
    import tkinter as tk
    from tkinter import ttk
    _TK_AVAILABLE = True
except ModuleNotFoundError:
    tk  = None   # type: ignore[assignment]
    ttk = None   # type: ignore[assignment]


# Stub base class used when tkinter is not available (headless / test environments).
# Widget classes inherit from it normally; they just cannot be instantiated.
if not _TK_AVAILABLE:
    class _TkFrameStub:
        """No-op base class used when tkinter is unavailable."""
        def __init__(self, *a, **kw): pass
    # Point tk.Frame at the stub so class definitions parse without error
    class _FakeTk:
        Frame = _TkFrameStub
    tk  = _FakeTk()   # type: ignore[assignment]
    ttk = _FakeTk()   # type: ignore[assignment]



# ═══════════════════════════════════════════════════════════════════════════════
# Design-system tokens
# To retheme the app change this block only — all widgets read from here.
# ═══════════════════════════════════════════════════════════════════════════════

class _DS:
    """Design-system colour and font constants shared by all custom widgets.

    Editing a single value here propagates the change to every widget that
    uses it without any other code changes.
    """

    # Accent palette
    PRIMARY     = "#2274A5"   # interactive blue
    PRIMARY_HV  = "#1b5d87"   # hover state
    PRIMARY_PR  = "#155078"   # pressed state

    # Surface colours
    BG          = "#f5f7fa"   # window / panel background
    CARD        = "#ffffff"   # card / panel surface
    ENTRY_BG    = "#ffffff"   # text-entry background
    ENTRY_BDR   = "#d0d7df"   # unfocused entry border
    ENTRY_FOC   = "#2274A5"   # focused entry border

    # Text colours
    TEXT        = "#1a1a1a"   # primary body text
    TEXT_SUBTLE = "#666666"   # secondary / hint text
    DIS_FG      = "#aaaaaa"   # disabled foreground
    DIS_BG      = "#eeeeee"   # disabled background
    DIS_BORDER  = "#cccccc"   # disabled border

    # Ghost button
    GHOST_BDR   = "#d0d7df"
    GHOST_HV    = "#e8edf3"

    # Fonts
    FONT        = ("Helvetica Neue", 12)
    FONT_BOLD   = ("Helvetica Neue", 12, "bold")
    FONT_MONO   = ("Menlo", 12)
    FONT_SM     = ("Helvetica Neue", 11)


# ═══════════════════════════════════════════════════════════════════════════════
# Metadata: field labels and tooltip hints
# ═══════════════════════════════════════════════════════════════════════════════

LABELS: dict[str, str] = {
    "excel_path":     "Excel File",
    "sheet":          "Sheet",
    "error":          "Error Bars",
    "show_points":    "Show Data Points",
    "jitter_amount":  "Jitter Amount",
    "color":          "Color Palette",
    "title":          "Plot Title",
    "xlabel":         "X-axis Label",
    "ytitle":         "Y-axis Label",
    "yscale":         "Y Scale",
    "ylim":           "Y Limits",
    "figsize":        "Figure Size",
    "font_size":      "Font Size",
    "bar_width":      "Bar Width",
    "line_width":     "Line Width",
    "marker_style":   "Marker Style",
    "marker_size":    "Marker Size",
    "show_stats":     "Show Significance Brackets",
    "stats_test":     "Statistical Test",
    "n_permutations": "Number of Permutations",
    "mc_correction":  "Multiple Comparison Correction",
    "posthoc":        "Post-hoc Test",
    "control":        "Control Group",
}

HINTS: dict[str, str] = {
    "excel_path":     "Path to your Excel file (.xlsx or .xls)",
    "sheet":          "Sheet name or index (0 = first sheet)",
    "error":          "Error bar style for the plot",
    "show_points":    "Overlay individual data points as a strip plot",
    "jitter_amount":  "Horizontal spread of data points (0 = no jitter)",
    "color":          "Seaborn palette name, single color, or blank for default Prism colors",
    "title":          "Main title displayed above the plot",
    "xlabel":         "Label for the X axis",
    "ytitle":         "Label for the Y axis",
    "yscale":         "Linear or log scale for the Y axis",
    "ylim":           "Fix Y-axis range (leave as None for automatic)",
    "figsize":        "Figure width x height in inches",
    "font_size":      "Base font size for tick labels and axis titles",
    "bar_width":      "Width of each bar (0.1 = thin, 1.0 = touching)",
    "line_width":     "Thickness of connecting lines",
    "marker_style":   "Shape of the data markers",
    "marker_size":    "Size of the data markers",
    "show_stats":     "Draw significance brackets and p-value annotations",
    "stats_test":     "Statistical test used to compute p-values",
    "n_permutations": "Number of permutations for the permutation test",
    "mc_correction":  "Method used to correct p-values for multiple comparisons",
    "posthoc":        "Post-hoc pairwise test (for 3+ groups, parametric only)",
    "control":        "Reference group for pairwise comparisons (blank = all pairs)",
}


def label(key: str) -> str:
    """Return the human-readable label for *key*, falling back to the key itself."""
    return LABELS.get(key, key)


def hint(key: str) -> str:
    """Return the tooltip hint text for *key*, or an empty string if none exists."""
    return HINTS.get(key, "")


def tip(widget: tk.Widget, key: str) -> None:
    """Attach a hint-dictionary tooltip to *widget* using the text from hint(key).

    Does nothing when no hint is registered for the key.
    """
    text = hint(key)
    if not text:
        return
    _create_tooltip(widget, text)


# ═══════════════════════════════════════════════════════════════════════════════
# UI helper functions
# ═══════════════════════════════════════════════════════════════════════════════

PAD = 12   # standard horizontal padding used by layout helpers


def section_sep(parent: tk.Widget, row: int, text: str) -> None:
    """Draw a filled blue-tinted strip with a left accent bar as a section header.

    Intended for use inside a ``tk.Frame`` using grid layout.
    The widget spans three columns (columnspan=3).
    """
    outer = tk.Frame(parent, bg="#edf2f8")
    outer.grid(row=row, column=0, columnspan=3, sticky="ew", padx=0, pady=(14, 2))
    tk.Frame(outer, bg="#2274A5", width=3).pack(side="left", fill="y", padx=(0, 9))
    tk.Label(
        outer, text=text.upper(), bg="#edf2f8", fg="#2274A5",
        font=("Helvetica Neue", 9, "bold"), anchor="w",
    ).pack(side="left", pady=5)


def _create_tooltip(widget: tk.Widget, text: str) -> None:
    """Attach a yellow hover tooltip showing *text* to *widget*.

    The tooltip appears 12px right and 4px below the cursor on ``<Enter>``
    and is destroyed on ``<Leave>``.
    """
    tt = None

    def _show(e):
        nonlocal tt
        tt = tk.Toplevel(widget)
        tt.wm_overrideredirect(True)
        tt.wm_geometry(f"+{e.x_root + 12}+{e.y_root + 4}")
        ttk.Label(
            tt, text=text, background="#fffbe6", relief="solid",
            borderwidth=1, font=("Helvetica Neue", 11), wraplength=320,
        ).pack(padx=4, pady=2)

    def _hide(e):
        nonlocal tt
        if tt:
            tt.destroy()
            tt = None

    widget.bind("<Enter>", _show)
    widget.bind("<Leave>", _hide)


def add_placeholder(entry: tk.Widget, var: tk.StringVar, text: str) -> None:
    """Show a grey hint inside *entry* when it is empty and unfocused.

    The placeholder is purely visual — it is never inserted into *var*.  This
    prevents hint text from leaking into plot labels when the user does not
    explicitly type a value.

    Rules
    -----
    - On creation: show placeholder when var is empty.
    - On ``<FocusIn>``: immediately clear the placeholder.
    - On ``<FocusOut>``: restore the placeholder if var is still empty.
    - On programmatic var reset (e.g. chart-type switch): restores placeholder
      because ``_reset_vars_to_defaults`` sets var to ``""``.
    """
    PLACEHOLDER_COLOR = "#aaaaaa"
    DEFAULT_COLOR     = "#000000"
    is_combo = isinstance(entry, (ttk.Combobox, PCombobox))
    _showing = [False]

    def _show_ph():
        try:
            entry.config(foreground=PLACEHOLDER_COLOR)
            if not is_combo:
                entry.delete(0, "end")
                entry.insert(0, text)
            else:
                entry.set(text)
            _showing[0] = True
        except Exception:
            pass

    def _hide_ph(clear_visual=True):
        if not _showing[0]:
            return
        entry.config(foreground=DEFAULT_COLOR)
        if clear_visual:
            if not is_combo:
                entry.delete(0, "end")
            else:
                entry.set("")
        _showing[0] = False

    def _on_focus_in(e):
        if _showing[0]:
            _hide_ph()

    def _on_focus_out(e):
        if not var.get().strip():
            _show_ph()
        else:
            entry.config(foreground=DEFAULT_COLOR)
            _showing[0] = False

    def _on_key(e):
        if _showing[0]:
            _hide_ph()

    def _on_var_change(*_):
        val = var.get()
        try:
            focused = str(entry.focus_get()) == str(entry)
        except Exception:
            focused = False
        if val and val != text:
            entry.config(foreground=DEFAULT_COLOR)
            _showing[0] = False
        elif not val and not focused:
            _show_ph()

    entry.bind("<FocusIn>",  _on_focus_in)
    entry.bind("<FocusOut>", _on_focus_out)
    entry.bind("<Key>",      _on_key, add=True)
    var.trace_add("write", _on_var_change)
    if not var.get():
        _show_ph()


def _bind_scroll_recursive(
    widget: tk.Widget,
    handler,
    button4_handler=None,
    button5_handler=None,
) -> None:
    """Bind mousewheel scroll to *widget* and every descendant in its tree.

    This is the safe alternative to ``dlg.bind_all()`` inside popup windows:
    ``bind_all`` on a ``Toplevel`` intercepts events from the parent window on
    macOS, causing scroll conflicts.  Binding only to the popup's own subtree
    limits the handler's scope.

    Also registers Linux ``<Button-4>`` / ``<Button-5>`` events when
    *button4_handler* is provided.
    """
    try:
        widget.bind("<MouseWheel>", handler, add=True)
        if button4_handler:
            widget.bind("<Button-4>", button4_handler, add=True)
            widget.bind("<Button-5>", button5_handler or button4_handler, add=True)
        for child in widget.winfo_children():
            _bind_scroll_recursive(child, handler, button4_handler, button5_handler)
    except Exception:
        pass


def _sys_bg(parent: tk.Widget) -> str:
    """Return the system background colour string for *parent*'s theme.

    Falls back to the _DS.BG token when the theme colour cannot be determined.
    Used by widgets that need to blend with the window background without
    knowing which ttk theme is active.
    """
    try:
        return ttk.Style().lookup("TFrame", "background") or _DS.BG
    except Exception:
        return _DS.BG


# ═══════════════════════════════════════════════════════════════════════════════
# PButton
# ═══════════════════════════════════════════════════════════════════════════════

class PButton(tk.Frame):
    """Design-system push button with three visual styles and hover/press states.

    Styles
    ------
    ``"primary"``   — filled blue background, white text (main action)
    ``"secondary"`` — outlined blue border, blue text (secondary action)
    ``"ghost"``     — light grey border, dark text (tertiary / toolbar action)

    Usage
    -----
    >>> btn = PButton(parent, text="Generate Plot", style="primary",
    ...               command=self._run)
    >>> btn.pack(side="right", padx=6)

    The widget exposes a ``config(**kw)`` method that forwards ``state``
    (``"normal"`` / ``"disabled"``) and ``text`` to the inner label.
    The ``_lock_exempt`` attribute, when ``True``, prevents the form-locking
    mechanism from disabling this button.
    """

    _is_pwidget  = True
    _lock_exempt = False

    def __init__(
        self,
        parent,
        text: str = "",
        command=None,
        style: str = "primary",
        state: str = "normal",
        width: int = None,
        **kw,
    ):
        # Strip kwargs that tk.Frame doesn't accept
        lock_exempt = kw.pop("lock_exempt", False)
        super().__init__(parent, cursor="hand2", **kw)
        self._lock_exempt = lock_exempt
        self._command  = command
        self._style    = style
        self._state    = state
        self._disabled = state == "disabled"

        self._label = tk.Label(
            self,
            text=text,
            font=("Helvetica Neue", 12, "bold"),
            cursor="hand2",
            padx=14,
            pady=5,
        )
        if width:
            self._label.config(width=width)
        self._label.pack(fill="both", expand=True)

        self._apply_normal() if not self._disabled else self._apply_disabled()
        self._bind_events()

    # ── visual state helpers ─────────────────────────────────────────────────

    def _apply_disabled(self):
        bg = _DS.DIS_BG; fg = _DS.DIS_FG; bdr = _DS.DIS_BORDER
        self.config(bg=bdr, bd=1, relief="flat")
        self._label.config(bg=bg, fg=fg)

    def _apply_normal(self):
        s = self._style
        if s == "primary":
            bg = _DS.PRIMARY;    fg = "white";    bdr = _DS.PRIMARY
        elif s == "secondary":
            bg = "white";        fg = _DS.PRIMARY; bdr = _DS.PRIMARY
        else:  # ghost
            bg = "white";        fg = _DS.TEXT;    bdr = _DS.GHOST_BDR
        self.config(bg=bdr, bd=1, relief="flat")
        self._label.config(bg=bg, fg=fg)

    def _bind_events(self):
        for w in (self, self._label):
            w.bind("<Enter>",           self._on_enter)
            w.bind("<Leave>",           self._on_leave)
            w.bind("<ButtonPress-1>",   self._on_press)
            w.bind("<ButtonRelease-1>", self._on_release)

    def _on_enter(self, e=None):
        if self._disabled: return
        s = self._style
        if s == "primary":
            self._label.config(bg=_DS.PRIMARY_HV)
        elif s == "secondary":
            self._label.config(bg="#e8f0f9")
        else:
            self._label.config(bg=_DS.GHOST_HV)

    def _on_leave(self, e=None):
        if self._disabled: return
        self._apply_normal()

    def _on_press(self, e=None):
        if self._disabled: return
        if self._style == "primary":
            self._label.config(bg=_DS.PRIMARY_PR)

    def _on_release(self, e=None):
        if self._disabled: return
        self._on_enter()
        if self._command:
            self._command()

    # ── public config API ────────────────────────────────────────────────────

    def config(self, **kw):
        """Update button state, text, or command.  Supports ``state`` and ``text``."""
        state   = kw.pop("state",   None)
        text    = kw.pop("text",    None)
        command = kw.pop("command", None)
        relief  = kw.pop("relief",  None)
        if state is not None:
            self._disabled = state == "disabled"
            self._state    = state
            self._apply_disabled() if self._disabled else self._apply_normal()
        if text is not None:
            self._label.config(text=text)
        if command is not None:
            self._command = command
        if relief is not None:
            tk.Frame.config(self, relief=relief)
        if kw:
            try:
                tk.Frame.config(self, **kw)
            except Exception:
                pass

    def cget(self, key: str):
        if key == "text":
            return self._label.cget("text")
        if key == "state":
            return "disabled" if self._disabled else "normal"
        try:
            return tk.Frame.cget(self, key)
        except Exception:
            return None


# ═══════════════════════════════════════════════════════════════════════════════
# PCheckbox
# ═══════════════════════════════════════════════════════════════════════════════

class PCheckbox(tk.Frame):
    """Checkmark toggle drawn on a Canvas for crisp rendering at any DPI.

    The checkbox renders a rounded-corner box with a blue fill + white
    check when checked, and an empty grey box when unchecked.

    Usage
    -----
    >>> var = tk.BooleanVar()
    >>> cb  = PCheckbox(parent, variable=var, text="Show data points")
    >>> cb.grid(row=r, column=0, sticky="w")
    """

    _is_pwidget = True

    _BOX  = 16   # canvas size
    _R    = 3    # corner radius

    def __init__(self, parent, variable=None, text="", **kw):
        bg = kw.pop("bg", _DS.BG)
        super().__init__(parent, bg=bg, cursor="hand2", **kw)
        self._var      = variable or tk.BooleanVar()
        self._disabled = False
        self._bg       = bg

        self._canvas = tk.Canvas(
            self, width=self._BOX, height=self._BOX,
            bg=bg, highlightthickness=0, cursor="hand2",
        )
        self._canvas.pack(side="left", padx=(0, 6))
        self._lbl = tk.Label(
            self, text=text, bg=bg, fg=_DS.TEXT,
            font=_DS.FONT, cursor="hand2",
        )
        self._lbl.pack(side="left")

        self._draw()
        self._var.trace_add("write", lambda *_: self._draw())
        for w in (self, self._canvas, self._lbl):
            w.bind("<Button-1>", self._toggle)
            w.bind("<Enter>",    self._on_enter)
            w.bind("<Leave>",    self._on_leave)

    def _draw(self, hover: bool = False) -> None:
        c   = self._canvas
        b   = self._BOX; r = self._R
        c.delete("all")
        checked = bool(self._var.get())
        fill    = _DS.PRIMARY if checked else ("white" if not hover else "#f0f0f0")
        border  = _DS.PRIMARY if checked else (_DS.PRIMARY if hover else "#aaaaaa")
        c.create_arc(0, 0, r*2, r*2, start=90,  extent=90,  style="arc", outline=border, width=1.5)
        c.create_arc(b-r*2, 0, b, r*2, start=0, extent=90,  style="arc", outline=border, width=1.5)
        c.create_arc(0, b-r*2, r*2, b, start=180, extent=90, style="arc", outline=border, width=1.5)
        c.create_arc(b-r*2, b-r*2, b, b, start=270, extent=90, style="arc", outline=border, width=1.5)
        c.create_rectangle(r, 0, b-r, b, fill=fill, outline="")
        c.create_rectangle(0, r, b, b-r, fill=fill, outline="")
        c.create_line(0, r, 0, b-r,     fill=border, width=1.5)
        c.create_line(b, r, b, b-r,     fill=border, width=1.5)
        c.create_line(r, 0, b-r, 0,     fill=border, width=1.5)
        c.create_line(r, b, b-r, b,     fill=border, width=1.5)
        if checked:
            c.create_line(3, 8, 6, 12, 13, 4, fill="white", width=2, capstyle="round", joinstyle="round")

    def _toggle(self, e=None):
        if not self._disabled:
            self._var.set(not self._var.get())

    def _on_enter(self, e=None):
        if not self._disabled:
            self._draw(hover=True)

    def _on_leave(self, e=None):
        self._draw(hover=False)

    def config(self, **kw):
        state = kw.pop("state", None)
        if state is not None:
            self._disabled = state == "disabled"
            fg = _DS.DIS_FG if self._disabled else _DS.TEXT
            self._lbl.config(fg=fg)
        if "text" in kw:
            self._lbl.config(text=kw.pop("text"))
        if kw:
            try:
                tk.Frame.config(self, **kw)
            except Exception:
                pass

    def cget(self, key: str):
        if key in ("state",):
            return "disabled" if self._disabled else "normal"
        return tk.Frame.cget(self, key)


# ═══════════════════════════════════════════════════════════════════════════════
# PRadioGroup
# ═══════════════════════════════════════════════════════════════════════════════

class PRadioGroup(tk.Frame):
    """Horizontal row of labelled radio buttons sharing a single StringVar.

    Each option is rendered as a small canvas dot + label.  The selected
    option's dot is filled blue; unselected dots are hollow.

    Usage
    -----
    >>> var = tk.StringVar(value="sem")
    >>> rg  = PRadioGroup(parent, variable=var,
    ...                   options=["sem", "sd", "ci95"])
    >>> rg.grid(row=r, column=0, sticky="w")
    """

    _is_pwidget = True
    _DOT = 14

    def __init__(self, parent, variable=None, options=None, **kw):
        bg = kw.pop("bg", _DS.BG)
        super().__init__(parent, bg=bg, **kw)
        self._var      = variable or tk.StringVar()
        self._options  = options or []
        self._disabled = False
        self._bg       = bg
        self._widgets: list[tuple] = []   # (canvas, label) per option

        for idx, opt in enumerate(self._options):
            c = tk.Canvas(
                self, width=self._DOT, height=self._DOT,
                bg=bg, highlightthickness=0, cursor="hand2",
            )
            c.grid(row=0, column=idx * 2, padx=(0 if idx == 0 else 8, 2))
            lbl = tk.Label(
                self, text=str(opt), bg=bg, fg=_DS.TEXT,
                font=_DS.FONT, cursor="hand2",
            )
            lbl.grid(row=0, column=idx * 2 + 1, padx=(0, 4))
            self._widgets.append((c, lbl))
            for w in (c, lbl):
                w.bind("<Button-1>", lambda e, o=opt: self._select(o))
                w.bind("<Enter>",    lambda e, i=idx: self._on_enter(i))
                w.bind("<Leave>",    lambda e, i=idx: self._on_leave(i))

        self._redraw_all()
        self._var.trace_add("write", lambda *_: self._redraw_all())

    def _draw_one(self, idx: int, canvas: tk.Canvas, hover: bool = False) -> None:
        d = self._DOT; r = d - 2
        canvas.delete("all")
        selected = (self._var.get() == self._options[idx])
        border   = _DS.PRIMARY if (selected or hover) else "#aaaaaa"
        canvas.create_oval(0, 0, d, d, outline=border, width=1.5)
        if selected:
            canvas.create_oval(3, 3, d-3, d-3, fill=_DS.PRIMARY, outline="")

    def _redraw_all(self):
        for i, (c, _) in enumerate(self._widgets):
            self._draw_one(i, c)

    def _select(self, option):
        if not self._disabled:
            self._var.set(option)

    def _on_enter(self, idx: int):
        if not self._disabled:
            self._draw_one(idx, self._widgets[idx][0], hover=True)

    def _on_leave(self, idx: int):
        self._draw_one(idx, self._widgets[idx][0], hover=False)

    def config(self, **kw):
        state = kw.pop("state", None)
        if state is not None:
            self._disabled = state == "disabled"
            fg = _DS.DIS_FG if self._disabled else _DS.TEXT
            for _, lbl in self._widgets:
                lbl.config(fg=fg)
        if kw:
            try:
                tk.Frame.config(self, **kw)
            except Exception:
                pass

    def cget(self, key: str):
        return "disabled" if self._disabled else "normal" if key == "state" else None


# ═══════════════════════════════════════════════════════════════════════════════
# PEntry
# ═══════════════════════════════════════════════════════════════════════════════

class PEntry(tk.Frame):
    """Flat-border text entry with a 1px coloured focus ring.

    The 1px coloured border is achieved by making the outer Frame's
    background show through a 1px gap around the inner ``tk.Entry``.
    On focus the frame bg switches from ``ENTRY_BDR`` (grey) to
    ``ENTRY_FOC`` (blue).

    Exposes the standard ``tk.Entry`` API (``get``, ``insert``, ``delete``,
    ``bind``) plus a ``config(state=…)`` override that applies both the
    disabled entry style *and* the disabled frame border colour.
    """

    _is_pwidget = True

    def __init__(
        self,
        parent,
        textvariable=None,
        width: int = None,
        font=None,
        state: str = "normal",
        **kw,
    ):
        super().__init__(parent, bg=_DS.ENTRY_BDR, padx=0, pady=0, **kw)
        self._is_pwidget = True
        self._disabled   = state == "disabled"

        entry_kw = dict(
            textvariable=textvariable,
            relief="flat", bg=_DS.ENTRY_BG, fg=_DS.TEXT,
            font=font or _DS.FONT,
            insertbackground=_DS.PRIMARY,
            highlightthickness=0, bd=0,
            disabledbackground=_DS.DIS_BG,
            disabledforeground=_DS.DIS_FG,
        )
        if width:
            entry_kw["width"] = width
        if state == "disabled":
            entry_kw["state"] = "disabled"

        self._entry = tk.Entry(self, **entry_kw)
        self._entry.pack(fill="both", expand=True, padx=1, pady=1)
        self._entry.bind("<FocusIn>",  self._on_focus)
        self._entry.bind("<FocusOut>", self._on_blur)

    def _on_focus(self, e=None):
        if not self._disabled:
            tk.Frame.config(self, bg=_DS.ENTRY_FOC)

    def _on_blur(self, e=None):
        tk.Frame.config(self, bg=_DS.ENTRY_BDR)

    def config(self, **kw):
        state = kw.pop("state", None)
        fg    = kw.pop("foreground", kw.pop("fg", None))
        if state is not None:
            self._disabled = state == "disabled"
            if self._disabled:
                self._entry.config(state="disabled", bg=_DS.DIS_BG, fg=_DS.DIS_FG)
                tk.Frame.config(self, bg=_DS.DIS_BORDER)
            else:
                self._entry.config(state="normal", bg=_DS.ENTRY_BG, fg=_DS.TEXT)
                tk.Frame.config(self, bg=_DS.ENTRY_BDR)
        if fg is not None:
            self._entry.config(fg=fg)
        if kw:
            try:
                self._entry.config(**kw)
            except Exception:
                pass

    def cget(self, key: str):
        if key in ("foreground", "fg"):
            return self._entry.cget("foreground")
        try:
            return self._entry.cget(key)
        except Exception:
            return tk.Frame.cget(self, key)

    def state(self, statespec):
        """ttk-compatible state setter.  Accepts ``["disabled"]`` / ``["!disabled"]``."""
        if not statespec:
            return
        s = statespec[0]
        self.config(state="disabled" if s == "disabled" else "normal")

    # Delegate text manipulation to inner entry
    def get(self):              return self._entry.get()
    def insert(self, *a):       return self._entry.insert(*a)
    def delete(self, *a):       return self._entry.delete(*a)
    def bind(self, *a, **kw):   return self._entry.bind(*a, **kw)

    def drop_target_register(self, *a):
        try:
            tk.Frame.drop_target_register(self, *a)
        except Exception:
            pass

    def dnd_bind(self, *a, **kw):
        try:
            tk.Frame.dnd_bind(self, *a, **kw)
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════════════════
# PCombobox
# ═══════════════════════════════════════════════════════════════════════════════

class PCombobox(tk.Frame):
    """Styled combobox that wraps ``ttk.Combobox`` with a focus-ring border.

    The outer ``tk.Frame`` acts as the border; its background switches between
    ``ENTRY_BDR`` (unfocused) and ``ENTRY_FOC`` (focused), matching the
    appearance of ``PEntry``.

    Exposes ``get()``, ``set(value)``, ``config(**kw)``, ``state(statespec)``,
    and ``bind()`` to match the ``ttk.Combobox`` API.
    """

    _is_pwidget = True

    def __init__(
        self,
        parent,
        textvariable=None,
        values=None,
        width: int = 20,
        state: str = "readonly",
        **kw,
    ):
        super().__init__(parent, bg=_DS.ENTRY_BDR, padx=1, pady=1, **kw)
        self._disabled = state == "disabled"

        self._combo = ttk.Combobox(
            self,
            textvariable=textvariable,
            values=values or [],
            width=width,
            state=state,
            font=_DS.FONT,
        )
        self._combo.pack(fill="both", expand=True)
        self._combo.bind("<FocusIn>",           self._on_focus)
        self._combo.bind("<FocusOut>",          self._on_blur)
        self._combo.bind("<<ComboboxSelected>>", self._on_selected)

    def _on_focus(self, e=None):
        if not self._disabled:
            tk.Frame.config(self, bg=_DS.ENTRY_FOC)

    def _on_blur(self, e=None):
        tk.Frame.config(self, bg=_DS.ENTRY_BDR)

    def _on_selected(self, e=None):
        self.after(10, self._on_blur)

    def config(self, **kw):
        state  = kw.pop("state",  None)
        values = kw.pop("values", None)
        font   = kw.pop("font",   None)
        if state is not None:
            self._disabled = state == "disabled"
            self._combo.config(state=state)
            if self._disabled:
                tk.Frame.config(self, bg=_DS.DIS_BORDER)
            else:
                tk.Frame.config(self, bg=_DS.ENTRY_BDR)
        if values is not None:
            self._combo.config(values=values)
        if font is not None:
            self._combo.config(font=font)
        if kw:
            try:
                self._combo.config(**kw)
            except Exception:
                pass

    def cget(self, key: str):
        try:
            return self._combo.cget(key)
        except Exception:
            return tk.Frame.cget(self, key)

    def state(self, statespec):
        """ttk-compatible state setter."""
        if not statespec:
            return
        s = statespec[0]
        self.config(state="disabled" if s == "disabled" else "readonly")

    def get(self):
        return self._combo.get()

    def set(self, val: str):
        self._combo.set(val)

    def bind(self, sequence=None, func=None, add=None):
        return self._combo.bind(sequence, func, add)


# ═══════════════════════════════════════════════════════════════════════════════
# Utility functions
# ═══════════════════════════════════════════════════════════════════════════════

def _is_num(v) -> bool:
    """Return True if *v* can be safely cast to ``float``."""
    try:
        float(v)
        return True
    except (ValueError, TypeError):
        return False


def _non_numeric_values(series, max_shown: int = 5) -> list:
    """Return a list of non-numeric string representations from *series*.

    Drops ``NaN`` / ``None`` values before filtering.  Used by validation
    helpers to produce concise error messages like
    ``"contains non-numeric values: ['abc', 'n/a']"``.

    Parameters
    ----------
    series    : pandas Series (or any iterable)
    max_shown : cap the number of bad values returned
    """
    return [str(v) for v in series.dropna() if not _is_num(v)][:max_shown]


def _scipy_summary(fn, max_chars: int = 280) -> str:
    """Return the opening summary sentence(s) from a scipy function's docstring.

    Walks the docstring paragraphs in order, stopping before the first
    section header (``Parameters``, ``Returns``, etc.) or when the accumulated
    length exceeds *max_chars*.  Returns an empty string when no docstring is
    available.
    """
    import inspect
    doc   = inspect.getdoc(fn) or ""
    paras = [p.strip() for p in doc.split("\n\n")]
    result: list[str] = []
    for p in paras:
        if any(p.startswith(h) for h in
               ("Parameters", "Returns", "See Also", "Notes",
                "Warns", "References", "Examples", "Attributes")):
            break
        clean = " ".join(p.split())
        if clean:
            result.append(clean)
        if sum(len(r) for r in result) > max_chars:
            break
    return " ".join(result)
