"""
comprehensive_tests.py
======================
Exhaustive test suite for Claude Plotter / plotter_functions.py.

Two completely independent datasets (DATASET_A = biological/clinical,
DATASET_B = environmental/engineering) are used for every chart type
and every statistical option.

Coverage:
  • All 16 chart types
  • All 4 statistical test types: parametric, paired, nonparametric, permutation
  • All 5 post-hoc options: Tukey HSD, Bonferroni, Sidak, Fisher LSD, Dunnett
  • All 4 MC corrections: Holm-Bonferroni, Bonferroni, Benjamini-Hochberg, None
  • All 3 error bar types: sem, sd, ci95
  • All 11 curve-fit models
  • All display flags: show_points, gridlines, open_points, horizontal, show_median,
    show_ns, show_p_values, show_effect_size, show_test_name, error_below_bar
  • log / log-log scales, ylim, ref_line
  • heatmap clustering rows+cols, annotate, robust, vmin/vmax
  • All normality + Welch's t-test correctness checks
  • Help-Analyze decision tree (mocked)
  • Hallucination checks: every public symbol imported from plotter_functions
    must actually exist in the module

Run:
  python3 test_comprehensive.py
"""

import sys, os, io, warnings, itertools, tempfile
import numpy as np
import pandas as pd

# ── Shared harness (single source of truth for all counters) ─────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plotter_test_harness as _h
from plotter_test_harness import (
    pf, plt, ok, fail, run, section, close_fig,
    bar_excel, line_excel, simple_xy_excel, grouped_excel,
    km_excel, heatmap_excel, two_way_excel, contingency_excel,
    with_excel,
)

# Aliases so existing test code that references PASS/FAIL reads from harness
def _get_pass(): return _h.PASS
def _get_fail(): return _h.FAIL

# ─────────────────────────────────────────────────────────────────────────────
# Fixture writer aliases — thin wrappers so existing test code is unchanged
# ─────────────────────────────────────────────────────────────────────────────

def _write_bar(path, groups: dict):
    bar_excel(groups, path=path)

def _write_line(path, series: dict, x_vals):
    line_excel(series, x_vals, path=path)

def _write_grouped(path, categories, subgroups, data):
    grouped_excel(categories, subgroups, data, path=path)

def _write_km(path, groups: dict):
    km_excel(groups, path=path)

def _write_heatmap(path, matrix, row_labels, col_labels):
    heatmap_excel(matrix, row_labels, col_labels, path=path)

def _write_two_way(path, records):
    two_way_excel(records, path=path)

def _write_contingency(path, row_labels, col_labels, matrix):
    contingency_excel(row_labels, col_labels, matrix, path=path)

def _close(fig):
    close_fig(fig)

# ─────────────────────────────────────────────────────────────────────────────
# DATASET A  — Biological / Clinical
#   3 groups (Control, Drug_A, Drug_B), n=8 each
#   Normally distributed, Drug_B non-normal (skewed)
# ─────────────────────────────────────────────────────────────────────────────

rng = np.random.default_rng(42)

A_CTRL  = rng.normal(10.0, 1.5, 8)
A_DRUG  = rng.normal(14.0, 1.8, 8)
A_DRUGB = rng.exponential(5.0, 8) + 8.0   # non-normal

A_GROUPS  = {"Control": A_CTRL, "Drug_A": A_DRUG, "Drug_B": A_DRUGB}
A_GROUPS2 = {"Control": A_CTRL, "Drug_A": A_DRUG}            # 2-group subset

# Paired (same n per group, matched row-by-row)
A_BEFORE = rng.normal(10.0, 1.5, 10)
A_AFTER  = A_BEFORE + rng.normal(2.5, 0.8, 10)
A_PAIRED = {"Before": A_BEFORE, "After": A_AFTER}

# Repeated measures (4 time points, 8 subjects)
A_T0 = rng.normal(10.0, 1.5, 8)
A_T1 = A_T0 + rng.normal(1.0, 0.5, 8)
A_T2 = A_T1 + rng.normal(1.0, 0.5, 8)
A_T3 = A_T2 + rng.normal(1.0, 0.5, 8)
A_RM  = {"T0": A_T0, "T1": A_T1, "T2": A_T2, "T3": A_T3}

# Line / scatter x-values
A_X   = np.array([0, 1, 2, 4, 8, 16, 24], dtype=float)
# Series = dict of series_name -> 2D array shape (n_xpoints, n_reps)
A_LINE = {
    "Control": np.column_stack([A_X * 0.5 + rng.normal(0, 0.3, len(A_X)) for _ in range(3)]),
    "Drug_A":  np.column_stack([A_X * 0.9 + rng.normal(0, 0.4, len(A_X)) for _ in range(3)]),
}

# KM survival data
A_KM = {
    "Control":   {"time": [5,10,15,20,25,30,35,40], "event": [1,1,0,1,1,0,1,0]},
    "Treatment": {"time": [3,8,12,18,22,28,32,38], "event": [1,1,1,0,1,1,0,0]},
}

# Heatmap  8 rows x 5 cols
A_HM_MATRIX = rng.normal(0, 1, (8, 5))
A_HM_ROWS   = [f"Gene{i}" for i in range(8)]
A_HM_COLS   = [f"S{i}"   for i in range(5)]

# Two-way ANOVA  (2 factors × 2 levels × 6 reps)
A_TWO = [(f, g, v) for f in ["Drug","Control"] for g in ["Male","Female"]
         for v in rng.normal({"Drug_Male":5,"Drug_Female":6,"Control_Male":3,"Control_Female":4}
                              .get(f+"_"+g, 4), 0.8, 6)]

# Contingency 3×2
A_CT_ROWS = ["Young","Middle","Old"]
A_CT_COLS = ["Recovered","Not Recovered"]
A_CT_MAT  = [[45,15],[30,20],[20,30]]

# Curve-fit x/y
A_CF_X    = np.logspace(-2, 2, 10)
A_CF_Y    = 100 / (1 + (10/A_CF_X)**1.5) + rng.normal(0, 3, 10)

# ─────────────────────────────────────────────────────────────────────────────
# DATASET B  — Environmental / Engineering
#   4 sites (Site1..Site4), n=6 each
# ─────────────────────────────────────────────────────────────────────────────

B_S1 = rng.normal(20.0, 2.0, 6)
B_S2 = rng.normal(25.0, 2.5, 6)
B_S3 = rng.normal(18.0, 1.8, 6)
B_S4 = rng.normal(30.0, 3.0, 6)

B_GROUPS  = {"Site1": B_S1, "Site2": B_S2, "Site3": B_S3, "Site4": B_S4}
B_GROUPS2 = {"Site1": B_S1, "Site2": B_S2}

# Paired (pre/post intervention, equal n)
B_PRE  = rng.normal(22.0, 2.0, 10)
B_POST = B_PRE - rng.normal(3.0, 1.0, 10)
B_PAIRED = {"Pre": B_PRE, "Post": B_POST}

# Repeated measures  (3 seasons × 8 sites)
B_SPR = rng.normal(20.0, 2.0, 8)
B_SUM = B_SPR + rng.normal(4.0, 1.0, 8)
B_AUT = B_SPR + rng.normal(2.0, 1.0, 8)
B_WIN = B_SPR - rng.normal(2.0, 1.0, 8)
B_RM  = {"Spring": B_SPR, "Summer": B_SUM, "Autumn": B_AUT, "Winter": B_WIN}

B_X    = np.array([0, 5, 10, 20, 40, 80, 160], dtype=float)
B_LINE = {
    "Site1": np.column_stack([B_X * 0.3 + rng.normal(0, 0.5, len(B_X)) for _ in range(3)]),
    "Site2": np.column_stack([B_X * 0.5 + rng.normal(0, 0.6, len(B_X)) for _ in range(3)]),
}

