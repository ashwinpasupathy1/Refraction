"""
plotter_app_wiki.py
===================
Statistical reference wiki popup for Refraction.
Two-pane Toplevel: TOC sidebar + scrollable content.
LaTeX rendered via matplotlib mathtext engine.
"""
import tkinter as tk
from tkinter import ttk


# ──────────────────────────────────────────────────────────────────
# PIL / ImageTk availability check
# ──────────────────────────────────────────────────────────────────
try:
    from PIL import Image, ImageTk
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False


def _render_latex_image(expression: str, fontsize: int = 13):
    """
    Render a matplotlib mathtext expression to a PIL Image.
    Returns (PIL.Image, PhotoImage-compatible) or None if rendering fails.
    """
    # LaTeX rendering removed (matplotlib dependency dropped).
    # Wiki displays plain text instead.
    return None


# ──────────────────────────────────────────────────────────────────
# Public entry point
# ──────────────────────────────────────────────────────────────────

def open_wiki_popup(parent_window, track_popup_fn=None, bind_scroll_fn=None):
    """
    Open the statistical reference wiki popup.

    Parameters
    ----------
    parent_window   : tk.Tk or tk.Toplevel — the parent window.
    track_popup_fn  : optional callable(window) — called with the Toplevel
                      so the caller can track open popups.
    bind_scroll_fn  : optional callable(frame) — called with the scrollable
                      inner content frame for extra scroll bindings.
    """
    from refraction.app.wiki_content import WIKI_SECTIONS  # lazy import

    # ── window setup ────────────────────────────────────────────────
    win = tk.Toplevel(parent_window)
    win.title("Refraction — Statistical Reference")
    win.geometry("920x660")
    win.minsize(640, 400)
    win.configure(bg="white")

    if track_popup_fn is not None:
        track_popup_fn(win)

    # ── outer paned window ──────────────────────────────────────────
    paned = tk.PanedWindow(win, orient=tk.HORIZONTAL, sashwidth=4,
                           bg="#e0e0e0", relief=tk.FLAT)
    paned.pack(fill=tk.BOTH, expand=True)

    # ─────────────────────────────────────────────────────────────────
    # LEFT PANE — TOC + search
    # ─────────────────────────────────────────────────────────────────
    left_frame = tk.Frame(paned, bg="white", width=210)
    left_frame.pack_propagate(False)
    paned.add(left_frame, minsize=140)

    # Search bar
    search_var = tk.StringVar()
    search_entry = tk.Entry(
        left_frame,
        textvariable=search_var,
        font=("Arial", 10),
        relief=tk.FLAT,
        bg="#f4f4f4",
        fg="#555555",
        insertbackground="#333333",
    )
    search_entry.pack(fill=tk.X, padx=6, pady=(6, 2))
    search_entry.insert(0, "Search…")
    search_entry.config(fg="#aaaaaa")

    def _on_search_focus_in(e):
        if search_entry.get() == "Search…":
            search_entry.delete(0, tk.END)
            search_entry.config(fg="#222222")

    def _on_search_focus_out(e):
        if search_entry.get() == "":
            search_entry.insert(0, "Search…")
            search_entry.config(fg="#aaaaaa")

    search_entry.bind("<FocusIn>", _on_search_focus_in)
    search_entry.bind("<FocusOut>", _on_search_focus_out)

    # TOC listbox
    toc_frame = tk.Frame(left_frame, bg="white")
    toc_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

    toc_scrollbar = tk.Scrollbar(toc_frame, orient=tk.VERTICAL)
    toc_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    toc_listbox = tk.Listbox(
        toc_frame,
        yscrollcommand=toc_scrollbar.set,
        font=("Arial", 10),
        selectbackground="#2274A5",
        selectforeground="white",
        activestyle="none",
        relief=tk.FLAT,
        bd=0,
        highlightthickness=0,
        bg="white",
        fg="#222222",
    )
    toc_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    toc_scrollbar.config(command=toc_listbox.yview)

    # Build TOC entries (index → section index)
    _toc_indices: list[int] = []  # maps listbox row → WIKI_SECTIONS index

    def _populate_toc(filter_text: str = ""):
        toc_listbox.delete(0, tk.END)
        _toc_indices.clear()
        query = filter_text.lower().strip()
        for idx, section in enumerate(WIKI_SECTIONS):
            title = section.get("title", "")
            tags = " ".join(section.get("tags", []))
            if query and query not in title.lower() and query not in tags.lower():
                continue
            # Wrap long titles in the listbox
            toc_listbox.insert(tk.END, f"  {title}")
            _toc_indices.append(idx)

    _populate_toc()

    def _on_search_changed(*_):
        text = search_var.get()
        if text == "Search…":
            text = ""
        _populate_toc(text)

    search_var.trace_add("write", _on_search_changed)

    # ─────────────────────────────────────────────────────────────────
    # RIGHT PANE — scrollable content
    # ─────────────────────────────────────────────────────────────────
    right_outer = tk.Frame(paned, bg="white")
    paned.add(right_outer, minsize=400)

    content_canvas = tk.Canvas(right_outer, bg="white",
                                highlightthickness=0, bd=0)
    content_scrollbar = tk.Scrollbar(right_outer, orient=tk.VERTICAL,
                                     command=content_canvas.yview)
    content_canvas.configure(yscrollcommand=content_scrollbar.set)

    content_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    content_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    content_frame = tk.Frame(content_canvas, bg="white")
    content_window = content_canvas.create_window(
        (0, 0), window=content_frame, anchor="nw"
    )

    def _on_canvas_configure(event):
        content_canvas.itemconfig(content_window, width=event.width)

    def _on_frame_configure(event):
        content_canvas.configure(scrollregion=content_canvas.bbox("all"))

    content_canvas.bind("<Configure>", _on_canvas_configure)
    content_frame.bind("<Configure>", _on_frame_configure)

    # Mouse-wheel scrolling
    def _on_mousewheel(event):
        if event.num == 4:
            content_canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            content_canvas.yview_scroll(1, "units")
        else:
            content_canvas.yview_scroll(int(-event.delta / 120), "units")

    for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
        content_canvas.bind(seq, _on_mousewheel)
        content_frame.bind(seq, _on_mousewheel)

    if bind_scroll_fn is not None:
        bind_scroll_fn(content_frame)

    # ─────────────────────────────────────────────────────────────────
    # Section anchor widgets (for TOC navigation)
    # ─────────────────────────────────────────────────────────────────
    _section_anchors: list[tk.Widget] = []  # one anchor frame per section

    # ─────────────────────────────────────────────────────────────────
    # Render all sections into content_frame
    # ─────────────────────────────────────────────────────────────────

    def _make_section(parent: tk.Frame, section: dict):
        """Render one wiki section into parent."""
        # Section anchor frame
        anchor = tk.Frame(parent, bg="white")
        anchor.pack(fill=tk.X, padx=0, pady=0)

        # Section title
        title_lbl = tk.Label(
            anchor,
            text=section.get("title", ""),
            font=("Arial", 14, "bold"),
            fg="#1a1a2e",
            bg="white",
            anchor="w",
            justify=tk.LEFT,
            wraplength=600,
        )
        title_lbl.pack(fill=tk.X, padx=14, pady=(14, 2))

        # Tags
        tags = section.get("tags", [])
        if tags:
            tags_lbl = tk.Label(
                anchor,
                text="  ".join(f"[{t}]" for t in tags),
                font=("Arial", 9),
                fg="#888888",
                bg="white",
                anchor="w",
                justify=tk.LEFT,
            )
            tags_lbl.pack(fill=tk.X, padx=14, pady=(0, 6))

        # Subsections
        for sub in section.get("subsections", []):
            _make_subsection(anchor, sub)

        # Horizontal separator
        sep = ttk.Separator(parent, orient=tk.HORIZONTAL)
        sep.pack(fill=tk.X, padx=10, pady=(8, 4))

        return anchor

    def _make_subsection(parent: tk.Frame, sub: dict):
        """Render one subsection into parent."""
        heading = sub.get("heading", "")
        sub_type = sub.get("type", "text")

        if heading:
            h_lbl = tk.Label(
                parent,
                text=heading,
                font=("Arial", 11, "bold"),
                fg="#2274A5",
                bg="white",
                anchor="w",
                justify=tk.LEFT,
            )
            h_lbl.pack(fill=tk.X, padx=14, pady=(8, 2))

        if sub_type == "text":
            _render_text_block(parent, sub.get("body", ""))

        elif sub_type == "latex_block":
            _render_latex_block(parent, sub)

        elif sub_type == "text_with_latex":
            body_before = sub.get("body", "")
            if body_before:
                _render_text_block(parent, body_before)
            _render_latex_block(parent, sub)
            body_after = sub.get("body_after", "")
            if body_after:
                _render_text_block(parent, body_after)

        elif sub_type == "numbered_list":
            _render_numbered_list(parent, sub.get("items", []))

        elif sub_type == "references":
            _render_references(parent, sub.get("items", []))

    def _render_text_block(parent: tk.Frame, text: str):
        lbl = tk.Label(
            parent,
            text=text,
            font=("Arial", 10),
            fg="#333333",
            bg="white",
            anchor="w",
            justify=tk.LEFT,
            wraplength=640,
        )
        lbl.pack(fill=tk.X, padx=20, pady=(2, 4))

    def _render_latex_block(parent: tk.Frame, sub: dict):
        expressions = sub.get("expressions", [])
        source = sub.get("source", "")

        for expr, description in expressions:
            _render_formula(parent, expr, description)

        if source:
            src_lbl = tk.Label(
                parent,
                text=f"  Source: {source}",
                font=("Arial", 9, "italic"),
                fg="#999999",
                bg="white",
                anchor="w",
                justify=tk.LEFT,
            )
            src_lbl.pack(fill=tk.X, padx=20, pady=(0, 4))

    def _render_formula(parent: tk.Frame, expression: str, description: str):
        """Render one formula + its description."""
        # Try PIL rendering first
        img = _render_latex_image(expression)
        if img is not None:
            try:
                photo = ImageTk.PhotoImage(img)
                formula_lbl = tk.Label(parent, image=photo, bg="white")
                formula_lbl._photo = photo  # prevent garbage collection
                formula_lbl.pack(anchor="w", padx=28, pady=(4, 1))
            except Exception:
                img = None  # fall through to text fallback

        if img is None:
            # Fallback: show raw expression as monospace text
            fallback_lbl = tk.Label(
                parent,
                text=expression,
                font=("Courier", 10),
                fg="#444444",
                bg="#f8f8f8",
                anchor="w",
                justify=tk.LEFT,
                relief=tk.FLAT,
                padx=6,
                pady=3,
            )
            fallback_lbl.pack(anchor="w", padx=28, pady=(4, 1), fill=tk.X)

        # Description below the formula
        if description:
            desc_lbl = tk.Label(
                parent,
                text=description,
                font=("Arial", 9),
                fg="#666666",
                bg="white",
                anchor="w",
                justify=tk.LEFT,
                wraplength=580,
            )
            desc_lbl.pack(anchor="w", padx=36, pady=(0, 4))

    def _render_numbered_list(parent: tk.Frame, items: list):
        for i, item in enumerate(items, 1):
            if isinstance(item, tuple) and len(item) == 2:
                title_text, desc_text = item
            else:
                title_text = str(item)
                desc_text = ""

            row = tk.Frame(parent, bg="white")
            row.pack(fill=tk.X, padx=20, pady=1)

            num_lbl = tk.Label(
                row,
                text=f"{i}.",
                font=("Arial", 10, "bold"),
                fg="#2274A5",
                bg="white",
                width=3,
                anchor="ne",
            )
            num_lbl.pack(side=tk.LEFT, anchor="n", padx=(0, 4))

            text_frame = tk.Frame(row, bg="white")
            text_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

            if title_text:
                t_lbl = tk.Label(
                    text_frame,
                    text=title_text,
                    font=("Arial", 10, "bold"),
                    fg="#222222",
                    bg="white",
                    anchor="w",
                    justify=tk.LEFT,
                    wraplength=560,
                )
                t_lbl.pack(anchor="w")

            if desc_text:
                d_lbl = tk.Label(
                    text_frame,
                    text=desc_text,
                    font=("Arial", 10),
                    fg="#444444",
                    bg="white",
                    anchor="w",
                    justify=tk.LEFT,
                    wraplength=560,
                )
                d_lbl.pack(anchor="w")

    def _render_references(parent: tk.Frame, items: list):
        for ref in items:
            row = tk.Frame(parent, bg="white")
            row.pack(fill=tk.X, padx=20, pady=1)

            bullet = tk.Label(
                row,
                text="•",
                font=("Arial", 10),
                fg="#888888",
                bg="white",
                width=2,
                anchor="n",
            )
            bullet.pack(side=tk.LEFT, anchor="n")

            ref_lbl = tk.Label(
                row,
                text=ref,
                font=("Arial", 9),
                fg="#555555",
                bg="white",
                anchor="w",
                justify=tk.LEFT,
                wraplength=580,
            )
            ref_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True, anchor="w")

    # Build content
    for section in WIKI_SECTIONS:
        anchor_widget = _make_section(content_frame, section)
        _section_anchors.append(anchor_widget)

    # ─────────────────────────────────────────────────────────────────
    # TOC navigation — scroll content to selected section
    # ─────────────────────────────────────────────────────────────────
    def _on_toc_select(event):
        sel = toc_listbox.curselection()
        if not sel:
            return
        listbox_row = sel[0]
        if listbox_row >= len(_toc_indices):
            return
        section_idx = _toc_indices[listbox_row]
        if section_idx >= len(_section_anchors):
            return
        target = _section_anchors[section_idx]
        # Wait for layout to settle then scroll
        win.after(20, lambda: _scroll_to_widget(target))

    def _scroll_to_widget(widget: tk.Widget):
        try:
            content_frame.update_idletasks()
            widget_y = widget.winfo_y()
            total_h = content_frame.winfo_height()
            if total_h <= 0:
                return
            fraction = widget_y / total_h
            content_canvas.yview_moveto(max(0.0, fraction - 0.01))
        except Exception:
            pass

    toc_listbox.bind("<<ListboxSelect>>", _on_toc_select)

    # ─────────────────────────────────────────────────────────────────
    # Bottom close button
    # ─────────────────────────────────────────────────────────────────
    bottom_bar = tk.Frame(win, bg="#f0f0f0", height=36)
    bottom_bar.pack(fill=tk.X, side=tk.BOTTOM)
    bottom_bar.pack_propagate(False)

    close_btn = tk.Button(
        bottom_bar,
        text="Close",
        command=win.destroy,
        font=("Arial", 10),
        relief=tk.FLAT,
        bg="#2274A5",
        fg="white",
        activebackground="#1a5a8a",
        activeforeground="white",
        padx=16,
        pady=4,
        cursor="hand2",
    )
    close_btn.pack(side=tk.RIGHT, padx=10, pady=5)

    win.lift()
    win.focus_set()
    return win
