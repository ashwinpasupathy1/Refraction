# Spectra (Claude Plotter) — Project Context for Claude Code

GraphPad Prism-style scientific plotting application for macOS.
Built entirely by Claude (Anthropic) with Ashwin Pasupathy.

---

## The one rule before every commit

```bash
python3 run_all.py   # must print 0 failures
```

Never commit if core tests fail. Never skip it. If tests regress, fix them
before doing anything else.

---

## Commands

```bash
# Run the full test suite (5 suites, ~30 seconds)
python3 run_all.py

# Run a single suite
python3 run_all.py comprehensive      # 309 tests — all chart types + stats engine
python3 run_all.py stats              #  57 tests — statistical verification + control logic
python3 run_all.py validators         #  35 tests — spreadsheet validators
python3 run_all.py specs              #  11+ tests — Plotly spec builders + server (needs plotly)
python3 run_all.py api                #  18 tests — FastAPI endpoint tests

# Launch the app
python3 plotter_barplot_app.py        # Tk desktop app
python3 plotter_desktop.py            # Desktop entry point (pywebview + FastAPI)
python3 plotter_web_server.py         # Standalone web server (no Tk)

# One-command setup (installs Python deps + npm build)
./setup.sh

# Build macOS .app bundle (PyInstaller + optional DMG)
./build_app.sh

# Quick syntax check of all modules
python3 -c "import plotter_functions, plotter_widgets, plotter_validators, plotter_results, plotter_registry, plotter_tabs, plotter_app_icons, plotter_presets, plotter_session, plotter_events, plotter_types, plotter_undo, plotter_errors, plotter_comparisons, plotter_project, plotter_import_pzfx, plotter_wiki_content, plotter_app_wiki, plotter_server, plotter_webview, plotter_plotly_theme, plotter_spec_bar, plotter_spec_grouped_bar, plotter_spec_line, plotter_spec_scatter, plotter_web_server; print('OK')"
```

---

## File map

