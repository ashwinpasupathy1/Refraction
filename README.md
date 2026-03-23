# Refraction

> A scientific plotting application for macOS — built entirely by Claude (Anthropic) with Ashwin Pasupathy.

![Python](https://img.shields.io/badge/python-3.12+-blue)
![Charts](https://img.shields.io/badge/chart%20types-29-orange)
![Tests](https://img.shields.io/badge/tests-430%20passing-brightgreen)
![Status](https://img.shields.io/badge/status-active-success)

---

## Overview

Refraction is a desktop scientific plotting application for macOS. Load data from an Excel spreadsheet, select a chart type, configure style and statistics, and export publication-quality figures in the correct dimensions for Nature, Science, or Cell.

The app uses a Tkinter shell with a pywebview panel for interactive Plotly charts. Matplotlib is retained as a fallback for environments where Plotly/kaleido is unavailable.

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Launch
python3 plotter_barplot_app.py
```

---

## Features

- **29 chart types** — bar, box, violin, scatter, Kaplan-Meier, forest plot, and more
- **Interactive Plotly charts** — rendered via pywebview with editable titles and axes
- **Journal export** — one-click export at correct dimensions for Nature, Science, or Cell using kaleido (PNG/SVG/PDF) or HTML for interactive sharing
- **Statistical overlays** — significance brackets, error bars (SEM, SD, 95% CI), posthoc corrections
- **Excel-native data model** — paste data from Excel; the app validates layout before plotting
- **Style presets** — 5 built-in presets (Classic, Publication, Presentation, Minimal, Dark) + save your own
- **Session persistence** — settings auto-saved; resume where you left off
- **Undo/redo** — Cmd+Z / Cmd+Shift+Z
- **Statistical wiki** — built-in reference with formulas and textbook citations for all 29 chart types
- **Results panel** — summary statistics exportable as CSV

---

## Export

The **Export Figure** dialog (Cmd+E) offers:

| Format | Engine | Use case |
|--------|--------|----------|
| PNG (high-res) | kaleido / matplotlib | Submission to journals |
| SVG | kaleido | Editing in Illustrator/Inkscape |
| PDF | kaleido | Print-ready figures |
| HTML | Plotly | Interactive sharing |

**Journal presets** automatically set width, height, DPI, and font family:

| Journal | Single column | Double column | Min font | DPI |
|---------|--------------|---------------|----------|-----|
| Nature  | 89 mm        | 183 mm        | 7 pt     | 300 |
| Science | 55 mm        | 182 mm        | 7 pt     | 300 |
| Cell    | 85 mm        | 174 mm        | 7 pt     | 300 |

---

## Chart Types

### Categorical / Distribution

| Chart | Description |
|---|---|
| Bar Chart | Mean ± error bar; SEM, SD, or 95% CI |
| Grouped Bar | Side-by-side bars for two-factor designs |
| Stacked Bar | Proportional or absolute stacked bars |
| Box Plot | Median, IQR, whiskers, outlier points |
| Violin Plot | Full distribution shape per group |
| Dot Plot | Each observation as a coloured dot |
| Subcolumn Scatter | Individual points overlaid on group column |
| Before / After | Paired measurements connected by lines |
| Repeated Measures | Multi-timepoint within-subject data |

### Regression / Correlation

| Chart | Description |
|---|---|
| Scatter Plot | XY scatter with optional best-fit line |
| Line Graph | Connected XY data, multiple series |
| Curve Fit | Nonlinear curve fitting (8 built-in models) |
| Bubble Chart | XY scatter with bubble size as third variable |

### Epidemiology / Clinical

| Chart | Description |
|---|---|
| Survival Curve | Kaplan-Meier with log-rank test |
| Bland-Altman | Method comparison; limits of agreement |
| Forest Plot | Meta-analysis effect sizes with CI |

### Statistical Tests

| Chart | Description |
|---|---|
| Histogram | Frequency or density distribution |
| ECDF | Empirical cumulative distribution function |
| Q-Q Plot | Quantile-quantile normality assessment |
| Column Statistics | Descriptive stats table per group |
| Two-Way ANOVA | Interaction plot from long-format data |
| Contingency | Grouped count data; chi-square or Fisher's |
| Chi-Sq GoF | Goodness-of-fit against expected proportions |

### Other

| Chart | Description |
|---|---|
| Heatmap | Colour-coded matrix with optional clustering |
| Area Chart | Filled line chart, stacked or overlapping |
| Raincloud | Half-violin + jitter + box |
| Lollipop | Dot-and-stem alternative to bar charts |
| Waterfall | Cumulative change, signed colouring |
| Pyramid | Back-to-back horizontal bars (e.g. population) |

---

## Data Format

All charts read from `.xlsx`. Expected layout:

| Chart family | Row 0 | Rows 1+ |
|---|---|---|
| Bar, Box, Violin, Dot, Before/After | Group names | Numeric values |
| Line, Scatter, Curve Fit | X-label + series names | X value, then Y replicates |
| Grouped Bar, Stacked Bar | Category names (row 0) + subgroup names (row 1) | Numeric values |
| Kaplan-Meier | Group names (2 cols each) | Time value, event indicator (0/1) |
| Heatmap | Blank + column labels | Row label + numeric values |
| Two-Way ANOVA | `Factor_A`, `Factor_B`, `Value` (headers) | One observation per row |
| Forest Plot | `Study`, `Effect`, `Lower CI`, `Upper CI` | One study per row |
| Bland-Altman | Method A name, Method B name | Paired measurements |

---

## Architecture

```
Desktop mode: Tkinter shell → pywebview panel → Plotly.js (interactive render)
Export:       Plotly spec → kaleido → PNG / SVG / PDF  (or matplotlib fallback)
Stats:        plotter_functions.py (scipy / pingouin) — shared by both paths
```

### Module map

```
# Entry points
plotter_barplot_app.py      Main desktop app (Tkinter + pywebview)
plotter_desktop.py          Alternate desktop entry (pywebview + FastAPI)
plotter_web_server.py       Standalone web server (no Tk)

# Core logic
plotter_functions.py        29 matplotlib chart functions + statistical tests
plotter_validators.py       Spreadsheet layout validators (one per chart type)
plotter_results.py          Results panel: summary stats, CSV export
plotter_export.py           Journal export presets (Nature/Science/Cell) + kaleido

# Infrastructure
plotter_registry.py         Chart type registry (PlotTypeConfig, 29 entries)
plotter_widgets.py          Design-system tokens, PButton/PEntry/PCheckbox etc.
plotter_tabs.py             Multi-tab state management
plotter_app_icons.py        Sidebar icon drawing (29 chart types)
plotter_types.py            Shared dataclasses (ChartData)
plotter_presets.py          Style preset load/save (.json)
plotter_session.py          Session persistence
plotter_events.py           EventBus pub/sub
plotter_undo.py             Undo/redo stack
plotter_errors.py           Structured error reporting
plotter_comparisons.py      Custom comparison builder
plotter_project.py          .cplot project files (ZIP)
plotter_import_pzfx.py      GraphPad Prism .pzfx importer
plotter_wiki_content.py     Statistical wiki (29 sections, textbook citations)
plotter_app_wiki.py         Wiki popup viewer

# Plotly rendering
plotter_server.py           FastAPI server + spec routing
plotter_webview.py          pywebview wrapper for desktop mode
plotter_plotly_theme.py     PRISM_TEMPLATE and PRISM_PALETTE constants
plotter_spec_bar.py         Bar chart Plotly spec builder
plotter_spec_grouped_bar.py ...  (one file per chart type — 29 total)

# Deployment
Dockerfile                  Docker config for web server deployment
requirements.txt            Desktop dependencies (includes kaleido)
requirements-web.txt        Web-only dependencies (no Tk/matplotlib)
setup.sh                    One-command setup
build_app.sh                PyInstaller + optional DMG builder
```

---

## Test Suite

```bash
python3 run_all.py                    # run all 5 suites

python3 run_all.py comprehensive      # 309 tests — chart functions + stats engine
python3 run_all.py stats              #  57 tests — statistical verification
python3 run_all.py validators         #  35 tests — spreadsheet validators
python3 run_all.py specs              #  11 tests — Plotly spec builders + server
python3 run_all.py api                #  18 tests — FastAPI endpoints
```

All suites must pass before any commit.

---

## Development

```bash
# Quick syntax check
python3 -c "import plotter_functions, plotter_widgets, plotter_validators, \
plotter_results, plotter_registry, plotter_tabs, plotter_app_icons, \
plotter_presets, plotter_session, plotter_events, plotter_types, \
plotter_undo, plotter_errors, plotter_comparisons, plotter_project, \
plotter_import_pzfx, plotter_wiki_content, plotter_app_wiki, \
plotter_server, plotter_export; print('OK')"
```

### Commit conventions

```
feat: add lollipop chart and wire into sidebar
fix: correct y-axis drag clamping for zero-mean data
test: add 8 ECDF validator tests
refactor: extract plotter_export.py from barplot_app
docs: update README with export format table
```

---

## Credits

Built entirely by [Claude](https://claude.ai) (Anthropic) in collaboration with Ashwin Pasupathy.
