# Refraction SwiftUI Client -- Comprehensive Architecture Guide

This document describes the entire SwiftUI client implementation. Combined
with CLAUDE.md, it gives a new Claude instance everything needed to understand
and modify the macOS frontend.

---

## 1. Architecture Overview

The app follows a single-window, observable-state architecture:

```
RefractionApp (@main)
  |-- @State AppState          (central observable state)
  |-- @State PythonServer      (subprocess lifecycle)
  |
  v
ContentView
  |-- ToolbarBanner            (Prism-style ribbon at top)
  |-- NavigatorView            (left sidebar: experiments tree)
  |-- Content area             (right: DataTableView / GraphSheetView / ResultsSheetView)
  |-- DebugConsolePanel        (bottom panel when developer mode on)
```

**Key patterns:**
- `AppState` is injected as an `@Environment` object. Every view that needs
  project state reads from it.
- `PythonServer` is also injected via `@Environment` for server status display.
- All models (`Experiment`, `DataTable`, `Graph`, `Analysis`) are `@Observable`
  reference types (classes), enabling fine-grained SwiftUI updates.
- The renderer package (`RefractionRenderer`) is a standalone Swift Package
  with zero app dependencies -- it only reads `ChartSpec` structs.

---

## 2. Data Model

### Hierarchy

```
Project (implicit, managed by AppState)
  +-- Experiment[]
        +-- DataTable[]     (data storage: columns + rows of CellValue)
        +-- Graph[]         (chart config + cached ChartSpec + format settings)
        +-- Analysis[]      (standalone statistical results + notes)
```

### Experiment (Experiment.swift)
- `@Observable` class with `id: UUID`, `label: String`, `dataTables`, `graphs`, `analyses`.
- Factory: `Experiment.new(label:)` creates an empty experiment.
- Owns CRUD methods for its children: `addDataTable()`, `addGraph()`, `addAnalysis()`,
  `removeDataTable()`, etc.
- `hasData` returns true if any data table has loaded data.
- `validChartTypes(for:)` returns chart types valid for a specific DataTable's type.

### DataTable (DataTable.swift)
- `@Observable` class: `id`, `label`, `tableType: TableType`, `columns: [String]`,
  `rows: [[CellValue]]`, `originalFileName: String?`.
- `CellValue` enum: `.number(Double)`, `.text(String)`, `.empty`. Codable.
- `hasData` = columns and rows are non-empty.
- `setCell(row:col:value:)` auto-expands the grid.
- `toAnalyzePayload()` builds `{"columns": [...], "rows": [[...]]}` dict for the API.
- `toJSON()` / `fromJSON()` for .refract bundle persistence (stores columns + rows).
- `loadFromServerResponse(columns:rows:)` populates from server data preview.

### Graph (Graph.swift)
- `@Observable` class: `id`, `label`, `dataTableID: UUID`, `chartType: ChartType`,
  `chartConfig: ChartConfig`, `chartSpec: ChartSpec?`, `formatSettings: FormatGraphSettings`,
  `formatAxesSettings: FormatAxesSettings`, `renderStyle: RenderStyle`, `isLoading`, `rawJSON`,
  `zoomLevel: Double`.
- `chartSpec` is the cached engine result -- set after a successful `/render` call.
- `applyRenderStyle(_:)` applies a preset to both format settings objects.
- Each Graph links to exactly one DataTable by `dataTableID`.

### Analysis (Analysis.swift)
- `@Observable` class: `id`, `label`, `dataTableID: UUID`, `analysisType: String`,
  `statsResults: StatsResult?`, `notes: String`, `rawJSON: String`.
- Created by `AppState.runAnalysis()` which calls `/analyze-stats`.

### CellValue (DataTable.swift)
- `.number(Double)`, `.text(String)`, `.empty`.
- `displayString` formats numbers without trailing `.0` for integers.
- `doubleValue` attempts numeric extraction from any variant.
- Codable: numbers encode as JSON numbers, text as strings, empty as null.

### TableType (TableType.swift)
- Enum: `xy`, `column`, `grouped`, `contingency`, `survival`, `parts`,
  `multipleVariables`, `nested`, `twoWay`, `comparison`, `meta`.
