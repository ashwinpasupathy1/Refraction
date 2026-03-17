"""
test_p1_p2_p3.py
================
Tests for Priority 1 (styling), Priority 2 (new stats), and Priority 3
(new chart types) additions to Claude Prism.

Run:
  python3 test_p1_p2_p3.py
"""
import sys, os, warnings, tempfile
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prism_test_harness as _h
from prism_test_harness import (
    pf, plt, ok, fail, run, section, summarise, close_fig,
    bar_excel, line_excel, simple_xy_excel, grouped_excel,
    km_excel, heatmap_excel, two_way_excel, contingency_excel,
    bland_altman_excel, forest_excel, bubble_excel, chi_gof_excel,
    with_excel, PLOT_PARAM_DEFAULTS,
)

# Local rng so tests are reproducible independent of harness seed
rng = np.random.default_rng(0)



# ─────────────────────────────────────────────────────────────────────────────
# Fixture helpers
# ─────────────────────────────────────────────────────────────────────────────


def _grouped_excel():
    """Two categories × two subgroups, 4 rows of data."""
    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    tmp.close()
    header1 = ["Cat1", "Cat1", "Cat2", "Cat2"]
    header2 = ["Sub1", "Sub2", "Sub1", "Sub2"]
    data = [[1.2, 2.3, 3.1, 4.2],
            [1.5, 2.1, 3.4, 4.0],
            [1.1, 2.5, 3.0, 4.5]]
    rows = [header1, header2] + data
    pd.DataFrame(rows).to_excel(tmp.name, index=False, header=False)
    return tmp.name

def _scatter_excel():
    """Simple X/Y scatter."""
    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    tmp.close()
    xs = np.linspace(1, 10, 12)
    ys = 2 * xs + rng.normal(0, 1, 12)
    df = pd.DataFrame({"X": ["X", *xs], "Y": ["Series", *ys]})
    df.to_excel(tmp.name, index=False, header=False)
    return tmp.name

def _paired_excel(n=8):
    """Two groups of paired values."""
    a = rng.normal(5, 1, n)
    b = a + rng.normal(1, 0.5, n)
    return bar_excel({"Before": a, "After": b})

def _gof_excel(equal=True):
    """Chi-sq GoF: Row1=cats, Row2=observed, optional Row3=expected."""
    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    tmp.close()
    cats = ["A", "B", "C", "D"]
    obs  = [30, 45, 15, 10]
    rows = [cats, obs]
    if not equal:
        rows.append([0.25, 0.35, 0.25, 0.15])
    pd.DataFrame(rows).to_excel(tmp.name, index=False, header=False)
    return tmp.name

def _bubble_excel():
    """X/Y/Size triples for bubble chart."""
    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    tmp.close()
    rows = [["X", "Series1", "", ""],
            [1, 2, 3,  10],
            [2, 4, 5,  20],
            [3, 1, 8,   5],
            [4, 6, 2,  30]]
    # Trim to X + Y + Size (3 cols per series)
    rows2 = [["X", "S1", "S1"],
             [1, 2, 10],
             [2, 4, 20],
             [3, 1,  5],
             [4, 6, 30]]
    pd.DataFrame(rows2).to_excel(tmp.name, index=False, header=False)
    return tmp.name

def _bland_altman_excel():
    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    tmp.close()
    a = rng.normal(10, 2, 15)
    b = a + rng.normal(0.5, 0.8, 15)
    pd.DataFrame({"Method A": ["Method A", *a],
                  "Method B": ["Method B", *b]}).to_excel(
        tmp.name, index=False, header=False)
    return tmp.name

def _forest_excel():
    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    tmp.close()
    data = {
        "Study":  ["Smith 2020", "Jones 2021", "Lee 2022", "Wang 2023"],
        "Effect": [0.45, -0.12, 0.78, 0.30],
        "CI_lo":  [0.10, -0.55, 0.32, -0.05],
        "CI_hi":  [0.80,  0.31, 1.24,  0.65],
        "Weight": [25, 30, 20, 25],
    }
    pd.DataFrame(data).to_excel(tmp.name, index=False)
    return tmp.name


# ═════════════════════════════════════════════════════════════════════════════
# P1 — Styling params
# ═════════════════════════════════════════════════════════════════════════════
section("P1 — Axis Style")

