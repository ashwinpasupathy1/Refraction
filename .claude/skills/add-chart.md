---
name: add-chart
description: Add a new chart type to Claude Prism following the 5-step checklist
---

You are adding a new chart type to Claude Prism. The user will specify the chart name and any details. Follow the 5-step checklist from CLAUDE.md exactly.

## Step 1 — Write the plot function in `prism_functions.py`

Insert the new function **before** the `# P20 — Export all chart types` block (~line 5586). The function must:
- Start with `_ensure_imports()`
- Call `_base_plot_setup(...)` then immediately `_style_kwargs(locals())`
- Pass `**_sk` to both `_apply_prism_style` and `_base_plot_finish`
- Return `fig, ax`
- Include the full shared style param block (copy verbatim from an existing function)
- Never import matplotlib/seaborn at module level

## Step 2 — Register in `_REGISTRY_SPECS` in `prism_barplot_app.py`

Add a `PlotTypeConfig(...)` entry to the list starting ~line 348. Choose:
- `tab_mode`: `"bar"` `"line"` `"grouped_bar"` `"scatter"` `"heatmap"` `"kaplan_meier"` `"before_after"`
- `stats_tab`: pick the closest match from the documented options
- Set `has_points`, `has_error_bars`, `has_legend`, `has_stats`, `x_continuous`, `axes_has_bar_width`, `axes_has_line_opts` appropriately
- Add `extra_collect` lambda for any chart-specific params

## Step 3 — Add UI controls (only if chart needs unique options)

If the chart needs custom controls not in standard tabs:
- Add a `_tab_stats_<key>` method to the App class
- Set `stats_tab="<key>"` in the registry entry
- Add new `tk.StringVar` / `tk.BooleanVar` defaults to `_reset_vars_to_defaults()`

## Step 4 — Add a validator in `prism_validators.py`

Write a `validate_<key>(df) -> tuple[list, list]` function that checks the expected Excel layout. Then:
- Import it in the `from prism_validators import ...` block at the top of `prism_barplot_app.py`
- Add it to `_STANDALONE_VALIDATORS` dict in `_validate_spreadsheet()`
- Set `PlotTypeConfig.validate` to `"_validate_<key>"`

## Step 5 — Write tests in `test_comprehensive.py`

Follow the existing pattern. Minimum required:
1. One test that renders without crashing
2. One that checks a specific visual property (axis label, bar count, etc.)
3. One that tests the validator with valid data
4. One that tests the validator with invalid data

## Final check

Run `python3 run_all.py` and confirm all existing tests still pass (count must be ≥ 571 with 0 failures) before declaring done.