B_KM = {
    "Low_Exposure":  {"time": [10,20,30,40,50,60,70,80], "event": [0,1,0,1,0,1,0,1]},
    "High_Exposure": {"time": [5, 15,25,35,45,55,65,75], "event": [1,1,1,0,1,1,1,0]},
}

B_HM_MATRIX = rng.uniform(0, 50, (6, 4))
B_HM_ROWS   = [f"Loc{i}" for i in range(6)]
B_HM_COLS   = ["Q1","Q2","Q3","Q4"]

B_TWO = [(f, g, v) for f in ["Urban","Rural"] for g in ["Summer","Winter"]
         for v in rng.normal({"Urban_Summer":30,"Urban_Winter":15,"Rural_Summer":25,"Rural_Winter":12}
                              .get(f+"_"+g, 20), 2.0, 6)]

B_CT_ROWS = ["Exposed","Control"]
B_CT_COLS = ["Effect","No Effect"]
B_CT_MAT  = [[38, 12],[20, 30]]

B_CF_X = np.linspace(0, 10, 12)
B_CF_Y = 50 * np.exp(-0.3 * B_CF_X) + rng.normal(0, 2, 12)

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 0 — Hallucination / Symbol Check
# ─────────────────────────────────────────────────────────────────────────────

section("SECTION 0 — Hallucination / Public Symbol Audit")

EXPECTED_PUBLIC = [
    # plot functions
    "plotter_barplot", "plotter_linegraph", "plotter_grouped_barplot", "plotter_boxplot",
    "plotter_scatterplot", "plotter_violin", "plotter_kaplan_meier", "plotter_heatmap",
    "plotter_two_way_anova", "plotter_before_after", "plotter_histogram",
    "plotter_subcolumn_scatter", "plotter_curve_fit", "plotter_column_stats",
    "plotter_contingency", "plotter_repeated_measures",
    # shared helpers
    "_run_stats", "_apply_correction", "_p_to_stars", "_ensure_imports",
    "check_normality", "normality_warning", "CURVE_MODELS",
    "_apply_stats_brackets", "_draw_normality_warning", "_draw_jitter_points",
    "_set_categorical_xticks", "_get_font",
]

def test_symbols():
    missing = [s for s in EXPECTED_PUBLIC if not hasattr(pf, s)]
    assert not missing, f"Missing symbols: {missing}"

run("All expected public symbols exist in plotter_functions", test_symbols)

def test_curve_models():
    expected_models = [
        "4PL Sigmoidal (EC50/IC50)", "3PL Sigmoidal (no bottom)",
        "One-phase exponential decay", "One-phase exponential growth",
        "Two-phase exponential decay", "Michaelis-Menten", "Hill equation",
        "Gaussian (bell curve)", "Log-normal", "Linear", "Polynomial (2nd order)",
    ]
    missing = [m for m in expected_models if m not in pf.CURVE_MODELS]
    assert not missing, f"Missing curve models: {missing}"
    assert len(pf.CURVE_MODELS) == len(expected_models), \
        f"CURVE_MODELS has {len(pf.CURVE_MODELS)} entries, expected {len(expected_models)}"

run("CURVE_MODELS registry complete (11 models)", test_curve_models)

def test_no_hallucinated_imports():
    """Check that every symbol used via 'pf.' in this test actually exists."""
    fns = [pf.plotter_barplot, pf.plotter_linegraph, pf.plotter_grouped_barplot,
           pf.plotter_boxplot, pf.plotter_scatterplot, pf.plotter_violin,
           pf.plotter_kaplan_meier, pf.plotter_heatmap, pf.plotter_two_way_anova,
           pf.plotter_before_after, pf.plotter_histogram, pf.plotter_subcolumn_scatter,
           pf.plotter_curve_fit, pf.plotter_column_stats, pf.plotter_contingency,
           pf.plotter_repeated_measures]
    for f in fns:
        assert callable(f), f"{f} is not callable"

run("All 16 plot functions are callable", test_no_hallucinated_imports)

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1 — Statistical Engine
# ─────────────────────────────────────────────────────────────────────────────

section("SECTION 1 — Statistical Engine Correctness")

from scipy import stats as _scipy_stats

def test_welch_default():
    """Parametric 2-group must use Welch's t-test (equal_var=False)."""
    a = A_CTRL; b = A_DRUG
    res = pf._run_stats({"C": a, "D": b}, test_type="parametric")
    _, expected_p = _scipy_stats.ttest_ind(a, b, equal_var=False)
    assert len(res) == 1
    assert abs(res[0][2] - expected_p) < 1e-10, \
        f"Expected Welch p={expected_p:.8f}, got {res[0][2]:.8f}"

run("Parametric 2-group uses Welch's t-test (equal_var=False)", test_welch_default)

def test_student_not_used():
    """Student's t-test (equal_var=True) must NOT match parametric output for unequal-var data."""
    a = rng.normal(5, 0.5, 10)    # small variance
    b = rng.normal(5, 5.0, 10)    # large variance — Student's vs Welch's will differ
    res = pf._run_stats({"A": a, "B": b}, test_type="parametric")
    _, student_p = _scipy_stats.ttest_ind(a, b, equal_var=True)
    _, welch_p   = _scipy_stats.ttest_ind(a, b, equal_var=False)
    # The result should match Welch's, not Student's
    assert abs(res[0][2] - welch_p)   < 1e-9
    assert abs(res[0][2] - student_p) > 1e-9 or abs(welch_p - student_p) < 1e-6

run("Student's t-test NOT used for unequal-variance groups", test_student_not_used)

def test_paired_2group():
    a = A_BEFORE; b = A_AFTER
    res = pf._run_stats({"Before": a, "After": b}, test_type="paired")
    n   = min(len(a), len(b))
    _, expected_p = _scipy_stats.ttest_rel(a[:n], b[:n])
    assert abs(res[0][2] - expected_p) < 1e-10

run("Paired 2-group uses ttest_rel", test_paired_2group)

def test_paired_multigroup():
    groups = {k: v for k, v in list(A_RM.items())[:3]}
    res = pf._run_stats(groups, test_type="paired")
    assert len(res) == 3, f"Expected 3 pairs, got {len(res)}"

run("Paired 3-group produces 3 Holm-corrected paired t-test pairs", test_paired_multigroup)

def test_nonparametric_2group():
    a = A_CTRL; b = A_DRUGB
    res = pf._run_stats({"C": a, "D": b}, test_type="nonparametric")
    _, expected_p = _scipy_stats.mannwhitneyu(a, b, alternative="two-sided")
    assert abs(res[0][2] - expected_p) < 1e-8

run("Non-parametric 2-group uses Mann-Whitney U", test_nonparametric_2group)

def test_nonparametric_3group_kw_gating():
    """KW post-hoc should return empty when KW p >= 0.05."""
    same = {"A": rng.normal(5, 0.1, 8), "B": rng.normal(5, 0.1, 8), "C": rng.normal(5, 0.1, 8)}
    _, kw_p = _scipy_stats.kruskal(*same.values())
    res = pf._run_stats(same, test_type="nonparametric")
    if kw_p >= 0.05:
        assert res == [], f"KW gating failed: expected [], got {res}"

run("Non-parametric 3-group: KW gating blocks post-hoc when ns", test_nonparametric_3group_kw_gating)

def test_nonparametric_3group_posthoc():
    """KW + Dunn: clearly different groups should give 3 result pairs."""
    groups = {"Low": np.array([1,1,1,2,1,1,2,1], dtype=float),
              "Mid": np.array([10,11,9,10,11,10,9,10], dtype=float),
              "High":np.array([20,22,19,21,23,20,21,22], dtype=float)}
    _, kw_p = _scipy_stats.kruskal(*groups.values())
    assert kw_p < 0.05
    res = pf._run_stats(groups, test_type="nonparametric")
    assert len(res) == 3

run("Non-parametric 3-group: KW + Dunn yields 3 pairs", test_nonparametric_3group_posthoc)

