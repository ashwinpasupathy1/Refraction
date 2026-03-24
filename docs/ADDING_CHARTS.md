# Adding a New Chart Type -- the 5-Step Checklist

## Step 1 -- Write the plot function in `plotter_functions.py`

Insert **before** the `# P20 -- Export all chart types` block (around line 5586).

Every function must follow this exact template:

```python
def prism_my_chart(
    excel_path: str,
    sheet=0,
    color=None,
    title: str = "",
    xlabel: str = "",
    ytitle: str = "",
    yscale: str = "linear",
    ylim=None,
    figsize=(5, 5),
    font_size: float = 12.0,
    # ... chart-specific params ...
    ref_line=None,
    ref_line_label: str = "",
    # -- shared style params (copy this block verbatim) --
    axis_style: str = "open",
    tick_dir: str = "out",
    minor_ticks: bool = False,
    point_size: float = 6.0,
    point_alpha: float = 0.80,
    cap_size: float = 4.0,
    ytick_interval: float = 0.0,
    xtick_interval: float = 0.0,
    fig_bg: str = "white",
    spine_width: float = 0.8,
    gridlines: bool = False,
    grid_style: str = "none",
):
    """One-line summary.

    Longer description. Excel layout explanation.
    """
    _ensure_imports()
    group_order, groups, bar_colors, fig, ax = _base_plot_setup(
        excel_path, sheet, color, None, figsize)
    _sk = _style_kwargs(locals())   # <-- always do this

    # ... drawing code ...

    _apply_prism_style(ax, font_size, **_sk)
    _apply_grid(ax, grid_style, gridlines)
    _base_plot_finish(ax, fig, title, xlabel, ytitle, yscale, ylim,
                      font_size, ref_line, len(group_order),
                      ref_line_label=ref_line_label, **_sk)
    return fig, ax
```

**Critical rules:**
- Always call `_ensure_imports()` first
- Always call `_style_kwargs(locals())` early and pass `**_sk` to both
  `_apply_prism_style` and `_base_plot_finish`
- Always `return fig, ax`
- Never import matplotlib or seaborn at module level -- they're lazy-loaded
  by `_ensure_imports()`

## Step 2 -- Register it in `plotter_registry.py`

Add a new `PlotTypeConfig(...)` entry to the registry list in `plotter_registry.py`.
Also add a sidebar icon drawing function to `plotter_app_icons.py`.

```python
PlotTypeConfig(
    key="my_chart",           # internal key -- used everywhere
    label="My Chart",         # shown in sidebar
    fn_name="plotter_my_chart", # must match the function name exactly
    tab_mode="bar",           # which UI tabs to use (see tab modes below)
    stats_tab="standard",     # which stats sub-tab
    validate="_validate_bar", # which validator method
    has_points=True,          # show point size/alpha sliders?
    has_error_bars=True,      # show error bar type selector?
    has_legend=False,         # show legend position selector?
    has_stats=True,           # show statistics tab?
    x_continuous=False,       # X axis is numeric (not categorical)?
    axes_has_bar_width=False, # show bar width slider?
    axes_has_line_opts=False, # show line width/marker options?
    extra_collect=lambda app, kw: kw.update({
        "my_param": app._get_var("my_var_key", default_value),
    }),
),
```

**tab_mode options** (controls which UI sub-sections appear):
- `"bar"` -- flat categorical data (bar, box, violin, dot_plot, etc.)
- `"line"` -- numeric X axis (line, scatter, curve_fit)
- `"grouped_bar"` -- two-row-header grouped data
- `"scatter"` -- XY scatter variants
- `"heatmap"` -- matrix data
- `"kaplan_meier"` -- survival data
- `"before_after"` -- paired/repeated measures

**stats_tab options**: `"standard"` `"grouped_bar"` `"scatter"` `"kaplan_meier"`
`"before_after"` `"histogram"` `"curve_fit"` `"column_stats"` `"contingency"`
`"repeated_measures"` `"chi_square_gof"` `"stacked_bar"` `"bubble"` `"dot_plot"`
`"bland_altman"` `"forest_plot"` `"heatmap"` `"two_way_anova"`

## Step 3 -- Add UI controls (if the chart has unique options)

If your chart needs custom UI controls not covered by the standard tabs,
add a `_tab_stats_my_chart` method to the App class (see `_tab_stats_histogram`
at line ~5143 for a template) and set `stats_tab="my_chart"` in the registry.

Add new `tk.StringVar` / `tk.BooleanVar` defaults to `_reset_vars_to_defaults()`
so the form resets correctly when switching chart types.

## Step 4 -- Add a validator in `plotter_validators.py`

```python
def validate_my_chart(df) -> tuple[list, list]:
    """Validate My Chart layout: row 0 = headers, rows 1+ = values."""
    errors, warnings = [], []
    # ... checks ...
    return errors, warnings
```

Then wire it in `plotter_barplot_app.py`:
- Import it in the `from plotter_validators import ...` block at the top
- Add it to `_STANDALONE_VALIDATORS` dict in `_validate_spreadsheet()`
- Update `PlotTypeConfig.validate` to `"_validate_my_chart"`

## Step 5 -- Write tests

Add a test section to `test_comprehensive.py` following the existing pattern.
At minimum: one test that renders without crashing, one that checks a specific
visual property, one that tests the validator.

Run `python3 run_all.py` -- all existing tests must still pass.

## Step 6 -- Add a Plotly spec builder (for web mode)

Create `refraction/specs/my_chart.py` following the pattern of existing spec
builders (e.g., `refraction/specs/bar.py`). Import theme constants from
`refraction.core.config` (via `refraction.specs.theme` re-exports) and use
`refraction.specs.helpers` for shared utilities.

Register the builder in the `_SPEC_BUILDERS` dict in `plotter_server.py`.
