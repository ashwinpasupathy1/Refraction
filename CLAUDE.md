# Refraction -- Project Context for Claude Code

GraphPad Prism-style scientific plotting and analysis for macOS.
Built entirely by Claude (Anthropic) with Ashwin Pasupathy.

---

## The one rule before every commit

```bash
python3 run_all.py   # must print 0 failures
```

Never commit if tests fail.  Never skip it.

---

## Commands

```bash
# Run the full test suite (4 suites, ~3 seconds)
python3 run_all.py

# Run a single suite
python3 run_all.py stats              # 56 tests -- statistical verification
python3 run_all.py validators         # 35 tests -- spreadsheet validators
python3 run_all.py specs              # 13 tests -- analysis engine + server
python3 run_all.py api                # 16 tests -- FastAPI endpoint tests

# Start the API server
python3 -m refraction.server.web_entry

# Quick import check
python3 -c "from refraction.analysis import analyze; print('OK')"
```

---

## File map

```
# -- Analysis engine -----------------------------------------------
refraction/analysis/__init__.py       Exports analyze()
refraction/analysis/engine.py         Core analyze() function

# -- Core library --------------------------------------------------
refraction/core/chart_helpers.py      Stats, palettes, helper functions
refraction/core/validators.py         Spreadsheet validators
refraction/core/registry.py           PlotTypeConfig chart registry
refraction/core/tabs.py               TabState dataclass
refraction/core/errors.py             ErrorReporter + logging
refraction/core/presets.py            Style preset load/save
refraction/core/session.py            Session persistence
refraction/core/undo.py               UndoStack for undo/redo

# -- I/O -----------------------------------------------------------
refraction/io/export.py               Journal export presets (Nature/Science/Cell)
refraction/io/import_pzfx.py          GraphPad .pzfx file importer
refraction/io/project.py              .cplot project files (ZIP)

# -- Server --------------------------------------------------------
refraction/server/api.py              FastAPI: /analyze, /upload, /health, /chart-types
refraction/server/web_entry.py        Standalone server entry point

# -- SwiftUI app ---------------------------------------------------
RefractionApp/                        macOS SwiftUI application (Xcode project)

# -- Sample data ---------------------------------------------------
RefractionApp/Refraction/Resources/SampleData/
  drug_treatment.xlsx                 3 groups, 8 values each
  time_series.xlsx                    X + 2 Y series
  survival_data.xlsx                  2 groups, time/event

# -- Tests ---------------------------------------------------------
tests/plotter_test_harness.py         Shared test bootstrap + fixtures
run_all.py                            4-suite unified test runner
tests/test_stats.py                   Statistical verification (56 tests)
tests/test_validators.py              Spreadsheet validator tests (35 tests)
tests/test_phase3_plotly.py           Analysis engine tests (13 tests)
tests/test_api.py                     FastAPI endpoint tests (16 tests)
```

---

## Architecture

```
SwiftUI app (RefractionApp/)
    |
    v  HTTP (localhost:7331)
    |
FastAPI server (refraction/server/api.py)
    |
    v
Analysis engine (refraction/analysis/engine.py)
    |
    v
Core library (refraction/core/chart_helpers.py)
    |-- _run_stats()    statistical tests
    |-- _calc_error()   descriptive statistics
    |-- PRISM_PALETTE   color constants
```

The Python backend is a pure analysis engine.  It reads Excel data,
computes descriptive statistics and runs statistical tests, and returns
plain dicts.  The SwiftUI frontend handles all chart rendering via
Apple's Charts framework.

### Key API endpoint: POST /analyze

```json
Request:
{
  "chart_type": "bar",
  "excel_path": "/path/to/data.xlsx",
  "config": {
    "error_type": "sem",
    "stats_test": "parametric",
    "posthoc": "Tukey HSD",
    "mc_correction": "Holm-Bonferroni",
    "control": null,
    "title": "My Chart",
    "x_label": "",
    "y_label": ""
  }
}

Response:
{
  "ok": true,
  "chart_type": "bar",
  "groups": [
    {"name": "Control", "mean": 5.0, "median": 5.1, "sd": 1.2,
     "sem": 0.42, "ci95": 0.96, "n": 8, "values": [...],
     "error": 0.42, "error_type": "sem", "color": "#E8453C"}
  ],
  "comparisons": [
    {"group_a": "Control", "group_b": "Drug A",
     "p_value": 0.003, "stars": "**"}
  ],
  "title": "My Chart", "x_label": "", "y_label": ""
}
```