```
# ── Core application ──────────────────────────────────────────────
plotter_barplot_app.py      6,688 lines   App class, sidebar, all UI wiring
plotter_functions.py        6,553 lines   29 matplotlib chart functions + stats
plotter_widgets.py            952 lines   _DS tokens, PButton/PEntry/PCheckbox etc.
plotter_validators.py         518 lines   Standalone spreadsheet validators
plotter_results.py            401 lines   Results panel: populate / export / copy

# ── Phase 2 infrastructure modules ────────────────────────────────
plotter_registry.py           475 lines   PlotTypeConfig registry (29 entries)
plotter_tabs.py               532 lines   Multi-tab state (TabState, TabManager, TabBar)
plotter_app_icons.py          352 lines   Sidebar icon drawing for all chart types
plotter_presets.py            163 lines   Style preset load/save (.json)
plotter_session.py             77 lines   Session persistence (last-used settings)
plotter_events.py              75 lines   EventBus for decoupled pub/sub messaging
plotter_types.py              121 lines   Shared type definitions and dataclasses
plotter_undo.py               131 lines   UndoStack for undo/redo support
plotter_errors.py              99 lines   ErrorReporter: structured error handling
plotter_comparisons.py        248 lines   Custom comparison builder UI
plotter_project.py            207 lines   .cplot project file save/open (ZIP format)
plotter_import_pzfx.py        316 lines   GraphPad .pzfx file importer
plotter_wiki_content.py     2,224 lines   Statistical wiki content (29 sections)
plotter_app_wiki.py           522 lines   Wiki popup viewer (Tk UI)

# ── Phase 3 — Plotly / FastAPI / Web ──────────────────────────────
plotter_server.py             183 lines   FastAPI server + auth + endpoints
plotter_webview.py            179 lines   pywebview wrapper for desktop mode
plotter_plotly_theme.py        51 lines   Plotly theme constants (PRISM_TEMPLATE)
plotter_spec_bar.py            67 lines   Bar chart Plotly spec builder
plotter_spec_grouped_bar.py    57 lines   Grouped bar Plotly spec builder
plotter_spec_line.py           55 lines   Line graph Plotly spec builder
plotter_spec_scatter.py        58 lines   Scatter plot Plotly spec builder

# ── Phase 5 — All 29 Plotly spec builders ─────────────────────────
plotter_spec_box.py            55 lines   Box plot Plotly spec builder
plotter_spec_violin.py         58 lines   Violin plot Plotly spec builder
plotter_spec_histogram.py      55 lines   Histogram Plotly spec builder
plotter_spec_dot_plot.py       61 lines   Dot plot Plotly spec builder
plotter_spec_raincloud.py      88 lines   Raincloud Plotly spec builder
plotter_spec_qq.py             77 lines   Q-Q plot Plotly spec builder
plotter_spec_ecdf.py           56 lines   ECDF Plotly spec builder
plotter_spec_before_after.py   69 lines   Before/After Plotly spec builder
plotter_spec_repeated_measures.py 77 lines Repeated Measures Plotly spec builder
plotter_spec_subcolumn.py      71 lines   Subcolumn scatter Plotly spec builder
plotter_spec_stacked_bar.py    57 lines   Stacked bar Plotly spec builder
plotter_spec_area.py           53 lines   Area chart Plotly spec builder
plotter_spec_lollipop.py       66 lines   Lollipop Plotly spec builder
plotter_spec_waterfall.py      54 lines   Waterfall Plotly spec builder
plotter_spec_pyramid.py        71 lines   Pyramid Plotly spec builder
plotter_spec_kaplan_meier.py  105 lines   Kaplan-Meier Plotly spec builder
plotter_spec_heatmap.py        49 lines   Heatmap Plotly spec builder
plotter_spec_bland_altman.py   64 lines   Bland-Altman Plotly spec builder
plotter_spec_forest_plot.py    73 lines   Forest plot Plotly spec builder
plotter_spec_bubble.py         71 lines   Bubble chart Plotly spec builder
plotter_spec_curve_fit.py      83 lines   Curve fit Plotly spec builder
plotter_spec_column_stats.py   73 lines   Column statistics Plotly spec builder
plotter_spec_contingency.py    45 lines   Contingency Plotly spec builder
plotter_spec_chi_square_gof.py 68 lines   Chi-Square GoF Plotly spec builder
plotter_spec_two_way_anova.py  57 lines   Two-Way ANOVA Plotly spec builder

# ── Phase 6 — Desktop + Deployment ────────────────────────────────
plotter_desktop.py            183 lines   Desktop entry point (pywebview + FastAPI)
setup.sh                      159 lines   One-command setup script
build_app.sh                  323 lines   PyInstaller + optional DMG builder

# ── Phase 4 — Web Deployment ──────────────────────────────────────
plotter_web_server.py          49 lines   Standalone web server entry point (no Tk)
plotter_web/                              React SPA (Vite + TypeScript + Plotly.js)
Dockerfile                                Docker deployment config
requirements.txt                          Desktop dependencies
requirements-web.txt                      Web-only dependencies (no Tk/matplotlib)

# ── Test infrastructure ────────────────────────────────────────────
tests/plotter_test_harness.py 363 lines   Shared test bootstrap (imports once)
run_all.py                    112 lines   5-suite unified test runner
tests/test_comprehensive.py 1,341 lines   Main chart function tests (309 tests)
tests/test_stats.py         1,200+ lines  Statistical verification + control logic (57 tests)
tests/test_validators.py      600+ lines  Spreadsheet validator tests (35 tests)
tests/test_api.py             500+ lines  FastAPI endpoint tests (18 tests)
tests/test_png_render.py      450+ lines  All 29 chart PNG render tests (29 tests)
tests/test_phase3_plotly.py   156 lines   Plotly spec builders + server (11 tests)
tests/visual_test.py          552 lines   Visual regression tests (manual)

# ── Archived ───────────────────────────────────────────────────────
docs/archive/phase2/                      Phase 2 development notes
docs/archive/phase3/                      Phase 3 development notes
docs/archive/phase4/                      Phase 4 development notes
```

---

## Architecture overview

### Rendering pipeline

All 29 chart types now have Plotly spec builders, making Plotly.js the primary
interactive rendering path for both desktop (pywebview) and web (browser) modes.
The matplotlib/PNG path is retained as a true fallback for offline export and
environments where Plotly is unavailable.

```
User clicks "Generate Plot"
    ↓
App._run()  →  App._do_run() [background thread]
    │
    ├── Plotly path (primary — all 29 chart types):
    │     POST /render {chart_type, kw}
    │     → plotter_server._build_spec()
    │     → plotter_spec_*.build_*_spec(kw)
    │     → Plotly JSON spec → rendered by Plotly.js in webview
    │
    └── Matplotlib path (fallback / export):
          plotter_functions.plotter_barplot(**kw)  →  matplotlib fig, ax
          → FigureCanvasTkAgg(fig)  or  fig.savefig(path)
```

### Dependency graph

```
plotter_barplot_app.py
  ├── plotter_widgets.py          (no prism deps — pure Tk + constants)
  ├── plotter_validators.py       (no prism deps — pure pandas)
  ├── plotter_results.py          (receives app object; no other prism imports)
  ├── plotter_functions.py        (numpy, pandas, matplotlib, scipy — all lazy)
  └── plotter_canvas_renderer.py  (numpy, pandas — NO matplotlib)
```

### Key App methods