- Each has `validChartTypes: [ChartType]` constraining which graphs can be created.
- Matches GraphPad Prism's table types plus additional types (twoWay, comparison, meta).

### ChartType (ChartType.swift)
- 29-case enum matching all engine chart types. `rawValue` is the API key (e.g. `"grouped_bar"`).
- Properties: `label` (UI name), `category: ChartCategory` (for sidebar grouping),
  `hasPoints`, `hasErrorBars`, `hasStats`, `sfSymbol`.
- `ChartType.byCategory` returns grouped tuples for sidebar display.
- 8 categories: Column, XY, Grouped, Distribution, Survival, Comparison, Specialized, Statistical.

### ChartConfig (ChartConfig.swift)
- `@Observable` class with ~40 properties organized by tab (Data, Labels, Style, Stats).
- `toDict()` serializes to the flat kwargs dict sent to Python `/render`.
- `loadFromDict(_:)` restores from saved project.
- Properties include: `errorType`, `statsTest`, `posthoc`, `mcCorrection`, `control`,
  `showPoints`, `barWidth`, `yScale`, `yMin`/`yMax`, `refLineValue`/`refLineLabel`, etc.

---

## 3. View Hierarchy

### ContentView (ContentView.swift)
Root layout with three sections stacked vertically:
1. `ToolbarBanner` -- Prism-style ribbon at top.
2. Main content: `HStack` of NavigatorView (fixed left sidebar, resizable 180-400px)
   + content area (dispatched by `activeItemKind`).
3. `DebugConsolePanel` -- shown at bottom when `developerMode` is true.

Content area dispatch (`contentArea` computed property):
- Error state -> `ErrorView`
- `.dataTable` -> `DataTableView`
- `.graph` -> `GraphSheetView`
- `.analysis` -> `ResultsSheetView`
- No selection -> blank canvas

The sidebar divider is draggable. The debug console divider is also draggable (100-500px).

### NavigatorView (Sidebar/NavigatorView.swift)
Prism-style experiment tree:
- Top bar: "New Experiment" button, expand/collapse all.
- Search bar: filters experiments and children by name.
- For each experiment: disclosure group with sections for Data Tables, Graphs, Analyses.
- Items are selectable (sets `appState.activeItemID` / `activeItemKind`).
- Supports drag-and-drop reordering within sections.
- Context menus for rename, delete, add graph/table.
- Items show SF Symbol icons colored by type.

### DataTableView (Sheets/DataTableView.swift)
- If no data: shows file picker prompt with "Open File..." button.
- If data loaded: shows spreadsheet grid with editable cells.
- Toolbar shows filename, table type, row/column count, add row/column buttons.
- Cell edits register undo via `appState.registerCellEdit()`.
- File import: accepts .xlsx/.xls/.csv via NSOpenPanel, calls `appState.uploadFile()`.

### GraphSheetView (Sheets/GraphSheetView.swift)
- Mini toolbar: chart type label + linked data table name.
- Chart area: renders `ChartCanvasView` with merged format settings.
- `mergedSpec` computed property: calls `applyFormatSettings()` to merge
  FormatGraphSettings + FormatAxesSettings + RenderStyle into the engine ChartSpec.
- Zoom control strip at bottom: Fit button, +/- buttons, slider (0.25x-4.0x), percentage.
- Auto-generates chart when graph appears with no spec and data is available
  (via `.task(id:)` modifier keyed on graph ID + data dimensions).
- Chart canvas is wrapped in a ScrollView for zoomed viewing.

### ResultsSheetView (Sheets/ResultsSheetView.swift)
- Displays statistical analysis results from `Analysis.notes`.
- Shows raw JSON in developer mode.

---

## 4. AppState (AppState.swift)

Central `@Observable` singleton managing all project state:

### State properties
- `experiments: [Experiment]` -- all experiments in the project.
- `activeExperimentID: UUID?` -- currently selected experiment.
- `activeItemID: UUID?` -- currently selected item (DataTable/Graph/Analysis).
- `activeItemKind: ItemKind?` -- `.dataTable`, `.graph`, or `.analysis`.
- `developerMode: Bool` -- true in DEBUG, false in RELEASE.
- `projectFilePath: URL?` -- nil for unsaved projects.
- `hasUnsavedChanges: Bool` -- dirty tracking.
- `isLoading: Bool` -- whether a render/analysis is in flight.
- `error: String?` -- current error message.

