# Phase 1 — Tabs + Renderer Unification

**Status:** Ready to implement
**Branch:** cut a new branch from master
**Test target:** 608/608 (run `python3 run_all.py` — must pass before every commit)

---

## What this phase delivers

1. A tab bar at the top of the right pane — icon + title + × close + drag-to-reorder + + new tab
2. Each tab is an independent plot session with its own chart type, data, form state, and rendered figure
3. New tabs always default to bar chart
4. Tab label = chart title (live-updates as user types)
5. Tab icon = the same 16×16 chart icon used in the sidebar
6. Fast tab switching (~10–20ms) — no re-render; plots persist as live Tk widgets
7. `prism_canvas_renderer.py` deleted; bar/grouped-bar use `FigureCanvasTkAgg` like every other chart type
8. Bar recoloring preserved via `mpl_connect` pick events (Tier 1)

---

## Files to create

### `prism_tabs.py` (new, ~480 lines)

Three classes: `TabState`, `TabManager`, `TabBar`.

#### `TabState` dataclass

```python
from dataclasses import dataclass, field
from typing import Any

@dataclass
class TabState:
    tab_id:          str
    chart_type:      str        # registry key e.g. "bar", "scatter"
    chart_type_idx:  int        # index in _REGISTRY_SPECS / sidebar position
    label:           str        # display name; defaults to "Untitled", becomes chart title
    vars_snapshot:   dict       # saved copy of all form var values (str/bool)
    file_path:       str        # absolute path to excel file, or ""
    sheet_name:      str        # sheet name or ""
    validated:       bool       # whether spreadsheet passed validation
    plot_frame:      Any        # ttk.Frame — container for rendered widget; NEVER replaced
    fig:             Any = None # matplotlib Figure, kept for export
    render_job_id:   str = None # UUID hex; used for thread safety
```

`plot_frame` is the stable interface between the tab system and the renderer.
The tab system shows/hides it. The renderer puts whatever it wants inside it.
This field never changes between phases.

#### `TabManager` class

Responsibilities: create/close/reorder tabs, save/restore form state on switch,
sync sidebar highlight, suppress live preview during switch.

Public API:
```python
class TabManager:
    def __init__(self, app): ...

    def new_tab(self, chart_type: str = "bar") -> TabState:
        """Create a new tab, add it to the bar, switch to it."""

    def close_tab(self, tab_id: str) -> None:
        """Close tab, destroy its plot_frame, activate nearest neighbour."""

    def switch_to(self, tab_id: str) -> None:
        """Save outgoing state, swap frames, restore incoming state."""

    def reorder(self, from_idx: int, to_idx: int) -> None:
        """Move tab in list and redraw tab bar."""

    def get_tab(self, tab_id: str) -> TabState | None:
        """Return TabState by id, or None if not found."""

    def update_label(self, tab_id: str, label: str) -> None:
        """Update tab label and redraw that tab in the bar."""

    @property
    def active(self) -> TabState | None: ...

    @property
    def all_tabs(self) -> list[TabState]: ...
```

##### `switch_to` implementation detail (critical)

```python
def switch_to(self, tab_id: str) -> None:
    outgoing = self.active
    incoming = self.get_tab(tab_id)
    if incoming is None or incoming is outgoing:
        return

    # 1. Save outgoing form state
    if outgoing is not None:
        outgoing.vars_snapshot = {k: v.get() for k, v in self._app._vars.items()}
        outgoing.file_path  = self._app._vars["excel_path"].get()
        outgoing.sheet_name = self._app._vars["sheet"].get()
        outgoing.validated  = self._app._validated
        outgoing.plot_frame.place_forget()

    # 2. Suppress live preview during var restore (prevents spurious re-render)
    self._app._live_preview_enabled = False

    # 3. Restore incoming form state
    for k, v in self._app._vars.items():
        if k in incoming.vars_snapshot:
            v.set(incoming.vars_snapshot[k])

    # 4. Re-enable live preview and cancel any pending preview that fired during restore
    self._app._live_preview_enabled = True
    if getattr(self._app, "_preview_after_id", None):
        self._app.after_cancel(self._app._preview_after_id)
        self._app._preview_after_id = None

    # 5. Restore file/validation state
    self._app._file_selected = bool(incoming.file_path)
    self._app._validated     = incoming.validated

    # 6. Show incoming plot frame
    incoming.plot_frame.place(relx=0, rely=0, relwidth=1, relheight=1)

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
```