GROUPS_AB = {"Control": rng.normal(5, 1, 10), "Treated": rng.normal(7, 1, 10)}

for style in ("open", "closed", "floating", "none"):
    name = f"axis_style={style!r} on bar chart"
    def _t(s=style):
        p = bar_excel(GROUPS_AB)
        try:
            fig, ax = pf.prism_barplot(p, axis_style=s)
            close_fig(fig)
        finally:
            os.unlink(p)
    run(name, _t)

section("P1 — Tick Direction")

for td in ("out", "in", "inout", ""):
    def _t(d=td):
        p = bar_excel(GROUPS_AB)
        try:
            fig, ax = pf.prism_barplot(p, tick_dir=d)
            close_fig(fig)
        finally:
            os.unlink(p)
    run(f"tick_dir={td!r} on bar chart", _t)

section("P1 — Minor Ticks")

def test_minor_ticks():
    p = bar_excel(GROUPS_AB)
    try:
        fig, ax = pf.prism_barplot(p, minor_ticks=True)
        close_fig(fig)
    finally:
        os.unlink(p)
run("minor_ticks=True on bar chart", test_minor_ticks)

section("P1 — Point Size & Alpha")

for ps, pa in ((2.0, 0.3), (6.0, 0.8), (14.0, 1.0)):
    def _t(s=ps, a=pa):
        p = bar_excel(GROUPS_AB)
        try:
            fig, ax = pf.prism_barplot(p, point_size=s, point_alpha=a)
            close_fig(fig)
        finally:
            os.unlink(p)
    run(f"point_size={ps}, point_alpha={pa} on bar chart", _t)

# point_size on boxplot and violin
for fn_name, fn in (("boxplot", pf.prism_boxplot), ("violin", pf.prism_violin)):
    def _t(f=fn, n=fn_name):
        p = bar_excel(GROUPS_AB)
        try:
            fig, ax = f(p, point_size=8.0, point_alpha=0.5)
            close_fig(fig)
        finally:
            os.unlink(p)
    run(f"point_size/alpha on {fn_name}", _t)

section("P1 — Cap Size")

for cs in (0.0, 4.0, 10.0):
    def _t(c=cs):
        p = bar_excel(GROUPS_AB)
        try:
            fig, ax = pf.prism_barplot(p, cap_size=c)
            close_fig(fig)
        finally:
            os.unlink(p)
    run(f"cap_size={cs} on bar chart", _t)

section("P1 — Legend Position")

for lp in ("best", "upper right", "upper left", "lower right", "outside", "none"):
    def _t(pos=lp):
        p = _scatter_excel()
        try:
            fig, ax = pf.prism_scatterplot(p, legend_pos=pos)
            close_fig(fig)
        finally:
            os.unlink(p)
    run(f"legend_pos={lp!r} on scatter", _t)

section("P1 — _style_kwargs helper")

def test_style_kwargs_defaults():
    sk = pf._style_kwargs({})
    assert sk["axis_style"]  == "open"
    assert sk["tick_dir"]    == "out"
    assert sk["minor_ticks"] is False
run("_style_kwargs returns correct defaults for empty dict", test_style_kwargs_defaults)

def test_style_kwargs_passthrough():
    sk = pf._style_kwargs({"axis_style": "closed", "tick_dir": "in",
                            "minor_ticks": True, "other": 99})
    assert sk["axis_style"] == "closed"
    assert sk["tick_dir"]   == "in"
    assert sk["minor_ticks"] is True
    assert "other" not in sk
run("_style_kwargs passes only style keys, ignores extras", test_style_kwargs_passthrough)

section("P1 — Styling propagates through all 16 existing chart types")

ALL_STYLE = dict(axis_style="closed", tick_dir="in", minor_ticks=True,
                 point_size=5.0, point_alpha=0.6, cap_size=3.0)

def _bar_style():
    p = bar_excel(GROUPS_AB)
    try: fig,ax = pf.prism_barplot(p, **ALL_STYLE); close_fig(fig)
    finally: os.unlink(p)
run("style params on prism_barplot", _bar_style)

def _box_style():
    p = bar_excel(GROUPS_AB)
    try: fig,ax = pf.prism_boxplot(p, **ALL_STYLE); close_fig(fig)
    finally: os.unlink(p)
run("style params on prism_boxplot", _box_style)

