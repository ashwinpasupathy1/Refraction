# Claude Prism — Project Context for Claude Code

GraphPad Prism-style scientific plotting application for macOS.
Built entirely by Claude (Anthropic) with Ashwin Pasupathy.

---

## The one rule before every commit

```bash
python3 run_all.py   # must print 417/417 (or higher) with 0 failures
```

Never commit if this fails. Never skip it. If tests regress, fix them before
doing anything else.

---

## Commands

```bash
# Run the full test suite (417 tests across 5 suites, ~52 seconds)
python3 run_all.py

# Run a single suite
python3 run_all.py comprehensive      # 175 tests — all 29 chart types
python3 run_all.py canvas_renderer    # 109 tests — tk.Canvas renderer
python3 run_all.py modular            # 53  tests — widgets/validators/results
python3 run_all.py p1p2p3             # 60  tests — style params
python3 run_all.py control            # 20  tests — control-group logic

# Launch the app (macOS only — needs a display)
python3 prism_barplot_app.py

# Quick syntax check of all modules
python3 -c "import prism_functions, prism_canvas_renderer, prism_widgets, prism_validators, prism_results; print('OK')"
```

---

## File map

```
prism_barplot_app.py      7,907 lines   App class, PLOT_REGISTRY, icon helpers
prism_widgets.py            952 lines   _DS tokens, PButton/PEntry/PCheckbox etc.
prism_validators.py         518 lines   Standalone spreadsheet validators
prism_results.py            387 lines   Results panel: populate / export / copy
prism_functions.py        6,468 lines   29 matplotlib chart functions
prism_canvas_renderer.py  1,687 lines   tk.Canvas bar+grouped-bar live renderer
prism_test_harness.py       363 lines   Shared test bootstrap (imports once)
run_all.py                  108 lines   5-suite unified test runner
test_comprehensive.py     1,341 lines   Main chart function tests
test_canvas_renderer.py   1,306 lines   Canvas renderer + GroupedCanvasRenderer
test_modular.py             599 lines   Widgets / validators / results modules
test_p1_p2_p3.py            796 lines   Style parameter regression tests
test_control.py             437 lines   Control-group statistics tests
```

---

## Architecture overview

### Rendering pipeline

```
User clicks "Generate Plot"
    ↓
App._run()  →  App._do_run() [background thread]
    │  calls prism_functions.prism_barplot(**kw)  →  matplotlib fig, ax
    │  deepcopy(kw) → _kw_snap
    └→ after(0) → App._embed_plot(fig, groups, kw=_kw_snap)
                       │
              canvas_mode && plot_type in ("bar","grouped_bar")?
               ├─ YES → App._try_canvas_embed(fig, kw)
               │         builds BarScene / GroupedBarScene
               │         CanvasRenderer / GroupedCanvasRenderer
               │         live hit-test, recolor, Y-drag, bar-width drag
               └─ NO  → FigureCanvasTkAgg(fig)   ← standard Agg path
```

### Dependency graph