#### `TabBar` widget

A `tk.Canvas` horizontal strip. Visual only — fires callbacks, owns no state.

```python
class TabBar(tk.Canvas):
    def __init__(self, parent, on_select, on_close, on_new, on_reorder,
                 height=32, **kwargs): ...

    def set_tabs(self, tabs: list[TabState]) -> None:
        """Full redraw from tab list."""

    def set_active(self, tab_id: str) -> None:
        """Highlight the active tab without full redraw."""

    def update_label(self, tab_id: str, label: str) -> None:
        """Update one tab's label text."""
```

Visual spec:
- Height: 32px
- Active tab: white background, bottom border removed, slightly raised
- Inactive tab: `#f0f2f5` background
- Tab contents: [chart icon 14×14] [title text, truncated to 18 chars] [× button]
- `+` button: right-aligned or after last tab
- Drag-to-reorder: on `<B1-Motion>` compute target position, call `on_reorder`
- Icons: reuse the same drawing functions already used in the sidebar (they're closures
  inside `_build_sidebar` — extract them into a standalone `draw_chart_icon(canvas, x, y,
  key, size)` function that both the sidebar and tab bar can call)

---

## Files to modify

### `prism_barplot_app.py`

#### 1. Imports (top of file)
```python
from prism_tabs import TabState, TabManager, TabBar
import uuid
```

#### 2. `__init__` — add instance vars
```python
self._tab_manager: TabManager | None = None
self._preview_after_id: int | None = None   # already exists, confirm it's here
```

#### 3. `_build_right_pane` (currently line ~2387)

Insert `TabBar` as the first widget in `right_outer`, above the plot scrollable canvas.
Create `TabManager`. Create the initial tab (bar chart, idx 0).

```python
def _build_right_pane(self, paned):
    self._right_pane = right_outer = ttk.Frame(paned)
    paned.add(right_outer, minsize=300)

    # ── Tab bar ───────────────────────────────────────────────────────────
    self._tab_bar_widget = TabBar(
        right_outer,
        on_select=lambda tab_id: self._tab_manager.switch_to(tab_id),
        on_close=lambda tab_id: self._tab_manager.close_tab(tab_id),
        on_new=lambda: self._tab_manager.new_tab("bar"),
        on_reorder=lambda f, t: self._tab_manager.reorder(f, t),
    )
    self._tab_bar_widget.pack(fill="x", side="top")

    # ... rest of existing _build_right_pane code unchanged ...

    # ── Tab manager (created after plot canvas exists) ────────────────────
    self._tab_manager = TabManager(self, self._tab_bar_widget, self._plot_canvas)
    self._tab_manager.new_tab("bar")   # open with one bar chart tab
```

`_plot_canvas` is the scrollable canvas that already exists. `TabManager` uses it
as the parent for each tab's `plot_frame`.

#### 4. `_run` (currently line ~6428)

Tag the render job before spawning the thread:
```python
def _run(self):
    if self._running: return
    # ... existing validation checks ...
    kw = self._collect(excel)
    if kw is None: return

    # Tag this job to the active tab for thread safety
    tab = self._tab_manager.active if self._tab_manager else None
    job_id = uuid.uuid4().hex
    if tab is not None:
        tab.render_job_id = job_id

    # ... existing history push, _running = True, spinner ...
    threading.Thread(
        target=self._do_run,
        args=(kw, tab.tab_id if tab else None, job_id),
        daemon=True
    ).start()
```

