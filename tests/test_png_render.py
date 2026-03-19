"""
test_png_render.py
==================
Tests that all 29 chart functions in plotter_functions.py render without
crashing. Uses plotter_test_harness fixtures.

Each test:
  1. Creates a temporary Excel file with appropriate data
  2. Calls the chart function
  3. Asserts it returns (fig, ax)
  4. Closes the figure

Minimum 29 tests (one per chart type).

Run:
  python3 tests/test_png_render.py  (or via run_all.py)
"""

import sys, os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import plotter_test_harness as _h
from plotter_test_harness import (
    pf, plt, ok, fail, run, section, summarise, close_fig,
    bar_excel, line_excel, simple_xy_excel, grouped_excel,
    km_excel, heatmap_excel, two_way_excel, contingency_excel,
    bland_altman_excel, forest_excel, bubble_excel, chi_gof_excel,
    with_excel,
)

rng = np.random.default_rng(42)

# ═══════════════════════════════════════════════════════════════════════════
# Shared data fixtures
# ═══════════════════════════════════════════════════════════════════════════

BAR_GROUPS = {"Control": rng.normal(10, 2, 8), "Drug A": rng.normal(14, 2, 8)}
THREE_GROUPS = {"Control": rng.normal(5, 1, 10), "Drug A": rng.normal(8, 1, 10), "Drug B": rng.normal(11, 1, 10)}
PAIRED = {"Before": rng.normal(5, 1, 10), "After": rng.normal(7, 1, 10)}
RM_GROUPS = {"T0": rng.normal(5, 1, 8), "T1": rng.normal(6, 1, 8), "T2": rng.normal(7, 1, 8)}

XS = np.array([1, 2, 3, 4, 5], dtype=float)
YS = np.array([2, 4, 6, 8, 10], dtype=float)

LINE_DATA = {
    "S1": np.column_stack([XS * 0.5 + rng.normal(0, 0.2, 5) for _ in range(3)]),
}

KM_DATA = {
    "Control": {"time": np.array([1, 3, 5, 7, 9, 12]),
                "event": np.array([1, 1, 0, 1, 0, 1])},
    "Treatment": {"time": np.array([2, 4, 6, 8, 10, 14]),
                  "event": np.array([1, 0, 1, 1, 0, 0])},
}

HM_MATRIX = rng.normal(0, 1, (5, 4))
HM_ROWS = [f"Gene{i}" for i in range(5)]
HM_COLS = [f"S{i}" for i in range(4)]

TWO_WAY_DATA = [(f, g, rng.normal({"Drug_Male": 5, "Drug_Female": 6, "Control_Male": 3, "Control_Female": 4}.get(f + "_" + g, 4), 0.8))
                for f in ["Drug", "Control"] for g in ["Male", "Female"] for _ in range(5)]

CT_ROWS = ["Group A", "Group B"]
CT_COLS = ["Outcome1", "Outcome2"]
CT_MAT = np.array([[30, 20], [15, 35]])

FOREST_STUDIES = ["Study A", "Study B", "Study C", "Study D"]
FOREST_EFFECTS = [0.5, 0.8, 1.2, 0.9]
FOREST_CI_LO = [0.2, 0.4, 0.7, 0.5]
FOREST_CI_HI = [0.8, 1.2, 1.7, 1.3]

BLAND_A = rng.normal(10, 2, 15)
BLAND_B = BLAND_A + rng.normal(0, 0.5, 15)

BUBBLE_X = rng.normal(5, 1, 10)
BUBBLE_Y = rng.normal(5, 1, 10)
BUBBLE_S = rng.uniform(5, 50, 10)

CHI_CATS = ["Cat1", "Cat2", "Cat3"]
CHI_OBS = [20.0, 30.0, 50.0]


# ═══════════════════════════════════════════════════════════════════════════
# 1. Bar Chart
# ═══════════════════════════════════════════════════════════════════════════
section("PNG render — all 29 chart types")

def test_render_bar():
    with with_excel(lambda p: bar_excel(BAR_GROUPS, path=p)) as xl:
        fig, ax = pf.plotter_barplot(xl)
        assert fig is not None and ax is not None
        close_fig(fig)
run("plotter_barplot: renders without crash", test_render_bar)

# 2. Line Graph
def test_render_line():
    with with_excel(lambda p: line_excel(LINE_DATA, XS, path=p)) as xl:
        fig, ax = pf.plotter_linegraph(xl)
        assert fig is not None and ax is not None
        close_fig(fig)
run("plotter_linegraph: renders without crash", test_render_line)

# 3. Grouped Bar
def test_render_grouped_bar():
    data = {
        "CatA": {"Sub1": rng.normal(5, 1, 5), "Sub2": rng.normal(7, 1, 5)},
        "CatB": {"Sub1": rng.normal(6, 1, 5), "Sub2": rng.normal(8, 1, 5)},
    }
    with with_excel(lambda p: grouped_excel(["CatA", "CatB"], ["Sub1", "Sub2"], data, path=p)) as xl:
        fig, ax = pf.plotter_grouped_barplot(xl)
        assert fig is not None and ax is not None
        close_fig(fig)