| Method | What it does |
|---|---|
| `App._do_run(kw)` | Background thread: calls plot function, schedules `_embed_plot` |
| `App._embed_plot(fig, groups, kw)` | Main thread: shows chart (canvas or Agg) |
| `App._try_canvas_embed(fig, kw)` | Builds tk.Canvas renderer; returns True/False |
| `App._collect(excel)` → `kw` | Assembles full kwargs dict from all UI vars |
| `App._collect_display(kw)` | Error bars, points, colours, alpha, axis style |
| `App._collect_labels(kw)` | Title, xlabel, ytitle |
| `App._collect_stats(kw)` | Stats test, posthoc, correction, permutations |
| `App._collect_figsize(kw)` | figsize, bar_width, font_size, jitter |
| `App._validate_spreadsheet()` | Reads sheet, dispatches to validator, shows result |
| `App._populate_results(...)` | Delegated to `plotter_results.populate_results(app,...)` |
| `App._build_sidebar(left)` | Chart-type selector (icons + labels) |
| `App._tab_data(f, mode)` | Data tab: file picker, sheet, color, labels |
| `App._tab_axes(f, mode)` | Axes tab: Y scale, limits, font, bar width |
| `App._tab_stats(f)` | Stats tab: test type, posthoc, correction |

---

## Adding a new chart type — the 5-step checklist

### Step 1 — Write the plot function in `plotter_functions.py`

Insert **before** the `# P20 — Export all chart types` block (around line 5586).

Every function must follow this exact template:

```python
def prism_my_chart(
    excel_path: str,
    sheet=0,
    color=None,
    title: str = "",
    xlabel: str = "",
    ytitle: str = "",
    yscale: str = "linear",
    ylim=None,
    figsize=(5, 5),
    font_size: float = 12.0,
    # ... chart-specific params ...
    ref_line=None,
    ref_line_label: str = "",
    # ── shared style params (copy this block verbatim) ──────────────────
    axis_style: str = "open",
    tick_dir: str = "out",
    minor_ticks: bool = False,
    point_size: float = 6.0,
    point_alpha: float = 0.80,
    cap_size: float = 4.0,
    ytick_interval: float = 0.0,
    xtick_interval: float = 0.0,
    fig_bg: str = "white",
    spine_width: float = 0.8,
    gridlines: bool = False,
    grid_style: str = "none",
):
    """One-line summary.

    Longer description. Excel layout explanation.
    """
    _ensure_imports()
    group_order, groups, bar_colors, fig, ax = _base_plot_setup(
        excel_path, sheet, color, None, figsize)
    _sk = _style_kwargs(locals())   # ← always do this

    # ... drawing code ...

    _apply_prism_style(ax, font_size, **_sk)
    _apply_grid(ax, grid_style, gridlines)
    _base_plot_finish(ax, fig, title, xlabel, ytitle, yscale, ylim,
                      font_size, ref_line, len(group_order),
                      ref_line_label=ref_line_label, **_sk)
    return fig, ax
```

**Critical rules:**
- Always call `_ensure_imports()` first
- Always call `_style_kwargs(locals())` early and pass `**_sk` to both `_apply_prism_style` and `_base_plot_finish`
- Always `return fig, ax`
- Never import matplotlib or seaborn at module level — they're lazy-loaded by `_ensure_imports()`

### Step 2 — Register it in `plotter_registry.py`

Add a new `PlotTypeConfig(...)` entry to the registry list in `plotter_registry.py`.
Also add a sidebar icon drawing function to `plotter_app_icons.py`.

```python
PlotTypeConfig(
    key="my_chart",           # internal key — used everywhere
    label="My Chart",         # shown in sidebar
    fn_name="plotter_my_chart", # must match the function name exactly
    tab_mode="bar",           # which UI tabs to use (see tab modes below)
    stats_tab="standard",     # which stats sub-tab
    validate="_validate_bar", # which validator method
    has_points=True,          # show point size/alpha sliders?
    has_error_bars=True,      # show error bar type selector?
    has_legend=False,         # show legend position selector?
    has_stats=True,           # show statistics tab?
    x_continuous=False,       # X axis is numeric (not categorical)?
    axes_has_bar_width=False, # show bar width slider?
    axes_has_line_opts=False, # show line width/marker options?
    extra_collect=lambda app, kw: kw.update({
        "my_param": app._get_var("my_var_key", default_value),
    }),
),
```

**tab_mode options** (controls which UI sub-sections appear):
- `"bar"` — flat categorical data (bar, box, violin, dot_plot, etc.)
- `"line"` — numeric X axis (line, scatter, curve_fit)
- `"grouped_bar"` — two-row-header grouped data
- `"scatter"` — XY scatter variants
- `"heatmap"` — matrix data
- `"kaplan_meier"` — survival data
- `"before_after"` — paired/repeated measures

**stats_tab options**: `"standard"` `"grouped_bar"` `"scatter"` `"kaplan_meier"` `"before_after"` `"histogram"` `"curve_fit"` `"column_stats"` `"contingency"` `"repeated_measures"` `"chi_square_gof"` `"stacked_bar"` `"bubble"` `"dot_plot"` `"bland_altman"` `"forest_plot"` `"heatmap"` `"two_way_anova"`