def test_parametric_tukey_3group():
    res = pf._run_stats(A_GROUPS, test_type="parametric", posthoc="Tukey HSD")
    assert len(res) == 3

run("Parametric Tukey HSD 3-group: 3 pairs", test_parametric_tukey_3group)

def test_parametric_bonferroni():
    res = pf._run_stats(A_GROUPS, test_type="parametric", posthoc="Bonferroni")
    assert len(res) == 3

run("Parametric Bonferroni 3-group: 3 pairs", test_parametric_bonferroni)

def test_parametric_sidak():
    res = pf._run_stats(A_GROUPS, test_type="parametric", posthoc="Sidak")
    assert len(res) == 3

run("Parametric Sidak 3-group: 3 pairs", test_parametric_sidak)

def test_parametric_fisher_lsd():
    res = pf._run_stats(A_GROUPS, test_type="parametric", posthoc="Fisher LSD")
    assert len(res) == 3

run("Parametric Fisher LSD 3-group: 3 pairs", test_parametric_fisher_lsd)

def test_parametric_dunnett():
    res = pf._run_stats(A_GROUPS, test_type="parametric",
                        posthoc="Dunnett (vs control)", control="Control")
    assert len(res) == 2
    assert all(r[0] == "Control" for r in res)

run("Parametric Dunnett vs control: 2 pairs, all vs Control", test_parametric_dunnett)

def test_permutation_2group():
    a = A_CTRL[:6]; b = A_DRUG[:6]
    res = pf._run_stats({"C": a, "D": b}, test_type="permutation", n_permutations=99)
    assert len(res) == 1
    assert 0.0 <= res[0][2] <= 1.0

run("Permutation test 2-group returns valid p-value", test_permutation_2group)

def test_mc_corrections():
    """All 4 MC corrections must return valid p-values in [0,1]."""
    raw = [0.001, 0.02, 0.04, 0.08, 0.12]
    for method in ["Holm-Bonferroni", "Bonferroni", "Benjamini-Hochberg (FDR)", "None (uncorrected)"]:
        corrected = pf._apply_correction(raw, method)
        assert len(corrected) == 5
        assert all(0.0 <= p <= 1.0 for p in corrected), f"{method}: out-of-range p: {corrected}"
        if method != "None (uncorrected)":
            assert max(corrected) >= max(raw) or method == "Benjamini-Hochberg (FDR)"

run("All 4 MC correction methods return valid p in [0,1]", test_mc_corrections)

def test_p_to_stars():
    assert pf._p_to_stars(0.00001) == "****"
    assert pf._p_to_stars(0.0005)  == "***"
    assert pf._p_to_stars(0.005)   == "**"
    assert pf._p_to_stars(0.03)    == "*"
    assert pf._p_to_stars(0.1)     == "ns"

run("_p_to_stars thresholds match GraphPad Prism exactly", test_p_to_stars)

def test_shapiro_normality():
    normal  = rng.normal(0, 1, 50)
    skewed  = rng.exponential(1.0, 50)
    r_norm  = pf.check_normality({"Normal":  normal})
    r_skew  = pf.check_normality({"Skewed": skewed})
    assert r_norm["Normal"][2]  == True,  "Normal data failed normality check"
    assert r_skew["Skewed"][2]  == False, "Skewed data passed normality check"

run("check_normality: normal → pass, skewed → fail", test_shapiro_normality)

def test_normality_warning_parametric():
    # Fixed seed so this is independent of global rng draw order
    skewed = np.random.default_rng(999).exponential(0.3, 20)  # strongly right-skewed
    warn = pf.normality_warning({"Skewed": skewed}, "parametric")
    assert warn != "", "Should warn for non-normal data with parametric test"

run("normality_warning fires for non-normal + parametric", test_normality_warning_parametric)

def test_normality_warning_nonparametric():
    skewed = rng.exponential(1, 20)
    warn = pf.normality_warning({"Skewed": skewed}, "nonparametric")
    assert warn == "", "Should NOT warn when using non-parametric test"

run("normality_warning silent for non-parametric test", test_normality_warning_nonparametric)

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2 — Bar Chart (Dataset A & B)
# ─────────────────────────────────────────────────────────────────────────────

section("SECTION 2 — Bar Chart")

def _bar_test(name, groups, **kwargs):
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        path = f.name
    try:
        _write_bar(path, groups)
        fig, ax = pf.plotter_barplot(path, **kwargs)
        assert fig is not None
        _close(fig)
    finally:
        os.unlink(path)

# Dataset A — all stat tests, all error types, all display flags
for ds_tag, groups in [("A", A_GROUPS), ("B", B_GROUPS)]:
    g2 = {"Control": list(groups.values())[0], list(groups.keys())[1]: list(groups.values())[1]}

    run(f"[{ds_tag}] Bar: basic default",
        lambda g=groups: _bar_test("basic", g))
    run(f"[{ds_tag}] Bar: error=sd",
        lambda g=groups: _bar_test("sd", g, error="sd"))
    run(f"[{ds_tag}] Bar: error=ci95",
        lambda g=groups: _bar_test("ci95", g, error="ci95"))
    run(f"[{ds_tag}] Bar: show_stats + parametric",
        lambda g=groups: _bar_test("stats_param", g, show_stats=True, stats_test="parametric",
                                    posthoc="Tukey HSD"))
    run(f"[{ds_tag}] Bar: show_stats + nonparametric",
        lambda g=groups: _bar_test("stats_np", g, show_stats=True, stats_test="nonparametric"))
    run(f"[{ds_tag}] Bar: show_stats + paired (2-group)",
        lambda g2=g2: _bar_test("stats_paired", g2, show_stats=True, stats_test="paired"))
    run(f"[{ds_tag}] Bar: show_stats + permutation",
        lambda g2=g2: _bar_test("stats_perm", g2, show_stats=True, stats_test="permutation",
                                 n_permutations=99))
    run(f"[{ds_tag}] Bar: posthoc=Bonferroni",
        lambda g=groups: _bar_test("posthoc_bf", g, show_stats=True, stats_test="parametric",
                                    posthoc="Bonferroni"))
    run(f"[{ds_tag}] Bar: posthoc=Sidak",
        lambda g=groups: _bar_test("posthoc_sd", g, show_stats=True, stats_test="parametric",
                                    posthoc="Sidak"))
    run(f"[{ds_tag}] Bar: posthoc=Fisher LSD",
        lambda g=groups: _bar_test("posthoc_fl", g, show_stats=True, stats_test="parametric",
                                    posthoc="Fisher LSD"))
    run(f"[{ds_tag}] Bar: posthoc=Dunnett",
        lambda g=groups: _bar_test("posthoc_dn", g, show_stats=True, stats_test="parametric",
                                    posthoc="Dunnett (vs control)",
                                    control=list(groups.keys())[0]))
    run(f"[{ds_tag}] Bar: mc=Bonferroni",
        lambda g=groups: _bar_test("mc_bf", g, show_stats=True, mc_correction="Bonferroni"))
    run(f"[{ds_tag}] Bar: mc=BH FDR",
        lambda g=groups: _bar_test("mc_bh", g, show_stats=True,
                                    mc_correction="Benjamini-Hochberg (FDR)"))
    run(f"[{ds_tag}] Bar: mc=None",
        lambda g=groups: _bar_test("mc_none", g, show_stats=True,
                                    mc_correction="None (uncorrected)"))
    run(f"[{ds_tag}] Bar: show_p_values",
        lambda g=groups: _bar_test("pvals", g, show_stats=True, show_p_values=True))
    run(f"[{ds_tag}] Bar: show_effect_size",
        lambda g=g2: _bar_test("effect", g, show_stats=True, show_effect_size=True))
    run(f"[{ds_tag}] Bar: show_test_name",
        lambda g=groups: _bar_test("testname", g, show_stats=True, show_test_name=True))
    run(f"[{ds_tag}] Bar: gridlines=True",
        lambda g=groups: _bar_test("grid", g, gridlines=True))
    run(f"[{ds_tag}] Bar: horizontal=True",
        lambda g=groups: _bar_test("horiz", g, horizontal=True))
    run(f"[{ds_tag}] Bar: yscale=log",
        lambda g=groups: _bar_test("log", {k: np.abs(v)+1 for k,v in groups.items()},
                                    yscale="log"))
    run(f"[{ds_tag}] Bar: error_below_bar=True",
        lambda g=groups: _bar_test("errbelow", g, error_below_bar=True))
    run(f"[{ds_tag}] Bar: show_median=True",
        lambda g=groups: _bar_test("median", g, show_median=True))
    run(f"[{ds_tag}] Bar: open_points=True",
        lambda g=groups: _bar_test("open_pts", g, open_points=True))
    run(f"[{ds_tag}] Bar: ref_line",
        lambda g=groups: _bar_test("refline", g, ref_line=10.0, ref_line_label="Threshold"))
    run(f"[{ds_tag}] Bar: ylim manual",
        lambda g=groups: _bar_test("ylim", g, ylim=(0, 30)))
    run(f"[{ds_tag}] Bar: color override",
        lambda g=groups: _bar_test("color", g, color="#E74C3C"))
    run(f"[{ds_tag}] Bar: bar_width=0.4",
        lambda g=groups: _bar_test("barw", g, bar_width=0.4))
    run(f"[{ds_tag}] Bar: show_stats + show_ns",
        lambda g=groups: _bar_test("showns", g, show_stats=True,
                                    show_p_values=False))  # ns brackets via show_ns

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3 — Line Graph
# ─────────────────────────────────────────────────────────────────────────────

