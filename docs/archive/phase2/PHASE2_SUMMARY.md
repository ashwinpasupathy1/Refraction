# Phase 2 Build Summary

## Test Results
- Total tests: 520
- Passing: 520
- Failing: 0

## New Files Created

### Infrastructure modules
- `plotter_registry.py` (475 lines) — PlotTypeConfig registry extracted from plotter_barplot_app.py
- `plotter_tabs.py` (532 lines) — Multi-tab state: TabState, TabManager, TabBar, draw_tab_icon
- `plotter_app_icons.py` (352 lines) — Sidebar icon drawing for all 29 chart types
- `plotter_presets.py` (163 lines) — Style preset system: load/save named presets as JSON
- `plotter_session.py` (77 lines) — Session persistence: auto-save and restore last-used settings
- `plotter_events.py` (75 lines) — EventBus for decoupled pub/sub messaging
- `plotter_types.py` (121 lines) — Shared type definitions and dataclasses
- `plotter_undo.py` (131 lines) — UndoStack implementing undo/redo for plot parameter changes
- `plotter_errors.py` (99 lines) — ErrorReporter for structured, user-friendly error messages
- `plotter_comparisons.py` (248 lines) — Custom comparison builder UI (select specific group pairs)
- `plotter_project.py` (207 lines) — .cplot project file save/open (ZIP archives)
- `plotter_import_pzfx.py` (316 lines) — GraphPad Prism .pzfx file importer
- `plotter_wiki_content.py` (2,224 lines) — Statistical wiki content (29 sections, 21 references)
- `plotter_app_wiki.py` (522 lines) — Statistical wiki popup viewer (Tk UI)

## Existing Files Modified

- `plotter_barplot_app.py` (6,637 lines) — Wired in all Phase 2 modules; added keyboard shortcuts
  (Cmd+1-9), session persistence, preset selector, project file menu items, wiki menu item,
  undo/redo, custom comparisons UI
- `plotter_functions.py` (6,553 lines) — Fixed pingouin >=0.5 compatibility (`p_unc` vs `p-unc`)
- `tests/test_modular.py` — Extended with Section 13: TabState/TabManager/TabBar tests (19 new tests)
- `CLAUDE.md` — Updated file map, checklist, gotchas list, Phase 2 Changes section
- `README.md` — Updated test counts, architecture section, chart types list, file format table
- `run_all.py` — Updated to run 6 suites (added p1p2p3 suite)

## Features Added

1. **Style presets** — 5 built-in presets (Classic, Publication, Presentation, Minimal, Dark)
2. **Session persistence** — Settings auto-saved on plot run; restored automatically at startup
3. **Project files** — File > Save Project / Open Project (.cplot ZIP format)
4. **GraphPad .pzfx import** — File > Import from GraphPad to extract group data from .pzfx files
5. **Statistical wiki** — Help > Statistical Methods: 29 chart types with formulas and citations
6. **Undo/redo** — Cmd+Z / Cmd+Shift+Z for all plot parameter changes
7. **Keyboard shortcuts** — Cmd+1 through Cmd+9 to switch chart types in the sidebar
8. **Custom comparisons** — UI for selecting arbitrary group pairs for statistical testing
9. **Event bus** — Internal pub/sub wiring for decoupled component communication
10. **Multi-tab architecture** — TabState/TabManager/TabBar infrastructure (UI not yet wired)
11. **14 new infrastructure modules** — Clean separation of concerns; no circular dependencies

## Bugs Fixed

1. `prism_repeated_measures`: `KeyError: 'p-unc'` — pingouin >=0.5 uses `p_unc` (underscore).
   Fixed with version-safe column lookup.

## Known Issues

None blocking. The following are pre-existing known issues documented in CLAUDE.md:
- 7 chart types (area_chart, raincloud, qq_plot, lollipop, waterfall, pyramid, ecdf) exist in
  plotter_functions.py and are tested but not yet wired into the app sidebar
- `_populate_results` for grouped charts merges two-row-header layout incorrectly (cosmetic)
- `_toggle_canvas_mode` checks `plot_type == "bar"` but should also include `"grouped_bar"`
- `ttk.Treeview` heading colours on macOS Aqua theme cannot be styled via ttk.Style

## Verification Checks

- [x] All 520 tests pass (0 failures)
- [x] All 19 modules import cleanly
- [x] No stale `import prism_*` / `from prism_*` references in production code
- [x] No TODO/FIXME/HACK stubs (PLACEHOLDER_COLOR is a constant name, not a stub)
- [x] Wiki content complete: 29 sections, 21 references, no issues
- [x] Documentation updated (CLAUDE.md, README.md)