run("plotter_grouped_barplot: renders without crash", test_render_grouped_bar)

# 4. Box Plot
def test_render_box():
    with with_excel(lambda p: bar_excel(THREE_GROUPS, path=p)) as xl:
        fig, ax = pf.plotter_boxplot(xl)
        assert fig is not None and ax is not None
        close_fig(fig)
run("plotter_boxplot: renders without crash", test_render_box)

# 5. Scatter Plot
def test_render_scatter():
    with with_excel(lambda p: simple_xy_excel(XS, YS, path=p)) as xl:
        fig, ax = pf.plotter_scatterplot(xl)
        assert fig is not None and ax is not None
        close_fig(fig)
run("plotter_scatterplot: renders without crash", test_render_scatter)

# 6. Violin Plot
def test_render_violin():
    with with_excel(lambda p: bar_excel(THREE_GROUPS, path=p)) as xl:
        fig, ax = pf.plotter_violin(xl)
        assert fig is not None and ax is not None
        close_fig(fig)
run("plotter_violin: renders without crash", test_render_violin)

# 7. Kaplan-Meier
def test_render_km():
    with with_excel(lambda p: km_excel(KM_DATA, path=p)) as xl:
        fig, ax = pf.plotter_kaplan_meier(xl)
        assert fig is not None and ax is not None
        close_fig(fig)
run("plotter_kaplan_meier: renders without crash", test_render_km)

# 8. Heatmap
def test_render_heatmap():
    with with_excel(lambda p: heatmap_excel(HM_MATRIX, HM_ROWS, HM_COLS, path=p)) as xl:
        fig, ax = pf.plotter_heatmap(xl)
        assert fig is not None and ax is not None
        close_fig(fig)
run("plotter_heatmap: renders without crash", test_render_heatmap)

# 9. Two-Way ANOVA
def test_render_two_way():
    with with_excel(lambda p: two_way_excel(TWO_WAY_DATA, path=p)) as xl:
        fig, ax = pf.plotter_two_way_anova(xl)
        assert fig is not None and ax is not None
        close_fig(fig)
run("plotter_two_way_anova: renders without crash", test_render_two_way)

# 10. Before / After
def test_render_before_after():
    with with_excel(lambda p: bar_excel(PAIRED, path=p)) as xl:
        fig, ax = pf.plotter_before_after(xl)
        assert fig is not None and ax is not None
        close_fig(fig)
run("plotter_before_after: renders without crash", test_render_before_after)

# 11. Histogram
def test_render_histogram():
    with with_excel(lambda p: bar_excel({"Data": rng.normal(0, 1, 50)}, path=p)) as xl:
        fig, ax = pf.plotter_histogram(xl)
        assert fig is not None and ax is not None
        close_fig(fig)
run("plotter_histogram: renders without crash", test_render_histogram)

# 12. Subcolumn Scatter
def test_render_subcolumn():
    with with_excel(lambda p: bar_excel(THREE_GROUPS, path=p)) as xl:
        fig, ax = pf.plotter_subcolumn_scatter(xl)
        assert fig is not None and ax is not None
        close_fig(fig)
run("plotter_subcolumn_scatter: renders without crash", test_render_subcolumn)

# 13. Curve Fit
def test_render_curve_fit():
    x_cf = np.linspace(0.1, 10, 15)
    y_cf = 2.0 * x_cf + 1.0 + rng.normal(0, 0.5, 15)
    with with_excel(lambda p: simple_xy_excel(x_cf, y_cf, path=p)) as xl:
        fig, ax = pf.plotter_curve_fit(xl, model_name="linear")
        assert fig is not None and ax is not None
        close_fig(fig)
run("plotter_curve_fit: renders without crash", test_render_curve_fit)

# 14. Column Statistics
def test_render_column_stats():
    with with_excel(lambda p: bar_excel(THREE_GROUPS, path=p)) as xl:
        fig, ax = pf.plotter_column_stats(xl)
        assert fig is not None and ax is not None
        close_fig(fig)
run("plotter_column_stats: renders without crash", test_render_column_stats)

# 15. Contingency
def test_render_contingency():
    with with_excel(lambda p: contingency_excel(CT_ROWS, CT_COLS, CT_MAT, path=p)) as xl:
        fig, ax = pf.plotter_contingency(xl)
        assert fig is not None and ax is not None
        close_fig(fig)
run("plotter_contingency: renders without crash", test_render_contingency)

# 16. Repeated Measures
def test_render_repeated_measures():
    with with_excel(lambda p: bar_excel(RM_GROUPS, path=p)) as xl:
        fig, ax = pf.plotter_repeated_measures(xl)
        assert fig is not None and ax is not None
        close_fig(fig)
run("plotter_repeated_measures: renders without crash", test_render_repeated_measures)

# 17. Chi-Square GoF
def test_render_chi_square_gof():
    with with_excel(lambda p: chi_gof_excel(CHI_CATS, CHI_OBS, path=p)) as xl:
        fig, ax = pf.plotter_chi_square_gof(xl)
        assert fig is not None and ax is not None
        close_fig(fig)