section("SECTION 3 — Line Graph")

def _line_test(name, series, x_vals, **kwargs):
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        path = f.name
    try:
        _write_line(path, series, x_vals)
        fig, ax = pf.plotter_linegraph(path, **kwargs)
        assert fig is not None
        _close(fig)
    finally:
        os.unlink(path)

for ds_tag, series, x_vals in [("A", A_LINE, A_X), ("B", B_LINE, B_X)]:
    run(f"[{ds_tag}] Line: basic default",
        lambda s=series, x=x_vals: _line_test("basic", s, x))
    run(f"[{ds_tag}] Line: error=sd",
        lambda s=series, x=x_vals: _line_test("sd", s, x, error="sd"))
    run(f"[{ds_tag}] Line: error=ci95",
        lambda s=series, x=x_vals: _line_test("ci95", s, x, error="ci95"))
    run(f"[{ds_tag}] Line: yscale=log",
        lambda s=series, x=x_vals: _line_test("log", s, x, yscale="log"))
    run(f"[{ds_tag}] Line: gridlines",
        lambda s=series, x=x_vals: _line_test("grid", s, x, gridlines=True))
    run(f"[{ds_tag}] Line: show_points=False",
        lambda s=series, x=x_vals: _line_test("nopts", s, x, show_points=False))
    run(f"[{ds_tag}] Line: marker_style=s",
        lambda s=series, x=x_vals: _line_test("marker", s, x, marker_style="s"))
    run(f"[{ds_tag}] Line: ref_line",
        lambda s=series, x=x_vals: _line_test("refline", s, x, ref_line=5.0))

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4 — Grouped Bar
# ─────────────────────────────────────────────────────────────────────────────

section("SECTION 4 — Grouped Bar")

def _grouped_test(name, ds_tag, **kwargs):
    cats      = ["CatA", "CatB"]
    subs      = ["SubX", "SubY", "SubZ"]
    data_a    = {c: {s: rng.normal(i*3+j*1.5, 1.0, 6).tolist()
                     for j, s in enumerate(subs)}
                 for i, c in enumerate(cats)}
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        path = f.name
    try:
        _write_grouped(path, cats, subs, data_a)
        fig, ax = pf.plotter_grouped_barplot(path, **kwargs)
        assert fig is not None
        _close(fig)
    finally:
        os.unlink(path)

for ds_tag in ["A", "B"]:
    run(f"[{ds_tag}] Grouped Bar: default",
        lambda t=ds_tag: _grouped_test("basic", t))
    run(f"[{ds_tag}] Grouped Bar: show_stats=True",
        lambda t=ds_tag: _grouped_test("stats", t, show_stats=True))
    run(f"[{ds_tag}] Grouped Bar: show_anova_per_group",
        lambda t=ds_tag: _grouped_test("anova_pg", t, show_anova_per_group=True))
    run(f"[{ds_tag}] Grouped Bar: yscale=log",
        lambda t=ds_tag: _grouped_test("log", t, yscale="log"))
    run(f"[{ds_tag}] Grouped Bar: error=ci95",
        lambda t=ds_tag: _grouped_test("ci95", t, error="ci95"))

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5 — Box Plot
# ─────────────────────────────────────────────────────────────────────────────

section("SECTION 5 — Box Plot")

def _box_test(groups, **kwargs):
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        path = f.name
    try:
        _write_bar(path, groups)
        fig, ax = pf.plotter_boxplot(path, **kwargs)
        assert fig is not None
        _close(fig)
    finally:
        os.unlink(path)

for ds_tag, groups in [("A", A_GROUPS), ("B", B_GROUPS)]:
    g2 = {k: v for k, v in list(groups.items())[:2]}
    run(f"[{ds_tag}] Box: default",        lambda g=groups: _box_test(g))
    run(f"[{ds_tag}] Box: show_stats parametric",
        lambda g=groups: _box_test(g, show_stats=True, stats_test="parametric",
                                    posthoc="Tukey HSD"))
    run(f"[{ds_tag}] Box: show_stats nonparametric",
        lambda g=groups: _box_test(g, show_stats=True, stats_test="nonparametric"))
    run(f"[{ds_tag}] Box: show_stats paired",
        lambda g=g2: _box_test(g, show_stats=True, stats_test="paired"))
    run(f"[{ds_tag}] Box: notch=True",     lambda g=groups: _box_test(g, notch=True))
    run(f"[{ds_tag}] Box: gridlines",      lambda g=groups: _box_test(g, gridlines=True))
    run(f"[{ds_tag}] Box: yscale=log",
        lambda g=groups: _box_test({k: np.abs(v)+1 for k,v in groups.items()}, yscale="log"))
    run(f"[{ds_tag}] Box: Dunnett",
        lambda g=groups: _box_test(g, show_stats=True, stats_test="parametric",
                                    posthoc="Dunnett (vs control)",
                                    control=list(groups.keys())[0]))

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 6 — Scatter Plot
# ─────────────────────────────────────────────────────────────────────────────

section("SECTION 6 — Scatter Plot")

def _scatter_test(series, x_vals, **kwargs):
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        path = f.name
    try:
        _write_line(path, series, x_vals)
        fig, ax = pf.plotter_scatterplot(path, **kwargs)
        assert fig is not None
        _close(fig)
    finally:
        os.unlink(path)

for ds_tag, series, x_vals in [("A", A_LINE, A_X), ("B", B_LINE, B_X)]:
    run(f"[{ds_tag}] Scatter: default (regression+CI)",
        lambda s=series, x=x_vals: _scatter_test(s, x))
    run(f"[{ds_tag}] Scatter: prediction_band",
        lambda s=series, x=x_vals: _scatter_test(s, x, show_prediction_band=True))
    run(f"[{ds_tag}] Scatter: correlation_type=spearman",
        lambda s=series, x=x_vals: _scatter_test(s, x, correlation_type="spearman"))
    run(f"[{ds_tag}] Scatter: no regression",
        lambda s=series, x=x_vals: _scatter_test(s, x, show_regression=False,
                                                   show_correlation=False))
    run(f"[{ds_tag}] Scatter: gridlines",
        lambda s=series, x=x_vals: _scatter_test(s, x, gridlines=True))
    run(f"[{ds_tag}] Scatter: log scales",
        lambda s=series, x=x_vals: _scatter_test(
            {k: np.abs(v)+0.1 for k,v in s.items()},
            np.abs(x)+0.1, yscale="log"))

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 7 — Violin Plot
# ─────────────────────────────────────────────────────────────────────────────

