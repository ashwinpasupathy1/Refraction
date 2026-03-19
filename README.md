# Spectra

> A publication-quality scientific plotting application for macOS — built entirely by Claude (Anthropic) with Ashwin Pasupathy.

![Tests](https://img.shields.io/badge/tests-531%20total%20·%20522%20core-brightgreen)
![Python](https://img.shields.io/badge/python-3.12+-blue)
![Charts](https://img.shields.io/badge/chart%20types-29-orange)
![Status](https://img.shields.io/badge/status-active-success)
![Lines](https://img.shields.io/badge/lines%20of%20code-27%2C300+-lightgrey)

---

![Spectra screenshot](assets/screenshot.png)

<!-- Screenshot placeholder — will be filled in with an actual app screenshot -->

---

## Overview

Spectra is a fully-featured scientific plotting application for macOS. Load your data from an Excel spreadsheet, choose a chart type, tweak your style parameters, and generate publication-quality figures — all without writing a single line of code.

The application runs in two modes:
- **Desktop**: Python + Tkinter UI with a pywebview panel for interactive Plotly charts
- **Web**: React SPA + FastAPI backend, deployable anywhere (Docker, cloud, etc.)

Both modes share the same Python business logic and FastAPI server.

---

## Quick Start

```bash
# Desktop (requires display)
pip install -r requirements.txt
python3 plotter_barplot_app.py
# Note: the main desktop entry point is being renamed to plotter_desktop.py

# Web server (no display required)
pip install -r requirements-web.txt
cd plotter_web && npm install && npm run build && cd ..
python3 plotter_web_server.py
# Open http://localhost:7331

# Docker
docker build -t spectra .
docker run -p 7331:7331 spectra
```

---

## Features

- **29 chart types** — from simple bar charts to Kaplan-Meier survival curves and forest plots
- **Plotly.js interactive charts** — bar, grouped bar, line, and scatter render via Plotly with editable titles and axes
- **FastAPI backend** — runs as desktop app or standalone web service
- **React SPA frontend** — Vite + TypeScript + Plotly.js
- **Docker deployment** — single Dockerfile for production web deployment
- **Live canvas renderer** — bar and grouped-bar charts render natively on `tk.Canvas` with interactive hit-testing, recolouring, and Y-axis drag
- **Publication-ready output** — 144 DPI renders, open/closed/floating spine styles, configurable tick directions, gridlines, and font sizes
- **Statistical overlays** — significance brackets, error bars (SEM, SD, 95% CI), jitter points, and posthoc corrections
- **Excel-native data model** — paste data directly from Excel or Numbers; the app validates your layout before plotting
- **Style presets** — 5 built-in presets (Classic, Publication, Presentation, Minimal, Dark) + save your own
- **Session persistence** — settings saved automatically; resume exactly where you left off
- **Undo/redo** — Cmd+Z / Cmd+Shift+Z for all plot parameter changes
- **Statistical wiki** — built-in reference for all 29 chart types with formulas and citations
- **Results panel** — summary statistics, exportable as CSV or copied as TSV for pasting into other apps
- **Fully modular architecture** — 30+ focused Python modules with zero circular dependencies

---

## Supported File Formats

| Format | Read | Write |
|--------|------|-------|
| .xlsx / .xls | Yes | — |
| .cplot (Spectra Project) | Yes | Yes |
| .pzfx (Prism format) | Yes (import) | — |

---

## Chart Types

Spectra supports **29 chart types** across a wide range of scientific use cases.

### Categorical / Distribution

| Chart | Description |
|---|---|
| **Bar Chart** | Mean +/- error bar per group; supports SEM, SD, 95% CI |
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

```
Desktop mode:   Tk shell -> pywebview -> React SPA -> FastAPI (127.0.0.1:7331)
Web mode:       Browser -> React SPA -> FastAPI (0.0.0.0:7331)
Both modes:     same Python business logic, same FastAPI server
```

Spectra is split into 30+ focused Python modules (~27,300 lines) with no circular dependencies.

```
# Core application
plotter_barplot_app.py      6,688 lines   App class, sidebar, all UI
plotter_functions.py        6,553 lines   29 Matplotlib chart functions + stats
plotter_widgets.py            952 lines   Design-system tokens, PButton/PEntry/etc.
plotter_validators.py         518 lines   Standalone spreadsheet validators
plotter_results.py            401 lines   Results panel: populate / export / copy

# Phase 2 — Infrastructure
plotter_registry.py           475 lines   PlotTypeConfig chart registry
plotter_tabs.py               532 lines   Multi-tab state management
plotter_app_icons.py          352 lines   Sidebar icon drawing (29 chart types)
plotter_presets.py            163 lines   Style preset system
plotter_session.py             77 lines   Session persistence
plotter_events.py              75 lines   EventBus pub/sub
plotter_types.py              121 lines   Shared type definitions / dataclasses
plotter_undo.py               131 lines   Undo/redo stack
plotter_errors.py              99 lines   Structured error reporting
plotter_comparisons.py        248 lines   Custom comparison builder
plotter_project.py            207 lines   .cplot project files (ZIP)
plotter_import_pzfx.py        316 lines   Prism .pzfx file importer
plotter_wiki_content.py     2,224 lines   Statistical wiki content (29 sections)
plotter_app_wiki.py           522 lines   Wiki popup viewer

# Phase 3 — Plotly / FastAPI
plotter_server.py             183 lines   FastAPI server + auth middleware
plotter_webview.py            179 lines   pywebview wrapper for desktop mode
plotter_plotly_theme.py        51 lines   Plotly theme constants
plotter_spec_bar.py            67 lines   Bar chart Plotly spec builder
plotter_spec_grouped_bar.py    57 lines   Grouped bar Plotly spec builder
plotter_spec_line.py           55 lines   Line graph Plotly spec builder
plotter_spec_scatter.py        58 lines   Scatter plot Plotly spec builder

# Phase 4 — Deployment
plotter_web_server.py          49 lines   Standalone web server entry point
plotter_web/                              React SPA (Vite + TypeScript + Plotly.js)
Dockerfile                                Docker deployment config
```

---

## Test Suite

430 tests across 5 suites.

```bash
# Run everything
python3 run_all.py

# Run a specific suite
python3 run_all.py comprehensive      # 309 tests — all chart types + stats engine
python3 run_all.py stats              #  57 tests — statistical verification + control logic
python3 run_all.py validators         #  35 tests — spreadsheet validators
python3 run_all.py specs              #  11+ tests — Plotly spec builders + server (needs plotly)
python3 run_all.py api                #  18 tests — FastAPI endpoint tests
```

All suites must pass before any commit. The `specs` suite requires the `plotly` package.

---

## Development

### Quick syntax check

```bash
python3 -c "import plotter_functions, plotter_widgets, plotter_validators, plotter_results, plotter_registry, plotter_tabs, plotter_app_icons, plotter_presets, plotter_session, plotter_events, plotter_types, plotter_undo, plotter_errors, plotter_comparisons, plotter_project, plotter_import_pzfx, plotter_wiki_content, plotter_app_wiki, plotter_server, plotter_web_server; print('OK')"
```

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

Built entirely by [Claude](https://claude.ai) (Anthropic) in collaboration with Ashwin Pasupathy.