### Step 3 — Add UI controls (if the chart has unique options)

If your chart needs custom UI controls not covered by the standard tabs,
add a `_tab_stats_my_chart` method to the App class (see `_tab_stats_histogram`
at line ~5143 for a template) and set `stats_tab="my_chart"` in the registry.

Add new `tk.StringVar` / `tk.BooleanVar` defaults to `_reset_vars_to_defaults()`
so the form resets correctly when switching chart types.

### Step 4 — Add a validator in `plotter_validators.py`

```python
def validate_my_chart(df) -> tuple[list, list]:
    """Validate My Chart layout: row 0 = headers, rows 1+ = values."""
    errors, warnings = [], []
    # ... checks ...
    return errors, warnings
```

Then wire it in `plotter_barplot_app.py`:
- Import it in the `from plotter_validators import ...` block at the top
- Add it to `_STANDALONE_VALIDATORS` dict in `_validate_spreadsheet()`
- Update `PlotTypeConfig.validate` to `"_validate_my_chart"`

### Step 5 — Write tests

Add a test section to `test_comprehensive.py` following the existing pattern.
At minimum: one test that renders without crashing, one that checks a specific
visual property, one that tests the validator.

Run `python3 run_all.py` — all existing tests must still pass.

---

## Core helper functions (use these, don't reinvent them)

### In `plotter_functions.py`

| Function | Purpose |
|---|---|
| `_ensure_imports()` | Loads plt, sns, stats lazily — always call first |
| `_base_plot_setup(excel_path, sheet, color, n, figsize)` | Reads Excel, assigns colours, creates fig/ax |
| `_base_plot_finish(ax, fig, ...)` | Applies labels, ref line, tight_layout |
| `_style_kwargs(locals())` | Extracts shared style params from locals() dict |
| `_apply_prism_style(ax, font_size, **_sk)` | Applies open-spine, tick direction, fonts |
| `_apply_stats_brackets(ax, groups, ...)` | Draws significance brackets |
| `_apply_grid(ax, grid_style, gridlines)` | Horizontal / full / no gridlines |
| `_apply_legend(ax, legend_pos, font_size)` | Places or hides legend |
| `_apply_log_formatting(ax)` | Log tick labels (10¹, 10², ...) |
| `_set_categorical_xticks(ax, ...)` | Group labels + n= counts on X axis |
| `_draw_jitter_points(ax, g_idx, vals, color, ...)` | Jittered data points |
| `_calc_error(vals, error_type)` | Returns (mean, half_width) for SEM/SD/CI95 |
| `_calc_error_asymmetric(vals, error_type)` | Asymmetric error bars for log scale |
| `_assign_colors(n, color)` | Returns list of n hex colours from palette |
| `_darken_color(c, factor=0.65)` | Darker version for edges |
| `_fmt_bar_label(v)` | Format a numeric value for bar top labels |
| `normality_warning(groups, stats_test)` | Returns warning string if non-normal |

### In `plotter_widgets.py`

| Symbol | Purpose |
|---|---|
| `_DS.PRIMARY` | Accent blue `#2274A5` |
| `PButton(parent, text, style, command)` | Styled button: `"primary"/"secondary"/"ghost"` |
| `PEntry(parent, textvariable, width)` | Flat-border text entry |
| `PCheckbox(parent, variable, text)` | Canvas-rendered checkbox |
| `PCombobox(parent, textvariable, values)` | Styled dropdown |
| `section_sep(parent, row, text)` | Blue section header band in grid layouts |
| `_create_tooltip(widget, text)` | Hover tooltip (yellow background) |
| `add_placeholder(entry, var, text)` | Grey hint text when empty |
| `label(key)` / `hint(key)` | LABELS/HINTS dict lookup |

### In `plotter_canvas_renderer.py`

| Class | Purpose |
|---|---|
| `BarScene` | Immutable bar chart description |
| `CanvasRenderer` | Renders BarScene on tk.Canvas; `render()`, `hit_test()`, `recolor()`, `rescale()` |
| `RescaleHandle` | Coordinate mapping; `set_y_range()`, `set_canvas_size()`, `set_bar_width()` |
| `GroupedBarScene` | Immutable grouped bar description |
| `GroupedCanvasRenderer` | Renderer for grouped charts |
| `build_bar_scene(kw, w, h)` | Builds BarScene from plot kwargs (no matplotlib) |
| `build_grouped_bar_scene(kw, w, h)` | Builds GroupedBarScene |

---

## Style constants (all in `plotter_functions.py`)