#### 5. `_do_run` (currently line ~6764)

Accept and forward `tab_id` + `job_id`:
```python
def _do_run(self, kw, tab_id=None, job_id=None):
    # ... existing body unchanged until the after() call ...
    self.after(0, lambda: self._embed_plot(
        fig, groups, kw=_kw_snap, tab_id=tab_id, job_id=job_id))
    self.after(80, lambda: self._populate_results(_ep, _sh, _pt, _kw_snap))
```

#### 6. `_embed_plot` (currently line ~6866)

Route render to the correct tab's `plot_frame`; validate job is still live:
```python
def _embed_plot(self, fig, groups=None, kw=None, tab_id=None, job_id=None):
    # Validate tab is still alive and this job hasn't been superseded
    if self._tab_manager is not None:
        tab = self._tab_manager.get_tab(tab_id)
        if tab is None or tab.render_job_id != job_id:
            import matplotlib.pyplot as _plt
            _plt.close(fig)
            return
        target_frame = tab.plot_frame
        tab.fig = fig
    else:
        target_frame = self._plot_frame   # fallback if tabs not yet initialised

    # Replace self._plot_frame references in the existing body with target_frame
    # Also update self._fig = fig (keep for export compatibility)
    self._fig = fig
    # ... rest of existing body, with _plot_frame → target_frame ...
```

#### 7. `_on_chart_type_change` (rename from `_on_tab_change`)

Rename `_on_tab_change` → `_on_chart_type_change` everywhere it's defined and called.
This prevents confusion between chart-type switching and tab switching.

Critically: `_on_chart_type_change` must NOT reset form state when the chart type
change was triggered by a tab switch (the tab system already handles state restore).
Add a guard parameter:

```python
def _on_chart_type_change(self, from_tab_switch=False):
    idx = _current_idx[0]
    key = _tab_map.get(idx, "bar")
    self._plot_type.set(key)
    if key in self._all_tabs_map:
        self._build_tab_content(key)
    if not from_tab_switch:
        self.after(0, self._reset_chart_type_state)   # also rename _reset_tab_state
```

#### 8. `_sb_select_silent` — new helper

The sidebar select currently always triggers `_on_chart_type_change`. Add a silent
variant for use by `TabManager.switch_to`:
```python
def _sb_select_silent(self, idx):
    """Update sidebar highlight without triggering chart-type reset."""
    _sb_select(idx)       # repaints the visual highlight only
    _show_pane(idx)       # shows the correct form pane
    # does NOT call _on_chart_type_change
```

#### 9. Title var trace for tab label

After `_setup_live_preview` is called, add:
```python
self._vars["title"].trace_add("write", lambda *_: self._sync_active_tab_label())

def _sync_active_tab_label(self):
    if self._tab_manager is None: return
    tab = self._tab_manager.active
    if tab is None: return
    raw = self._vars["title"].get().strip()
    label = raw if raw else "Untitled"
    tab.label = label
    self._tab_manager.update_label(tab.tab_id, label)
```

### `prism_canvas_renderer.py` — DELETE

Remove the file entirely. Remove its import from `prism_barplot_app.py`.
Remove `_try_canvas_embed`, `_recolor_bar_dialog`, `_toggle_canvas_mode`,
and the `🎨` canvas mode button.

Remove `self._bar_renderer` and `self._canvas_mode` instance vars.

In `_embed_plot`, remove the canvas-mode branch entirely — always use `FigureCanvasTkAgg`.

### Add `mpl_connect` bar recoloring

After `FigureCanvasTkAgg` is created in `_embed_plot`, wire pick events for bar charts:

