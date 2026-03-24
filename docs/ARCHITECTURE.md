# Refraction Architecture

GraphPad Prism-style scientific plotting application for macOS.

---

## Rendering pipeline

All 29 chart types now have Plotly spec builders, making Plotly.js the primary
interactive rendering path for both desktop (pywebview) and web (browser) modes.
The matplotlib/PNG path is retained as a true fallback for offline export and
environments where Plotly is unavailable.

```
User clicks "Generate Plot"
    |
App._run()  ->  App._do_run() [background thread]
    |
    |-- Plotly path (primary -- all 29 chart types):
    |     POST /render {chart_type, kw}
    |     -> plotter_server._build_spec()
    |     -> plotter_spec_*.build_*_spec(kw)
    |     -> Plotly JSON spec -> rendered by Plotly.js in webview
    |
    +-- Matplotlib path (fallback / export):
          plotter_functions.plotter_barplot(**kw)  ->  matplotlib fig, ax
          -> FigureCanvasTkAgg(fig)  or  fig.savefig(path)
```

## Dependency graph

```
plotter_barplot_app.py
  |-- plotter_widgets.py          (no prism deps -- pure Tk + constants)
  |-- plotter_validators.py       (no prism deps -- pure pandas)
  |-- plotter_results.py          (receives app object; no other prism imports)
  |-- plotter_functions.py        (numpy, pandas, matplotlib, scipy -- all lazy)
  +-- plotter_canvas_renderer.py  (numpy, pandas -- NO matplotlib)
```

## Desktop vs. Web architecture

```
Desktop mode:   Tk shell -> pywebview -> React SPA -> FastAPI (127.0.0.1:7331)
Web mode:       Browser -> React SPA -> FastAPI (0.0.0.0:7331)
Both modes:     same Python business logic, same FastAPI server
```

---

## Key App methods

| Method | What it does |
|---|---|
| `App._do_run(kw)` | Background thread: calls plot function, schedules `_embed_plot` |
| `App._embed_plot(fig, groups, kw)` | Main thread: shows chart (canvas or Agg) |
| `App._try_canvas_embed(fig, kw)` | Builds tk.Canvas renderer; returns True/False |
| `App._collect(excel)` -> `kw` | Assembles full kwargs dict from all UI vars |
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

## Core helper functions

### In `refraction/core/chart_helpers.py`

| Function | Purpose |
|---|---|
| `_calc_error(vals, error_type)` | Returns (mean, half_width) for SEM/SD/CI95 |
| `_calc_error_asymmetric(vals, error_type)` | Asymmetric error bars for log scale |
| `_style_kwargs(locals())` | Extracts shared style params from locals() dict |
| `_p_to_stars(p)` | Converts p-value to significance stars |
| `_run_stats(groups, ...)` | Runs the specified statistical test |
| `_apply_correction(p_vals, method)` | Bonferroni/Holm/BH correction |
| `_fmt_bar_label(v)` | Format a numeric value for bar top labels |
| `normality_warning(groups, stats_test)` | Returns warning string if non-normal |
| `_cohens_d(a, b)` | Cohen's d effect size |
| `_hedges_g(a, b)` | Hedges' g (bias-corrected effect size) |
| `_km_curve(times, events)` | Kaplan-Meier survival curve |
| `_logrank_test(groups)` | Log-rank test for survival curves |
| `_fit_model(x, y, model_name)` | Curve fitting (linear, polynomial, etc.) |

### In `refraction/core/config.py` (canonical source for constants)

| Symbol | Purpose |
|---|---|
| `PRISM_PALETTE` | 10 default colours matching GraphPad Prism |
| `AXIS_STYLES` | Dict mapping UI labels to axis style keys |
| `TICK_DIRS` | Dict mapping UI labels to tick direction keys |
| `LEGEND_POSITIONS` | Dict mapping UI labels to matplotlib legend positions |
| `PLOT_PARAM_DEFAULTS` | Default values for all shared style parameters |

### In `refraction/specs/theme.py`