run("plotter_chi_square_gof: renders without crash", test_render_chi_square_gof)

# 18. Stacked Bar
def test_render_stacked_bar():
    data = {
        "CatA": {"Sub1": rng.normal(5, 1, 5), "Sub2": rng.normal(3, 1, 5)},
        "CatB": {"Sub1": rng.normal(6, 1, 5), "Sub2": rng.normal(4, 1, 5)},
    }
    with with_excel(lambda p: grouped_excel(["CatA", "CatB"], ["Sub1", "Sub2"], data, path=p)) as xl:
        fig, ax = pf.plotter_stacked_bar(xl)
        assert fig is not None and ax is not None
        close_fig(fig)
run("plotter_stacked_bar: renders without crash", test_render_stacked_bar)

# 19. Bubble Chart
def test_render_bubble():
    with with_excel(lambda p: bubble_excel(BUBBLE_X, BUBBLE_Y, BUBBLE_S, path=p)) as xl:
        fig, ax = pf.plotter_bubble(xl)
        assert fig is not None and ax is not None
        close_fig(fig)
run("plotter_bubble: renders without crash", test_render_bubble)

# 20. Dot Plot
def test_render_dot_plot():
    with with_excel(lambda p: bar_excel(THREE_GROUPS, path=p)) as xl:
        fig, ax = pf.plotter_dot_plot(xl)
        assert fig is not None and ax is not None
        close_fig(fig)
run("plotter_dot_plot: renders without crash", test_render_dot_plot)

# 21. Bland-Altman
def test_render_bland_altman():
    with with_excel(lambda p: bland_altman_excel(BLAND_A, BLAND_B, path=p)) as xl:
        fig, ax = pf.plotter_bland_altman(xl)
        assert fig is not None and ax is not None
        close_fig(fig)
run("plotter_bland_altman: renders without crash", test_render_bland_altman)

# 22. Forest Plot
def test_render_forest_plot():
    with with_excel(lambda p: forest_excel(FOREST_STUDIES, FOREST_EFFECTS, FOREST_CI_LO, FOREST_CI_HI, path=p)) as xl:
        fig, ax = pf.plotter_forest_plot(xl)
        assert fig is not None and ax is not None
        close_fig(fig)
run("plotter_forest_plot: renders without crash", test_render_forest_plot)

# 23. Area Chart
def test_render_area_chart():
    with with_excel(lambda p: line_excel(LINE_DATA, XS, path=p)) as xl:
        fig, ax = pf.plotter_area_chart(xl)
        assert fig is not None and ax is not None
        close_fig(fig)
run("plotter_area_chart: renders without crash", test_render_area_chart)

# 24. Raincloud
def test_render_raincloud():
    with with_excel(lambda p: bar_excel(THREE_GROUPS, path=p)) as xl:
        fig, ax = pf.plotter_raincloud(xl)
        assert fig is not None and ax is not None
        close_fig(fig)
run("plotter_raincloud: renders without crash", test_render_raincloud)

# 25. Q-Q Plot
def test_render_qq_plot():
    with with_excel(lambda p: bar_excel({"Data": rng.normal(0, 1, 30)}, path=p)) as xl:
        fig, ax = pf.plotter_qq_plot(xl)
        assert fig is not None and ax is not None
        close_fig(fig)
run("plotter_qq_plot: renders without crash", test_render_qq_plot)

# 26. Lollipop
def test_render_lollipop():
    with with_excel(lambda p: bar_excel(BAR_GROUPS, path=p)) as xl:
        fig, ax = pf.plotter_lollipop(xl)
        assert fig is not None and ax is not None
        close_fig(fig)
run("plotter_lollipop: renders without crash", test_render_lollipop)

# 27. Waterfall
def test_render_waterfall():
    with with_excel(lambda p: bar_excel({"Values": np.array([10, -3, 5, -2, 8, -6])}, path=p)) as xl:
        fig, ax = pf.plotter_waterfall(xl)
        assert fig is not None and ax is not None
        close_fig(fig)
run("plotter_waterfall: renders without crash", test_render_waterfall)

# 28. Pyramid
def test_render_pyramid():
    import pandas as pd
    import tempfile
    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    tmp.close()
    try:
        rows = [["Age", "Male", "Female"],
                ["0-9", 100, 95],
                ["10-19", 120, 115],
                ["20-29", 130, 125],
                ["30-39", 110, 105]]
        pd.DataFrame(rows).to_excel(tmp.name, index=False, header=False)
        fig, ax = pf.plotter_pyramid(tmp.name)
        assert fig is not None and ax is not None
        close_fig(fig)
    finally:
        os.unlink(tmp.name)
run("plotter_pyramid: renders without crash", test_render_pyramid)

# 29. ECDF
def test_render_ecdf():
    with with_excel(lambda p: bar_excel(THREE_GROUPS, path=p)) as xl:
        fig, ax = pf.plotter_ecdf(xl)
        assert fig is not None and ax is not None
        close_fig(fig)
run("plotter_ecdf: renders without crash", test_render_ecdf)


# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
summarise()
sys.exit(0 if _h.FAIL == 0 else 1)