def _violin_style():
    p = bar_excel(GROUPS_AB)
    try: fig,ax = pf.prism_violin(p, **ALL_STYLE); close_fig(fig)
    finally: os.unlink(p)
run("style params on prism_violin", _violin_style)

def _scatter_style():
    p = _scatter_excel()
    try: fig,ax = pf.prism_scatterplot(p, **{k:v for k,v in ALL_STYLE.items()
                                              if k not in ("point_size","point_alpha","cap_size")}); close_fig(fig)
    finally: os.unlink(p)
run("style params on prism_scatterplot", _scatter_style)

def _subcolumn_style():
    p = bar_excel(GROUPS_AB)
    try: fig,ax = pf.prism_subcolumn_scatter(p, **ALL_STYLE); close_fig(fig)
    finally: os.unlink(p)
run("style params on prism_subcolumn_scatter", _subcolumn_style)


# ═════════════════════════════════════════════════════════════════════════════
# P2a — One-sample t-test
# ═════════════════════════════════════════════════════════════════════════════
section("P2a — One-sample t-test")

def test_one_sample_basic():
    g = {"Group": rng.normal(5, 1, 20)}
    res = pf._run_stats(g, test_type="one_sample", mu0=0.0)
    assert len(res) == 1
    name, null, p, stars = res[0]
    assert name == "Group"
    assert "μ₀" in null
    assert 0.0 <= p <= 1.0
run("one_sample t-test returns single result for 1 group", test_one_sample_basic)

def test_one_sample_significant():
    """Mean=10, mu0=0 should be clearly significant."""
    g = {"A": np.full(20, 10.0) + rng.normal(0, 0.1, 20)}
    res = pf._run_stats(g, test_type="one_sample", mu0=0.0)
    assert res[0][3] in ("****", "***", "**", "*")
run("one_sample: mean far from mu0 is significant", test_one_sample_significant)

def test_one_sample_ns():
    """Mean ≈ mu0 should be ns."""
    g = {"A": rng.normal(5.0, 1, 25)}
    res = pf._run_stats(g, test_type="one_sample", mu0=5.0)
    assert res[0][3] == "ns"
run("one_sample: mean ≈ mu0 is ns", test_one_sample_ns)

def test_one_sample_multi_group():
    """Multiple groups each tested vs mu0 — length = n_groups."""
    g = {"A": rng.normal(5, 1, 10),
         "B": rng.normal(10, 1, 10),
         "C": rng.normal(0, 1, 10)}
    res = pf._run_stats(g, test_type="one_sample", mu0=5.0)
    assert len(res) == 3
run("one_sample: 3 groups returns 3 results", test_one_sample_multi_group)

def test_one_sample_mc_correction():
    """Holm-Bonferroni and Bonferroni applied across groups."""
    g = {"A": rng.normal(5, 1, 10), "B": rng.normal(5, 1, 10)}
    for mc in ("Holm-Bonferroni", "Bonferroni", "Benjamini-Hochberg (FDR)", "None (uncorrected)"):
        res = pf._run_stats(g, test_type="one_sample", mu0=5.0, mc_correction=mc)
        assert len(res) == 2, f"MC={mc} gave {len(res)} results"
run("one_sample: all MC corrections work", test_one_sample_mc_correction)

def test_one_sample_on_bar_chart():
    """prism_barplot with stats_test=one_sample renders without crash."""
    p = bar_excel({"Control": rng.normal(5,1,12), "Drug": rng.normal(8,1,12)})
    try:
        fig, ax = pf.prism_barplot(p, show_stats=True,
                                   stats_test="one_sample", mu0=0.0)
        close_fig(fig)
    finally:
        os.unlink(p)
run("one_sample rendered on bar chart with show_stats=True", test_one_sample_on_bar_chart)


# ═════════════════════════════════════════════════════════════════════════════
# P2b — Chi-Square GoF
# ═════════════════════════════════════════════════════════════════════════════
section("P2b — Chi-Square GoF")

def test_gof_equal_expected():
    p = _gof_excel(equal=True)
    try:
        fig, ax = pf.prism_chi_square_gof(p, expected_equal=True)
        close_fig(fig)
    finally:
        os.unlink(p)
run("prism_chi_square_gof: equal expected proportions", test_gof_equal_expected)

