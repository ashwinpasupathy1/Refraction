# Refraction — Architecture & Developer Guide

> A hands-on technical reference for the Refraction codebase.
> Written for someone with Python experience who is new to Swift/SwiftUI.
>
> For the comprehensive SwiftUI client architecture, see **SWIFT_UI.md**.

---

## Table of Contents

1. [How the System Works](#1-how-the-system-works)
2. [The Python Backend](#2-the-python-backend)
3. [The Swift Frontend](#3-the-swift-frontend)
4. [The API Contract](#4-the-api-contract)
5. [Swift Concepts You Need to Know](#5-swift-concepts-you-need-to-know)
6. [Common Tasks — Worked Examples](#6-common-tasks--worked-examples)
7. [Debugging Playbook](#7-debugging-playbook)
8. [File Reference](#8-file-reference)

---

## 1. How the System Works

Refraction is a two-process app: a **Python backend** that does all the
data analysis (statistics, curve fitting, data parsing), and a **macOS
SwiftUI frontend** that handles the UI and chart rendering.

They communicate over HTTP on `localhost:7331`.

```
┌──────────────────────────────────────────────────────┐
│  macOS App  (SwiftUI)                                │
│                                                      │
│  ┌──────────┐  ┌──────────────┐  ┌────────────────┐ │
│  │ Sidebar  │  │ Chart Canvas │  │  Config Panel  │ │
│  │ (chart   │  │ (Core        │  │  (Data, Style, │ │
│  │  types)  │  │  Graphics)   │  │   Stats tabs)  │ │
│  └──────────┘  └──────────────┘  └────────────────┘ │
│       │               ▲                  │           │
│       └───────────────┼──────────────────┘           │
│                       │                              │
│              AppState (central state)                │
│                       │                              │
│              APIClient (HTTP POST)                   │
│                       │                              │
└───────────────────────┼──────────────────────────────┘
                        │  HTTP localhost:7331
┌───────────────────────┼──────────────────────────────┐
│  Python Server  (FastAPI + uvicorn)                  │
│                       │                              │
│              ┌────────▼────────┐                     │
│              │  /render        │ ← SwiftUI calls this│
│              │  /analyze       │ ← raw analysis      │
│              │  /upload        │ ← file upload       │
│              │  /health        │ ← liveness check    │
│              │  /sheet-list    │ ← Excel sheet names  │
│              │  /validate-table│ ← layout validation  │
│              │  /render-latex  │ ← LaTeX → PNG        │
│              │  /data-preview  │ ← spreadsheet peek  │
│              │  /recommend-test│ ← test suggestion   │
│              │  /analyze-stats │ ← stats-only run    │
│              │  /project/save- │                      │
│              │    refract      │ ← .refract save     │
│              └────────┬────────┘                     │
│                       │                              │
│          Dedicated analyzers (analysis/*.py)          │
│                       │                              │
│              ┌────────▼────────┐                     │
│              │  core/stats.py  │ ← pure math layer   │
│              │  _calc_error()  │                      │
│              │  _run_stats()   │                      │
│              └─────────────────┘                     │
└──────────────────────────────────────────────────────┘
```

### The Request Lifecycle

Here's exactly what happens when the user clicks "Generate":

1. **SwiftUI** → `AppState.generatePlot()` is called
2. **AppState** → calls `APIClient.shared.analyze(chartType:, config:)`
3. **APIClient** → sends `POST /render` with JSON body:
   ```json
   {"chart_type": "bar", "kw": {"excel_path": "/tmp/.../file.xlsx", "error": "sem", ...}}
   ```
4. **FastAPI `/render`** → extracts `excel_path` from `kw`, maps config keys, calls `analyze()`
5. **`analyze()`** → reads Excel with pandas, computes stats, returns flat dict
6. **`/render`** → transforms flat dict into nested `ChartSpec` JSON via `_to_chart_spec()`
7. **APIClient** → decodes JSON into Swift `ChartSpec` struct
8. **AppState** → sets `currentSpec`, which triggers SwiftUI to re-render
9. **ChartCanvasView** → draws the chart using Core Graphics

### File Upload Flow

Before analysis, the user must upload a file:

1. User picks file via `NSOpenPanel` or clicks "Try Sample Data"
2. `AppState.uploadFile(url:)` → `APIClient.upload(fileURL:)`
3. `POST /upload` (multipart form) → server saves to `/tmp/refraction-uploads/{uuid}.xlsx`
4. Server returns `{"ok": true, "path": "/tmp/refraction-uploads/abc123.xlsx"}`
5. `chartConfig.excelPath` is set to the server-side path

This means the Swift app never reads the Excel file directly — it always
goes through the server.

---

## 2. The Python Backend

### 2.1 Server (`refraction/server/api.py`)

The server is a FastAPI app created by `_make_app()` and run with uvicorn.
It starts in a daemon thread via `start_server()` (called from terminal)
or as a subprocess managed by the Swift app's `PythonServer` class.

**Endpoints:**

| Endpoint | Method | What It Does |
|----------|--------|-------------|
| `/health` | GET | Returns `{"status": "ok"}` — used by the Swift app to detect when the server is ready |
| `/chart-types` | GET | Lists all 29 chart types with a "priority" subset for the UI |
| `/analyze` | POST | Raw analysis — takes `{chart_type, excel_path, config}`, returns flat results |
| `/render` | POST | **Bridge for SwiftUI** — takes `{chart_type, kw}`, calls analyze, transforms into `ChartSpec` format |
| `/upload` | POST | Accepts `.xlsx/.xls/.csv` via multipart upload, saves to temp dir, returns path |
| `/sheet-list` | POST | Lists sheet names in an Excel file |
| `/validate-table` | POST | Validates spreadsheet layout for a given chart type |
| `/render-latex` | POST | Renders a LaTeX formula to PNG image (used by Stats Wiki) |
| `/data-preview` | POST | Returns a preview of spreadsheet contents for the data table view |
| `/recommend-test` | POST | Suggests an appropriate statistical test based on data characteristics |
| `/analyze-stats` | POST | Runs statistical analysis only (no chart spec generation) |
| `/analyze-layout` | POST | Detects data layout and recommends chart types |
| `/curve-models` | GET | Lists all curve fitting models by category |
| `/curve-fit` | POST | Fits a model to X/Y data |
| `/transforms` | GET | Lists available column transformations |
| `/transform` | POST | Applies a transform to a column |
| `/project/save-refract` | POST | Saves a `.refract` project archive (new format) |
| `/project/save` | POST | Saves a `.refract` project archive (legacy) |
| `/project/load` | POST | Loads a `.refract` project archive |

**Why `/render` and `/analyze` are separate:**

`/analyze` returns a flat dict — good for tests, scripts, and direct use.
`/render` wraps `/analyze` and reshapes the response into the nested JSON
schema that Swift's `ChartSpec` structs expect (with `groups[].values.raw`,
`style`, `axes`, `stats`, `brackets` sub-objects). It also maps Swift-style
config keys to Python-style ones (e.g., `"error"` → `"error_type"`).

**Auth:** Optional API key via `REFRACTION_API_KEY` env var. Localhost is
always allowed without auth.

**Logging:** File-based at `~/Library/Logs/Refraction/api.log` with rotation.

### 2.2 Analysis Engine (`refraction/analysis/engine.py`)

The core function: `analyze(chart_type, excel_path, config) → dict`

**For most chart types**, it follows a generic path:

```python
# 1. Read Excel
df = pd.read_excel(excel_path, sheet_name=sheet)

# 2. Extract groups (each column = one group)
for col in df.columns:
    vals = pd.to_numeric(df[col], errors="coerce").dropna().values
    groups_dict[col] = vals

# 3. Descriptive stats per group
for name, vals in groups_dict.items():
    mean, error = _calc_error(vals, error_type)  # SEM, SD, or CI95
    group_results.append({"name": name, "mean": mean, "sem": sem, ...})

# 4. Statistical comparisons (if requested)
if stats_test != "none":
    raw = _run_stats(groups_dict, test_type=stats_test, ...)
    comparisons = [{"group_a": a, "group_b": b, "p_value": p, "stars": s}]

# 5. Return
return {"ok": True, "chart_type": ..., "groups": ..., "comparisons": ...}
```

**15+ chart types have dedicated analyzers** registered in the
`_DEDICATED_ANALYZERS` dispatch table (lazily loaded):

| Chart Type | Analyzer Module | What's Different |
|-----------|----------------|-----------------|
| `dot_plot` | `dot_plot` | Column statistics |
| `kaplan_meier` | `kaplan_meier` | Paired time/event columns |
| `forest_plot` | `forest_plot` | Study/Effect/CI columns |
| `raincloud` | `raincloud` | Density + box + jitter |
| `contingency` | `contingency` | Chi-square on count tables |
| `bland_altman` | `bland_altman` | Paired method comparison |
| `chi_square_gof` | `chi_square_gof` | Goodness-of-fit test |
| `grouped_bar` | `grouped_bar` | Category x subgroup layout |
| `stacked_bar` | `grouped_bar` | Shares grouped bar analyzer |
| `two_way_anova` | `two_way_anova` | Factor_A, Factor_B, Value layout |
| `scatter` | `xy` | XY data with series |
| `line` | `xy` | XY data with series |
| `area_chart` | `xy` | XY data with series |
| `curve_fit` | `xy` | XY data with model fitting |
| `bubble` | `xy` | XY data with size channel |

Additional analyzer modules exist for `bar`, `box`, `violin`, `histogram`,
`before_after`, `scatter`, and `line` though not all are wired into the
dispatch table yet.

### 2.3 Statistics (`refraction/core/stats.py`)

This is where the actual math lives. No plotting dependencies — pure
numpy/scipy. The `chart_helpers.py` module re-exports all functions from
`stats.py` for backward compatibility.

**Key functions:**

**`_calc_error(vals, error_type) → (mean, error_half_width)`**
- `"sem"`: SD / √n
- `"sd"`: raw standard deviation
- `"ci95"`: t₀.₉₇₅(df=n-1) × SEM

**`_run_stats(groups, test_type, ...) → [(group_a, group_b, p_value, stars)]`**

The statistical test dispatch:

| `test_type` | 2 groups | 3+ groups |
|------------|----------|-----------|
| `"parametric"` | Welch's t-test | Levene's → ANOVA → posthoc |
| `"nonparametric"` | Mann-Whitney U | Kruskal-Wallis → pairwise MW |
| `"paired"` | Paired t-test | Pairwise paired t-tests |
| `"one_sample"` | One-sample t-test vs μ₀ | Same, per group |
| `"permutation"` | Permutation test | Pairwise permutation |

**Posthoc methods** (for 3+ group parametric):
- Tukey HSD (default) — uses studentized range distribution
- Dunnett (vs control) — requires `control` group name
- Bonferroni, Šidák, Fisher LSD — pairwise t-tests with correction

**`_apply_correction(raw_p_list, method)`** — multiple comparisons:
- Bonferroni: p × m
- Holm-Bonferroni: step-down (default)
- Benjamini-Hochberg: FDR control

**`_p_to_stars(p)`** — the classic Prism notation:
- \> 0.05: "ns", ≤ 0.05: "\*", ≤ 0.01: "\*\*", ≤ 0.001: "\*\*\*", ≤ 0.0001: "\*\*\*\*"

### 2.4 Validators (`refraction/core/validators.py`)

Pure functions that check whether a spreadsheet follows the expected layout
for a given chart type. Returns `(errors: list[str], warnings: list[str])`.
Empty errors = valid.

Each chart type has a validator registered in the `PlotTypeConfig` registry.
Validators check for things like: enough columns, numeric data present,
no empty cells in critical positions, matching replicate counts, etc.

### 2.5 Supporting Modules

| Module | Purpose |
|--------|---------|
| `core/registry.py` | `PlotTypeConfig` dataclass — defines capabilities per chart type (has error bars? has stats? which validator?) |
| `core/errors.py` | `ErrorReporter` class — structured logging to `~/Library/Logs/refraction.log` |
| `core/presets.py` | Named style presets (Publication B&W, Presentation, etc.) — load/save JSON to `~/Library/Application Support/Refraction/presets/` |
| `core/session.py` | Session persistence — saves/restores app state across launches via `~/Library/Preferences/refraction_session.json` |
| `core/undo.py` | Command-pattern undo/redo stack with compound command support |
| `io/export.py` | Journal figure specs (Nature, Science, Cell) — dimensions, DPI, font requirements |
| `io/import_pzfx.py` | GraphPad Prism `.pzfx` XML importer → temp `.xlsx` |
| `io/project.py` | `.cplot` project files (ZIP archives with manifest, CSV data, settings, thumbnail) |

---

## 3. The Swift Frontend

### 3.1 App Entry Point (`RefractionApp.swift`)

```swift
@main
struct RefractionApp: App {
    @State private var appState = AppState()
    @State private var pythonServer = PythonServer()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environment(appState)      // inject into view tree
                .environment(pythonServer)
                .onAppear { pythonServer.start() }   // auto-launch server
                .onDisappear { pythonServer.stop() }
        }
    }
}
```

**What this does:** Creates the app's state objects, injects them into the
view hierarchy via `.environment()`, and manages the Python server lifecycle.

### 3.2 Central State (`AppState.swift`)

```swift
@Observable
final class AppState {
    var experiments: [Experiment] = []         // top-level containers
    var selectedExperimentID: UUID?            // active experiment
    var selectedItemID: UUID?                  // active item within experiment
    var selectedItemKind: ItemKind = .graph    // dataTable, graph, or analysis
    var isLoading: Bool = false
    var error: String?
}
```

This is the single source of truth. Every view reads from it and writes
to it. When any property changes, SwiftUI automatically re-renders only
the views that depend on that property.

**Key methods:**
- `addExperiment()` / `removeExperiment()` — manage experiments
- `addDataTable()` / `addGraph()` / `addAnalysis()` — add items within an experiment
- `selectItem(_ id, kind:)` — navigate to a specific item
- `generatePlot()` — async, calls the API, sets graph's `chartSpec`
- `uploadFile(url:, for:)` — async, uploads file, sets data table path
- `runAnalysis()` — async, runs standalone stats analysis
- `saveProjectFile()` / `loadProjectFromURL()` — .refract file I/O

### 3.3 View Hierarchy

The UI follows a Prism-style architecture with a project navigator,
multiple sheet types per graph, and Format dialogs:

```
RefractionApp
└── ContentView
    ├── Sidebar: NavigatorView (Prism-style experiment navigator)
    │   └── Tree of Experiments → DataTables + Graphs + Analyses
    │       ├── NewExperimentDialog
    │       ├── NewDataTableDialog
    │       └── NewGraphDialog
    │
    ├── Content: Sheet Area (depends on selected item kind)
    │   ├── GraphSheetView     → ChartCanvasView + ChartOverlayView
    │   ├── DataTableView      → Spreadsheet-style data editor
    │   ├── ResultsSheetView   → Statistical results display
    │   └── InfoSheetView      → Metadata / notes
    │
    ├── Dialogs (modal):
    │   ├── FormatGraphDialog   — Prism-style graph formatting
    │   ├── FormatAxesDialog    — Prism-style axes formatting
    │   ├── AnalyzeDataDialog   — Run analysis on data
    │   ├── ExportChartDialog   — Export with DPI/format/size options
    │   ├── StatsWikiDialog     — Stats test encyclopedia (LaTeX formulas)
    │   ├── StatsTestDetailDialog — Individual test details
    │   └── ArchitectureGuideDialog — Architecture reference
    │
    ├── ToolbarBanner — Status messages and actions
    ├── DebugConsoleView — API trace / engine log viewer
    │
    └── Detail: ConfigTabView (tab bar)
        ├── DataTabView    — file picker, sheet selector, labels
        ├── AxesTabView    — scale, limits, tick marks, reference line
        ├── StyleTabView   — error bars, points, grid, opacity
        └── StatsTabView   — test type, posthoc, correction, thresholds
```

### 3.4 Chart Rendering

Charts are drawn natively using Apple's `Canvas` view with `GraphicsContext`
— there's no web view, no Plotly, no third-party charting library.

```
ChartCanvasView + ChartOverlayView (interactive hit regions, zoom)
├── AxisRenderer.draw()          — spines, ticks, labels, title, grid
├── BarRenderer.draw()           — bars, error bars, data points
├── BoxRenderer.draw()           — box plots (whiskers, median, quartiles)
├── ViolinRenderer.draw()        — violin plots (KDE curves)
├── ScatterRenderer.draw()       — scatter plots
├── LineRenderer.draw()          — line graphs
├── HistogramRenderer.draw()     — histograms
├── GroupedBarRenderer.draw()    — grouped bar charts
├── StackedBarRenderer.draw()    — stacked bar charts
├── DotPlotRenderer.draw()       — dot plots
├── BeforeAfterRenderer.draw()   — before/after paired charts
├── KaplanMeierRenderer.draw()   — survival curves
└── BracketRenderer.draw()       — significance brackets ("***", "ns")
```

The renderers live in a separate Swift Package (`RefractionRenderer/`)
so they can be built and tested independently. `HitRegion.swift` provides
interactive hit testing for chart elements.

**Format settings** are merged into the engine-provided `ChartSpec` by
`FormatSettingsMerger.swift`, which bridges the Format Graph/Axes dialogs
to the renderer without re-running analysis.

**Render style presets** (in `RenderStyle.swift`, client-side only):
- **Default**: clean with light grid
- **Prism**: L-shaped axes, no grid, bold (GraphPad Prism style)
- **ggplot2**: gray background, white grid lines (R ggplot2 style)
- **Matplotlib**: full frame, dashed grid (Python matplotlib style)

### 3.5 Services

**`APIClient.swift`** — an `actor` (thread-safe singleton) that does HTTP:
- `analyze(chartType:, config:)` → POST /render
- `upload(fileURL:)` → POST /upload (multipart)
- `health()` → GET /health
- All requests/responses logged to `DebugLog` with timing

**`DebugLog.swift`** — centralized debug logger (singleton):
- Captures API requests/responses, engine traces, app events, errors
- Ring buffer (500 entries max), displayed in `DebugConsoleView`
- Logs Python tracebacks from server error responses

**`PythonServer.swift`** — manages the Python subprocess:
- Finds the right Python binary (bundled > env var > well-known paths > system)
- Finds the project root (env var > walk up from bundle > SOURCE_ROOT > known paths)
- Sets `PYTHONPATH` so `import refraction` works
- Polls `/health` every 0.5s until the server responds (15s timeout)
- Auto-restarts once on crash; shows alert on second failure
- Writes crash logs to `~/Library/Logs/Refraction/crash.log`

### 3.6 Models

**`ChartType`** — enum with all 29 chart type values. Each has a `key`
(API string), `label` (display name), `category` (sidebar group), and
capability flags (`hasPoints`, `hasErrorBars`, `hasStats`).

**`ChartConfig`** — `@Observable` class with ~40 properties covering every
configurable parameter. Has `toDict()` that serializes to the flat dict
the API expects.

**`ChartSpec`** — the response from `/render`, decoded from JSON. Contains
`groups` (data + stats), `style`, `axes`, `stats`, `brackets`.
Has a custom `Decodable` init that can parse both our native format and
legacy Plotly JSON.

**`Experiment`** — Top-level container. Owns multiple `DataTable`s,
`Graph`s, and `Analysis` objects. Provides methods for adding/removing
items and lookups (`dataTable(for:)`, `validChartTypes(for:)`).

**`DataTable`** — Data table within an experiment. Has a `TableType`, an
optional file path, and constrains which chart types are valid.

**`Graph`** — Graph within an experiment. Links to one `DataTable` by ID.
Holds `chartType`, `chartConfig`, cached `chartSpec`, `formatSettings`,
`formatAxesSettings`, `renderStyle`, and `zoomLevel`.

**`Analysis`** — Statistical analysis within an experiment. Links to one
`DataTable` by ID. Holds `analysisType`, `statsResults`, and `notes`.

**`RenderStyle`** — Enum of client-side render style presets (Default,
Prism, ggplot2, Matplotlib). Each applies visual settings to format
settings objects.

**`TableType`** — Enum matching Prism's eight data table types (XY, Column,
Grouped, Contingency, Survival, Parts of whole, Multiple variables, Nested).

**`FormatGraphSettings`** / **`FormatAxesSettings`** — Settings models for
the Prism-style Format Graph and Format Axes dialogs.

**`ProjectState`** — Project state for save/load serialization.

**`StatsTestCatalog`** — Encyclopedia of statistical tests with descriptions,
assumptions, and usage guidance. Formulas use `$...$` LaTeX markup.

**`ArchitectureGuideCatalog`** — Architecture reference guide content.

---

## 4. The API Contract

### Request: POST /render

```json
{
  "chart_type": "bar",
  "kw": {
    "excel_path": "/tmp/refraction-uploads/abc123.xlsx",
    "sheet": 0,
    "error": "sem",
    "stats_test": "parametric",
    "posthoc": "Tukey HSD",
    "mc_correction": "Holm-Bonferroni",
    "title": "My Chart",
    "xlabel": "Treatment",
    "ytitle": "Response",
    "show_points": true,
    "point_size": 6.0,
    "axis_style": "open",
    "bar_width": 0.6
  }
}
```

### Response: POST /render (success)

```json
{
  "ok": true,
  "spec": {
    "chart_type": "bar",
    "groups": [
      {
        "name": "Control",
        "values": {
          "raw": [3.2, 4.1, 5.0, 4.8, 3.9, 5.2, 4.5, 4.2],
          "mean": 4.36,
          "sem": 0.24,
          "sd": 0.67,
          "ci95": 0.56,
          "n": 8
        },
        "color": "#E8453C"
      }
    ],
    "style": {
      "colors": ["#E8453C", "#2274A5", "#32936F"],
      "show_points": true,
      "show_brackets": true,
      "point_size": 6.0,
      "point_alpha": 0.8,
      "bar_width": 0.6,
      "error_type": "sem",
      "axis_style": "open"
    },
    "axes": {
      "title": "My Chart",
      "x_label": "Treatment",
      "y_label": "Response",
      "x_scale": "linear",
      "y_scale": "linear",
      "tick_direction": "out",
      "spine_width": 1.0,
      "font_size": 12.0
    },
    "stats": {
      "test_name": "parametric",
      "comparisons": [
        {
          "group_1": "Control",
          "group_2": "Drug A",
          "p_value": 0.003,
          "significant": true,
          "label": "**"
        }
      ]
    },
    "brackets": [
      {
        "left_index": 0,
        "right_index": 1,
        "label": "**",
        "stacking_order": 0
      }
    ],
    "reference_line": null
  }
}
```

### Key Mapping (Swift → Python)

The `/render` endpoint translates these config keys:

| Swift sends | Python expects | Notes |
|------------|---------------|-------|
| `error` | `error_type` | "sem", "sd", "ci95" |
| `xlabel` | `x_label` | X-axis label |
| `ytitle` | `y_label` | Y-axis label |

### Response Mapping (Python → Swift)

The `_to_chart_spec()` function in `api.py` transforms:

| Python analyze() returns | Swift ChartSpec expects |
|-------------------------|------------------------|
| `groups[].values` (flat list) | `groups[].values.raw` (nested object with mean, sem, etc.) |
| `comparisons[].group_a` | `stats.comparisons[].group_1` |
| `comparisons[].group_b` | `stats.comparisons[].group_2` |
| `comparisons[].stars` | `stats.comparisons[].label` + `brackets[]` |
| `title`, `x_label`, `y_label` (top-level) | `axes.title`, `axes.x_label`, `axes.y_label` |

---

## 5. Swift Concepts You Need to Know

### 5.1 `@Observable` (Observation Framework)

```swift
@Observable
final class AppState {
    var selectedChartType: ChartType = .bar  // SwiftUI tracks reads
    var error: String?
}
```

**Python equivalent:** Think of it like a class where every property has
a change listener attached. When a SwiftUI view reads `appState.error`
during rendering, SwiftUI remembers that dependency. When `error` changes,
only that view re-renders. No manual notification needed.

**Key difference from Python:** You don't call `self.notify()` or emit
signals — SwiftUI handles it automatically via compile-time macros.

### 5.2 `@State` vs `@Environment`

```swift
// @State = owned by THIS view, private, mutable
@State private var selectedTab: Tab = .data

// @Environment = injected from a parent view, shared
@Environment(AppState.self) private var appState
```

**Python equivalent:** `@State` is like an instance variable.
`@Environment` is like dependency injection — a parent sets it up, and any
descendant can read it without passing it through every intermediate layer.

### 5.3 `actor` (Thread Safety)

```swift
actor APIClient {
    static let shared = APIClient()
    func analyze(...) async throws -> ChartSpec { ... }
}
```

**Python equivalent:** An `actor` is like a class where every method call
is automatically serialized — only one caller can execute at a time. It's
Swift's answer to thread safety without manual locks. Calling an actor
method requires `await` because it might have to wait in line.

### 5.4 `async`/`await`

```swift
@MainActor
func generatePlot() async {
    let spec = try await APIClient.shared.analyze(chartType: type, config: cfg)
    currentSpec = spec  // UI update — must be on main thread
}
```

**Python equivalent:** Very similar to Python's `async`/`await`. The
`@MainActor` annotation is like saying "this function must run on the main
thread" — equivalent to `asyncio.get_event_loop().call_soon()` for GUI
updates.

### 5.5 `struct` vs `class`

In Swift, **structs are value types** (like Python's `int` or `tuple`) and
**classes are reference types** (like Python's regular objects).

- Views (`struct ContentView: View`) are structs — lightweight, recreated
  frequently by SwiftUI
- State objects (`class AppState`) are classes — long-lived, shared by
  reference

### 5.6 SwiftUI View Lifecycle

```swift
struct ContentView: View {
    var body: some View {  // Called by SwiftUI whenever dependencies change
        if appState.isLoading {
            ProgressView()
        } else {
            ChartCanvasView(spec: appState.currentSpec!)
        }
    }
}
```

**Python equivalent:** Think of `body` like a `render()` method in React.
SwiftUI calls it whenever the view's data changes, diffs the result against
what's on screen, and applies only the minimal updates. You never manually
update the UI — you change the data, and SwiftUI handles the rest.

### 5.7 `Decodable` (JSON Parsing)

```swift
struct ChartSpec: Decodable {
    let chartType: String
    enum CodingKeys: String, CodingKey {
        case chartType = "chart_type"  // maps JSON key to Swift property
    }
}
```

**Python equivalent:** Like `@dataclass` with a custom JSON decoder. The
`CodingKeys` enum maps snake_case JSON keys to camelCase Swift properties.
`JSONDecoder().decode(ChartSpec.self, from: data)` is like
`json.loads()` + `dacite.from_dict()`.

---

## 6. Common Tasks — Worked Examples

### 6.1 Adding a New Chart Type (End-to-End)

**Python side:**

1. **Add to registry** (`core/registry.py`):
   ```python
   PlotTypeConfig(
       key="my_chart",
       label="My Chart",
       fn_name="my_chart",
       tab_mode="bar",
       stats_tab="standard",
       validate="validate_flat_header",
       has_points=True,
       has_error_bars=True,
       has_stats=True,
       ...
   )
   ```

2. **Add to chart-types list** (`server/api.py`, `/chart-types` endpoint):
   Add `"my_chart"` to the `all` list.

3. **If special data layout needed**, add a dedicated analyzer:
   - Create `refraction/analysis/analyzers/my_chart.py`
   - Add to `_DEDICATED_ANALYZERS` dispatch table in `engine.py`

4. **If generic layout works** (columns = groups), the existing
   `analyze()` generic path handles it automatically.

5. **Add a validator** if needed (`core/validators.py`).

**Swift side:**

6. **Add enum case** to `ChartType` in `ChartConfig.swift`:
   ```swift
   case my_chart
   // Add label, category, sfSymbol, capability flags
   ```

7. **Add renderer** (if not bar-like):
   - Create `RefractionRenderer/Sources/RefractionRenderer/MyChartRenderer.swift`
   - Add case to `ChartCanvasView.swift`'s rendering switch

**Tests:**

8. Write test in `tests/` using the harness:
   ```python
   def test_my_chart():
       with with_excel(lambda p: bar_excel({"A": [1,2,3]}, path=p)) as path:
           result = analyze("my_chart", path)
           assert result["ok"] is True
   ```

9. Run `python3 run_all.py` — must be 0 failures.

### 6.2 Adding a New API Endpoint

1. **Define the request model** in `api.py`:
   ```python
   class MyRequest(BaseModel):
       param1: str
       param2: int = 10
   ```

2. **Add the endpoint** inside `_make_app()`:
   ```python
   @api.post("/my-endpoint")
   def my_endpoint(req: MyRequest):
       try:
           result = do_something(req.param1, req.param2)
           return {"ok": True, "data": result}
       except Exception as exc:
           return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)
   ```

3. **Add Swift client method** in `APIClient.swift`:
   ```swift
   func myEndpoint(param1: String) async throws -> MyResponse {
       let body: [String: Any] = ["param1": param1, "param2": 10]
       let data = try await post(path: "/my-endpoint", body: body)
       return try JSONDecoder().decode(MyResponse.self, from: data)
   }
   ```

4. **Add test** in `tests/test_api.py`.

### 6.3 Debugging a "Server Connection Error"

1. **Check if the server is running:**
   ```bash
   curl http://127.0.0.1:7331/health
   # Should return: {"status":"ok"}
   ```

2. **If not running, check the crash log:**
   ```bash
   cat ~/Library/Logs/Refraction/crash.log
   ```

3. **Common causes:**
   - `ModuleNotFoundError: No module named 'uvicorn'` → wrong Python binary
   - `ModuleNotFoundError: No module named 'refraction'` → wrong PYTHONPATH / project root
   - Port already in use → `lsof -ti:7331 | xargs kill -9`

4. **Start manually to see errors:**
   ```bash
   cd /path/to/repo
   python3 -c "from refraction.server.api import start_server; start_server(); import time; time.sleep(999999)"
   ```

### 6.4 Debugging a Chart Rendering Issue

1. **Test the analysis directly:**
   ```bash
   curl -X POST http://127.0.0.1:7331/analyze \
     -H "Content-Type: application/json" \
     -d '{"chart_type": "bar", "excel_path": "/path/to/file.xlsx", "config": {"error_type": "sem"}}'
   ```

2. **Test the /render bridge:**
   ```bash
   curl -X POST http://127.0.0.1:7331/render \
     -H "Content-Type: application/json" \
     -d '{"chart_type": "bar", "kw": {"excel_path": "/path/to/file.xlsx", "error": "sem"}}'
   ```

3. **Compare the responses.** `/render` should wrap the analyze result in
   a `{"ok": true, "spec": {...}}` envelope with nested value objects.

4. **Check the Swift console** (Xcode → Debug area) for `[PythonServer]`
   log messages.

### 6.5 Adding a New Style Option

1. **Add property** to `ChartConfig.swift`:
   ```swift
   var myOption: Bool = false
   ```

2. **Add to `toDict()`** in `ChartConfig.swift`:
   ```swift
   d["my_option"] = myOption
   ```

3. **Add UI control** in the appropriate tab view (e.g., `StyleTabView.swift`):
   ```swift
   Toggle("My Option", isOn: $config.myOption)
   ```

4. **Read it in Python** — either in `analyze()`:
   ```python
   my_option = cfg.get("my_option", False)
   ```
   Or in `_to_chart_spec()` if it affects the ChartSpec response.

---

## 7. Debugging Playbook

### Logs Location

| Log | Path | Contains |
|-----|------|----------|
| API server log | `~/Library/Logs/Refraction/api.log` | Request/response logging, Python exceptions |
| Crash log | `~/Library/Logs/Refraction/crash.log` | Server startup failures, unexpected exits, stderr |
| App log | `~/Library/Logs/refraction.log` | ErrorReporter output (analysis warnings, validation errors) |
| Xcode console | Debug area in Xcode | `[PythonServer]` prefixed messages, NSLog output |

### Error Flow

```
Python exception
    ↓
FastAPI catches it, returns {"ok": false, "error": "..."}
    ↓
APIClient throws APIError.serverError("...")
    ↓
AppState.generatePlot() catches it, sets self.error = "Analysis failed: ..."
    ↓
ContentView sees error != nil, shows ErrorView
    ↓
ErrorView parses the error string into a friendly title/description
    ↓
User can "Copy Error Details" → clipboard gets full report with versions
```

### Quick Checks

```bash
# Is the server running?
curl http://127.0.0.1:7331/health

# Kill stale server
lsof -ti:7331 | xargs kill -9

# Test analyze directly
python3 -c "
from refraction.analysis import analyze
r = analyze('bar', '/path/to/file.xlsx', {'stats_test': 'parametric'})
print(r['ok'], len(r.get('groups', [])), 'groups')
"

# Run all tests
python3 run_all.py

# Check Python can import everything
python3 -c "from refraction.server.api import _make_app; print('OK')"
```

---

## 8. File Reference

### Python Backend

```
refraction/
├── __init__.py
├── analysis/
│   ├── __init__.py              # Exports analyze()
│   ├── engine.py                # Core analyze() + _DEDICATED_ANALYZERS dispatch
│   ├── xy.py                    # XY analyzer (scatter, line, area, curve_fit, bubble)
│   ├── grouped_bar.py           # Grouped bar / stacked bar analyzer
│   ├── two_way_anova.py         # Two-way ANOVA analyzer
│   ├── kaplan_meier.py          # Survival curve analyzer
│   ├── contingency.py           # Contingency table analyzer
│   ├── chi_square_gof.py        # Chi-square GoF analyzer
│   ├── forest_plot.py           # Forest plot analyzer
│   ├── bland_altman.py          # Bland-Altman analyzer
│   ├── dot_plot.py              # Dot plot analyzer
│   ├── raincloud.py             # Raincloud analyzer
│   ├── bar.py                   # Bar chart analyzer
│   ├── box.py                   # Box plot analyzer
│   ├── violin.py                # Violin plot analyzer
│   ├── histogram.py             # Histogram analyzer
│   ├── before_after.py          # Before/after analyzer
│   ├── scatter.py               # Scatter plot analyzer
│   ├── line.py                  # Line graph analyzer
│   ├── curve_fit.py             # Curve fitting analyzer
│   ├── curve_models.py          # Curve model definitions
│   ├── helpers.py               # Shared analyzer helpers
│   ├── layout.py                # Data layout detection
│   ├── results.py               # Result object builders
│   ├── schema.py                # Analysis result schema
│   ├── stats_annotator.py       # Statistical annotation helpers
│   └── transforms.py            # Column transforms
├── core/
│   ├── stats.py                 # Pure statistical computation (all math lives here)
│   ├── chart_helpers.py         # Presentation helpers + re-exports from stats.py
│   ├── validators.py            # Spreadsheet format validators
│   ├── registry.py              # PlotTypeConfig chart type registry
│   ├── config.py                # Configuration utilities
│   ├── types.py                 # Shared type definitions
│   ├── outliers.py              # Outlier detection
│   ├── errors.py                # ErrorReporter + file logging
│   ├── presets.py               # Named style presets (load/save)
│   ├── session.py               # Session persistence across launches
│   └── undo.py                  # Command-pattern undo/redo
├── io/
│   ├── export.py                # Journal export specs (Nature/Science/Cell)
│   ├── import_pzfx.py           # GraphPad .pzfx XML importer
│   └── project.py               # .cplot project files (ZIP archives)
└── server/
    └── api.py                   # FastAPI server: /analyze, /render, /upload, etc.
```

### Swift Frontend

```
RefractionApp/
├── project.yml                  # XcodeGen spec (generates .xcodeproj)
└── Refraction/
    ├── App/
    │   ├── RefractionApp.swift  # @main entry point, server lifecycle
    │   └── AppState.swift       # Central @Observable state (experiments, selection)
    ├── Models/
    │   ├── Experiment.swift     # Top-level container: DataTables + Graphs + Analyses
    │   ├── DataTable.swift      # Data table within an experiment
    │   ├── Graph.swift          # Graph within an experiment (chart type, config, spec)
    │   ├── Analysis.swift       # Statistical analysis within an experiment
    │   ├── RenderStyle.swift    # Render style presets (Default/Prism/ggplot2/Matplotlib)
    │   ├── ChartType.swift      # Chart type enum (29 types)
    │   ├── ChartConfig.swift    # ~40 config properties + toDict()
    │   ├── TableType.swift      # Data table type enum (XY, Column, etc.)
    │   ├── FormatGraphSettings.swift   # Graph formatting settings
    │   ├── FormatAxesSettings.swift    # Axes formatting settings
    │   ├── ProjectState.swift   # Project state for save/load
    │   ├── StatsTestCatalog.swift      # Stats test encyclopedia
    │   └── ArchitectureGuideCatalog.swift  # Architecture reference content
    ├── Services/
    │   ├── APIClient.swift      # HTTP client (actor, singleton)
    │   ├── PythonServer.swift   # Python subprocess manager
    │   └── DebugLog.swift       # Centralized debug logger (API trace, engine logs)
    ├── Views/
    │   ├── ContentView.swift    # Root layout
    │   ├── ErrorView.swift      # Error display + parsing
    │   ├── ToolbarBanner.swift  # Toolbar status banner
    │   ├── DebugConsoleView.swift    # Debug console with API trace
    │   ├── ExportChartDialog.swift   # Export (DPI, format, size)
    │   ├── LaTeXView.swift      # LaTeX formula renderer
    │   ├── Chart/
    │   │   ├── ChartCanvasView.swift       # Core Graphics canvas rendering
    │   │   ├── ChartOverlayView.swift      # Interactive overlay (hit regions, zoom)
    │   │   ├── FormatGraphDialog.swift     # Prism-style Format Graph dialog
    │   │   ├── FormatAxesDialog.swift      # Prism-style Format Axes dialog
    │   │   └── FormatSettingsMerger.swift  # Merges format overrides into ChartSpec
    │   ├── Sidebar/
    │   │   ├── NavigatorView.swift         # Experiment navigator
    │   │   ├── ChartSidebarView.swift      # Chart type list
    │   │   ├── NewExperimentDialog.swift   # New experiment dialog
    │   │   ├── NewDataTableDialog.swift    # New data table dialog
    │   │   └── NewGraphDialog.swift        # New graph dialog
    │   ├── Sheets/
    │   │   ├── GraphSheetView.swift        # Graph sheet container
    │   │   ├── DataTableView.swift         # Spreadsheet-style data editor
    │   │   ├── ResultsSheetView.swift      # Statistical results sheet
    │   │   ├── InfoSheetView.swift         # Info/metadata sheet
    │   │   ├── AnalyzeDataDialog.swift     # Analyze data dialog
    │   │   ├── StatsWikiDialog.swift       # Stats test encyclopedia
    │   │   ├── StatsTestDetailDialog.swift # Test detail dialog
    │   │   └── ArchitectureGuideDialog.swift # Architecture reference
    │   ├── Results/
    │   │   └── ResultsView.swift           # Stats results table
    │   └── Config/
    │       ├── ConfigTabView.swift    # Tab container
    │       ├── DataTabView.swift      # File + labels
    │       ├── AxesTabView.swift      # Axis config
    │       ├── StyleTabView.swift     # Visual style
    │       └── StatsTabView.swift     # Statistical tests
    └── Resources/
        └── SampleData/
            ├── drug_treatment.xlsx
            ├── time_series.xlsx
            └── survival_data.xlsx
```

### Renderer Package

```
RefractionRenderer/Sources/RefractionRenderer/
├── ChartSpec.swift          # ChartSpec/GroupSpec/StyleSpec/AxisSpec structs
├── AxisRenderer.swift       # Axes, ticks, labels, grid
├── BarRenderer.swift        # Bar charts + error bars
├── BoxRenderer.swift        # Box plots
├── ViolinRenderer.swift     # Violin plots (KDE)
├── ScatterRenderer.swift    # Scatter plots
├── LineRenderer.swift       # Line graphs
├── HistogramRenderer.swift  # Histograms
├── GroupedBarRenderer.swift # Grouped bar charts
├── StackedBarRenderer.swift # Stacked bar charts
├── DotPlotRenderer.swift    # Dot plots
├── BeforeAfterRenderer.swift # Before/after paired charts
├── KaplanMeierRenderer.swift # Survival curves
├── BracketRenderer.swift    # Significance brackets
├── HitRegion.swift          # Interactive hit testing
├── RenderHelpers.swift      # Shared drawing utilities
└── RenderTheme.swift        # Theme definitions
```

### Tests

```
tests/
├── conftest.py                  # Shared pytest fixtures
├── test_stats.py                # Statistical verification
├── test_validators.py           # Spreadsheet validator tests
├── test_api.py                  # FastAPI endpoint tests
├── test_analysis.py             # Dedicated analyzer tests
├── test_stats_exhaustive.py     # Exhaustive statistical coverage
├── test_deficiency_fixes.py     # Deficiency fix verification
├── test_render_contract.py      # Render contract tests
├── test_phase6_qa.py            # QA regression tests
├── engine/                      # Pure computational tests
│   ├── test_stats_core.py       # Core stats function tests
│   ├── test_helpers.py          # Helper function tests
│   ├── test_validators.py       # Validator unit tests
│   ├── test_layout.py           # Layout detection tests
│   ├── test_transforms.py       # Transform tests
│   ├── test_curve_models.py     # Curve model tests
│   ├── test_results.py          # Result builder tests
│   └── test_project_v2.py       # Project file v2 tests
└── integration/                 # API + pipeline integration tests
    ├── test_api.py              # API integration tests
    └── test_pipeline.py         # End-to-end pipeline tests

run_all.py                       # 10-suite unified test runner (must pass before commit)
```