| Symbol | Purpose |
|---|---|
| `PRISM_TEMPLATE` | Plotly layout template dict |
| `apply_open_spine(layout)` | Returns layout dict for open-spine style |

### In `refraction/specs/helpers.py`

| Function | Purpose |
|---|---|
| `extract_common_kw(kw)` | Extracts excel_path, sheet, title, xlabel, ytitle, color |
| `read_excel_or_error(path, sheet)` | Returns (df, None) or (None, error_json) |
| `resolve_colors(color, n)` | Resolves color arg to list of n colors |
| `spec_error(msg)` | Returns JSON error string |

---

## Style constants

All style constants are defined in `refraction/core/config.py` and re-exported
from `refraction/core/chart_helpers.py` for backward compatibility.

Key rendering constants:

| Constant | Value | Purpose |
|---|---|---|
| `_DPI` | 144 | Render DPI (retina-grade) |
| `_FONT` | "Arial" | Axis/tick font |
| `_ALPHA_BAR` | 0.85 | Default bar fill alpha |
| `_LABEL_PAD` | 6 | Axis label padding (pts) |
| `_TITLE_PAD` | 8 | Title padding (pts) |
| `_TIGHT_PAD` | 1.2 | fig.tight_layout pad |

All shared style params (axis_style, tick_dir, fig_bg, etc.) live in
`PLOT_PARAM_DEFAULTS` and are extracted by `_style_kwargs(locals())`.
If you add a new universal style param, add it to `PLOT_PARAM_DEFAULTS` --
that is the single change needed.

---

## Excel layout conventions

| Chart type | Row 0 | Row 1 | Rows 2+ |
|---|---|---|---|
| Bar, Box, Violin, Dot, Before/After, Histogram | Group names | -- | Numeric values |
| Line, Scatter, Curve Fit | X-label, Series names | -- | X value, Y replicates |
| Grouped Bar, Stacked Bar | Category names | Subgroup names | Numeric values |
| Kaplan-Meier | Group names (each spans 2 cols) | "Time", "Event" | time, 0/1 |
| Heatmap | blank, Col labels | -- | Row label, numeric values |
| Two-Way ANOVA | `Factor_A`, `Factor_B`, `Value` | -- | one row per observation |
| Contingency | blank, Outcome labels | -- | Group name, counts |
| Chi-Square GoF | Category names | Observed counts | (optional) Expected |
| Forest Plot | Study, Effect, Lower CI, Upper CI | -- | one row per study |
| Bland-Altman | Method A, Method B | -- | paired measurements |
| Pyramid | Category, Left series, Right series | -- | values |

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

## Journal Export

`plotter_export.py` provides publication-quality figure export with presets for
Nature, Science, and Cell journals.

### Journal dimension presets

| Journal | Single col | Double col | Max height | Min font | DPI |
|---------|-----------|------------|------------|----------|-----|
| Nature  | 89 mm      | 183 mm     | 247 mm     | 7 pt     | 300 |
| Science | 55 mm      | 182 mm     | 245 mm     | 7 pt     | 300 |
| Cell    | 85 mm      | 174 mm     | 235 mm     | 7 pt     | 300 |

### Export path priority

1. **kaleido** (primary) -- rebuilds Plotly spec and exports via `plotly.io.write_image()`.
   Supports PNG, SVG, PDF. Enforces journal font family (Arial) and minimum font size.
2. **matplotlib** (fallback) -- resizes `self._fig` and calls `fig.savefig()`.
   Used when kaleido is not installed or spec rebuild fails.
3. **HTML** -- uses Plotly's `fig.write_html()` (no kaleido required).

---

## Phase history

- **Phase 2**: Added 14 infrastructure modules (registry, tabs, presets, session,
  events, undo, comparisons, project files, pzfx import, wiki)
- **Phase 3**: Plotly/FastAPI/Web rendering (4 initial spec builders)
- **Phase 4**: Deployment readiness (Docker, web server, React SPA)
- **Phase 5**: Full web migration (all 29 Plotly spec builders, React SPA rebuild)
- **Phase 6**: Desktop + deployment (PyInstaller, DMG builder)