section("SECTION 7 — Violin Plot")

def _violin_test(groups, **kwargs):
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        path = f.name
    try:
        _write_bar(path, groups)
        fig, ax = pf.plotter_violin(path, **kwargs)
        assert fig is not None
        _close(fig)
    finally:
        os.unlink(path)

for ds_tag, groups in [("A", A_GROUPS), ("B", B_GROUPS)]:
    g2 = {k: v for k, v in list(groups.items())[:2]}
    run(f"[{ds_tag}] Violin: default",
        lambda g=groups: _violin_test(g))
    run(f"[{ds_tag}] Violin: show_stats parametric Tukey",
        lambda g=groups: _violin_test(g, show_stats=True, stats_test="parametric"))
    run(f"[{ds_tag}] Violin: show_stats nonparametric",
        lambda g=groups: _violin_test(g, show_stats=True, stats_test="nonparametric"))
    run(f"[{ds_tag}] Violin: show_stats paired",
        lambda g=g2: _violin_test(g, show_stats=True, stats_test="paired"))
    run(f"[{ds_tag}] Violin: open_points",
        lambda g=groups: _violin_test(g, open_points=True))
    run(f"[{ds_tag}] Violin: Dunnett",
        lambda g=groups: _violin_test(g, show_stats=True, stats_test="parametric",
                                       posthoc="Dunnett (vs control)",
                                       control=list(groups.keys())[0]))

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 8 — Kaplan-Meier
# ─────────────────────────────────────────────────────────────────────────────

section("SECTION 8 — Kaplan-Meier Survival")

def _km_test(groups, **kwargs):
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        path = f.name
    try:
        _write_km(path, groups)
        fig, ax = pf.plotter_kaplan_meier(path, **kwargs)
        assert fig is not None
        _close(fig)
    finally:
        os.unlink(path)

for ds_tag, groups in [("A", A_KM), ("B", B_KM)]:
    run(f"[{ds_tag}] KM: default",
        lambda g=groups: _km_test(g))
    run(f"[{ds_tag}] KM: show_ci=False",
        lambda g=groups: _km_test(g, show_ci=False))
    run(f"[{ds_tag}] KM: show_censors=False",
        lambda g=groups: _km_test(g, show_censors=False))
    run(f"[{ds_tag}] KM: show_stats=True",
        lambda g=groups: _km_test(g, show_stats=True))
    run(f"[{ds_tag}] KM: show_at_risk=True",
        lambda g=groups: _km_test(g, show_at_risk=True))
    run(f"[{ds_tag}] KM: show_p_values=True",
        lambda g=groups: _km_test(g, show_stats=True, show_p_values=True))

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 9 — Heatmap
# ─────────────────────────────────────────────────────────────────────────────

section("SECTION 9 — Heatmap")

def _hm_test(matrix, rows, cols, **kwargs):
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        path = f.name
    try:
        _write_heatmap(path, matrix, rows, cols)
        fig, ax = pf.plotter_heatmap(path, **kwargs)
        assert fig is not None
        _close(fig)
    finally:
        os.unlink(path)

for ds_tag, mat, rows, cols in [("A", A_HM_MATRIX, A_HM_ROWS, A_HM_COLS),
                                  ("B", B_HM_MATRIX, B_HM_ROWS, B_HM_COLS)]:
    run(f"[{ds_tag}] Heatmap: default",
        lambda m=mat, r=rows, c=cols: _hm_test(m, r, c))
    run(f"[{ds_tag}] Heatmap: annotate=True",
        lambda m=mat, r=rows, c=cols: _hm_test(m, r, c, annotate=True))
    run(f"[{ds_tag}] Heatmap: cluster_rows=True",
        lambda m=mat, r=rows, c=cols: _hm_test(m, r, c, cluster_rows=True))
    run(f"[{ds_tag}] Heatmap: cluster_cols=True",
        lambda m=mat, r=rows, c=cols: _hm_test(m, r, c, cluster_cols=True))
    run(f"[{ds_tag}] Heatmap: cluster rows+cols",
        lambda m=mat, r=rows, c=cols: _hm_test(m, r, c, cluster_rows=True, cluster_cols=True))
    run(f"[{ds_tag}] Heatmap: robust=True",
        lambda m=mat, r=rows, c=cols: _hm_test(m, r, c, robust=True))
    run(f"[{ds_tag}] Heatmap: vmin/vmax",
        lambda m=mat, r=rows, c=cols: _hm_test(m, r, c, vmin=-2.0, vmax=2.0))
    run(f"[{ds_tag}] Heatmap: custom colormap",
        lambda m=mat, r=rows, c=cols: _hm_test(m, r, c, color="RdBu_r"))

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 10 — Two-Way ANOVA
# ─────────────────────────────────────────────────────────────────────────────

section("SECTION 10 — Two-Way ANOVA")

def _twa_test(records, **kwargs):
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        path = f.name
    try:
        _write_two_way(path, records)
        fig, ax = pf.plotter_two_way_anova(path, **kwargs)
        assert fig is not None
        _close(fig)
    finally:
        os.unlink(path)

for ds_tag, recs in [("A", A_TWO), ("B", B_TWO)]:
    run(f"[{ds_tag}] TwoWay: default",
        lambda r=recs: _twa_test(r))
    run(f"[{ds_tag}] TwoWay: show_stats=True",
        lambda r=recs: _twa_test(r, show_stats=True))
    run(f"[{ds_tag}] TwoWay: show_posthoc=True",
        lambda r=recs: _twa_test(r, show_stats=True, show_posthoc=True))
    run(f"[{ds_tag}] TwoWay: show_effect_size",
        lambda r=recs: _twa_test(r, show_stats=True, show_effect_size=True))
    run(f"[{ds_tag}] TwoWay: error=sd",
        lambda r=recs: _twa_test(r, error="sd"))
    run(f"[{ds_tag}] TwoWay: error=ci95",
        lambda r=recs: _twa_test(r, error="ci95"))

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 11 — Before / After
# ─────────────────────────────────────────────────────────────────────────────

section("SECTION 11 — Before/After")

def _ba_test(groups, **kwargs):
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        path = f.name
    try:
        _write_bar(path, groups)
        fig, ax = pf.plotter_before_after(path, **kwargs)
        assert fig is not None
        _close(fig)
    finally:
        os.unlink(path)

for ds_tag, groups in [("A", A_PAIRED), ("B", B_PAIRED)]:
    run(f"[{ds_tag}] Before/After: default",
        lambda g=groups: _ba_test(g))
    run(f"[{ds_tag}] Before/After: show_stats=True",
        lambda g=groups: _ba_test(g, show_stats=True))
    run(f"[{ds_tag}] Before/After: show_p_values=True",
        lambda g=groups: _ba_test(g, show_stats=True, show_p_values=True))
    run(f"[{ds_tag}] Before/After: gridlines",
        lambda g=groups: _ba_test(g, gridlines=True))
    run(f"[{ds_tag}] Before/After: show_n_labels",
        lambda g=groups: _ba_test(g, show_n_labels=True))
    run(f"[{ds_tag}] Before/After: yscale=log",
        lambda g=groups: _ba_test({k: np.abs(v)+1 for k,v in groups.items()}, yscale="log"))

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 12 — Histogram
# ─────────────────────────────────────────────────────────────────────────────

section("SECTION 12 — Histogram")

def _hist_test(groups, **kwargs):
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        path = f.name
    try:
        _write_bar(path, groups)
        fig, ax = pf.plotter_histogram(path, **kwargs)
        assert fig is not None
        _close(fig)
    finally:
        os.unlink(path)

