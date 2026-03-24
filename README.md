# Refraction

> GraphPad Prism-style scientific plotting and analysis for macOS.
> Built entirely by Claude (Anthropic) with Ashwin Pasupathy.

![Python](https://img.shields.io/badge/python-3.12+-blue)
![Charts](https://img.shields.io/badge/chart%20types-29-orange)
![Version](https://img.shields.io/badge/version-0.1.0-green)

---

## Overview

Refraction brings the familiar workflow of GraphPad Prism to macOS as a native SwiftUI application backed by a Python analysis engine.  Load your data from an Excel spreadsheet, choose a chart type, and get publication-quality figures with full statistical analysis -- all without writing a single line of code.

**Architecture:**

```
SwiftUI app (RefractionApp/)  <-->  FastAPI server  <-->  Analysis engine
      Charts framework                /analyze            refraction.analysis
      Native macOS UI                 /upload             refraction.core
                                      /health
```

The Python backend is a pure analysis engine with no rendering dependencies.  The SwiftUI frontend handles all chart rendering via Apple's Charts framework.

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

- **29 chart types** -- from bar charts to Kaplan-Meier survival curves and forest plots
- **Native macOS app** -- SwiftUI with Apple Charts framework
- **Statistical engine** -- parametric, nonparametric, paired, and permutation tests
- **Publication-ready** -- journal export presets for Nature, Science, and Cell
- **Excel-native data model** -- validates your spreadsheet layout before analysis
- **FastAPI backend** -- `/analyze` endpoint returns renderer-independent results
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
| `/analyze` | POST | Run analysis on uploaded data |
| `/upload` | POST | Accept .xlsx/.xls/.csv file |

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
  analysis/         Analysis engine (analyze function)
  core/             Stats, validators, registry, types, config
  io/               Export presets, .pzfx import, .cplot projects
  server/           FastAPI server with /analyze endpoint

RefractionApp/      SwiftUI macOS application
tests/              Python test suites (118 tests)
run_all.py          Unified test runner
```

---

## Development

```bash
# Run the full test suite
python3 run_all.py

# Run a single suite
python3 run_all.py stats        # statistical verification
python3 run_all.py validators   # spreadsheet validators
python3 run_all.py specs        # analysis engine tests
python3 run_all.py api          # FastAPI endpoint tests

# Quick import check
python3 -c "from refraction.analysis import analyze; print('OK')"
```

---

## Credits

Built entirely by [Claude](https://claude.ai) (Anthropic) in collaboration with Ashwin Pasupathy.
