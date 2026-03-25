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

## Architecture Principles

1. **No generic analysis path.** Every chart type MUST have a dedicated
   analyzer that understands its data layout. The generic column-as-groups
   fallback in `engine.py` exists only as legacy — new chart types must
   never rely on it. Analyzers are grouped by data table type (XY, Column,
   Grouped, etc.) and registered in `_DEDICATED_ANALYZERS`.

2. **Renderer knows nothing about statistics.** The SwiftUI renderer reads
   the JSON spec and draws what it sees. It has no knowledge of p-values,
   test types, or raw data. All computation happens in the Python engine.

3. **Engine knows nothing about visuals.** The Python engine computes
   statistics and returns data. It has no knowledge of colors, fonts, axis
   styles, or rendering. Visual formatting lives in `FormatGraphSettings`
   and `FormatAxesSettings` on the Swift side.

4. **Data table types match Prism.** The eight table types (XY, Column,
   Grouped, Contingency, Survival, Parts of whole, Multiple variables,
   Nested) follow GraphPad Prism's conventions exactly. Each constrains
   which chart types are valid.

See `HUMAN_REVIEW_TODO.md` for manual verification tasks.

---

## Commands

```bash
# Run the full test suite (767 tests, ~3 seconds)
python3 run_all.py

# Run a single suite
python3 run_all.py stats              # statistical verification
python3 run_all.py validators         # spreadsheet validators
python3 run_all.py api                # FastAPI endpoint tests
python3 run_all.py engine             # tests/engine/ -- pure computation tests
python3 run_all.py integration        # tests/integration/ -- API + pipeline tests
python3 run_all.py analysis           # dedicated analyzer tests
python3 run_all.py qa                 # QA regression tests
python3 run_all.py stats_exhaustive   # exhaustive statistical coverage
python3 run_all.py deficiency         # deficiency fix verification
python3 run_all.py render             # render contract tests

# Run the app locally
# 1. Start the Python backend (in a terminal):
python3 -c "from refraction.server.api import start_server; start_server(); import time; time.sleep(999999)"
# 2. Build and run the SwiftUI app (in another terminal):
cd RefractionApp && xcodegen generate && open Refraction.xcodeproj
# Then Cmd+R in Xcode

# Quick import check
python3 -c "from refraction.analysis import analyze; print('OK')"
```

---

## File map

