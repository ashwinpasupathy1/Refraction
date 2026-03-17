---
name: wire-chart
description: Wire an already-implemented but unregistered chart function into the app sidebar
---

You are wiring one or more existing but unregistered chart functions into the Claude Prism app sidebar. These functions exist in `prism_functions.py` and are tested in `test_comprehensive.py`, but do not yet appear in the UI.

The 7 currently unregistered chart types are:
- `prism_area_chart` → key `area_chart`, label "Area Chart"
- `prism_raincloud` → key `raincloud`, label "Raincloud"
- `prism_qq_plot` → key `qq_plot`, label "Q-Q Plot"
- `prism_lollipop` → key `lollipop`, label "Lollipop"
- `prism_waterfall` → key `waterfall`, label "Waterfall"
- `prism_pyramid` → key `pyramid`, label "Pyramid"
- `prism_ecdf` → key `ecdf`, label "ECDF"

## What to do

1. **Read the target function** in `prism_functions.py` to understand its parameters, especially any chart-specific ones beyond the shared style block.

2. **Add a `PlotTypeConfig` entry** to `_REGISTRY_SPECS` in `prism_barplot_app.py` (~line 348). Choose appropriate values for:
   - `tab_mode` and `stats_tab` based on the chart's data shape
   - `has_points`, `has_error_bars`, `has_legend`, `has_stats` based on what the function supports
   - `extra_collect` lambda for any chart-specific params the function accepts

3. **Add a validator** in `prism_validators.py` if one does not already exist for this chart type. Then import it and register it in `_STANDALONE_VALIDATORS` in `prism_barplot_app.py`.

4. **Add `tk.Var` defaults** for any new chart-specific UI variables to `_reset_vars_to_defaults()`.

5. **Run `python3 run_all.py`** and confirm 0 failures before finishing.

If the user specifies which chart(s) to wire, do only those. If no chart is specified, ask which one(s) to wire.