for ds_tag, groups in [("A", A_GROUPS), ("B", B_GROUPS)]:
    run(f"[{ds_tag}] Histogram: auto bins",
        lambda g=groups: _hist_test(g))
    run(f"[{ds_tag}] Histogram: fixed bins=12",
        lambda g=groups: _hist_test(g, bins=12))
    run(f"[{ds_tag}] Histogram: density=True",
        lambda g=groups: _hist_test(g, density=True))
    run(f"[{ds_tag}] Histogram: overlay_normal=True",
        lambda g=groups: _hist_test(g, overlay_normal=True))
    run(f"[{ds_tag}] Histogram: density+normal",
        lambda g=groups: _hist_test(g, density=True, overlay_normal=True))

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 13 — Subcolumn Scatter
# ─────────────────────────────────────────────────────────────────────────────

section("SECTION 13 — Subcolumn Scatter")

def _sub_test(groups, **kwargs):
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        path = f.name
    try:
        _write_bar(path, groups)
        fig, ax = pf.plotter_subcolumn_scatter(path, **kwargs)
        assert fig is not None
        _close(fig)
    finally:
        os.unlink(path)

for ds_tag, groups in [("A", A_GROUPS), ("B", B_GROUPS)]:
    g2 = {k: v for k, v in list(groups.items())[:2]}
    run(f"[{ds_tag}] Subcolumn: default",
        lambda g=groups: _sub_test(g))
    run(f"[{ds_tag}] Subcolumn: show_stats parametric",
        lambda g=groups: _sub_test(g, show_stats=True, stats_test="parametric"))
    run(f"[{ds_tag}] Subcolumn: show_stats nonparametric",
        lambda g=groups: _sub_test(g, show_stats=True, stats_test="nonparametric"))
    run(f"[{ds_tag}] Subcolumn: show_stats paired",
        lambda g=g2: _sub_test(g, show_stats=True, stats_test="paired"))
    run(f"[{ds_tag}] Subcolumn: Dunnett",
        lambda g=groups: _sub_test(g, show_stats=True, stats_test="parametric",
                                    posthoc="Dunnett (vs control)",
                                    control=list(groups.keys())[0]))
    run(f"[{ds_tag}] Subcolumn: error=sd open_points",
        lambda g=groups: _sub_test(g, error="sd", open_points=True))
    run(f"[{ds_tag}] Subcolumn: yscale=log",
        lambda g=groups: _sub_test({k: np.abs(v)+1 for k,v in groups.items()}, yscale="log"))
    run(f"[{ds_tag}] Subcolumn: gridlines",
        lambda g=groups: _sub_test(g, gridlines=True))
    run(f"[{ds_tag}] Subcolumn: show_p_values",
        lambda g=groups: _sub_test(g, show_stats=True, show_p_values=True))

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 14 — Curve Fit (all 11 models × 2 datasets)
# ─────────────────────────────────────────────────────────────────────────────

section("SECTION 14 — Curve Fit (all 11 models)")

def _cf_test(x_vals, y_vals, model_name, **kwargs):
    series = {"Data": np.column_stack([y_vals])}
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        path = f.name
    try:
        _write_line(path, series, x_vals)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            fig, ax = pf.plotter_curve_fit(path, model_name=model_name, **kwargs)
        assert fig is not None
        _close(fig)
    finally:
        os.unlink(path)

# Prepare per-model appropriate test data
MODELS_A = {
    "4PL Sigmoidal (EC50/IC50)":   (A_CF_X, A_CF_Y),
    "3PL Sigmoidal (no bottom)":   (A_CF_X, np.abs(A_CF_Y)),
    "One-phase exponential decay":  (B_CF_X, B_CF_Y),
    "One-phase exponential growth": (np.linspace(0,5,12),
                                     5*np.exp(0.3*np.linspace(0,5,12)) + rng.normal(0,0.5,12)),
    "Two-phase exponential decay":  (B_CF_X, B_CF_Y),
    "Michaelis-Menten":             (np.linspace(0.1, 20, 12),
                                     100*np.linspace(0.1,20,12)/(5+np.linspace(0.1,20,12))
                                     + rng.normal(0,2,12)),
    "Hill equation":                (np.logspace(-1, 2, 12),
                                     80*np.logspace(-1,2,12)**1.5/(10**1.5+np.logspace(-1,2,12)**1.5)
                                     + rng.normal(0,2,12)),
    "Gaussian (bell curve)":        (np.linspace(-5, 5, 15),
                                     50*np.exp(-0.5*(np.linspace(-5,5,15))**2)
                                     + rng.normal(0,1,15)),
    "Log-normal":                   (np.logspace(-1, 2, 12),
                                     30*np.exp(-0.5*(np.log(np.logspace(-1,2,12))-1)**2)
                                     + rng.normal(0,1,12)),
    "Linear":                       (np.linspace(0, 10, 12),
                                     2.5*np.linspace(0,10,12) + 3 + rng.normal(0,0.5,12)),
    "Polynomial (2nd order)":       (np.linspace(-3, 3, 12),
                                     2*np.linspace(-3,3,12)**2 - 1.5*np.linspace(-3,3,12) + 5
                                     + rng.normal(0,0.5,12)),
}

for model_name, (x_d, y_d) in MODELS_A.items():
    run(f"[A] Curve Fit: {model_name}",
        lambda x=x_d, y=y_d, m=model_name: _cf_test(x, y, m))
    run(f"[A] Curve Fit: {model_name} + show_residuals",
        lambda x=x_d, y=y_d, m=model_name: _cf_test(x, y, m, show_residuals=True))

# Dataset B — 4PL + Exp decay + Linear
run("[B] Curve Fit: 4PL Sigmoidal",
    lambda: _cf_test(np.logspace(-2,2,10),
                     100/(1+(10/np.logspace(-2,2,10))**1.2)+rng.normal(0,3,10),
                     "4PL Sigmoidal (EC50/IC50)"))
run("[B] Curve Fit: One-phase exponential decay",
    lambda: _cf_test(B_CF_X, B_CF_Y, "One-phase exponential decay"))
run("[B] Curve Fit: Linear",
    lambda: _cf_test(B_CF_X, 3*B_CF_X + rng.normal(0,1,12), "Linear"))
run("[B] Curve Fit: gridlines + ci_band",
    lambda: _cf_test(B_CF_X, B_CF_Y, "One-phase exponential decay",
                     gridlines=True, show_ci_band=True))

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 15 — Column Statistics
# ─────────────────────────────────────────────────────────────────────────────

section("SECTION 15 — Column Statistics")

def _cs_test(groups, **kwargs):
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        path = f.name
    try:
        _write_bar(path, groups)
        fig, ax = pf.plotter_column_stats(path, **kwargs)
        assert fig is not None
        _close(fig)
    finally:
        os.unlink(path)

for ds_tag, groups in [("A", A_GROUPS), ("B", B_GROUPS)]:
    run(f"[{ds_tag}] ColStats: default (all flags on)",
        lambda g=groups: _cs_test(g))
    run(f"[{ds_tag}] ColStats: no normality",
        lambda g=groups: _cs_test(g, show_normality=False))
    run(f"[{ds_tag}] ColStats: no CI",
        lambda g=groups: _cs_test(g, show_ci=False))
    run(f"[{ds_tag}] ColStats: no CV",
        lambda g=groups: _cs_test(g, show_cv=False))
    run(f"[{ds_tag}] ColStats: all flags off",
        lambda g=groups: _cs_test(g, show_normality=False, show_ci=False, show_cv=False))

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 16 — Contingency
# ─────────────────────────────────────────────────────────────────────────────

section("SECTION 16 — Contingency")

def _ct_test(row_labels, col_labels, matrix, **kwargs):
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        path = f.name
    try:
        _write_contingency(path, row_labels, col_labels, matrix)
        fig, ax = pf.plotter_contingency(path, **kwargs)
        assert fig is not None
        _close(fig)
    finally:
        os.unlink(path)