```
prism_barplot_app.py
  ├── prism_widgets.py          (no prism deps — pure Tk + constants)
  ├── prism_validators.py       (no prism deps — pure pandas)
  ├── prism_results.py          (receives app object; no other prism imports)
  ├── prism_functions.py        (numpy, pandas, matplotlib, scipy — all lazy)
  └── prism_canvas_renderer.py  (numpy, pandas — NO matplotlib)
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
| `App._populate_results(...)` | Delegated to `prism_results.populate_results(app,...)` |
| `App._build_sidebar(left)` | Chart-type selector (icons + labels) |
| `App._tab_data(f, mode)` | Data tab: file picker, sheet, color, labels |
| `App._tab_axes(f, mode)` | Axes tab: Y scale, limits, font, bar width |
| `App._tab_stats(f)` | Stats tab: test type, posthoc, correction |

---

## Adding a new chart type — the 5-step checklist

### Step 1 — Write the plot function in `prism_functions.py`

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

### Step 2 — Register it in `_REGISTRY_SPECS` in `prism_barplot_app.py`

Find the list starting at line ~348. Add a new `PlotTypeConfig(...)` entry:

```python
PlotTypeConfig(
    key="my_chart",           # internal key — used everywhere
    label="My Chart",         # shown in sidebar
    fn_name="prism_my_chart", # must match the function name exactly
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

### Step 4 — Add a validator in `prism_validators.py`

```python
def validate_my_chart(df) -> tuple[list, list]:
    """Validate My Chart layout: row 0 = headers, rows 1+ = values."""
    errors, warnings = [], []
    # ... checks ...
    return errors, warnings
```

Then wire it in `prism_barplot_app.py`:
- Import it in the `from prism_validators import ...` block at the top
- Add it to `_STANDALONE_VALIDATORS` dict in `_validate_spreadsheet()`
- Update `PlotTypeConfig.validate` to `"_validate_my_chart"`

### Step 5 — Write tests

Add a test section to `test_comprehensive.py` following the existing pattern.
At minimum: one test that renders without crashing, one that checks a specific
visual property, one that tests the validator.

Run `python3 run_all.py` — all existing 417 tests must still pass.

---

## Core helper functions (use these, don't reinvent them)

### In `prism_functions.py`

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

### In `prism_widgets.py`

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

### In `prism_canvas_renderer.py`

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

## Style constants (all in `prism_functions.py`)

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

| UI Label | Registry key | Function |
|---|---|---|
| Bar Chart | `bar` | `prism_barplot` |
| Line Graph | `line` | `prism_linegraph` |
| Grouped Bar | `grouped_bar` | `prism_grouped_barplot` |
| Box Plot | `box` | `prism_boxplot` |
| Scatter Plot | `scatter` | `prism_scatterplot` |
| Violin Plot | `violin` | `prism_violin` |
| Survival Curve | `kaplan_meier` | `prism_kaplan_meier` |
| Heatmap | `heatmap` | `prism_heatmap` |
| Two-Way ANOVA | `two_way_anova` | `prism_two_way_anova` |
| Before / After | `before_after` | `prism_before_after` |
| Histogram | `histogram` | `prism_histogram` |
| Subcolumn | `subcolumn_scatter` | `prism_subcolumn_scatter` |
| Curve Fit | `curve_fit` | `prism_curve_fit` |
| Col Statistics | `column_stats` | `prism_column_stats` |
| Contingency | `contingency` | `prism_contingency` |
| Repeated Meas. | `repeated_measures` | `prism_repeated_measures` |
| Chi-Sq GoF | `chi_square_gof` | `prism_chi_square_gof` |
| Stacked Bar | `stacked_bar` | `prism_stacked_bar` |
| Bubble Chart | `bubble` | `prism_bubble` |
| Dot Plot | `dot_plot` | `prism_dot_plot` |
| Bland-Altman | `bland_altman` | `prism_bland_altman` |
| Forest Plot | `forest_plot` | `prism_forest_plot` |
| Area Chart | *(not yet in registry)* | `prism_area_chart` |
| Raincloud | *(not yet in registry)* | `prism_raincloud` |
| Q-Q Plot | *(not yet in registry)* | `prism_qq_plot` |
| Lollipop | *(not yet in registry)* | `prism_lollipop` |
| Waterfall | *(not yet in registry)* | `prism_waterfall` |
| Pyramid | *(not yet in registry)* | `prism_pyramid` |
| ECDF | *(not yet in registry)* | `prism_ecdf` |

---

## Test harness patterns

```python
# All test files follow this pattern:
import prism_test_harness as _h
from prism_test_harness import pf, plt, ok, fail, run, section, summarise, bar_excel, with_excel

# Write a test:
def test_my_feature():
    with bar_excel({"Control": [1,2,3], "Drug": [4,5,6]}) as path:
        fig, ax = pf.prism_barplot(path)
        assert ax.get_xlim()[0] < 0
        plt.close(fig)
run("prism_barplot: x axis extends left of first bar", test_my_feature)

# Run standalone:
summarise()
sys.exit(0 if _h.FAIL == 0 else 1)
```

**Available fixtures**: `bar_excel`, `line_excel`, `grouped_excel`, `km_excel`,
`heatmap_excel`, `two_way_excel`, `contingency_excel`, `with_excel`

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

6. **New chart types added to `prism_functions.py` but NOT yet to `_REGISTRY_SPECS`**
   (area_chart, raincloud, qq_plot, lollipop, waterfall, pyramid, ecdf) —
   these functions exist and are tested in `test_comprehensive.py` but do not
   appear in the app sidebar yet. To add them to the UI, follow Step 2 above.

7. **`ttk.Treeview` heading colours on macOS Aqua theme** — `ttk.Style.configure`
   heading background is ignored on Aqua. Headers appear in the system default
   colour. Fix requires `style.theme_use("clam")` or custom drawing.

8. **`_populate_results` for grouped charts** reads `df.select_dtypes(include="number")`
   which merges the two-row-header grouped layout incorrectly. Results panel
   shows all numeric cells combined for grouped/stacked charts — known issue.

9. **Toggling canvas mode while viewing a grouped chart** — `_toggle_canvas_mode`
   checks `plot_type == "bar"` before re-triggering a run. Should be
   `in ("bar", "grouped_bar")`. Known bug, not yet fixed.

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