```python
_DPI        = 144       # render DPI (144 = retina-grade)
_FONT       = "Arial"   # axis/tick font (falls back on non-macOS)
_ALPHA_BAR  = 0.85      # default bar fill alpha
_LABEL_PAD  = 6         # axis label padding (pts)
_TITLE_PAD  = 8         # title padding (pts)
_TIGHT_PAD  = 1.2       # fig.tight_layout pad

PRISM_PALETTE = [        # 10 default colours matching GraphPad Prism
    "#E8453C", "#2274A5", "#32936F", "#F18F01", "#A846A0",
    "#6B4226", "#048A81", "#D4AC0D", "#3B1F2B", "#44BBA4",
]

AXIS_STYLES = {
    "Open (Prism default)": "open",   # left + bottom spines only
    "Closed box":           "closed", # all four spines
    "Floating":             "floating",
    "None":                 "none",
}

TICK_DIRS = {"Outward (default)": "out", "Inward": "in", "Both": "inout", "None": ""}
```

All shared style params (axis_style, tick_dir, fig_bg, etc.) live in
`PLOT_PARAM_DEFAULTS` and are extracted by `_style_kwargs(locals())`.
**If you add a new universal style param, add it to `PLOT_PARAM_DEFAULTS` — that
is the single change needed.**

---

## Excel layout conventions

| Chart type | Row 0 | Row 1 | Rows 2+ |
|---|---|---|---|
| Bar, Box, Violin, Dot, Before/After, Histogram | Group names | — | Numeric values |
| Line, Scatter, Curve Fit | X-label, Series names | — | X value, Y replicates |
| Grouped Bar, Stacked Bar | Category names | Subgroup names | Numeric values |
| Kaplan-Meier | Group names (each spans 2 cols) | "Time", "Event" | time, 0/1 |
| Heatmap | blank, Col labels | — | Row label, numeric values |
| Two-Way ANOVA | `Factor_A`, `Factor_B`, `Value` | — | one row per observation |
| Contingency | blank, Outcome labels | — | Group name, counts |
| Chi-Square GoF | Category names | Observed counts | (optional) Expected |
| Forest Plot | Study, Effect, Lower CI, Upper CI | — | one row per study |
| Bland-Altman | Method A, Method B | — | paired measurements |
| Pyramid | Category, Left series, Right series | — | values |

---

## All 29 chart types

| UI Label | Registry key | Function | Has Plotly Spec |
|---|---|---|---|
| Bar Chart | `bar` | `plotter_barplot` | Yes |
| Line Graph | `line` | `plotter_linegraph` | Yes |
| Grouped Bar | `grouped_bar` | `plotter_grouped_barplot` | Yes |
| Box Plot | `box` | `plotter_boxplot` | Yes |
| Scatter Plot | `scatter` | `plotter_scatterplot` | Yes |
| Violin Plot | `violin` | `plotter_violin` | Yes |
| Survival Curve | `kaplan_meier` | `plotter_kaplan_meier` | Yes |
| Heatmap | `heatmap` | `plotter_heatmap` | Yes |
| Two-Way ANOVA | `two_way_anova` | `plotter_two_way_anova` | Yes |
| Before / After | `before_after` | `plotter_before_after` | Yes |
| Histogram | `histogram` | `plotter_histogram` | Yes |
| Subcolumn | `subcolumn_scatter` | `plotter_subcolumn_scatter` | Yes |
| Curve Fit | `curve_fit` | `plotter_curve_fit` | Yes |
| Col Statistics | `column_stats` | `plotter_column_stats` | Yes |
| Contingency | `contingency` | `plotter_contingency` | Yes |
| Repeated Meas. | `repeated_measures` | `plotter_repeated_measures` | Yes |
| Chi-Sq GoF | `chi_square_gof` | `plotter_chi_square_gof` | Yes |
| Stacked Bar | `stacked_bar` | `plotter_stacked_bar` | Yes |
| Bubble Chart | `bubble` | `plotter_bubble` | Yes |
| Dot Plot | `dot_plot` | `plotter_dot_plot` | Yes |
| Bland-Altman | `bland_altman` | `plotter_bland_altman` | Yes |
| Forest Plot | `forest_plot` | `plotter_forest_plot` | Yes |
| Area Chart | `area_chart` | `plotter_area_chart` | Yes |
| Raincloud | `raincloud` | `plotter_raincloud` | Yes |
| Q-Q Plot | `qq_plot` | `plotter_qq_plot` | Yes |
| Lollipop | `lollipop` | `plotter_lollipop` | Yes |
| Waterfall | `waterfall` | `plotter_waterfall` | Yes |
| Pyramid | `pyramid` | `plotter_pyramid` | Yes |
| ECDF | `ecdf` | `plotter_ecdf` | Yes |

---

## Test harness patterns

```python
# All test files follow this pattern:
import plotter_test_harness as _h
from plotter_test_harness import pf, plt, ok, fail, run, section, summarise, bar_excel, with_excel

# Write a test:
def test_my_feature():
    with bar_excel({"Control": [1,2,3], "Drug": [4,5,6]}) as path:
        fig, ax = pf.plotter_barplot(path)
        assert ax.get_xlim()[0] < 0
        plt.close(fig)
run("plotter_barplot: x axis extends left of first bar", test_my_feature)

# Run standalone:
summarise()
sys.exit(0 if _h.FAIL == 0 else 1)
```