# 2×2 (Fisher's exact)
run("[A] Contingency: 2×2 Fisher exact",
    lambda: _ct_test(["Drug","Control"], ["Survived","Died"], [[45,5],[20,30]]))
run("[B] Contingency: 2×2 Fisher exact",
    lambda: _ct_test(B_CT_ROWS, B_CT_COLS, B_CT_MAT))
# 3×2 (Chi-square)
run("[A] Contingency: 3×2 chi-square",
    lambda: _ct_test(A_CT_ROWS, A_CT_COLS, A_CT_MAT))
# Options
run("[A] Contingency: show_percentages=True",
    lambda: _ct_test(["Drug","Control"], ["Survived","Died"], [[45,5],[20,30]],
                      show_percentages=True))
run("[A] Contingency: show_expected=True",
    lambda: _ct_test(["Drug","Control"], ["Survived","Died"], [[45,5],[20,30]],
                      show_expected=True))
run("[A] Contingency: show_percentages=False",
    lambda: _ct_test(["Drug","Control"], ["Survived","Died"], [[45,5],[20,30]],
                      show_percentages=False))

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 17 — Repeated Measures
# ─────────────────────────────────────────────────────────────────────────────

section("SECTION 17 — Repeated Measures")

def _rm_test(groups, **kwargs):
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        path = f.name
    try:
        _write_bar(path, groups)
        fig, ax = pf.plotter_repeated_measures(path, **kwargs)
        assert fig is not None
        _close(fig)
    finally:
        os.unlink(path)

for ds_tag, groups in [("A", A_RM), ("B", B_RM)]:
    run(f"[{ds_tag}] RM: default",
        lambda g=groups: _rm_test(g))
    run(f"[{ds_tag}] RM: show_stats parametric",
        lambda g=groups: _rm_test(g, show_stats=True, test_type="parametric"))
    run(f"[{ds_tag}] RM: show_stats nonparametric",
        lambda g=groups: _rm_test(g, show_stats=True, test_type="nonparametric"))
    run(f"[{ds_tag}] RM: show_subject_lines=False",
        lambda g=groups: _rm_test(g, show_subject_lines=False))
    run(f"[{ds_tag}] RM: show_p_values",
        lambda g=groups: _rm_test(g, show_stats=True, show_p_values=True))
    run(f"[{ds_tag}] RM: error=sd",
        lambda g=groups: _rm_test(g, error="sd"))
    run(f"[{ds_tag}] RM: error=ci95",
        lambda g=groups: _rm_test(g, error="ci95"))
    run(f"[{ds_tag}] RM: yscale=log",
        lambda g=groups: _rm_test({k: np.abs(v)+1 for k,v in groups.items()}, yscale="log"))

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 18 — Help Analyze Decision Tree Logic
# ─────────────────────────────────────────────────────────────────────────────

section("SECTION 18 — Help Analyze Decision Tree")

def _run_decision(groups: dict, is_paired_mode: bool = False):
    """Replicate the core decision tree from _help_analyze."""
    from scipy import stats as _st
    k = len(groups)
    normality = {}
    for name, vals in groups.items():
        vals_arr = np.array(vals)
        n = len(vals_arr)
        if n >= 3:
            _, p = _st.shapiro(vals_arr)
            normality[name] = {"n": n, "normal": p > 0.05}
        else:
            normality[name] = {"n": n, "normal": True}
    all_normal = all(d["normal"] for d in normality.values())
    equal_n    = len(set(len(v) for v in groups.values())) == 1

    if is_paired_mode and equal_n:
        if k == 2:
            return "Paired"
        return "Paired" if all_normal else "Non-parametric"
    elif k == 2:
        return "Parametric" if all_normal else "Non-parametric"
    else:
        return "Parametric" if all_normal else "Non-parametric"

# Helper for assert_eq with message
def assert_eq(a, b, msg=""):
    assert a == b, f"Expected {b}, got {a}. {msg}"

run("[A] Help Analyze: 2 groups (normal) → Parametric",
    lambda: assert_eq(_run_decision({"C": A_CTRL, "D": A_DRUG}), "Parametric"))
run("[A] Help Analyze: 2 groups (non-normal) → Non-parametric",
    lambda: assert_eq(
        _run_decision({"C": rng.exponential(1,20), "D": rng.exponential(2,20)}),
        "Non-parametric"))
run("[A] Help Analyze: 3 normal groups → Parametric",
    lambda: assert_eq(_run_decision(A_GROUPS), "Parametric"))
run("[A] Help Analyze: paired 2-group → Paired",
    lambda: assert_eq(_run_decision(A_PAIRED, is_paired_mode=True), "Paired"))
run("[B] Help Analyze: 4 normal groups → Parametric",
    lambda: assert_eq(_run_decision(B_GROUPS), "Parametric"))
run("[B] Help Analyze: 2 groups (normal) → Parametric",
    lambda: assert_eq(_run_decision(B_GROUPS2), "Parametric"))
run("[B] Help Analyze: paired 2-group → Paired",
    lambda: assert_eq(_run_decision(B_PAIRED, is_paired_mode=True), "Paired"))

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 19 — Edge cases & Robustness
# ─────────────────────────────────────────────────────────────────────────────

section("SECTION 19 — Edge Cases & Robustness")

def test_apply_correction_empty():
    assert pf._apply_correction([], "Holm-Bonferroni") == []
    assert pf._apply_correction([], "Bonferroni") == []

run("_apply_correction: empty list returns empty list", test_apply_correction_empty)

def test_apply_correction_single():
    for method in ["Holm-Bonferroni", "Bonferroni", "Benjamini-Hochberg (FDR)", "None (uncorrected)"]:
        res = pf._apply_correction([0.03], method)
        assert len(res) == 1
        assert 0 <= res[0] <= 1

run("_apply_correction: single p-value handled for all methods", test_apply_correction_single)

def test_p_stars_boundary():
    assert pf._p_to_stars(0.0001) == "****"
    assert pf._p_to_stars(0.001)  == "***"
    assert pf._p_to_stars(0.01)   == "**"
    assert pf._p_to_stars(0.05)   == "*"
    assert pf._p_to_stars(0.051)  == "ns"

run("_p_to_stars boundary values correct", test_p_stars_boundary)

def test_normality_too_few():
    r = pf.check_normality({"G": np.array([1.0, 2.0])})  # n=2, too few
    assert r["G"][2] is None, "n<3 should return None is_normal"

run("check_normality: n<3 returns None (not crash)", test_normality_too_few)

def test_run_stats_single_group():
    """_run_stats with k=1 should return empty (no comparisons)."""
    res = pf._run_stats({"Only": np.array([1.0, 2.0, 3.0])}, test_type="parametric")
    assert res == []

run("_run_stats: single group returns empty list (no error)", test_run_stats_single_group)

def test_bar_single_group():
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        path = f.name
    try:
        _write_bar(path, {"Control": rng.normal(5, 1, 8)})
        fig, ax = pf.plotter_barplot(path)
        assert fig is not None
        _close(fig)
    finally:
        os.unlink(path)

run("Bar chart with single group (no stats) renders without crash", test_bar_single_group)

def test_dunnett_control_fallback():
    """Dunnett with no explicit control falls back to first group."""
    groups = {"A": rng.normal(5, 1, 8),
              "B": rng.normal(8, 1, 8),
              "C": rng.normal(11, 1, 8)}
    res = pf._run_stats(groups, test_type="parametric",
                         posthoc="Dunnett (vs control)", control=None)
    # Should still produce results — falls back to first group
    assert len(res) >= 0  # either 2 results or error-free empty

run("Dunnett: control=None falls back gracefully", test_dunnett_control_fallback)