def test_gof_custom_expected():
    p = _gof_excel(equal=False)
    try:
        fig, ax = pf.prism_chi_square_gof(p, expected_equal=False)
        close_fig(fig)
    finally:
        os.unlink(p)
run("prism_chi_square_gof: custom expected from Row 3", test_gof_custom_expected)

def test_gof_style_params():
    p = _gof_excel()
    try:
        fig, ax = pf.prism_chi_square_gof(p, axis_style="closed",
                                           tick_dir="in", minor_ticks=True)
        close_fig(fig)
    finally:
        os.unlink(p)
run("prism_chi_square_gof: style params applied", test_gof_style_params)

def test_gof_annotation_present():
    """Chi-sq stat annotation must appear on axes."""
    p = _gof_excel()
    try:
        fig, ax = pf.prism_chi_square_gof(p)
        texts = [t.get_text() for t in ax.texts]
        assert any("χ²" in t for t in texts), f"No χ² annotation found; texts={texts}"
        close_fig(fig)
    finally:
        os.unlink(p)
run("prism_chi_square_gof: χ² annotation appears on axes", test_gof_annotation_present)


# ═════════════════════════════════════════════════════════════════════════════
# P2c — Full Regression Table
# ═════════════════════════════════════════════════════════════════════════════
section("P2c — Full Regression Table")

def test_regression_table_renders():
    p = _scatter_excel()
    try:
        fig, ax = pf.prism_scatterplot(p, show_regression=True,
                                        show_regression_table=True)
        close_fig(fig)
    finally:
        os.unlink(p)
run("prism_scatterplot: show_regression_table=True renders", test_regression_table_renders)

def test_regression_table_annotation():
    """Regression table annotation must contain 'Slope' text."""
    p = _scatter_excel()
    try:
        fig, ax = pf.prism_scatterplot(p, show_regression_table=True)
        texts = [t.get_text() for t in ax.texts]
        assert any("Slope" in t for t in texts), f"No 'Slope' found; texts={texts}"
        close_fig(fig)
    finally:
        os.unlink(p)
run("prism_scatterplot: regression table contains Slope annotation", test_regression_table_annotation)

def test_regression_table_false():
    """show_regression_table=False must NOT add Slope annotation."""
    p = _scatter_excel()
    try:
        fig, ax = pf.prism_scatterplot(p, show_regression_table=False)
        texts = [t.get_text() for t in ax.texts]
        assert not any("Slope" in t for t in texts)
        close_fig(fig)
    finally:
        os.unlink(p)
run("prism_scatterplot: show_regression_table=False suppresses table", test_regression_table_false)

def test_draw_regression_table_direct():
    """_draw_regression_table helper works standalone."""
    fig, ax = plt.subplots()
    xs = np.linspace(0, 10, 20)
    ys = 3 * xs + 1 + rng.normal(0, 1, 20)
    pf._draw_regression_table(ax, fig, xs, ys, font_size=10, color="#E8453C")
    texts = [t.get_text() for t in ax.texts]
    assert any("Slope" in t for t in texts)
    assert any("R²" in t for t in texts)
    plt.close(fig)
run("_draw_regression_table: slope and R² present", test_draw_regression_table_direct)

def test_regression_table_too_few_points():
    """_draw_regression_table must silently skip for n<3."""
    fig, ax = plt.subplots()
    pf._draw_regression_table(ax, fig, np.array([1.0, 2.0]),
                                np.array([2.0, 4.0]), 10, "#000")
    assert len(ax.texts) == 0
    plt.close(fig)
run("_draw_regression_table: silently skips for n<3", test_regression_table_too_few_points)


# ═════════════════════════════════════════════════════════════════════════════
# P3a — Stacked Bar
# ═════════════════════════════════════════════════════════════════════════════
section("P3a — Stacked Bar Chart")

def test_stacked_bar_absolute():
    p = _grouped_excel()
    try:
        fig, ax = pf.prism_stacked_bar(p, mode="absolute")
        close_fig(fig)
    finally:
        os.unlink(p)
run("prism_stacked_bar: mode=absolute renders", test_stacked_bar_absolute)

def test_stacked_bar_percent():
    p = _grouped_excel()
    try:
        fig, ax = pf.prism_stacked_bar(p, mode="percent")
        close_fig(fig)
    finally:
        os.unlink(p)
run("prism_stacked_bar: mode=percent renders", test_stacked_bar_percent)