```python
if kw and self._plot_type.get() in ("bar", "grouped_bar"):
    for artist in ax.patches:
        artist.set_picker(True)
    def _on_pick(event):
        patch = event.artist
        from tkinter import colorchooser
        current = patch.get_facecolor()
        # convert RGBA to hex
        import matplotlib.colors as mcolors
        hex_color = mcolors.to_hex(current)
        result = colorchooser.askcolor(color=hex_color, title="Choose bar color")
        if result and result[1]:
            patch.set_facecolor(result[1])
            canvas.draw_idle()
    canvas.mpl_connect("pick_event", _on_pick)
```

Note: `ax` needs to be passed into `_embed_plot` or retrieved from `fig.axes[0]`.
Currently `_embed_plot` only receives `fig` — add `ax=None` parameter and pass it
from `_do_run`.

---

## Files to modify: tests

### `tests/test_modular.py` — add tab system tests

Add a new section at the bottom (follow existing pattern in that file):

```python
# ── Tab system ────────────────────────────────────────────────────────────────
section("TabState")

def test_tabstate_defaults():
    import tkinter as tk
    root = tk.Tk(); root.withdraw()
    frame = ttk.Frame(root)
    tab = TabState(
        tab_id="t1", chart_type="bar", chart_type_idx=0,
        label="Untitled", vars_snapshot={}, file_path="",
        sheet_name="", validated=False, plot_frame=frame,
    )
    assert tab.render_job_id is None
    assert tab.fig is None
    root.destroy()
run("TabState: defaults are correct", test_tabstate_defaults)

# ... add ~10 more tests for TabManager create/close/reorder logic ...
```

---

## Files to DELETE

- `prism_canvas_renderer.py`

---

## Execution order

1. Read `docs/PLAN.md` and this document fully before writing any code.
2. Create `prism_tabs.py` with `TabState`, `TabManager`, `TabBar`.
3. Modify `prism_barplot_app.py`:
   a. Remove canvas renderer import and all canvas-mode code
   b. Add `mpl_connect` bar recoloring
   c. Add `_sb_select_silent`
   d. Rename `_on_tab_change` → `_on_chart_type_change`
   e. Rename `_reset_tab_state` → `_reset_chart_type_state`
   f. Modify `_build_right_pane` to add tab bar and TabManager
   g. Modify `_run`, `_do_run`, `_embed_plot` for tab routing + thread safety
   h. Add title trace for tab label sync
4. Delete `prism_canvas_renderer.py`
5. Run `python3 run_all.py` — must be 608/608
6. Add tab tests to `tests/test_modular.py`
7. Run `python3 run_all.py` again — must be 608+ / 0 failures
8. Commit with message: `feat: implement plot tabs and unify rendering pipeline`

---

## Design decisions (do not revisit without good reason)

| Decision | Rationale |
|---|---|
| New tabs default to bar chart | User preference |
| `plot_frame` is stable and never replaced | Phase boundary: renderer swaps what's inside, not the container |
| Thread safety via `(tab_id, job_id)` | Prevents stale renders landing in wrong tab or closed tab |
| Live preview suppressed during `switch_to` | Prevents spurious re-renders when restoring ~694 form vars |
| `_on_tab_change` renamed to `_on_chart_type_change` | Naming collision with tab switching would cause bugs |
| Canvas renderer deleted, not disabled | It was a parallel implementation; no toggle needed |
| `mpl_connect` pick events replace recolor dialog | Consistent with all chart types; canvas renderer gone |
| Tab bar is a `tk.Canvas` widget (not `ttk.Notebook`) | Full visual control; `ttk.Notebook` doesn't support icons + custom close buttons |

---

## Constraints

- Do not touch `prism_functions.py`, `prism_registry.py`, `prism_validators.py`,
  `prism_results.py`, `prism_widgets.py`, or any file in `tests/` except `test_modular.py`.
- Do not change the export pipeline.
- Do not change how the results panel works.
- `run_all.py` must print 608 passed / 0 failed before the final commit.