### Computed properties
- `activeExperiment` / `activeGraph` / `activeDataTable` / `activeAnalysis` --
  resolve the active item from experiments array.
- `activeGraphDataTable` -- the DataTable linked to the active graph.
- `projectDisplayName` -- title bar text (filename or "Untitled.refract", with "Edited" suffix).

### Experiment/Item CRUD
- `addExperiment()`, `removeExperiment()`, `moveExperiment()`.
- `addDataTable()`, `removeDataTable()`, `moveDataTable()`.
- `addGraph()`, `removeGraph()`, `moveGraph()` -- `addGraph` auto-calls `generatePlot()`.
- `addAnalysis()`, `removeAnalysis()`, `moveAnalysis()`.
- `selectItem(_:kind:)` -- searches all experiments, sets active IDs.
- All mutations call `markDirty()` and register undo actions.

### File Operations
- `uploadFile(url:for:)` -- uploads file via `APIClient.shared.upload()`,
  then fetches data via `/data-preview` and populates the DataTable in memory.
- `generatePlot()` -- sends inline data + config to `/render`, stores ChartSpec
  and rawJSON on the Graph. Includes single retry on failure.
- `runAnalysis()` -- calls `/analyze-stats`, creates an Analysis item with
  formatted notes (summary, descriptive stats, comparisons, recommendation).

### Project Save/Load
- `requestNewProject()` -- prompts save if dirty, then calls `newProject()`.
- `newProject()` -- resets to blank state with one empty experiment.
- `openProjectFile()` -- NSOpenPanel for `.refract` files.
- `loadProjectFromURL(_:)` -- calls `loadBundleProject()`.
- `saveProjectFile()` -- saves to existing path or prompts Save As.
- `saveProjectFileAs()` -- NSSavePanel for `.refract` files.
- `saveProject()` -- writes `ProjectState` to `~/.refraction/project.json` (session restore).
- `loadProjectIfExists()` -- restores from `~/.refraction/project.json` on launch.