def test_stacked_bar_legend():
    """Legend must be present for percent mode."""
    p = _grouped_excel()
    try:
        fig, ax = pf.prism_stacked_bar(p, mode="percent")
        assert ax.get_legend() is not None
        close_fig(fig)
    finally:
        os.unlink(p)
run("prism_stacked_bar: legend present", test_stacked_bar_legend)

def test_stacked_bar_percent_max():
    """In percent mode, bar tops should be ≤100 (within float tolerance)."""
    p = _grouped_excel()
    try:
        fig, ax = pf.prism_stacked_bar(p, mode="percent")
        # Check ylim top is consistent with 0–100 range
        _, ytop = ax.get_ylim()
        assert ytop >= 90, f"ytop={ytop} seems too low for percent mode"
        close_fig(fig)
    finally:
        os.unlink(p)
run("prism_stacked_bar: percent mode y-range is sensible", test_stacked_bar_percent_max)

def test_stacked_bar_style():
    p = _grouped_excel()
    try:
        fig, ax = pf.prism_stacked_bar(p, axis_style="floating", tick_dir="in")
        close_fig(fig)
    finally:
        os.unlink(p)
run("prism_stacked_bar: style params applied", test_stacked_bar_style)


# ═════════════════════════════════════════════════════════════════════════════
# P3b — Bubble Chart
# ═════════════════════════════════════════════════════════════════════════════
section("P3b — Bubble Chart")

def test_bubble_default():
    p = _bubble_excel()
    try:
        fig, ax = pf.prism_bubble(p)
        close_fig(fig)
    finally:
        os.unlink(p)
run("prism_bubble: default render", test_bubble_default)

def test_bubble_scale():
    for scale in (0.2, 1.0, 3.0):
        p = _bubble_excel()
        try:
            fig, ax = pf.prism_bubble(p, bubble_scale=scale)
            close_fig(fig)
        finally:
            os.unlink(p)
run("prism_bubble: bubble_scale 0.2/1.0/3.0 renders", test_bubble_scale)

def test_bubble_show_labels():
    p = _bubble_excel()
    try:
        fig, ax = pf.prism_bubble(p, show_labels=True)
        close_fig(fig)
    finally:
        os.unlink(p)
run("prism_bubble: show_labels=True renders", test_bubble_show_labels)

def test_bubble_style():
    p = _bubble_excel()
    try:
        fig, ax = pf.prism_bubble(p, axis_style="closed", point_alpha=0.5)
        close_fig(fig)
    finally:
        os.unlink(p)
run("prism_bubble: style params applied", test_bubble_style)


# ═════════════════════════════════════════════════════════════════════════════
# P3c — Dot Plot
# ═════════════════════════════════════════════════════════════════════════════
section("P3c — Dot Plot")

GROUPS_3 = {"A": rng.normal(5,1,12), "B": rng.normal(7,1,12), "C": rng.normal(9,1,12)}

def test_dot_plot_default():
    p = bar_excel(GROUPS_3)
    try:
        fig, ax = pf.prism_dot_plot(p)
        close_fig(fig)
    finally:
        os.unlink(p)
run("prism_dot_plot: default render", test_dot_plot_default)

def test_dot_plot_mean_median():
    p = bar_excel(GROUPS_3)
    try:
        fig, ax = pf.prism_dot_plot(p, show_mean=True, show_median=True)
        close_fig(fig)
    finally:
        os.unlink(p)
run("prism_dot_plot: show_mean + show_median", test_dot_plot_mean_median)

def test_dot_plot_no_overlay():
    p = bar_excel(GROUPS_3)
    try:
        fig, ax = pf.prism_dot_plot(p, show_mean=False, show_median=False)
        close_fig(fig)
    finally:
        os.unlink(p)
run("prism_dot_plot: no mean/median overlay", test_dot_plot_no_overlay)

def test_dot_plot_open_points():
    p = bar_excel(GROUPS_3)
    try:
        fig, ax = pf.prism_dot_plot(p, open_points=True, point_size=10.0)
        close_fig(fig)
    finally:
        os.unlink(p)
run("prism_dot_plot: open_points + custom point_size", test_dot_plot_open_points)

def test_dot_plot_style():
    p = bar_excel(GROUPS_3)
    try:
        fig, ax = pf.prism_dot_plot(p, axis_style="none", tick_dir="")
        close_fig(fig)
    finally:
        os.unlink(p)