**Available fixtures**: `bar_excel`, `line_excel`, `grouped_excel`, `km_excel`,
`heatmap_excel`, `two_way_excel`, `contingency_excel`, `bland_altman_excel`,
`forest_excel`, `bubble_excel`, `chi_gof_excel`, `with_excel`

---

## Test suites

| Suite | Module | Tests | What it covers |
|---|---|---|---|
| comprehensive | test_comprehensive | 309 | All chart types + stats engine |
| stats | test_stats | 57 | Statistical verification + control-group logic |
| validators | test_validators | 35 | All spreadsheet validators |
| specs | test_phase3_plotly | 11+ | Plotly spec builders + FastAPI server |
| api | test_api | 18 | FastAPI endpoint tests (TestClient) |

Additional test files (not in run_all.py):
- `tests/test_png_render.py` — 29 tests, one per chart type (matplotlib render)
- `tests/visual_test.py` — manual visual regression tests

---

## Known gotchas

1. **`_ensure_imports()` must be first** in every chart function. matplotlib is
   `None` at module load time. Calling `plt.subplots()` before `_ensure_imports()`
   raises `TypeError: 'NoneType' is not callable`.

2. **`_style_kwargs(locals())`** must be called *after all parameters are defined*
   but *before* any code that modifies locals(). Call it immediately after
   `_base_plot_setup()`.

3. **Docstring indentation after multi-line signatures** — if you add a docstring
   to a function with multi-line parameters, place the docstring *after the closing
   `):`*, never between parameter lines. The regex-based docstring insertion in
   session 13 accidentally broke this; it was fixed with a de-indent pass.

4. **Canvas-mode and `_canvas_widget`** — in canvas mode `self._canvas_widget`
   is `None`. Never call `self._canvas_widget.get_tk_widget()` without first
   checking `if self._canvas_widget is not None`.

5. **`_bar_renderer` lifetime** — cleared to `None` before each new render.
   Check for `None` before using.

6. **All 29 chart types are now registered** — area_chart, raincloud, qq_plot,
   lollipop, waterfall, pyramid, and ecdf were added to `plotter_registry.py`
   and appear in the sidebar. This gotcha is resolved.

7. **`ttk.Treeview` heading colours on macOS Aqua theme** — `ttk.Style.configure`
   heading background is ignored on Aqua. Headers appear in the system default
   colour. Fix requires `style.theme_use("clam")` or custom drawing.

8. **`_populate_results` for grouped charts** reads `df.select_dtypes(include="number")`
   which merges the two-row-header grouped layout incorrectly. Results panel
   shows all numeric cells combined for grouped/stacked charts — known issue.

9. **Old test_canvas_renderer and test_modular** — Deleted. Replaced by
   `tests/test_stats.py`, `tests/test_validators.py`, `tests/test_api.py`,
   and `tests/test_png_render.py`.

10. **The `_kw_snap` deep-copy** in `_do_run` is taken *after* `spec.filter_kwargs`
    strips unsupported keys. `build_bar_scene` reads `kw["excel_path"]` so the
    path must survive the filter. It always does for bar/grouped_bar, but check
    if adding a new chart type with unusual kwargs.

---

## Commit conventions

```
feat: add lollipop chart and wire into sidebar
fix: correct y-axis drag clamping for zero-mean data
test: add 8 ECDF validator tests
refactor: extract prism_export.py from barplot_app
docs: update CLAUDE.md with pyramid chart layout
```

Always run `python3 run_all.py` and confirm 0 failures before pushing.

---

## Phase 2 Changes (March 2026)

Phase 2 added 14 new modules and significant new features while maintaining full
backward compatibility. All 438 tests pass.

### New infrastructure modules

| Module | Purpose |
|---|---|
| `plotter_registry.py` | `PlotTypeConfig` registry extracted from `plotter_barplot_app.py` |
| `plotter_tabs.py` | Multi-tab state management: `TabState`, `TabManager`, `TabBar` |
| `plotter_app_icons.py` | Sidebar icon drawing for all 29 chart types |
| `plotter_presets.py` | Style preset system: load/save named presets as `.json` |
| `plotter_session.py` | Session persistence: auto-save and restore last-used settings |
| `plotter_events.py` | `EventBus` for decoupled pub/sub messaging between components |
| `plotter_types.py` | Shared dataclasses and type definitions |
| `plotter_undo.py` | `UndoStack` implementing undo/redo for plot parameter changes |
| `plotter_errors.py` | `ErrorReporter` for structured, user-friendly error messages |
| `plotter_comparisons.py` | Custom comparison builder: select arbitrary group pairs for stats |
| `plotter_project.py` | `.cplot` project file save/open (ZIP archives with data + settings) |
| `plotter_import_pzfx.py` | GraphPad Prism `.pzfx` file importer |
| `plotter_wiki_content.py` | Statistical wiki content: 29 sections, 21 references |
| `plotter_app_wiki.py` | Statistical wiki popup viewer (Tk UI) |

