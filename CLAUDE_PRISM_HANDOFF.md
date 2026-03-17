# CLAUDE PRISM — LLM HANDOFF DOCUMENT
**Generated:** 2026-03-17 (Session 13)
**Zip:** `claude_prism_v11.zip` → folder `prism_v10/`
**Lines:** 7,834 app · 952 widgets · 483 validators · 387 results · 5,711 functions · 1,687 canvas
**Status:** 571/571 tests pass across 5 suites.

---

## 1. QUICK-START FOR NEXT SESSION

```
Continue from the handoff.
python3 run_all.py  →  571/571
```

---

## 2. SESSION 13 CHANGES

### Modular refactor — three new companion modules

#### `prism_widgets.py` (952 lines)
All design-system tokens, custom Tk widget classes, and shared UI helpers,
extracted from the top of `prism_barplot_app.py`.

| Exported symbol | Description |
|---|---|
| `_DS` | Design-system colour / font constants (edit once, propagates everywhere) |
| `PButton` | Styled push button with `primary` / `secondary` / `ghost` styles |
| `PCheckbox` | Canvas-rendered checkbox with crisp check mark at any DPI |
| `PRadioGroup` | Row of canvas-dot radio buttons sharing a `StringVar` |
| `PEntry` | Flat-border entry with 1px focus ring |
| `PCombobox` | Styled combobox wrapping `ttk.Combobox` |
| `section_sep` | Blue-tinted section-header band for grid layouts |
| `_create_tooltip` | Plain hover tooltip attached to any widget |
| `add_placeholder` | Grey hint text shown when entry is empty & unfocused |
| `_bind_scroll_recursive` | Safe subtree scroll binding (alternative to `bind_all`) |
| `LABELS`, `HINTS` | Field metadata dicts; `label(key)` / `hint(key)` / `tip(widget,key)` |
| `_is_num`, `_non_numeric_values`, `_scipy_summary`, `_sys_bg` | Utility functions |

**Headless-safe:** `tkinter` import is guarded by `_TK_AVAILABLE`; a no-op
stub base class (`_TkFrameStub`) stands in when tkinter is absent so the
module imports cleanly in CI/test environments.

#### `prism_validators.py` (483 lines)
All 11 spreadsheet validation functions extracted as standalone pure functions.
Each accepts a `pandas.DataFrame` and returns `(errors: list[str], warnings: list[str])`.

| Function | Chart type |
|---|---|
| `validate_flat_header(df, min_groups, min_rows, chart_name)` | Shared base for flat-header charts |
| `validate_bar(df)` | Bar, box, violin, subcolumn, before_after, repeated_measures |
| `validate_line(df)` | Line, scatter, curve_fit |
| `validate_grouped_bar(df)` | Grouped bar, stacked bar |
| `validate_kaplan_meier(df)` | Kaplan-Meier survival |
| `validate_heatmap(df)` | Heatmap |
| `validate_two_way_anova(df)` | Two-way ANOVA (long format with column headers) |
| `validate_contingency(df)` | Contingency table |
| `validate_chi_square_gof(df)` | Chi-square goodness of fit |
| `validate_bland_altman(df)` | Bland-Altman agreement |
| `validate_forest_plot(df)` | Forest plot (meta-analysis) |

**`_validate_spreadsheet()` dispatch patch:** `App._validate_spreadsheet` now
checks `_VALIDATORS_AVAILABLE` and calls the standalone function when possible;
falls back to `getattr(self, spec.validate)(df)` for any not-yet-extracted validator.

#### `prism_results.py` (387 lines)
Results panel logic extracted as three standalone functions that accept the
`app` object as their first argument (thin delegation from App methods).

| Function | Replaces |
|---|---|
| `populate_results(app, excel_path, sheet, plot_type, kw_snapshot)` | `App._populate_results` |
| `export_results_csv(app)` | `App._export_results_csv` |
| `copy_results_tsv(app)` | `App._copy_results_tsv` |

#### `prism_barplot_app.py` — import block update
The file now starts with a module docstring explaining the 6-file architecture,
followed by guarded imports from all three new companion modules:

```python
from prism_widgets   import _DS, PButton, ..., _is_num, _scipy_summary
from prism_validators import validate_bar, validate_line, ...
from prism_results    import populate_results, export_results_csv, copy_results_tsv
```

Each import is wrapped in `try/except ImportError` with a `print()` warning
so the app still starts in degraded mode if a companion file is missing.

### Documentation pass
- `prism_functions.py`: added docstrings to all 11 `_make_*` curve-fit model
  factory functions that were previously undocumented.
- `prism_canvas_renderer.py`: added docstrings to all colour helpers
  (`_hex_to_rgb`, `_rgb_to_hex`, `_darken_hex`, `_rgba_to_hex`, `_blend_alpha`),
  utility functions (`_calc_error_plain`, `_read_bar_groups`, `_prism_palette_n`,
  `_fmt_tick_label`), and bare dataclasses (`BarElement`, `BarScene`,
  `ClickResult`, `CoordTransform`, `GroupedBarGroup`, `GroupedBarScene`).
- `prism_widgets.py`: every exported symbol has a full docstring at class and
  method level.
- `prism_validators.py`: every `validate_*` function has a one-line docstring
  with layout description.