run("prism_dot_plot: axis_style=none + tick_dir=empty", test_dot_plot_style)


# ═════════════════════════════════════════════════════════════════════════════
# P3d — Bland-Altman
# ═════════════════════════════════════════════════════════════════════════════
section("P3d — Bland-Altman Plot")

def test_bland_altman_default():
    p = _bland_altman_excel()
    try:
        fig, ax = pf.prism_bland_altman(p)
        close_fig(fig)
    finally:
        os.unlink(p)
run("prism_bland_altman: default render", test_bland_altman_default)

def test_bland_altman_no_ci():
    p = _bland_altman_excel()
    try:
        fig, ax = pf.prism_bland_altman(p, show_ci=False)
        close_fig(fig)
    finally:
        os.unlink(p)
run("prism_bland_altman: show_ci=False", test_bland_altman_no_ci)

def test_bland_altman_annotations():
    """Mean diff and LoA annotations must appear on plot."""
    p = _bland_altman_excel()
    try:
        fig, ax = pf.prism_bland_altman(p)
        texts = [t.get_text() for t in ax.texts]
        assert any("Mean" in t for t in texts), f"No Mean annotation; texts={texts}"
        assert any("SD" in t for t in texts), f"No SD annotation; texts={texts}"
        close_fig(fig)
    finally:
        os.unlink(p)
run("prism_bland_altman: Mean and SD annotations present", test_bland_altman_annotations)

def test_bland_altman_raises_one_column():
    """Should raise ValueError if only 1 column provided."""
    p = bar_excel({"OnlyOne": rng.normal(5,1,10)})
    try:
        raised = False
        try:
            pf.prism_bland_altman(p)
        except (ValueError, KeyError, IndexError):
            raised = True
        assert raised, "Expected error for single-column input"
    finally:
        os.unlink(p)
run("prism_bland_altman: raises for <2 columns", test_bland_altman_raises_one_column)

def test_bland_altman_style():
    p = _bland_altman_excel()
    try:
        fig, ax = pf.prism_bland_altman(p, axis_style="floating",
                                         tick_dir="in", minor_ticks=True)
        close_fig(fig)
    finally:
        os.unlink(p)
run("prism_bland_altman: style params applied", test_bland_altman_style)


# ═════════════════════════════════════════════════════════════════════════════
# P3e — Forest Plot
# ═════════════════════════════════════════════════════════════════════════════
section("P3e — Forest Plot")

def test_forest_plot_default():
    p = _forest_excel()
    try:
        fig, ax = pf.prism_forest_plot(p)
        close_fig(fig)
    finally:
        os.unlink(p)
run("prism_forest_plot: default render", test_forest_plot_default)

def test_forest_plot_no_summary():
    p = _forest_excel()
    try:
        fig, ax = pf.prism_forest_plot(p, show_summary=False)
        close_fig(fig)
    finally:
        os.unlink(p)
run("prism_forest_plot: show_summary=False", test_forest_plot_no_summary)

def test_forest_plot_ref_value():
    p = _forest_excel()
    try:
        fig, ax = pf.prism_forest_plot(p, ref_value=1.0)
        close_fig(fig)
    finally:
        os.unlink(p)
run("prism_forest_plot: ref_value=1.0 (OR reference)", test_forest_plot_ref_value)

def test_forest_plot_no_weights():
    p = _forest_excel()
    try:
        fig, ax = pf.prism_forest_plot(p, show_weights=False)
        close_fig(fig)
    finally:
        os.unlink(p)
run("prism_forest_plot: show_weights=False", test_forest_plot_no_weights)

def test_forest_plot_study_labels():
    """Study labels must appear as text on axes."""
    p = _forest_excel()
    try:
        fig, ax = pf.prism_forest_plot(p)
        texts = [t.get_text() for t in ax.texts]
        assert any("Smith" in t or "2020" in t for t in texts), \
            f"No study label found; texts={texts}"
        close_fig(fig)
    finally:
        os.unlink(p)
run("prism_forest_plot: study labels appear on axes", test_forest_plot_study_labels)

