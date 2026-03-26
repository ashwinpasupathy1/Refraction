# Refraction

> GraphPad Prism-style scientific plotting and analysis for macOS.
> Built entirely by Claude (Anthropic) with Ashwin Pasupathy.

![Python](https://img.shields.io/badge/python-3.12+-blue)
![Charts](https://img.shields.io/badge/chart%20types-29-orange)
![Version](https://img.shields.io/badge/version-0.1.0-green)

---

## Overview

Refraction brings the familiar workflow of GraphPad Prism to macOS as a native SwiftUI application backed by a Python analysis engine.  Projects are organized into Experiments, each containing Data Tables, Graphs, and Analyses.  Format Graph/Axes dialogs with live preview, render style presets, and a statistical test encyclopedia with LaTeX formulas provide a complete scientific plotting workflow.  Load your data from an Excel spreadsheet, choose a chart type, and get publication-quality figures with full statistical analysis -- all without writing a single line of code.

**Architecture:**

```
SwiftUI app (Experiment → DataTables + Graphs + Analyses)
      |
      v  HTTP (localhost:7331)
      |
FastAPI server  →  Dedicated analyzers  →  Pure stats
  /render, /analyze      analysis/*.py        core/stats.py
```

The Python backend is a pure analysis engine with no rendering dependencies.  15+ chart types have dedicated analyzers; statistical computation lives in `refraction/core/stats.py`.  The SwiftUI frontend renders charts natively via Core Graphics.  See **SWIFT_UI.md** for the full client architecture and **CLAUDE.md** for project context.

---

## Quick Start

```bash
# Install Python dependencies
pip3 install -e .

# Run tests
python3 run_all.py

# Start the API server (for development)
python3 -m refraction.server.web_entry

# Open the macOS app
open RefractionApp/ in Xcode
```

---

## Features

- **29 chart types** -- from bar charts to Kaplan-Meier survival curves and forest plots, each with a dedicated analyzer
- **Experiment-based project organization** -- Experiments contain Data Tables, Graphs, and Analyses (Prism-style hierarchy)
- **Native macOS app** -- SwiftUI with Core Graphics rendering, no web views or third-party charting
- **Format Graph/Axes dialogs** -- Prism-style formatting with live preview
- **Render style presets** -- Default, Prism, ggplot2, Matplotlib looks with one click
- **Statistical engine** -- parametric, nonparametric, paired, and permutation tests with posthoc methods
- **Stats Wiki** -- encyclopedia of statistical tests with LaTeX formulas
- **Publication-ready** -- journal export presets (Nature/Science/Cell) with DPI/format/size options
- **Debug console** -- API trace and engine log viewer for development
- **Architecture reference guide** -- built-in codebase documentation
- **Zoom controls** -- 0.25x to 4.0x chart zoom
- **`.refract` project files** -- portable project archives with embedded data
- **Excel-native data model** -- validates spreadsheet layout before analysis
- **FastAPI backend** -- `/analyze` and `/render` endpoints return renderer-independent results
- **Sample datasets** -- included for quick exploration

---

## Supported Chart Types

### Categorical / Distribution
Bar Chart, Grouped Bar, Stacked Bar, Box Plot, Violin Plot, Dot Plot,
Subcolumn Scatter, Before/After, Repeated Measures

### Regression / Correlation
Scatter Plot, Line Graph, Curve Fit, Bubble Chart

### Epidemiology / Clinical
Survival Curve (Kaplan-Meier), Bland-Altman, Forest Plot

### Statistical Tests
Histogram, ECDF, Q-Q Plot, Column Statistics, Two-Way ANOVA,
Contingency, Chi-Square GoF

### Other
Heatmap, Area Chart, Raincloud, Lollipop, Waterfall, Pyramid

---

## Data Format

All charts read from a single Excel file (`.xlsx`).  The expected layout depends on the chart type:

| Chart family | Row 0 | Rows 1+ |
|---|---|---|
| Bar, Box, Violin, Dot | Group names | Numeric values |
| Line, Scatter, Curve Fit | X-label + series names | X value, Y replicates |
| Grouped Bar, Stacked Bar | Category names (row 0) + subgroup names (row 1) | Values |
| Kaplan-Meier | Group names (each spanning 2 columns) | Time, event (0/1) |
| Heatmap | Blank + column labels | Row label + values |

The analysis engine validates your spreadsheet layout and returns specific error messages if the format is unexpected.

---

## API

The FastAPI server exposes these endpoints:

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Liveness check |
| `/chart-types` | GET | List all 29 supported chart types |
| `/analyze` | POST | Run analysis on uploaded data (flat dict) |
| `/render` | POST | Bridge for SwiftUI (nested ChartSpec JSON) |
| `/upload` | POST | Accept .xlsx/.xls/.csv file |
| `/sheet-list` | POST | List sheet names in an Excel file |
| `/validate-table` | POST | Validate spreadsheet layout |
| `/render-latex` | POST | Render LaTeX formula to PNG |
| `/data-preview` | POST | Preview spreadsheet contents |
| `/recommend-test` | POST | Suggest appropriate statistical test |
| `/analyze-stats` | POST | Run stats-only analysis |
| `/analyze-layout` | POST | Detect data layout, recommend chart types |
| `/curve-models` | GET | List curve fitting models |
| `/curve-fit` | POST | Fit a model to X/Y data |
| `/transforms` | GET | List available column transforms |
| `/transform` | POST | Apply a transform to a column |
| `/project/save-refract` | POST | Save .refract project archive |
| `/project/save` | POST | Save project (legacy) |
| `/project/load` | POST | Load .refract project archive |

### POST /analyze

```json
{
  "chart_type": "bar",
  "excel_path": "/path/to/data.xlsx",
  "config": {
    "error_type": "sem",
    "stats_test": "parametric",
    "title": "Drug Treatment"
  }
}
```

Returns descriptive statistics (mean, median, SD, SEM, CI95) per group,
plus pairwise statistical comparisons with p-values and significance stars.

---

## Project Structure

```
refraction/
  analysis/         Analysis engine (dedicated analyzers per chart type)
  core/             Stats, validators, registry, types, config
  io/               Export presets, .pzfx import, .refract projects
  server/           FastAPI server (/analyze, /render, /upload, etc.)

RefractionApp/      SwiftUI macOS application (Experiment → DataTables + Graphs + Analyses)
RefractionRenderer/ Swift Package for Core Graphics chart rendering
tests/              Python test suites (767 tests)
run_all.py          Unified test runner
```

---

## Development

```bash
# Run the full test suite
python3 run_all.py

# Run a single suite
python3 run_all.py stats              # statistical verification
python3 run_all.py validators         # spreadsheet validators
python3 run_all.py api                # FastAPI endpoint tests
python3 run_all.py engine             # pure computation tests
python3 run_all.py integration        # API + pipeline tests
python3 run_all.py analysis           # dedicated analyzer tests
python3 run_all.py stats_exhaustive   # exhaustive stats coverage
python3 run_all.py deficiency         # deficiency fix verification
python3 run_all.py render             # render contract tests
python3 run_all.py qa                 # QA regression tests

# Quick import check
python3 -c "from refraction.analysis import analyze; print('OK')"
```

---

## Credits

Built entirely by [Claude](https://claude.ai) (Anthropic) in collaboration with Ashwin Pasupathy.