### New test suite: `test_modular.py` (53 tests)
Added as `"modular"` suite in `run_all.py`.

| Section | Tests |
|---|---|
| prism_widgets: module structure | 9 |
| prism_widgets: utility functions | 7 |
| prism_widgets: widget class attributes | 6 |
| prism_validators: flat-header | 6 |
| prism_validators: line chart | 2 |
| prism_validators: grouped bar | 3 |
| prism_validators: kaplan-meier | 2 |
| prism_validators: heatmap | 2 |
| prism_validators: miscellaneous | 6 |
| prism_results: module structure | 4 |
| prism_validators: module integrity | 3 |
| prism_widgets: module integrity | 3 |

---

## 3. ARCHITECTURE

### File map

```
prism_v10/
├── prism_barplot_app.py     7,834 lines  App class + PLOT_REGISTRY + icon helpers
├── prism_widgets.py           952 lines  _DS, P-widgets, UI helpers (no business logic)
├── prism_validators.py        483 lines  Standalone spreadsheet validators (pure functions)
├── prism_results.py           387 lines  Results panel: populate / export / copy
├── prism_functions.py       5,711 lines  22 matplotlib chart functions
├── prism_canvas_renderer.py 1,687 lines  tk.Canvas bar+grouped-bar renderer
├── prism_test_harness.py      363 lines  Shared test bootstrap
├── run_all.py                 110 lines  5-suite unified runner
├── test_comprehensive.py    1,341 lines  309 tests (all 22 chart types)
├── test_p1_p2_p3.py           796 lines   80 tests (style params, regressions)
├── test_control.py            437 lines   20 tests (control-group logic)
├── test_canvas_renderer.py  1,306 lines  109 tests (CanvasRenderer + GroupedCanvasRenderer)
└── test_modular.py            562 lines   53 tests (widget/validator/results modules)
```

### Dependency graph

```
prism_barplot_app.py
  ├── prism_widgets.py          (no dependencies on other prism modules)
  ├── prism_validators.py       (no dependencies on other prism modules)
  ├── prism_results.py          (no dependencies on other prism modules)
  ├── prism_functions.py        (numpy, pandas, matplotlib, scipy — lazy imports)
  └── prism_canvas_renderer.py  (numpy, pandas — no matplotlib)
```

---

## 4. REMAINING WORK

### High priority

- **Treeview heading colours on macOS Aqua** (Gotcha 44): the `ttk.Style`
  heading background is ignored on Aqua. Fix: call
  `style.theme_use("clam")` before building the results panel, or use a
  custom `ttk.Style` element.

- **`_populate_results` grouped-bar support** (Gotcha 46): the results panel
  reads `df.select_dtypes(include="number")` which misreads the two-row-header
  grouped layout. Add a chart-type dispatch inside `populate_results()` that
  calls `_read_grouped_groups()` from `prism_canvas_renderer` for grouped charts.

- **`_toggle_canvas_mode` grouped-bar trigger** (Gotcha 45): the re-run
  triggered by toggling canvas mode only fires for `plot_type == "bar"`.
  Patch: change the condition to `in ("bar", "grouped_bar")`.

### Medium priority

- Missing stats: Cochran's Q, McNemar, mixed-effects RM-ANOVA.
- P19 UI: `ytitle_right` field for twin-axis.
- Navigator keyboard shortcuts: ⌘1/⌘2/⌘3.
- Box-plot canvas renderer (`BoxBarScene`).

### Quick wins

- `_populate_results`: add "Copy Table" button per Treeview section.
- Permutation ticker: time one trial run to calibrate the % estimate.
- `snapshot_png`: render offscreen at 2× for Retina-quality export.

---

## 5. GOTCHAS (additions to v12 list)

48. **`_TK_AVAILABLE` guard in prism_widgets** — when `tkinter` is absent the
    widget classes inherit from `_TkFrameStub` (a no-op stub). Attempting to
    *instantiate* them (e.g. `PButton(parent)`) will silently succeed but
    produce an unusable object. Tests that check class attributes
    (`._is_pwidget`, `._BOX`) work correctly because those are class-level
    constants. Tests that actually create a widget need a real display.

49. **Docstring insertion via regex** — the two passes that added docstrings to
    `prism_functions.py` and `prism_canvas_renderer.py` used regex substitution
    which mis-placed some docstrings inside multi-line function signatures. Both
    were corrected by a targeted de-indent pass. If docstrings are added to
    either file in future, prefer the pattern:
    ```
    def fn(arg1,
           arg2):
        """Docstring goes here, after the closing parenthesis."""
    ```
    Never insert between parameter lines.

50. **`prism_validators.py` is the canonical validator source** — the original
    `App._validate_*` methods still exist in `prism_barplot_app.py` (they are
    not deleted) as fallbacks for any chart type not yet in `_STANDALONE_VALIDATORS`.
    The dispatch in `_validate_spreadsheet` prefers the standalone versions.
    Long term the App methods should be removed once all validators are
    confirmed identical to the standalone versions.

---

## 6. TEST COUNTS

```
run_all.py  →  571 / 571 pass
  comprehensive    →  309 / 309
  p1p2p3           →   80 /  80
  control          →   20 /  20
  canvas_renderer  →  109 / 109
  modular          →   53 /  53   (new this session)
```