### Config keys

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| sheet | int/str | 0 | Sheet name or 0-based index |
| error_type | str | "sem" | "sem", "sd", or "ci95" |
| stats_test | str | "none" | "parametric", "nonparametric", "paired", "permutation", "one_sample", "none" |
| posthoc | str | "Tukey HSD" | Posthoc method |
| mc_correction | str | "Holm-Bonferroni" | Multiple comparisons correction |
| control | str/null | null | Control group name |
| title | str | "" | Chart title |
| x_label | str | "" | X-axis label (also accepts "xlabel") |
| y_label | str | "" | Y-axis label (also accepts "ytitle") |

---

## All 29 chart types

| Registry key | UI Label |
|---|---|
| bar | Bar Chart |
| line | Line Graph |
| grouped_bar | Grouped Bar |
| box | Box Plot |
| scatter | Scatter Plot |
| violin | Violin Plot |
| kaplan_meier | Survival Curve |
| heatmap | Heatmap |
| two_way_anova | Two-Way ANOVA |
| before_after | Before / After |
| histogram | Histogram |
| subcolumn_scatter | Subcolumn |
| curve_fit | Curve Fit |
| column_stats | Col Statistics |
| contingency | Contingency |
| repeated_measures | Repeated Meas. |
| chi_square_gof | Chi-Sq GoF |
| stacked_bar | Stacked Bar |
| bubble | Bubble Chart |
| dot_plot | Dot Plot |
| bland_altman | Bland-Altman |
| forest_plot | Forest Plot |
| area_chart | Area Chart |
| raincloud | Raincloud |
| qq_plot | Q-Q Plot |
| lollipop | Lollipop |
| waterfall | Waterfall |
| pyramid | Pyramid |
| ecdf | ECDF |

---

## Excel layout conventions

| Chart type | Row 0 | Rows 1+ |
|---|---|---|
| Bar, Box, Violin, Dot, Histogram | Group names | Numeric values |
| Line, Scatter, Curve Fit | X-label, Series names | X value, Y replicates |
| Grouped Bar, Stacked Bar | Category names (row 0) + Subgroup names (row 1) | Values |
| Kaplan-Meier | Group names (each spans 2 cols: Time, Event) | time, 0/1 |
| Heatmap | blank, Col labels | Row label, values |
| Two-Way ANOVA | Factor_A, Factor_B, Value | one row per observation |
| Contingency | blank, Outcome labels | Group name, counts |
| Forest Plot | Study, Effect, Lower CI, Upper CI | one row per study |
| Bland-Altman | Method A, Method B | paired measurements |

---

## Test harness patterns

```python
import plotter_test_harness as _h
from plotter_test_harness import run, section, summarise, bar_excel, with_excel

def test_my_feature():
    with with_excel(lambda p: bar_excel({"A": [1,2,3]}, path=p)) as path:
        from refraction.analysis import analyze
        result = analyze("bar", path)
        assert result["ok"] is True

run("my feature works", test_my_feature)
summarise()
```

**Available fixtures**: `bar_excel`, `line_excel`, `grouped_excel`, `km_excel`,
`heatmap_excel`, `two_way_excel`, `contingency_excel`, `bland_altman_excel`,
`forest_excel`, `bubble_excel`, `chi_gof_excel`, `simple_xy_excel`, `with_excel`

---

## Core helper functions

### In `refraction/core/chart_helpers.py`

| Function | Purpose |
|---|---|
| `_run_stats(groups, test_type, ...)` | Run statistical tests, return (a, b, p, stars) tuples |
| `_calc_error(vals, error_type)` | Return (mean, error_half_width) for SEM/SD/CI95 |
| `_calc_error_asymmetric(vals, error_type)` | Asymmetric error bars for log scale |
| `_p_to_stars(p)` | Convert p-value to asterisk annotation |
| `_apply_correction(raw_p, method)` | Apply multiple comparisons correction |
| `normality_warning(groups, test)` | Warning string if data non-normal |
| `check_normality(vals)` | Shapiro-Wilk test |

---

## Style constants

```python
PRISM_PALETTE = [
    "#E8453C", "#2274A5", "#32936F", "#F18F01", "#A846A0",
    "#6B4226", "#048A81", "#D4AC0D", "#3B1F2B", "#44BBA4",
]
```

---

## Commit conventions

```
feat: add lollipop chart analysis
fix: correct SEM calculation for single-value groups
test: add analysis engine error handling tests
refactor: extract analysis engine from api.py
docs: update CLAUDE.md for new architecture
```

Always run `python3 run_all.py` and confirm 0 failures before pushing.