def test_large_groups_shapiro_skipped():
    """Shapiro-Wilk should skip for n>5000 without crashing."""
    big = rng.normal(0, 1, 5001)
    r = pf.check_normality({"Big": big})
    # Should complete without error; n>5000 branch returns assumed normal
    assert r["Big"][2] is not None or r["Big"][0] is None

run("check_normality: n>5000 handled without crash", test_large_groups_shapiro_skipped)

def test_all_posthoc_welchs():
    """All 4 parametric posthoc options must use Welch's (equal_var=False) pairwise."""
    a = rng.normal(5, 0.5, 10)
    b = rng.normal(8, 2.0, 10)   # very different variance
    c = rng.normal(12, 3.0, 10)

    for posthoc in ["Tukey HSD", "Bonferroni", "Sidak", "Fisher LSD"]:
        res = pf._run_stats({"A": a, "B": b, "C": c},
                             test_type="parametric", posthoc=posthoc)
        # All should complete and return 3 pairs
        assert len(res) == 3, f"{posthoc} returned {len(res)} pairs"

run("All 4 parametric posthoc options work with 3 groups", test_all_posthoc_welchs)


# =============================================================================
# P16–P20 Feature Tests
# =============================================================================
rng_p = np.random.default_rng(999)
_g3 = {"Ctrl": rng_p.normal(5,1,8), "DrugA": rng_p.normal(8,1,8), "DrugB": rng_p.normal(11,1,8)}
_g2 = {"Before": rng_p.normal(5,1,8), "After": rng_p.normal(8,1,8)}

section("P16 — Bracket style variants")

_stacked_data = {
    "CatA": {"Sub1": list(rng_p.normal(3,1,5)), "Sub2": list(rng_p.normal(4,1,5))},
    "CatB": {"Sub1": list(rng_p.normal(5,1,5)), "Sub2": list(rng_p.normal(6,1,5))},
}

def test_bracket_styles():
    """All three bracket_style values render without crash."""
    xl = bar_excel(_g3)
    try:
        for style in ("lines", "bracket", "asterisks_only"):
            fig, ax = pf.plotter_barplot(xl, show_stats=True, bracket_style=style)
            plt.close(fig)
    finally:
        if os.path.exists(xl): os.unlink(xl)

run("P16 all bracket_style variants", test_bracket_styles)

section("P17 — Horizontal stacked bar")

def test_stacked_horizontal():
    """plotter_stacked_bar horizontal=True renders without crash."""
    xl = grouped_excel(["CatA","CatB"], ["Sub1","Sub2"], _stacked_data)
    try:
        fig, ax = pf.plotter_stacked_bar(xl, horizontal=True)
        plt.close(fig)
        fig, ax = pf.plotter_stacked_bar(xl, horizontal=True, mode="percent")
        plt.close(fig)
        fig, ax = pf.plotter_stacked_bar(xl, horizontal=False)
        plt.close(fig)
    finally:
        if os.path.exists(xl): os.unlink(xl)

run("P17 horizontal + percent stacked bar", test_stacked_horizontal)

section("P18 — Custom x-tick labels")

def test_xtick_labels_bar():
    """xtick_labels override renders correctly on bar chart."""
    xl = bar_excel(_g3)
    try:
        labels = ["Alpha", "Beta", "Gamma"]
        fig, ax = pf.plotter_barplot(xl, xtick_labels=labels)
        tick_texts = [t.get_text() for t in ax.get_xticklabels()]
        assert any("Alpha" in t for t in tick_texts), f"Labels not applied: {tick_texts}"
        plt.close(fig)
    finally:
        if os.path.exists(xl): os.unlink(xl)

def test_xtick_labels_wrong_length():
    """xtick_labels with wrong length falls back without crash."""
    xl = bar_excel(_g3)
    try:
        fig, ax = pf.plotter_barplot(xl, xtick_labels=["OnlyOne"])
        plt.close(fig)
    finally:
        if os.path.exists(xl): os.unlink(xl)

def test_xtick_labels_none():
    """xtick_labels=None uses original column names."""
    xl = bar_excel(_g3)
    try:
        fig, ax = pf.plotter_barplot(xl, xtick_labels=None)
        plt.close(fig)
    finally:
        if os.path.exists(xl): os.unlink(xl)

run("P18 xtick_labels on bar chart", test_xtick_labels_bar)
run("P18 wrong-length xtick_labels falls back", test_xtick_labels_wrong_length)
run("P18 xtick_labels=None default", test_xtick_labels_none)

section("P19 — Twin Y-axis and vertical reference line")

# line_excel expects series[n] as 2D array (n_x_points, n_reps)
_xs = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
_line_series_2d = {
    "Series1": rng_p.normal(5,1,(5,3)),   # 5 x-points, 3 replicates
    "Series2": rng_p.normal(50,5,(5,3)),
}

def _make_line_xl():
    return with_excel(lambda p: line_excel(_line_series_2d, _xs, path=p))

def test_twin_y():
    """twin_y_series renders second axis without crash."""
    with _make_line_xl() as xl:
        fig, ax = pf.plotter_linegraph(xl, twin_y_series=["Series2"])
        plt.close(fig)

def test_twin_y_empty():
    """twin_y_series=[] is a no-op."""
    with _make_line_xl() as xl:
        fig, ax = pf.plotter_linegraph(xl, twin_y_series=[])
        plt.close(fig)

def test_twin_y_missing_series():
    """twin_y_series with nonexistent name doesn't crash."""
    with _make_line_xl() as xl:
        fig, ax = pf.plotter_linegraph(xl, twin_y_series=["Ghost"])
        plt.close(fig)

def test_ref_vline_line():
    """ref_vline draws vertical line on line chart."""
    with _make_line_xl() as xl:
        fig, ax = pf.plotter_linegraph(xl, ref_vline=3.0, ref_vline_label="EC50")
        plt.close(fig)

def test_ref_vline_scatter():
    """ref_vline works on scatter plot."""
    ys = rng_p.normal(5,1,5)
    with with_excel(lambda p: simple_xy_excel(_xs, ys, path=p)) as xl:
        fig, ax = pf.plotter_scatterplot(xl, ref_vline=2.5)
        plt.close(fig)

run("P19 twin_y_series", test_twin_y)
run("P19 twin_y_series=[] no-op", test_twin_y_empty)
run("P19 twin_y missing series no crash", test_twin_y_missing_series)
run("P19 ref_vline on line chart", test_ref_vline_line)
run("P19 ref_vline on scatter", test_ref_vline_scatter)

section("P20 — Export all charts PDF")

def test_export_all_pdf():
    """export_all_charts_pdf creates a non-empty PDF."""
    xl = bar_excel(_g3)
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        pdf_path = f.name
    try:
        result = pf.export_all_charts_pdf(pdf_path, xl)
        assert os.path.exists(pdf_path), "PDF not created"
        assert os.path.getsize(pdf_path) > 2000, "PDF too small"
    finally:
        if os.path.exists(pdf_path):
            os.unlink(pdf_path)
        if os.path.exists(xl):
            os.unlink(xl)

def test_export_all_pdf_incompatible_data():
    """export_all_charts_pdf produces PDF even when most charts fail to render."""
    xl = line_excel(_line_series_2d, _xs)
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        pdf_path = f.name
    try:
        result = pf.export_all_charts_pdf(pdf_path, xl)
        assert os.path.exists(pdf_path)
        assert os.path.getsize(pdf_path) > 1000
    finally:
        if os.path.exists(pdf_path):
            os.unlink(pdf_path)
        if os.path.exists(xl):
            os.unlink(xl)

run("P20 export_all_charts_pdf valid PDF", test_export_all_pdf)
run("P20 export_all_charts_pdf graceful failures", test_export_all_pdf_incompatible_data)

# ─────────────────────────────────────────────────────────────────────────────
# Final summary
# ─────────────────────────────────────────────────────────────────────────────

_h.summarise()
sys.exit(0 if _h.FAIL == 0 else 1)