### New features wired into the app

- **Style presets**: preset selector in Data tab; ships with 5 built-in presets
- **Session persistence**: settings auto-saved on plot run, restored at startup
- **Project files**: File > Save Project / Open Project (.cplot ZIP format)
- **.pzfx import**: File > Import from GraphPad (.pzfx) to extract group data
- **Statistical wiki**: Help > Statistical Methods (29 documented tests)
- **Undo/redo**: Cmd+Z / Cmd+Shift+Z for plot parameter changes
- **Keyboard shortcuts**: Cmd+1-9 to switch chart types in the sidebar
- **Event bus**: internal pub/sub wiring (not yet widely used by UI components)
- **Custom comparisons**: UI for selecting specific group pairs to test

### Bugs fixed

1. `plotter_repeated_measures`: `KeyError: 'p-unc'` — pingouin >=0.5 uses `p_unc`
   (underscore) not `p-unc` (hyphen). Fixed with version-safe column lookup.

### Additional gotchas (Phase 2)

11. **Headless / CI environments** — `plotter_tabs.py` and other Tk modules
    need a display. Run `xvfb-run python3 run_all.py` on CI. Without `$DISPLAY`
    the modular test suite will show ~19 Tk-related failures (all expected).

12. **All new modules use `plotter_` prefix** — never create new modules with
    `prism_` prefix. Comments and docstrings may still say "GraphPad Prism"
    (that's the product being emulated) but Python identifiers use `plotter_`.

13. **Event bus is optional** — components don't need to use `EventBus`. It is
    wired in but not required for rendering or stats.

14. **`.cplot` files are ZIP archives** — they contain `settings.json` +
    the original Excel file. Do not assume plain JSON.

15. **`plotter_registry.py` is the canonical source** for `PlotTypeConfig` entries.
    `plotter_barplot_app.py` imports the registry; do not add new chart types
    directly to `plotter_barplot_app.py`.

## Phase 3 — Plotly / FastAPI / Web Rendering (March 2026)

Phase 3 added interactive Plotly.js chart rendering and a FastAPI backend,
enabling both desktop (pywebview) and web (browser) modes.

### New modules

| Module | Lines | Purpose |
|---|---|---|
| `plotter_server.py` | 183 | FastAPI server: `/health`, `/render`, auth middleware |
| `plotter_webview.py` | 179 | `PlotterWebView` class wrapping pywebview for desktop |
| `plotter_plotly_theme.py` | 51 | `PRISM_TEMPLATE` and `PRISM_PALETTE` for Plotly |
| `plotter_spec_bar.py` | 67 | `build_bar_spec()` — bar chart Plotly JSON builder |
| `plotter_spec_grouped_bar.py` | 57 | `build_grouped_bar_spec()` |
| `plotter_spec_line.py` | 55 | `build_line_spec()` |
| `plotter_spec_scatter.py` | 58 | `build_scatter_spec()` |

### Phase 3 gotchas

20. **Plotly is optional** — the `plotly` package is required only for
    Phase 3 spec builders. Desktop matplotlib rendering works without it.

21. **Spec builders read Excel directly** — each `build_*_spec()` function
    reads the Excel file and returns a Plotly JSON dict. They do NOT go
    through `plotter_functions.py`.

22. **`plotter_server.py` vs `plotter_web_server.py`** — `plotter_server.py`
    defines the FastAPI app and endpoints. `plotter_web_server.py` is a thin
    entry point that imports and runs it for standalone web deployment.

---

## Phase 4 — Deployment Readiness

### New files
| File | Purpose |
|---|---|
| `plotter_web_server.py` | Standalone web server entry point (no Tk) |
| `Dockerfile` | Docker deployment config |
| `requirements.txt` | Desktop dependencies |
| `requirements-web.txt` | Web server dependencies (no Tk/matplotlib) |
| `plotter_web/` | React SPA (Vite + TypeScript + Plotly.js) |

### Running as a web service
```bash
# Local development
python3 plotter_web_server.py

# With Docker
docker build -t claude-plotter .
docker run -p 7331:7331 claude-plotter

# With API key authentication
PLOTTER_API_KEY=your-secret python3 plotter_web_server.py
```

### Architecture
```
Desktop mode:   Tk shell -> pywebview -> React SPA -> FastAPI (127.0.0.1:7331)
Web mode:       Browser -> React SPA -> FastAPI (0.0.0.0:7331)
Both modes:     same Python business logic, same FastAPI server
```

### Phase 4 gotchas

16. **pywebview on headless servers** — pywebview requires a display.
    Use `plotter_web_server.py` (no Tk, no pywebview) for headless deployment.

17. **React SPA build** — Run `cd plotter_web && npm install && npm run build`
    before deployment. The dist/ directory must exist for static file serving.

18. **CORS** — FastAPI allows all origins by default. In production, restrict
    `allow_origins` in plotter_server.py to your domain.

19. **API key** — Set `PLOTTER_API_KEY` env var for non-local request auth.
    Local requests (127.0.0.1 / localhost) always bypass auth.

---

## Phase 5 — Full Web Migration (March 2026)

Phase 5 expanded web mode from 4 chart types to all 29, rebuilt the React SPA
with a full UI (sidebar, config panel, file upload), and hardened the FastAPI
backend with input validation and upload support.

### New Plotly spec builders (25 files)

| Module | Function | Chart type |
|---|---|---|
| `plotter_spec_box.py` | `build_box_spec` | Box plot |
| `plotter_spec_violin.py` | `build_violin_spec` | Violin plot |
| `plotter_spec_histogram.py` | `build_histogram_spec` | Histogram |
| `plotter_spec_dot_plot.py` | `build_dot_plot_spec` | Dot plot |
| `plotter_spec_raincloud.py` | `build_raincloud_spec` | Raincloud |
| `plotter_spec_qq.py` | `build_qq_spec` | Q-Q plot |
| `plotter_spec_ecdf.py` | `build_ecdf_spec` | ECDF |
| `plotter_spec_before_after.py` | `build_before_after_spec` | Before/After |
| `plotter_spec_repeated_measures.py` | `build_repeated_measures_spec` | Repeated Measures |
| `plotter_spec_subcolumn.py` | `build_subcolumn_spec` | Subcolumn scatter |
| `plotter_spec_stacked_bar.py` | `build_stacked_bar_spec` | Stacked bar |
| `plotter_spec_area.py` | `build_area_spec` | Area chart |
| `plotter_spec_lollipop.py` | `build_lollipop_spec` | Lollipop |
| `plotter_spec_waterfall.py` | `build_waterfall_spec` | Waterfall |
| `plotter_spec_pyramid.py` | `build_pyramid_spec` | Pyramid |
| `plotter_spec_kaplan_meier.py` | `build_kaplan_meier_spec` | Kaplan-Meier |
| `plotter_spec_heatmap.py` | `build_heatmap_spec` | Heatmap |
| `plotter_spec_bland_altman.py` | `build_bland_altman_spec` | Bland-Altman |
| `plotter_spec_forest_plot.py` | `build_forest_plot_spec` | Forest plot |
| `plotter_spec_bubble.py` | `build_bubble_spec` | Bubble chart |
| `plotter_spec_curve_fit.py` | `build_curve_fit_spec` | Curve fit |
| `plotter_spec_column_stats.py` | `build_column_stats_spec` | Column statistics |
| `plotter_spec_contingency.py` | `build_contingency_spec` | Contingency |
| `plotter_spec_chi_square_gof.py` | `build_chi_square_gof_spec` | Chi-Square GoF |
| `plotter_spec_two_way_anova.py` | `build_two_way_anova_spec` | Two-Way ANOVA |

### React SPA rebuild

| File | Purpose |
|---|---|
| `plotter_web/src/App.tsx` | 3-column layout: Sidebar + Chart + ConfigPanel |
| `plotter_web/src/App.css` | Full stylesheet with responsive breakpoints |
| `plotter_web/src/Sidebar.tsx` | Chart type selector with 6 collapsible categories |
| `plotter_web/src/ConfigPanel.tsx` | Data/Labels/Style panels + Generate button |
| `plotter_web/src/FileUpload.tsx` | Drag-and-drop Excel upload → `/upload` endpoint |

### Backend hardening

- `/upload` POST endpoint — accepts `.xlsx`/`.xls`/`.csv`, validates size (10 MB limit), UUID-prefixed storage
- `RequestSizeLimitMiddleware` — rejects oversized requests (20 MB) at the HTTP layer
- `_SPEC_BUILDERS` dict — all 29 chart types mapped via `importlib.import_module` (lazy loading)
- Input validation on `/render` and `/spec` — unknown chart types and missing files rejected early
- `/chart-types` endpoint auto-synced with `_KNOWN_CHART_TYPES` set

### Phase 5 gotchas

23. **All 29 spec builders require `plotly`** — install with `pip install plotly`.
    Without it, `/render` will return import errors for any chart type.

24. **`/upload` stores files in `$TMPDIR/claude-plotter-uploads/`** — files are
    UUID-prefixed to prevent collisions. Clean up periodically in production.

25. **React SPA needs rebuild after changes** — `cd plotter_web && npm run build`.
    The FastAPI server serves the built `dist/` directory as static files.

26. **Spec builders are independent of `plotter_functions.py`** — they read Excel
    directly and produce Plotly JSON. They do NOT share rendering code with the
    matplotlib chart functions. Visual parity is maintained by using `PRISM_PALETTE`
    and `PRISM_TEMPLATE` from `plotter_plotly_theme.py`.