### Undo/Redo
- Uses a standard `UndoManager`.
- `canUndo` / `canRedo` are manually tracked (UndoManager doesn't notify @Observable).
- `refreshUndoState()` must be called after any undo/redo action.
- `registerCellEdit()` registers cell-level undo with proper redo chain.
- All CRUD operations register undo/redo handlers.

---

## 5. Toolbar and Dialogs

### ToolbarBanner (ToolbarBanner.swift)
Prism-style ribbon organized into groups separated by vertical dividers:

| Group | Buttons | Actions |
|-------|---------|---------|
| File | New, Open (menu), Save | `requestNewProject()`, `openProjectFile()`, `saveProjectFile()` |
| Sheet | Table, Graph, Delete | Open NewDataTableDialog, NewGraphDialog, delete selected item |
| Undo | Undo, Redo | `undoManager.undo()` / `.redo()` |
| Clipboard | Copy | Copies chart as image to pasteboard |
| Analysis | Analyze | Opens AnalyzeDataDialog |
| Format | Data, Format, Axes, Style, Stats | Opens DataSettingsDialog, FormatGraphDialog, FormatAxesDialog, StyleSettingsDialog, StatsSettingsDialog |
| Insert | Text, Line, Bracket | Disabled (not yet implemented) |
| View | Zoom In, Zoom Out, Fit | Disabled (not yet implemented) |
| Reference | Wiki, Guide | Opens StatsWikiDialog, ArchitectureGuideDialog |
| Export | Export | Opens ExportChartDialog |

Buttons are colored when active, grayed when disabled (e.g. no experiment, no data, no graph).

### Dialogs (opened as sheets)
- **NewDataTableDialog** -- choose table type, create a new DataTable.
- **NewGraphDialog** -- choose chart type (filtered by data table type), create a Graph.
- **AnalyzeDataDialog** -- choose analysis type, run standalone statistical analysis.
- **FormatGraphDialog** -- symbols, bars, error bars, lines, area fill, legend.
- **FormatAxesDialog** -- axis titles, ranges, ticks, grid, frame style, fonts.
- **DataSettingsDialog** -- data tab settings for the active graph.
- **StatsSettingsDialog** -- statistical test settings for the active graph.
- **StyleSettingsDialog** -- render style preset picker + visual style overrides.
- **StatsWikiDialog** -- statistical test encyclopedia (catalog of tests with LaTeX formulas).
- **ArchitectureGuideDialog** -- architecture reference guide.
- **ExportChartDialog** -- export chart as PNG/PDF/SVG with DPI and size options.

---

## 6. Chart Rendering Pipeline

Data flows through a multi-stage pipeline:

```
DataTable (in-memory CellValue grid)
    |
    | toAnalyzePayload() -> {"columns": [...], "rows": [[...]]}
    v
APIClient.analyzeWithRawJSON(chartType, config, inlineData)
    |
    | POST /render -> { chart_type, kw: { data: {...}, ...config } }
    v
Python engine (dedicated analyzer -> ChartSpec JSON)
    |
    | JSON decode -> ChartSpec (groups, style, axes, stats, brackets)
    v
Graph.chartSpec = spec  (cached on the Graph object)
    |
    | GraphSheetView.mergedSpec
    v
applyFormatSettings(spec, graphSettings, axesSettings, renderStyle)
    |
    | Produces new ChartSpec with format overrides merged in
    v
ChartCanvasView(spec: mergedSpec)
    |
    | SwiftUI Canvas { context, size in ... }
    v
Renderers (AxisRenderer, BarRenderer, BoxRenderer, etc.)
    |
    | Core Graphics drawing into GraphicsContext
    v
Rendered chart on screen
```

### Key details:
1. **Inline data**: Data is sent inline as JSON (not file paths). `DataTable.toAnalyzePayload()`
   converts the CellValue grid to `{"columns": [...], "rows": [[number|string|null]]}`.
2. **Format merging**: `FormatSettingsMerger.applyFormatSettings()` creates a NEW ChartSpec
   with user overrides. This happens on every render -- no engine call needed.
3. **Split axis rendering**: `AxisRenderer.drawBackground()` is called BEFORE chart data
   (grid lines, plot area fill), then chart-specific renderer, then `AxisRenderer.drawForeground()`
   (spines, ticks, labels, title) so axes draw ON TOP of chart data.
4. **Fixed bar slots**: Bar-like charts use `idealSlotWidth = 90pt` per group to prevent
   bars from stretching. The plot area is centered horizontally.
5. **Y range merging**: The canvas computes a Y range from both engine-provided range AND
   raw data points (scatter points may exceed mean +/- error).

---

## 7. Renderer Package (RefractionRenderer)

A standalone Swift Package in `RefractionRenderer/` with no app dependencies.
Imported by both the app and any future test targets.

### ChartSpec (ChartSpec.swift)
The core data structure decoded from the Python engine's JSON response:

```
ChartSpec
  +-- chartType: String          ("bar", "box", "scatter", etc.)
  +-- groups: [GroupData]        (one per data group/series)
  |     +-- name: String
  |     +-- values: ValuesData   (raw, mean, sem, sd, ci95, n)
  |     +-- color: String        (hex color from palette)
  +-- style: StyleSpec           (colors, showPoints, barWidth, symbolShape, ...)
  +-- axes: AxisSpec             (title, labels, yRange, yTicks, grid settings, ...)
  +-- stats: StatsResult?        (test name, p-value, comparisons, normality)
  +-- brackets: [Bracket]        (significance brackets between group indices)
  +-- referenceLine: ReferenceLine?  (horizontal reference line)
  +-- data: [String: JSONValue]?     (chart-type-specific payload)
```

`RenderResponse` is the JSON envelope: `{ ok: Bool, spec: ChartSpec?, error: String? }`.

`JSONValue` is a recursive enum for arbitrary JSON: `.string`, `.number`, `.bool`,
`.array([JSONValue])`, `.object([String: JSONValue])`, `.null`.

### Renderers
Each renderer is a static enum with a `draw(in:plotRect:...)` method:

| Renderer | Chart types |
|----------|-------------|
| `AxisRenderer` | All charts (background: grid/fill; foreground: spines/ticks/labels/title) |
| `BarRenderer` | bar, column_stats, waterfall, pyramid |
| `BoxRenderer` | box |
| `ViolinRenderer` | violin |
| `ScatterRenderer` | scatter |
| `LineRenderer` | line |
| `HistogramRenderer` | histogram |
| `GroupedBarRenderer` | grouped_bar |
| `StackedBarRenderer` | stacked_bar |
| `DotPlotRenderer` | dot_plot, subcolumn_scatter |
| `BeforeAfterRenderer` | before_after |
| `KaplanMeierRenderer` | kaplan_meier |
| `BracketRenderer` | Significance brackets (drawn after chart data) |

### Support files
- `RenderHelpers.swift` -- shared drawing utilities (color parsing, coordinate mapping).
- `HitRegion.swift` -- interactive hit testing for chart elements (click detection).
- `RenderTheme.swift` -- renderer theme definitions.

### Not yet implemented
These chart types show a placeholder message: area_chart, curve_fit, bubble,
lollipop, ecdf, qq_plot, raincloud, forest_plot, bland_altman, contingency,
chi_square_gof, heatmap, two_way_anova, repeated_measures.

---

## 8. Format System

Three layers of visual configuration:

### FormatGraphSettings (FormatGraphSettings.swift)
Controls data element appearance. `@Observable`, `Codable`. Properties:
- **Symbols**: showSymbols, symbolColor, symbolShape, symbolSize, symbolBorderColor/Thickness.
- **Bars**: showBars, barColor, barWidth, barFillOpacity, barBorderColor/Thickness, barPattern.
- **Error bars**: showErrorBars, errorBarColor, errorBarDirection (both/up/down),
  errorBarStyle (tCap/line), errorBarThickness.
- **Lines**: showConnectingLine, lineColor, lineThickness, lineStyle (solid/dashed/dotted).
- **Area fill**: showAreaFill, areaFillColor, areaFillPosition (below/above), areaFillAlpha.
- **Legend**: showLegend.
- **Labels**: labelPoints.

### FormatAxesSettings (FormatAxesSettings.swift)
Controls axes and frame appearance. `@Observable`, `Codable`. Properties:
- **Frame**: originMode, axisThickness, axisColor, plotAreaColor, pageBackground,
  frameStyle (noFrame/plain/shadow), hideAxes (showBoth/hideX/hideY/hideBoth).
- **Grid**: majorGrid/minorGrid (none/solid/dashed/dotted), colors, thicknesses.
- **X axis**: title, titleFontSize, tickDirection, tickLength, labelFontSize, labelRotation.
- **Y axis**: title, titleFontSize, tickDirection, tickLength, labelFontSize,
  autoRange, min/max, tickInterval, scale (linear/log).
- **Titles**: chartTitle, chartTitleFontSize, globalFontName.

### RenderStyle (RenderStyle.swift)
Four presets: `default`, `prism`, `ggplot2`, `matplotlib`.
Each has a color palette and `apply(to:axes:)` method that sets properties on
FormatGraphSettings and FormatAxesSettings:

| Style | Key visual traits |
|-------|-------------------|
| Default | Clean L-shape, light grid, standard symbols |
| Prism | Bold L-shaped axes, no grid, 50% opacity bars with colored border, 45 degree labels |
| ggplot2 | Gray background (#EBEBEB), white grid lines, no axis lines, no ticks |
| Matplotlib | Full box frame, dashed grid, inward ticks |

All fonts are standardized to 12pt Arial Bold across all styles.

### FormatSettingsMerger (FormatSettingsMerger.swift)
`applyFormatSettings(spec:graphSettings:axesSettings:renderStyle:)` -> `ChartSpec`

Merges app-layer format settings into the renderer's ChartSpec structs.
Creates a NEW ChartSpec with overrides applied -- the original spec is not mutated.
Maps between app-layer types (FormatGraphSettings enums) and renderer-layer strings
(StyleSpec/AxisSpec string properties).

---

## 9. File Format (.refract)

A `.refract` file is a directory bundle (not a ZIP):

```
MyProject.refract/
  project.json          (metadata: experiments, graphs, analyses, selection state)
  data/
    {UUID}.json         (one per DataTable: {"columns": [...], "rows": [[...]]})
    ...
```

### project.json structure
```json
{
  "experiments": [
    {
      "id": "UUID",
      "label": "Experiment 1",
      "description": "",
      "createdAt": 1234567890.0,
      "lastModifiedAt": 1234567890.0,
      "dataTables": [
        { "id": "UUID", "label": "Column 1", "tableType": "column", "originalFileName": "data.xlsx" }
      ],
      "graphs": [
        { "id": "UUID", "label": "Bar Chart", "dataTableID": "UUID", "chartType": "bar",
          "chartConfig": { ... }, "formatSettings": { ... }, "formatAxesSettings": { ... },
          "renderStyle": "prism" }
      ],
      "analyses": [
        { "id": "UUID", "label": "Results", "dataTableID": "UUID",
          "analysisType": "parametric", "notes": "..." }
      ]
    }
  ],
  "activeExperimentID": "UUID",
  "activeItemID": "UUID",
  "activeItemKind": "graph"
}
```

### Save flow
1. `AppState.saveToPath(url)` creates the bundle directory + data/ subdirectory.
2. Each DataTable with data is written as `data/{UUID}.json` via `DataTable.toJSON()`.
3. `buildProjectMetadata()` generates the project.json with all experiment/graph/analysis
   metadata, chart configs, format settings (serialized to JSON dicts).
4. Selection state (activeExperimentID, activeItemID, activeItemKind) is included.

### Load flow
1. `AppState.loadBundleProject(from:)` reads `project.json`.
2. For each experiment, DataTables are loaded from `data/{UUID}.json` via `DataTable.fromJSON()`.
3. Graphs are restored with their chart configs, format settings, and render styles.
4. Analyses are restored with their notes.
5. Selection state is restored.

### Session restore
Separately from .refract files, `ProjectState` provides lightweight session restore
via `~/.refraction/project.json` (written on app quit, read on launch).
This uses a Codable struct and includes columns/rows inline (no separate data files).

---

## 10. API Integration

### APIClient (APIClient.swift)
Actor-based singleton (`APIClient.shared`) communicating with Python on `http://127.0.0.1:7331`.

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `analyze()` | POST /render | Send ChartConfig, get ChartSpec back |
| `analyzeWithRawJSON()` | POST /render | Same + raw JSON string for debug display |
| `health()` | GET /health | Check server liveness |
| `upload()` | POST /upload | Multipart file upload, returns server-side path |
| `listSheets()` | POST /sheet-list | Excel sheet names |
| `validateTable()` | POST /validate-table | Validate data against table type |
| `renderLatex()` | POST /render-latex | LaTeX to PNG (for Stats Wiki) |
| `dataPreview()` | POST /data-preview | Read data from uploaded file |
| `recommendTest()` | POST /recommend-test | Suggest statistical test |
| `analyzeStats()` | POST /analyze-stats | Run standalone statistics |

### Request/Response flow
All POST requests go through a private `post(path:body:)` method that:
1. Serializes body to JSON.
2. Logs the request via `DebugLog.shared.logRequest()`.
3. Sends via URLSession.
4. Logs response via `DebugLog.shared.logResponse()`.
5. Extracts engine trace (`_trace` array) from response if present.
6. Extracts Python traceback on error responses.
7. Returns raw Data for caller to decode.

### Inline data flow
The primary analysis path sends data inline (not as file paths):
1. `DataTable.toAnalyzePayload()` -> `{"columns": [...], "rows": [[...]]}`.
2. This dict is passed as `inlineData` to `APIClient.analyzeWithRawJSON()`.
3. The API client adds it as `kw["data"]` in the request body.
4. The Python engine reads it from `kw["data"]` instead of reading from disk.

---

## 11. Debug System

### DebugLog (DebugLog.swift)
`@Observable` singleton (`DebugLog.shared`) with a ring buffer of 500 entries.

Entry kinds:
- `REQ` -- API request (method + path + body)
- `RES` -- API response (status + path + duration)
- `ERR` -- Errors (API errors, tracebacks)
- `APP` -- Application events (addExperiment, generatePlot, save/load)
- `ENGINE` -- Python engine trace lines (from `_trace` in responses)
- `UI` -- User interaction events (button clicks, dialog open/close)
- `VRB` -- Verbose/high-frequency events (cell edits, re-renders), hidden by default

### Developer mode
- Enabled by default in DEBUG builds, disabled in RELEASE.
- Toggled via terminal icon in window toolbar.
- Shows the DebugConsolePanel at bottom of ContentView.
- When on, generates charts with `_debug: true` flag for engine trace output.

### PythonServer (PythonServer.swift)
Manages the Python uvicorn subprocess:
- States: `idle`, `starting`, `running`, `failed(String)`.
- `start()`: Resolves Python binary (bundled > REFRACTION_PYTHON env > well-known paths > system),
  launches subprocess, polls `/health` every 0.5s until ready (15s timeout).
- `stop()`: SIGTERM then SIGKILL after 2s.
- Auto-restarts once on unexpected crash. Shows alert on second crash.
- Crash logs written to `~/Library/Logs/Refraction/crash.log`.
- Server port: 7331.
- Resolves project root via multiple strategies: REFRACTION_ROOT env > bundle walk-up >
  SOURCE_ROOT > worktree scan > known paths > cwd.

---

## 12. Undo/Redo

AppState owns a standard `UndoManager`. Because UndoManager doesn't integrate
with Swift's @Observable, `canUndo`/`canRedo` are manually tracked Bool properties
updated by `refreshUndoState()`.

### Tracked actions
- Add/remove experiment (restores full experiment on undo)
- Add/remove data table (re-inserts at original index on undo)
- Add/remove graph (re-inserts at original index on undo)
- Add/remove analysis (re-inserts at original index on undo)
- Cell edits in data tables (restores old CellValue on undo)

### Implementation pattern
Each CRUD method registers an undo closure that reverses the operation,
and within that closure registers a redo closure. This creates a proper
undo/redo chain. Example:
```swift
undoManager.registerUndo(withTarget: self) { target in
    target.removeGraph(id: graphID)    // undo = remove
}
undoManager.setActionName("Add Graph")
```

Menu commands (Cmd+Z / Cmd+Shift+Z) call `undoManager.undo()`/`.redo()` then
`refreshUndoState()`. The ToolbarBanner also has undo/redo buttons.

---

## 13. Key Files Reference

### App layer
| File | Purpose |
|------|---------|
| `App/RefractionApp.swift` | @main entry point; creates AppState + PythonServer, manages WindowGroup with menus |
| `App/AppState.swift` | Central @Observable state: experiments, selection, CRUD, undo, save/load, chart generation |

### Models
| File | Purpose |
|------|---------|
| `Models/Experiment.swift` | Top-level container owning DataTables + Graphs + Analyses; CRUD methods |
| `Models/DataTable.swift` | In-memory data grid (CellValue matrix); JSON persistence; analyze payload builder |
| `Models/Graph.swift` | Graph config + cached ChartSpec + format settings; linked to DataTable by ID |
| `Models/Analysis.swift` | Statistical analysis results + notes; linked to DataTable by ID |
| `Models/ChartType.swift` | 29-case enum: API keys, labels, categories, capabilities (hasPoints/hasErrorBars/hasStats) |
| `Models/TableType.swift` | 11-case enum: Prism table types + extras; each constrains valid chart types |
| `Models/ChartConfig.swift` | ~40 observable config properties; toDict() for API serialization |
| `Models/FormatGraphSettings.swift` | Visual overrides for data elements (symbols, bars, errors, lines, area, legend) |
| `Models/FormatAxesSettings.swift` | Visual overrides for axes (frame, grid, ticks, labels, fonts, scale) |
| `Models/RenderStyle.swift` | 4 presets (Default/Prism/ggplot2/Matplotlib) with palettes and apply() methods |
| `Models/ProjectState.swift` | Lightweight Codable snapshot for session restore (~/.refraction/project.json) |
| `Models/StatsTestCatalog.swift` | Statistical test encyclopedia content (for Stats Wiki dialog) |
| `Models/ArchitectureGuideCatalog.swift` | Architecture reference guide content |

### Views
| File | Purpose |
|------|---------|
| `Views/ContentView.swift` | Root layout: toolbar + sidebar + content area + debug console |
| `Views/ToolbarBanner.swift` | Prism-style ribbon with grouped buttons; opens all dialogs |
| `Views/ErrorView.swift` | Error display with retry/dismiss |
| `Views/DebugConsoleView.swift` | Debug console with filtering, search, detail pane |
| `Views/ExportChartDialog.swift` | Export chart as PNG/PDF/SVG with DPI/size options |
| `Views/LaTeXView.swift` | LaTeX formula renderer (calls /render-latex) |
| `Views/Sidebar/NavigatorView.swift` | Experiment tree: sections for DataTables/Graphs/Analyses; search, drag-drop |
| `Views/Sidebar/ChartSidebarView.swift` | Chart type picker list |
| `Views/Sidebar/NewExperimentDialog.swift` | Create new experiment |
| `Views/Sidebar/NewDataTableDialog.swift` | Create new data table (choose type) |
| `Views/Sidebar/NewGraphDialog.swift` | Create new graph (choose chart type + data table) |
| `Views/Sheets/GraphSheetView.swift` | Graph view: merges format settings, renders ChartCanvasView, zoom strip |
| `Views/Sheets/DataTableView.swift` | Spreadsheet editor or file picker; cell editing with undo |
| `Views/Sheets/ResultsSheetView.swift` | Statistical results display |
| `Views/Sheets/InfoSheetView.swift` | Info/metadata sheet |
| `Views/Sheets/AnalyzeDataDialog.swift` | Run standalone statistical analysis |
| `Views/Sheets/DataSettingsDialog.swift` | Data tab settings for active graph |
| `Views/Sheets/StatsSettingsDialog.swift` | Stats test settings for active graph |
| `Views/Sheets/StyleSettingsDialog.swift` | Render style preset picker |
| `Views/Sheets/StatsWikiDialog.swift` | Stats test encyclopedia browser |
| `Views/Sheets/StatsTestDetailDialog.swift` | Individual test detail view |
| `Views/Sheets/ArchitectureGuideDialog.swift` | Architecture reference guide |
| `Views/Chart/ChartCanvasView.swift` | SwiftUI Canvas: dispatches to renderers based on chartType |
| `Views/Chart/FormatGraphDialog.swift` | Format Graph dialog (Prism-style property editor) |
| `Views/Chart/FormatAxesDialog.swift` | Format Axes dialog (Prism-style property editor) |
| `Views/Chart/FormatSettingsMerger.swift` | Merges format overrides into ChartSpec without engine call |
| `Views/Chart/ChartOverlayView.swift` | Interactive overlay for hit regions and zoom |

### Services
| File | Purpose |
|------|---------|
| `Services/APIClient.swift` | Actor-based HTTP client; all endpoint methods; response types (AnyCellValue, etc.) |
| `Services/PythonServer.swift` | Python subprocess lifecycle; health polling; crash recovery; project root resolution |
| `Services/DebugLog.swift` | Centralized debug logger; ring buffer of 500 entries; 7 entry kinds |

### Renderer package (RefractionRenderer/)
| File | Purpose |
|------|---------|
| `ChartSpec.swift` | All Decodable structs: ChartSpec, GroupData, ValuesData, StyleSpec, AxisSpec, StatsResult, Bracket, JSONValue |
| `AxisRenderer.swift` | Split-phase axis drawing: drawBackground (grid) + drawForeground (spines/ticks/labels) |
| `BarRenderer.swift` | Bar charts with error bars and data points overlay |
| `BoxRenderer.swift` | Box plots with whiskers, median, quartiles |
| `ViolinRenderer.swift` | Violin plots with KDE curves |
| `ScatterRenderer.swift` | Scatter plots with configurable symbols |
| `LineRenderer.swift` | Line graphs with optional area fill |
| `HistogramRenderer.swift` | Histograms with bin rendering |
| `GroupedBarRenderer.swift` | Grouped (side-by-side) bar charts |
| `StackedBarRenderer.swift` | Stacked bar charts |
| `DotPlotRenderer.swift` | Dot plots and subcolumn scatter |
| `BeforeAfterRenderer.swift` | Before/after paired line charts |
| `KaplanMeierRenderer.swift` | Kaplan-Meier survival curves |
| `BracketRenderer.swift` | Significance brackets between groups |
| `HitRegion.swift` | Interactive hit testing geometry |
| `RenderHelpers.swift` | Shared drawing utilities (color hex parsing, coordinate mapping) |
| `RenderTheme.swift` | Renderer theme definitions |
