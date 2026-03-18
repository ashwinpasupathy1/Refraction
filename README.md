# Claude Plotter

> A GraphPad Prism-style scientific plotting application for macOS — built entirely by Claude (Anthropic) with Ashwin Pasupathy.

![Platform](https://img.shields.io/badge/platform-macOS-lightgrey?logo=apple)
![Python](https://img.shields.io/badge/python-3.9%2B-blue?logo=python&logoColor=white)
![Tests](https://img.shields.io/badge/tests-520%20passing-brightgreen)
![Charts](https://img.shields.io/badge/chart%20types-29-orange)
![Status](https://img.shields.io/badge/status-active-success)

---

## Overview

Claude Plotter is a fully-featured desktop application that brings the familiar workflow of GraphPad Prism to macOS. Load your data from an Excel spreadsheet, choose a chart type, tweak your style parameters, and generate publication-quality figures — all without writing a single line of code.

The application is built on Python + Tkinter for the UI, Matplotlib for rendering, and a bespoke `tk.Canvas` live renderer for interactive bar charts that respond to clicks, colour changes, and drag gestures in real time.

---

## Features

- **29 chart types** — from simple bar charts to Kaplan-Meier survival curves and forest plots
- **Live canvas renderer** — bar and grouped-bar charts render natively on `tk.Canvas` with interactive hit-testing, recolouring, and Y-axis drag
- **Publication-ready output** — 144 DPI renders, open/closed/floating spine styles, configurable tick directions, gridlines, and font sizes
- **Statistical overlays** — significance brackets, error bars (SEM, SD, 95% CI), jitter points, and posthoc corrections
- **Excel-native data model** — paste data directly from Prism, Excel, or Numbers; the app validates your layout before plotting
- **Multiple file formats** — `.xlsx`, `.xls` for data; `.cplot` project files; `.pzfx` GraphPad import
- **Style presets** — 5 built-in presets (Classic, Publication, Presentation, Minimal, Dark) + save your own
- **Session persistence** — settings saved automatically; resume exactly where you left off
- **Undo/redo** — Cmd+Z / Cmd+Shift+Z for all plot parameter changes
- **Statistical wiki** — built-in reference for all 29 chart types with formulas and citations
- **Results panel** — summary statistics, exportable as CSV or copied as TSV for pasting into other apps
- **Fully modular architecture** — 19 focused Python modules with zero circular dependencies

---

## Quick Start

### Requirements

```bash
pip install matplotlib numpy pandas scipy seaborn openpyxl
```

Python 3.9 or later is required. A macOS display is required to run the GUI.

### Launch

```bash
# From the terminal
python3 plotter_barplot_app.py

# Or double-click PrismBarplot.app in Finder
# (macOS may prompt you to allow it on first launch)
```

> **Gatekeeper blocked the app?**
> Right-click → Open → "Open anyway", or run:
> ```bash
> xattr -cr PrismBarplot.app
> ```

---

## Chart Types

Claude Plotter supports 29 chart types across a wide range of scientific use cases.

### Categorical / Distribution

| Chart | Description |
|---|---|
| **Bar Chart** | Mean ± error bar per group; supports SEM, SD, 95% CI |
| **Grouped Bar** | Side-by-side bars for two-factor designs |
| **Stacked Bar** | Proportional or absolute stacked bars |
| **Box Plot** | Median, IQR, whiskers, and outlier points |
| **Violin Plot** | Full distribution shape per group |
| **Dot Plot** | Each observation as a coloured dot, jittered or aligned |
| **Subcolumn Scatter** | Individual points overlaid on group column |
| **Before / After** | Paired measurements connected by lines |
| **Repeated Measures** | Multi-timepoint within-subject data |

### Regression / Correlation

| Chart | Description |
|---|---|
| **Scatter Plot** | XY scatter with optional best-fit line |
| **Line Graph** | Connected XY data, multiple series |
| **Curve Fit** | Nonlinear curve fitting (8 built-in models) |
| **Bubble Chart** | XY scatter with a third variable encoded as bubble size |

### Epidemiology / Clinical

| Chart | Description |
|---|---|
| **Survival Curve** | Kaplan-Meier with log-rank test |
| **Bland-Altman** | Method comparison; limits of agreement |
| **Forest Plot** | Meta-analysis effect sizes with CI |

### Statistical Tests

| Chart | Description |
|---|---|
| **Histogram** | Frequency or density distribution |
| **ECDF** | Empirical cumulative distribution function |
| **Q-Q Plot** | Quantile-quantile normality assessment |
| **Column Statistics** | Descriptive stats table per group |
| **Two-Way ANOVA** | Interaction plot from long-format data |
| **Contingency** | Grouped count data; chi-square or Fisher's |
| **Chi-Sq GoF** | Goodness-of-fit against expected proportions |

### Other

| Chart | Description |
|---|---|
| **Heatmap** | Colour-coded matrix with optional clustering |
| **Area Chart** | Filled line chart, stacked or overlapping |
| **Raincloud** | Half-violin + jitter + box summary |
| **Lollipop** | Dot-and-stem alternative to bar charts |
| **Waterfall** | Cumulative change, positive/negative coloured |
| **Pyramid** | Back-to-back horizontal bars (e.g. population) |

---

## Data Format

All charts read from a single Excel file (`.xlsx`). The expected layout depends on the chart type:

| Chart family | Row 0 | Rows 1+ |
|---|---|---|
| Bar, Box, Violin, Dot, Before/After | Group names | Numeric values (one per cell) |
| Line, Scatter, Curve Fit | X-label + series names | X value, then Y replicates |
| Grouped Bar, Stacked Bar | Category names (row 0) + subgroup names (row 1) | Numeric values |
| Kaplan-Meier | Group names (each spanning 2 columns) | Time value, event indicator (0/1) |
| Heatmap | Blank cell + column labels | Row label + numeric values |
| Two-Way ANOVA | `Factor_A`, `Factor_B`, `Value` (headers) | One observation per row |
| Contingency | Blank + outcome labels | Group name + counts |
| Forest Plot | `Study`, `Effect`, `Lower CI`, `Upper CI` | One study per row |
| Bland-Altman | Method A name, Method B name | Paired measurements |

The app validates your spreadsheet layout before plotting and shows specific error messages if the format is unexpected.

---

## Architecture

Claude Plotter is split into 19 focused modules with no circular dependencies.

```
# Core
plotter_barplot_app.py      6,637 lines   App class, sidebar, all UI
plotter_functions.py        6,553 lines   29 Matplotlib chart functions
plotter_widgets.py            952 lines   Design-system tokens, PButton/PEntry/etc.
plotter_validators.py         518 lines   Standalone spreadsheet validators
plotter_results.py            401 lines   Results panel: populate / export / copy

# Phase 2 infrastructure
plotter_registry.py           475 lines   PlotTypeConfig chart registry
plotter_tabs.py               532 lines   Multi-tab state management
plotter_app_icons.py          352 lines   Sidebar icon drawing
plotter_presets.py            163 lines   Style preset system
plotter_session.py             77 lines   Session persistence
plotter_events.py              75 lines   EventBus pub/sub
plotter_types.py              121 lines   Shared type definitions
plotter_undo.py               131 lines   Undo/redo stack
plotter_errors.py              99 lines   Structured error reporting
plotter_comparisons.py        248 lines   Custom comparison builder
plotter_project.py            207 lines   .cplot project files (ZIP)
plotter_import_pzfx.py        316 lines   GraphPad .pzfx importer
plotter_wiki_content.py     2,224 lines   Statistical wiki content
plotter_app_wiki.py           522 lines   Wiki popup viewer
```

### Rendering pipeline

```
User clicks "Generate Plot"
        │
        ▼
App._do_run()  [background thread]
  calls plotter_functions.prism_<chart_type>(**kwargs)
  returns (fig, ax)
        │
        ▼
App._embed_plot()  [main thread, via after(0)]
  ┌─ canvas mode + bar/grouped_bar? ──────────────────────────────┐
  │  YES → App._try_canvas_embed()                                │
  │         builds BarScene / GroupedBarScene                     │
  │         CanvasRenderer / GroupedCanvasRenderer                │
  │         live hit-test, recolour, Y-drag, bar-width drag       │
  └─ NO  → FigureCanvasTkAgg(fig)  (standard Agg path)  ─────────┘
```

### Dependency graph

```
plotter_barplot_app.py
  ├── plotter_widgets.py          (pure Tk + constants — no prism deps)
  ├── plotter_validators.py       (pure pandas — no prism deps)
  ├── plotter_results.py          (accepts app object; no other prism imports)
  ├── plotter_functions.py        (numpy / pandas / matplotlib / scipy — lazy)
  └── plotter_canvas_renderer.py  (numpy / pandas — no matplotlib)
```

---

## Test Suite

438 tests across 5 suites, running in ~52 seconds on a modern Mac.

```bash
# Run everything
python3 run_all.py

# Run a specific suite
python3 run_all.py comprehensive      # 175 tests — all 0 chart types
python3 run_all.py canvas_renderer    # 109 tests — tk.Canvas renderer
python3 run_all.py modular            #  74 tests — widgets / validators / results
python3 run_all.py p1p2p3             #  60 tests — style parameter regressions
python3 run_all.py control            #  20 tests — control-group statistics
```

All 438 tests must pass before any commit. If tests regress, fix them before doing anything else.

---

## Development

### Quick syntax check

```bash
python3 -c "import plotter_functions, plotter_canvas_renderer, plotter_widgets, plotter_validators, plotter_results; print('OK')"
```

### Adding a new chart type

The process follows a five-step checklist:

1. **Write the plot function** in `plotter_functions.py`
2. **Register it** in `_REGISTRY_SPECS` inside `plotter_barplot_app.py`
3. **Add UI controls** (if the chart needs custom options beyond the standard tabs)
4. **Add a validator** in `plotter_validators.py`
5. **Write tests** in `test_comprehensive.py`

See `CLAUDE.md` for the full detailed checklist with code templates.

### Commit conventions

```
feat: add lollipop chart and wire into sidebar
fix: correct y-axis drag clamping for zero-mean data
test: add 8 ECDF validator tests
refactor: extract prism_export.py from barplot_app
docs: update README with pyramid chart layout
```

---

## Credits

Built entirely by [Claude](https://claude.ai) (Anthropic) in collaboration with Ashwin Pasupathy across 13 sessions.