```
# -- Analysis engine -----------------------------------------------
refraction/analysis/__init__.py       Exports analyze()
refraction/analysis/engine.py         Core analyze() + _DEDICATED_ANALYZERS dispatch
refraction/analysis/xy.py             Dedicated XY analyzer (scatter, line, area, curve_fit, bubble)
refraction/analysis/grouped_bar.py    Dedicated grouped bar / stacked bar analyzer
refraction/analysis/two_way_anova.py  Dedicated two-way ANOVA analyzer
refraction/analysis/kaplan_meier.py   Survival curve analyzer
refraction/analysis/contingency.py    Contingency table analyzer
refraction/analysis/chi_square_gof.py Chi-square goodness-of-fit analyzer
refraction/analysis/forest_plot.py    Forest plot analyzer
refraction/analysis/bland_altman.py   Bland-Altman paired comparison analyzer
refraction/analysis/dot_plot.py       Dot plot analyzer
refraction/analysis/raincloud.py      Raincloud plot analyzer
refraction/analysis/bar.py            Bar chart analyzer
refraction/analysis/box.py            Box plot analyzer
refraction/analysis/violin.py         Violin plot analyzer
refraction/analysis/histogram.py      Histogram analyzer
refraction/analysis/before_after.py   Before/after analyzer
refraction/analysis/scatter.py        Scatter plot analyzer
refraction/analysis/line.py           Line graph analyzer
refraction/analysis/curve_fit.py      Curve fitting analyzer
refraction/analysis/curve_models.py   Curve model definitions
refraction/analysis/helpers.py        Shared analyzer helper functions
refraction/analysis/layout.py         Data layout detection
refraction/analysis/results.py        Result object builders
refraction/analysis/schema.py         Analysis result schema definitions
refraction/analysis/stats_annotator.py  Statistical annotation helpers
refraction/analysis/transforms.py     Column transforms

# -- Core library --------------------------------------------------
refraction/core/stats.py              Pure statistical computation (all math lives here)
refraction/core/chart_helpers.py      Presentation helpers + re-exports from stats.py for compat
refraction/core/validators.py         Spreadsheet validators
refraction/core/registry.py           PlotTypeConfig chart registry
refraction/core/config.py             Configuration utilities
refraction/core/types.py              Shared type definitions
refraction/core/outliers.py           Outlier detection
refraction/core/errors.py             ErrorReporter + logging
refraction/core/presets.py            Style preset load/save
refraction/core/session.py            Session persistence
refraction/core/undo.py               UndoStack for undo/redo

# -- I/O -----------------------------------------------------------
refraction/io/export.py               Journal export presets (Nature/Science/Cell)
refraction/io/import_pzfx.py          GraphPad .pzfx file importer
refraction/io/project.py              .cplot project files (ZIP)

# -- Server --------------------------------------------------------
refraction/server/api.py              FastAPI: /analyze, /render, /upload, /health, /chart-types,
                                        /data-preview, /recommend-test, /analyze-stats,
                                        /analyze-layout, /curve-models, /curve-fit,
                                        /transforms, /transform, /project/save-refract,
                                        /project/save, /project/load

# -- SwiftUI app ---------------------------------------------------
RefractionApp/Refraction/App/
  RefractionApp.swift                 @main entry point, server lifecycle
  AppState.swift                      Central @Observable state

RefractionApp/Refraction/Models/
  DataTable.swift                     Prism-style data table model
  Sheet.swift                         Sheet (graph + data + results) model
  TableType.swift                     Data table type enum (XY, Column, Grouped, etc.)
  FormatGraphSettings.swift           Graph formatting settings
  FormatAxesSettings.swift            Axes formatting settings
  ProjectState.swift                  Multi-sheet project state
  StatsTestCatalog.swift              Statistical test catalog/wiki
  ChartType.swift                     Chart type enum + capabilities
  ChartConfig.swift                   ~40 config properties + toDict()

RefractionApp/Refraction/Views/
  ContentView.swift                   Root layout
  WelcomeView.swift                   First-run experience
  ErrorView.swift                     Error display + parsing
  ToolbarBanner.swift                 Toolbar status banner
  Sidebar/NavigatorView.swift         Prism-style project navigator
  Sidebar/ChartSidebarView.swift      Chart type list
  Sheets/GraphSheetView.swift         Graph sheet container
  Sheets/DataTableView.swift          Data table editor
  Sheets/ResultsSheetView.swift       Statistical results sheet
  Sheets/InfoSheetView.swift          Info/metadata sheet
  Sheets/AnalyzeDataDialog.swift      Analyze data dialog
  Sheets/StatsWikiDialog.swift        Stats test encyclopedia dialog
  Sheets/StatsTestDetailDialog.swift  Individual test detail dialog
  Chart/ChartCanvasView.swift         Canvas rendering
  Chart/FormatGraphDialog.swift       Format Graph dialog (Prism-style)
  Chart/FormatAxesDialog.swift        Format Axes dialog (Prism-style)
  Config/ConfigTabView.swift          Tab container
  Config/DataTabView.swift            File + labels
  Config/AxesTabView.swift            Axis config
  Config/StyleTabView.swift           Visual style
  Config/StatsTabView.swift           Statistical tests
  Results/ResultsView.swift           Stats results table

RefractionApp/Refraction/Services/
  APIClient.swift                     HTTP client (actor, singleton)
  PythonServer.swift                  Python subprocess manager

# -- Sample data ---------------------------------------------------
RefractionApp/Refraction/Resources/SampleData/
  drug_treatment.xlsx                 3 groups, 8 values each
  time_series.xlsx                    X + 2 Y series
  survival_data.xlsx                  2 groups, time/event

# -- Tests ---------------------------------------------------------
run_all.py                            10-suite unified test runner
tests/conftest.py                     Shared pytest fixtures

tests/test_stats.py                   Statistical verification
tests/test_validators.py              Spreadsheet validator tests
tests/test_api.py                     FastAPI endpoint tests
tests/test_analysis.py                Dedicated analyzer tests
tests/test_stats_exhaustive.py        Exhaustive statistical coverage
tests/test_deficiency_fixes.py        Deficiency fix verification
tests/test_render_contract.py         Render contract tests
tests/test_phase6_qa.py              QA regression tests

tests/engine/                         Pure computational tests
  test_stats_core.py                  Core stats function tests
  test_helpers.py                     Helper function tests
  test_validators.py                  Validator unit tests
  test_layout.py                      Layout detection tests
  test_transforms.py                  Transform tests
  test_curve_models.py                Curve model tests
  test_results.py                     Result builder tests
  test_project_v2.py                  Project file v2 tests

tests/integration/                    API + pipeline integration tests
  test_api.py                         API integration tests
  test_pipeline.py                    End-to-end pipeline tests
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
Dedicated analyzers (refraction/analysis/*.py)
    |
    v
Pure stats (refraction/core/stats.py)
    |-- _run_stats()    statistical tests
    |-- _calc_error()   descriptive statistics
    |-- _km_curve()     survival analysis
    |-- _twoway_anova() two-way ANOVA
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

### In `refraction/core/stats.py` (re-exported by `chart_helpers.py` for compat)

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
