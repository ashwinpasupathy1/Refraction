# Phase 2 Build Summary

**Date**: 2026-03-18
**Branch**: phase2/agent-g
**Agents**: A–G (7 agents)

---

## Test Results

- **Total tests**: 520
- **Passing**: 520
- **Failing**: 0
- **Wall time**: ~120 seconds

Note: ~19 modular tests require `$DISPLAY` (Tk) and will fail in headless
environments without `xvfb-run`. All non-Tk tests pass unconditionally.

---

## New Files Created

### Infrastructure modules

| File | Lines | Purpose |
|------|-------|---------|
| `plotter_registry.py` | 475 | PlotTypeConfig registry, extracted from app |
| `plotter_tabs.py` | 532 | Multi-tab state: TabState, TabManager, TabBar |
| `plotter_app_icons.py` | 352 | Sidebar icon drawing for all 29 chart types |
| `plotter_presets.py` | 163 | Style preset load/save (.json) |
| `plotter_session.py` | 77 | Session persistence (last-used settings) |
| `plotter_events.py` | 75 | EventBus pub/sub messaging |
| `plotter_types.py` | 121 | Shared dataclasses and type definitions |
| `plotter_undo.py` | 131 | UndoStack for undo/redo |
| `plotter_errors.py` | 99 | ErrorReporter: structured error handling |
| `plotter_comparisons.py` | 248 | Custom comparison builder UI |
| `plotter_project.py` | 207 | .cplot project file save/open (ZIP) |
| `plotter_import_pzfx.py` | 316 | GraphPad .pzfx file importer |
| `plotter_wiki_content.py` | 2,224 | Statistical wiki content (29 sections) |
| `plotter_app_wiki.py` | 522 | Wiki popup viewer (Tk UI) |

---

## Existing Files Modified

| File | Changes |
|------|---------|
| `plotter_barplot_app.py` | Wired EventBus, UndoStack, ErrorReporter; added preset selector, session persistence, .cplot project save/open, .pzfx import, wiki popup, redo binding (Cmd+Shift+Z), Cmd+1–9 chart shortcuts |
| `plotter_functions.py` | Fixed `KeyError: 'p-unc'` in `plotter_repeated_measures` (pingouin version compatibility) |
| `CLAUDE.md` | Updated file map, test counts, checklist, gotchas; added Phase 2 section |
| `run_all.py` | Added 6th suite for new modular tests |

---

## Features Added

1. **Style presets** — preset selector in Data tab; 5 built-in presets (Classic, Publication, Presentation, Minimal, Dark)
2. **Session persistence** — settings auto-saved on every plot run, restored at startup
3. **Project files (.cplot)** — File > Save Project / Open Project; ZIP archives containing Excel data + JSON settings
4. **GraphPad .pzfx import** — File > Import from GraphPad; reads .pzfx XML to extract group values
5. **Statistical wiki** — Help > Statistical Methods; 29 sections with formulas, references, usage notes
6. **Undo/redo** — Cmd+Z / Cmd+Shift+Z for plot parameter changes via UndoStack
7. **Keyboard shortcuts** — Cmd+1–9 to switch between chart types in the sidebar
8. **Event bus** — decoupled pub/sub messaging via EventBus (wired but not yet widely used)
9. **Custom comparisons** — UI for selecting specific group pairs for statistical tests
10. **Error reporter** — structured, user-friendly error reporting via ErrorReporter
11. **Multi-tab infrastructure** — TabState/TabManager/TabBar for future multi-tab support
12. **Chart type icons** — programmatic icon drawing for all 29 chart types in sidebar

---

## Bugs Fixed

1. **`plotter_repeated_measures` KeyError: 'p-unc'** — pingouin ≥0.5 changed
   column names from `p-unc`/`p-corr` (hyphens) to `p_unc`/`p_corr` (underscores).
   Fixed with version-safe column lookup (`p_unc` if available, else `p-unc`).
   This fixed 4 test failures in the comprehensive suite.

---

## Known Issues

See `phase2/KNOWN_ISSUES.txt` for full details. Summary:

1. **Tk tests in headless environments**: ~19 modular tests need `$DISPLAY`; use `xvfb-run`
2. **Duplicate private helpers**: `_is_num`, `_non_numeric_values`, `_pd`, `_scipy_summary` defined in multiple modules (no functional impact)
3. **Results panel for grouped charts**: shows all numeric cells combined (cosmetic)
4. **Canvas mode toggle for grouped charts**: doesn't auto-re-render (minor edge case)
5. **Treeview heading colours on macOS**: system default colour used (cosmetic)

---

## Verification Checks

- [x] All 520 tests pass (`python3 run_all.py`)
- [x] All 19 modules import cleanly
- [x] No structural duplicate definitions (only private helpers with local scope)
- [x] No broken `prism_` import statements (only comments/docstrings remain)
- [x] No unresolved TODO/FIXME stubs (only `PLACEHOLDER_COLOR` which is intentional)
- [x] Wiki content complete: 29 sections, 21 references
- [x] Documentation updated (CLAUDE.md, phase2/PHASE2_SUMMARY.md)
