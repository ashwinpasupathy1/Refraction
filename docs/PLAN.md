# Claude Prism — Architecture Roadmap

**Agreed direction:** Move from a generate-then-display model to a live direct-manipulation
model where changes happen on the rendered chart itself. Target is Tier 3 interactivity
(drag to reposition elements, click-to-edit, recolor, annotation).

---

## Guiding principles

1. **Separate state from rendering.** The tab system owns identity and form state. It
   never knows how a chart is rendered. The renderer is swappable without touching tabs.
2. **One rendering system at a time.** The canvas renderer + matplotlib parallel path was
   a mistake. All phases use a single rendering path per chart type.
3. **Statistics and data logic are never touched by rendering changes.** `prism_functions.py`,
   `prism_validators.py`, `prism_registry.py` are insulated from all rendering work.
4. **608 tests pass at the end of every phase.** Never commit a regression.
5. **Journal-quality output is the baseline.** Visual style matching GraphPad Prism is
   desirable but secondary. Correct statistics and clean exports are non-negotiable.

---

## Phase 1 — Clean foundation (tabs + renderer unification)

**Goal:** Tabs working for all 29 chart types. Single rendering path.

### Deliverables
- `prism_tabs.py` — `TabState`, `TabManager`, `TabBar` widget
- Drop `prism_canvas_renderer.py` entirely
- Replace canvas renderer with `mpl_connect` pick events (Tier 1 bar recoloring)
- Tab bar at top of right pane: icon + title + × close + + new + drag-to-reorder
- New tabs default to bar chart
- Thread-safe render routing: `(tab_id, job_id)` passed through `_run` → `_do_run` → `_embed_plot`
- Live preview suppressed during tab switch (guard in `TabManager.switch_to`)
- 608/608 tests pass

### What does NOT change
- `prism_functions.py`, `prism_validators.py`, `prism_registry.py`, `prism_results.py`
- `prism_widgets.py`
- All test files
- Export pipeline

### See also
`docs/PHASE1_TABS.md` — full implementation spec for this phase.

---

## Phase 2 — Web renderer for priority charts

**Goal:** Replace `FigureCanvasTkAgg` with a `pywebview` + Plotly.js panel for the four
priority chart types. Both renderers coexist during this phase.

### Priority chart types
Bar, Grouped Bar, Line, Scatter.

### Architecture
```
Python process
├── FastAPI server (~200 lines, background thread)
│   ├── POST /render  →  accepts chart spec kwargs, returns Plotly JSON
│   └── POST /event   ←  receives edit events from JS (Phase 3)
└── prism_spec_{bar,grouped_bar,line,scatter}.py
        Each builds a plotly.graph_objects Figure in Python and returns fig.to_json()

pywebview panel (replaces _plot_frame for priority charts)
└── Plotly.js renders the JSON spec
```

### Key decisions
- Chart specs are built in **Python** using `plotly.py` — no JavaScript written for specs.
- `TabState` gets an optional `plotly_spec: dict | None` field alongside `fig`.
- `_embed_plot` checks `chart_type`: priority → pywebview; others → FigureCanvasTkAgg.
- Tab system is unchanged. The frame container interface is the stable boundary.
- Validate `pywebview` embedding on macOS before starting (run `pip install pywebview`
  and confirm WKWebView opens cleanly).

### Pre-work (can be done in parallel with Phase 1)
- Build and validate a Prism-style Plotly template (open spine, Arial, Prism palette).
- Confirm `pywebview` embeds correctly on the current macOS version.
- Define journal export requirements (DPI, size, format) for the export pipeline.

### What does NOT change
- Tab system (`prism_tabs.py`) — zero changes expected.
- `prism_functions.py` — matplotlib versions retained as export fallback.
- All 25 non-priority chart types — continue using FigureCanvasTkAgg.

---

## Phase 3 — Direct manipulation

**Goal:** Tier 2–3 interactivity on priority charts. Edit elements directly on the chart.

### Interactions
- Click title / axis labels → inline text edit (Plotly `editable: true` covers this for free)
- Drag legend → reposition
- Click bar → color picker → recolor (replaces the mpl_connect implementation from Phase 1)
- Drag Y-axis limit → rescale
- Add annotation by clicking chart area
- All edits post events back to Python → form state updates bidirectionally

### Event flow
```
User drags title in pywebview
    → JS posts { event: "title_changed", value: "New Title" } to FastAPI /event
    → Python: tab.vars_snapshot["title"] = "New Title"
    → If form is visible: self._vars["title"].set("New Title")
    → Live preview suppressed (change came from chart, not form)
```

### What does NOT change
- Tab system — zero changes expected.
- FastAPI server from Phase 2 — adds `/event` endpoint only.
- Statistics engine, validators, registry.

---

## Phase 4 — Deployment readiness

**Goal:** App runnable as a web service. Desktop version remains via pywebview.

### Architecture shift
```
Current (Phases 1–3):  Tkinter shell  +  pywebview plot panel
Phase 4:               React SPA      +  Python FastAPI backend
                       (desktop: pywebview wrapping the React SPA)
                       (web:     serve React + FastAPI normally)
```

### What transfers cleanly
- All Python business logic (stats, validators, registry, spec builders).
- `TabManager` state management logic → maps to React/Zustand state.
- FastAPI server → already present, just needs auth + deployment config.

### What gets rewritten
- Tkinter left panel → React components.
- `TabBar` Tk widget → React tab component.

### Note
Phase 4 is only worth pursuing if Phase 2/3 validate that Plotly can meet the
journal-quality output bar. Do not start Phase 4 until Phase 3 is stable.

---

## Parallel work available at each phase

### During Phase 2
- Develop and validate Prism-style Plotly template in a notebook.
- Confirm `pywebview` on current macOS version.
- Define journal export spec (DPI, figure sizes, formats).

### During Phase 3
- Audit all 25 non-priority chart types for Plotly coverage difficulty.
  - Easy (standard Plotly): box, violin, heatmap, histogram, bubble, scatter variants.
  - Hard (custom): subcolumn scatter, before/after, chi-square GoF, forest plot, pyramid.
- Define direct manipulation interaction spec: which elements draggable vs click-to-edit.

---

## Rendering decision record

**Why not Tkinter + matplotlib overlay?**
Coordinate sync between matplotlib and Tk overlay is fragile and breaks on every resize.
Two rendering systems. Drag interactions are laggy (30–150ms redraws). Closed off future
web deployment.

**Why not Qt?**
Near-total UI rewrite (~7,900 lines of Tkinter). Only worth it starting from scratch.

**Why Plotly.js + pywebview?**
- Plotly.js is a retained-mode renderer: objects persist, drag is smooth at 60fps.
- `plotly.py` means chart specs are written in Python, not JavaScript.
- SVG/PDF export from Plotly is vector-quality, suitable for journals.
- pywebview uses WKWebView on macOS — native, fast, well-maintained.
- Same Python backend serves a web deployment in Phase 4 with no changes.

**Why drop `prism_canvas_renderer.py`?**
It was a parallel implementation of bar charts that required maintaining two codebases
in sync. The interactive features it provided (recolor, Y-drag, width-drag) are
superseded by Phase 2/3 Plotly interactivity. Removed in Phase 1.