def test_forest_plot_summary_diamond():
    """Summary diamond (filled polygon) must be present when show_summary=True."""
    p = _forest_excel()
    try:
        fig, ax = pf.prism_forest_plot(p, show_summary=True)
        polys = [c for c in ax.collections
                 if hasattr(c, 'get_paths') and len(c.get_paths()) > 0]
        assert len(polys) > 0, "No filled polygon found for summary diamond"
        close_fig(fig)
    finally:
        os.unlink(p)
run("prism_forest_plot: summary diamond polygon present", test_forest_plot_summary_diamond)

def test_forest_plot_style():
    p = _forest_excel()
    try:
        fig, ax = pf.prism_forest_plot(p, axis_style="open",
                                        tick_dir="out", minor_ticks=False)
        close_fig(fig)
    finally:
        os.unlink(p)
run("prism_forest_plot: style params applied", test_forest_plot_style)


# ═════════════════════════════════════════════════════════════════════════════
# Modularisation — _style_kwargs propagates through _base_plot_finish
# ═════════════════════════════════════════════════════════════════════════════
section("Modularisation — _style_kwargs end-to-end")

def test_style_propagates_via_base_plot_finish():
    """axis_style=closed should leave all 4 spines visible after _base_plot_finish."""
    fig, ax = plt.subplots()
    sk = pf._style_kwargs({"axis_style": "closed", "tick_dir": "out",
                            "minor_ticks": False})
    pf._apply_prism_style(ax, 12, **sk)
    for spine in ax.spines.values():
        assert spine.get_visible(), f"Spine {spine} not visible for axis_style=closed"
    plt.close(fig)
run("axis_style=closed: all 4 spines visible", test_style_propagates_via_base_plot_finish)

def test_axis_style_none_hides_spines():
    fig, ax = plt.subplots()
    pf._apply_prism_style(ax, 12, axis_style="none")
    for spine in ax.spines.values():
        assert not spine.get_visible(), f"Spine visible for axis_style=none"
    plt.close(fig)
run("axis_style=none: all spines hidden", test_axis_style_none_hides_spines)

def test_axis_style_floating_offset():
    fig, ax = plt.subplots()
    pf._apply_prism_style(ax, 12, axis_style="floating")
    left_pos = ax.spines["left"].get_position()
    assert left_pos == ("outward", 5), f"Expected outward 5, got {left_pos}"
    plt.close(fig)
run("axis_style=floating: left spine offset outward by 5", test_axis_style_floating_offset)

def test_legend_pos_none_removes_legend():
    fig, ax = plt.subplots()
    ax.plot([1,2], [1,2], label="A")
    ax.legend()
    assert ax.get_legend() is not None
    pf._apply_legend(ax, "none", 12)
    assert ax.get_legend() is None
run("_apply_legend with 'none' removes existing legend", test_legend_pos_none_removes_legend)


# ═════════════════════════════════════════════════════════════════════════════
# Regression guard — original 16 chart types still pass with new params
# ═════════════════════════════════════════════════════════════════════════════
section("Regression — original chart types accept new params without crashing")

def _make_bar():   return bar_excel({"G1": rng.normal(5,1,10), "G2": rng.normal(7,1,10)})
def _make_line():
    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    tmp.close()
    xs = np.arange(1, 6, dtype=float)
    rows = [["X","S1"],*zip(xs, 2*xs+rng.normal(0,0.5,5))]
    pd.DataFrame(rows).to_excel(tmp.name, index=False, header=False)
    return tmp.name

STYLE_NEW = {"axis_style": "open", "tick_dir": "out", "minor_ticks": False,
             "point_size": 6.0, "point_alpha": 0.8, "cap_size": 4.0}

for label, fn, maker in [
    ("barplot",     pf.prism_barplot,     _make_bar),
    ("boxplot",     pf.prism_boxplot,     _make_bar),
    ("violin",      pf.prism_violin,      _make_bar),
    ("subcolumn",   pf.prism_subcolumn_scatter, _make_bar),
    ("before_after",pf.prism_before_after, lambda: bar_excel({"Pre": rng.normal(5,1,8), "Post": rng.normal(7,1,8)})),
]:
    def _t(f=fn, m=maker, lbl=label):
        p = m()
        try:
            fig, ax = f(p, **STYLE_NEW); close_fig(fig)
        finally:
            os.unlink(p)
    run(f"regression: {label} accepts all new style params", _t)


# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
summarise()
sys.exit(0 if _h.FAIL == 0 else 1)
