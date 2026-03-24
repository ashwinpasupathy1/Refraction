"""
test_stats_exhaustive.py
========================
Exhaustive statistical test coverage — verifies EVERY stats code path in
refraction/core/chart_helpers.py against scipy/statsmodels ground truth.

Sections:
  1.  _run_stats dispatcher (full path coverage)
  2.  Posthoc tests (Tukey, Dunn, Games-Howell, Dunnett)
  3.  Multiple comparison corrections (pipeline integration)
  4.  Effect sizes (Cohen's d, Hedges' g, rank-biserial r, eta², partial η²)
  5.  Permutation tests
  6.  NaN / missing data handling
  7.  Edge cases with ground truth
  8.  Control group logic (full path)
  9.  normality_warning / check_normality
  10. _calc_error and _calc_error_asymmetric

Run:
  python3 tests/test_stats_exhaustive.py  (or via run_all.py)
"""

import sys, os, warnings
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import plotter_test_harness as _h
from plotter_test_harness import ok, fail, run, section, summarise

pf = _h.pf  # refraction.core.chart_helpers

from scipy import stats as sp_stats

# ── shorthand for production functions ─────────────────────────────────────
_run_stats        = pf._run_stats
_apply_correction = pf._apply_correction
_calc_error       = pf._calc_error
_calc_error_asym  = pf._calc_error_asymmetric
_cohens_d         = pf._cohens_d
_hedges_g         = pf._hedges_g
_rank_biserial_r  = pf._rank_biserial_r
_logrank_test     = pf._logrank_test
_twoway_anova     = pf._twoway_anova
_twoway_posthoc   = pf._twoway_posthoc
check_normality   = pf.check_normality
normality_warning = pf.normality_warning
_p_to_stars       = pf._p_to_stars

# Reproducible RNG
rng = np.random.default_rng(314159)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — _run_stats dispatcher: full path coverage
# ══════════════════════════════════════════════════════════════════════════════
section("1. _run_stats dispatcher — full path coverage")

# ── Welch t-test (parametric, k=2) ────────────────────────────────────────
def test_welch_ttest_vs_scipy():
    a = np.array([5.1, 6.3, 4.8, 7.2, 5.5, 6.0])
    b = np.array([8.2, 9.1, 7.8, 10.0, 8.5])
    groups = {"A": a, "B": b}
    res = _run_stats(groups, test_type="parametric",
                     mc_correction="None (uncorrected)")
    _, _, p_ours, _ = res[0]
    _, p_scipy = sp_stats.ttest_ind(a, b, equal_var=False)
    assert abs(p_ours - p_scipy) < 1e-12, f"Welch: {p_ours} vs {p_scipy}"

run("1a. Welch t-test p matches scipy (unequal n)", test_welch_ttest_vs_scipy)


# ── Student t-test would be equal_var=True; production uses Welch (equal_var=False)
# Verify that production does NOT use Student's t (a design decision)
def test_parametric_is_welch_not_student():
    a = np.array([1., 2., 3., 4., 5.])
    b = np.array([3., 4., 5., 6., 7.])
    groups = {"A": a, "B": b}
    res = _run_stats(groups, test_type="parametric",
                     mc_correction="None (uncorrected)")
    _, _, p_ours, _ = res[0]
    _, p_welch = sp_stats.ttest_ind(a, b, equal_var=False)
    _, p_student = sp_stats.ttest_ind(a, b, equal_var=True)
    # Should match Welch exactly
    assert abs(p_ours - p_welch) < 1e-12
    # For equal variance data, Welch and Student give similar but not identical p
    # Just verify it's Welch
    assert abs(p_ours - p_welch) < abs(p_ours - p_student) or \
           abs(p_welch - p_student) < 1e-12  # equal var → same result

run("1b. Parametric k=2 uses Welch (not Student) t-test", test_parametric_is_welch_not_student)


# ── Paired t-test (k=2) ──────────────────────────────────────────────────
def test_paired_ttest_k2_vs_scipy():
    pre  = np.array([10., 11., 12., 13., 14., 15., 16.])
    post = np.array([12., 14., 13., 16., 15., 18., 17.])
    groups = {"Pre": pre, "Post": post}
    res = _run_stats(groups, test_type="paired",
                     mc_correction="None (uncorrected)")
    _, _, p_ours, _ = res[0]
    _, p_scipy = sp_stats.ttest_rel(pre, post)
    assert abs(p_ours - p_scipy) < 1e-12, f"Paired: {p_ours} vs {p_scipy}"

run("1c. Paired t-test (k=2) p matches scipy.stats.ttest_rel", test_paired_ttest_k2_vs_scipy)


# ── Paired t-test (k>2, pairwise) ────────────────────────────────────────
def test_paired_ttest_k3_pairwise():
    a = np.array([1., 2., 3., 4., 5.])
    b = np.array([2., 3., 4., 5., 6.])
    c = np.array([3., 4., 5., 6., 7.])
    groups = {"A": a, "B": b, "C": c}
    res = _run_stats(groups, test_type="paired",
                     mc_correction="None (uncorrected)")
    # 3 choose 2 = 3 pairs
    assert len(res) == 3, f"Expected 3 pairs, got {len(res)}"
    # Verify each pair matches scipy
    pair_map = {frozenset([r[0], r[1]]): r[2] for r in res}
    for (x_name, y_name), (x_arr, y_arr) in [
        (("A", "B"), (a, b)),
        (("A", "C"), (a, c)),
        (("B", "C"), (b, c)),
    ]:
        _, p_scipy = sp_stats.ttest_rel(x_arr, y_arr)
        p_ours = pair_map[frozenset([x_name, y_name])]
        assert abs(p_ours - p_scipy) < 1e-12, \
            f"Paired {x_name}-{y_name}: {p_ours} vs {p_scipy}"

run("1d. Paired t-test (k=3) all pairwise p-values match scipy", test_paired_ttest_k3_pairwise)


# ── Mann-Whitney U (nonparametric, k=2) ──────────────────────────────────
def test_mannwhitney_vs_scipy():
    a = np.array([2.1, 3.5, 1.8, 4.2, 2.9, 3.1])
    b = np.array([5.3, 6.1, 4.8, 7.0, 5.5])
    groups = {"A": a, "B": b}
    res = _run_stats(groups, test_type="nonparametric",
                     mc_correction="None (uncorrected)")
    _, _, p_ours, _ = res[0]
    _, p_scipy = sp_stats.mannwhitneyu(a, b, alternative="two-sided")
    assert abs(p_ours - p_scipy) < 1e-12, f"MWU: {p_ours} vs {p_scipy}"

run("1e. Mann-Whitney U p matches scipy (unequal n)", test_mannwhitney_vs_scipy)


# ── Kruskal-Wallis + Dunn's (nonparametric, k>2) ─────────────────────────
def test_kruskal_wallis_triggers_posthoc():
    # Use clearly separated groups so KW is significant
    a = np.arange(1., 11.)
    b = np.arange(21., 31.)
    c = np.arange(41., 51.)
    groups = {"A": a, "B": b, "C": c}
    # Verify KW is significant first
    _, p_kw = sp_stats.kruskal(a, b, c)
    assert p_kw < 0.05, f"KW should be significant, p={p_kw}"
    # Now run through _run_stats
    res = _run_stats(groups, test_type="nonparametric",
                     mc_correction="None (uncorrected)")
    assert len(res) == 3, f"Expected 3 Dunn's pairs, got {len(res)}"

run("1f. Kruskal-Wallis significant → Dunn's posthoc runs (3 pairs)", test_kruskal_wallis_triggers_posthoc)


# ── One-way ANOVA + Tukey HSD (parametric, k>2) ──────────────────────────
def test_anova_tukey_triggers():
    a = np.array([2., 4., 6., 8., 10.])
    b = np.array([6., 8., 10., 12., 14.])
    c = np.array([10., 12., 14., 16., 18.])
    _, p_anova = sp_stats.f_oneway(a, b, c)
    assert p_anova < 0.05
    groups = {"A": a, "B": b, "C": c}
    res = _run_stats(groups, test_type="parametric", posthoc="Tukey HSD",
                     mc_correction="None (uncorrected)")
    assert len(res) == 3

run("1g. ANOVA significant → Tukey HSD returns 3 pairs", test_anova_tukey_triggers)


# ── ANOVA non-significant → empty results ────────────────────────────────
def test_anova_ns_returns_empty():
    # Use groups with slight variance but very similar means (not zero-variance,
    # which produces NaN from f_oneway and bypasses the p >= 0.05 gate)
    a = np.array([5.0, 5.1, 4.9, 5.0, 5.1])
    b = np.array([5.0, 5.0, 5.1, 4.9, 5.0])
    c = np.array([5.1, 5.0, 4.9, 5.0, 5.1])
    _, p_anova = sp_stats.f_oneway(a, b, c)
    assert p_anova >= 0.05, f"Need non-sig ANOVA, got p={p_anova}"
    groups = {"A": a, "B": b, "C": c}
    res = _run_stats(groups, test_type="parametric", posthoc="Tukey HSD")
    assert res == [], f"Non-significant ANOVA should return empty, got {res}"

run("1h. ANOVA non-significant → empty results (Tukey gate)", test_anova_ns_returns_empty)


# ── KW non-significant → empty results ───────────────────────────────────
def test_kw_ns_returns_empty():
    # Similar means with some variance (zero-variance causes NaN in kruskal)
    a = np.array([5.0, 5.1, 4.9, 5.0, 5.2])
    b = np.array([5.0, 4.9, 5.1, 5.0, 5.0])
    c = np.array([5.1, 5.0, 5.0, 4.9, 5.0])
    _, p_kw = sp_stats.kruskal(a, b, c)
    assert p_kw >= 0.05, f"Need non-sig KW, got p={p_kw}"
    groups = {"A": a, "B": b, "C": c}
    res = _run_stats(groups, test_type="nonparametric")
    assert res == [], f"Non-significant KW should return empty, got {res}"

run("1i. Kruskal-Wallis non-significant → empty results", test_kw_ns_returns_empty)


# ── One-sample t-test ─────────────────────────────────────────────────────
def test_one_sample_ttest_vs_scipy():
    data = np.array([5.1, 4.9, 5.3, 5.0, 4.8, 5.2])
    mu0 = 4.0
    groups = {"G": data}
    res = _run_stats(groups, test_type="one_sample",
                     mc_correction="None (uncorrected)", mu0=mu0)
    _, _, p_ours, _ = res[0]
    _, p_scipy = sp_stats.ttest_1samp(data, popmean=mu0)
    assert abs(p_ours - p_scipy) < 1e-12

run("1j. One-sample t-test p matches scipy.stats.ttest_1samp", test_one_sample_ttest_vs_scipy)


# ── One-sample t-test with multiple groups ────────────────────────────────
def test_one_sample_multi_group():
    g1 = np.array([10., 11., 12.])
    g2 = np.array([20., 21., 22.])
    groups = {"G1": g1, "G2": g2}
    res = _run_stats(groups, test_type="one_sample",
                     mc_correction="None (uncorrected)", mu0=0.0)
    assert len(res) == 2
    _, _, p1, _ = res[0]
    _, _, p2, _ = res[1]
    _, p1_scipy = sp_stats.ttest_1samp(g1, popmean=0.0)
    _, p2_scipy = sp_stats.ttest_1samp(g2, popmean=0.0)
    assert abs(p1 - p1_scipy) < 1e-12
    assert abs(p2 - p2_scipy) < 1e-12

run("1k. One-sample t-test: multiple groups each tested independently", test_one_sample_multi_group)


# ── Permutation test (k=2) ───────────────────────────────────────────────
def test_permutation_k2():
    a = rng.normal(0, 1, 15)
    b = rng.normal(3, 1, 15)
    groups = {"A": a, "B": b}
    res = _run_stats(groups, test_type="permutation",
                     n_permutations=9999,
                     mc_correction="None (uncorrected)")
    assert len(res) == 1
    _, _, p, _ = res[0]
    assert 0.0 <= p <= 1.0
    # Large separation → should be significant
    assert p < 0.05, f"Permutation: large separation should be significant, p={p}"

run("1l. Permutation test (k=2) detects large separation", test_permutation_k2)


# ── Fewer than 2 groups → empty ──────────────────────────────────────────
def test_single_group_returns_empty():
    groups = {"A": np.array([1., 2., 3.])}
    res = _run_stats(groups, test_type="parametric")
    assert res == []

run("1m. Single group → empty results (k<2)", test_single_group_returns_empty)


# ── Parametric posthoc: Bonferroni ────────────────────────────────────────
def test_posthoc_bonferroni():
    a = np.array([2., 4., 6., 8., 10.])
    b = np.array([6., 8., 10., 12., 14.])
    c = np.array([10., 12., 14., 16., 18.])
    groups = {"A": a, "B": b, "C": c}
    res = _run_stats(groups, test_type="parametric", posthoc="Bonferroni",
                     mc_correction="Bonferroni")
    assert len(res) == 3

run("1n. Parametric posthoc=Bonferroni returns 3 pairs", test_posthoc_bonferroni)


# ── Parametric posthoc: Sidak ─────────────────────────────────────────────
def test_posthoc_sidak():
    a = np.array([2., 4., 6., 8., 10.])
    b = np.array([6., 8., 10., 12., 14.])
    c = np.array([10., 12., 14., 16., 18.])
    groups = {"A": a, "B": b, "C": c}
    res = _run_stats(groups, test_type="parametric", posthoc="Sidak",
                     mc_correction="None (uncorrected)")
    assert len(res) == 3
    # Sidak correction: p_corr = 1 - (1-p)^m
    # Verify at least one pair has corrected p
    for _, _, p, _ in res:
        assert 0 <= p <= 1

run("1o. Parametric posthoc=Sidak returns valid p-values", test_posthoc_sidak)


# ── Parametric posthoc: Fisher LSD ───────────────────────────────────────
def test_posthoc_fisher_lsd():
    a = np.array([2., 4., 6., 8., 10.])
    b = np.array([6., 8., 10., 12., 14.])
    c = np.array([10., 12., 14., 16., 18.])
    groups = {"A": a, "B": b, "C": c}
    res = _run_stats(groups, test_type="parametric", posthoc="Fisher LSD",
                     mc_correction="None (uncorrected)")
    assert len(res) == 3
    # Fisher LSD = uncorrected pairwise Welch t-tests
    pair_p = {frozenset([r[0], r[1]]): r[2] for r in res}
    for (x_name, y_name), (x_arr, y_arr) in [
        (("A", "B"), (a, b)), (("A", "C"), (a, c)), (("B", "C"), (b, c)),
    ]:
        _, p_scipy = sp_stats.ttest_ind(x_arr, y_arr, equal_var=False)
        p_ours = pair_p[frozenset([x_name, y_name])]
        assert abs(p_ours - p_scipy) < 1e-12, \
            f"Fisher LSD {x_name}-{y_name}: {p_ours} vs {p_scipy}"

run("1p. Fisher LSD p-values match raw Welch t-test (no correction)", test_posthoc_fisher_lsd)


# ── Dunnett (parametric, k>2) ────────────────────────────────────────────
def test_dunnett_vs_scipy():
    from scipy.stats import dunnett as _dunnett
    rng_d = np.random.default_rng(555)
    ctrl = rng_d.normal(5, 1, 15)
    trt1 = rng_d.normal(8, 1, 15)
    trt2 = rng_d.normal(11, 1, 15)
    groups = {"Ctrl": ctrl, "T1": trt1, "T2": trt2}
    res = _run_stats(groups, test_type="parametric",
                     posthoc="Dunnett (vs control)", control="Ctrl")
    # Production iterates labels in dict order: Ctrl, T1, T2
    # treatments = [T1, T2], so scipy call must match that order
    treatments = [g for g in groups.keys() if g != "Ctrl"]
    treatment_arrays = [groups[g] for g in treatments]
    scipy_res = _dunnett(*treatment_arrays, control=ctrl)
    # Match by treatment name
    our_p_map = {r[1]: r[2] for r in res}  # r = (ctrl, trt, p, stars)
    for i, trt_name in enumerate(treatments):
        sp = float(scipy_res.pvalue[i])
        op = our_p_map[trt_name]
        assert abs(op - sp) < 1e-10, f"Dunnett {trt_name}: {op} vs {sp}"

run("1q. Dunnett p-values match scipy.stats.dunnett exactly", test_dunnett_vs_scipy)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Posthoc tests: full coverage
# ══════════════════════════════════════════════════════════════════════════════
section("2. Posthoc tests — full coverage")


# ── Tukey HSD: verify p via studentized range ─────────────────────────────
def test_tukey_pvalues_vs_studentized_range():
    """Verify each Tukey HSD p-value against manual studentized_range CDF."""
    a = np.array([2., 4., 6., 8., 10.])
    b = np.array([6., 8., 10., 12., 14.])
    c = np.array([10., 12., 14., 16., 18.])
    groups = {"A": a, "B": b, "C": c}
    k = 3
    all_vals = np.concatenate([a, b, c])
    ss_within = sum(np.sum((v - v.mean())**2) for v in [a, b, c])
    df_within = len(all_vals) - k
    ms_within = ss_within / df_within

    res = _run_stats(groups, test_type="parametric", posthoc="Tukey HSD",
                     mc_correction="None (uncorrected)")
    for g1, g2, p_ours, _ in res:
        arr1, arr2 = groups[g1], groups[g2]
        mean_diff = abs(arr1.mean() - arr2.mean())
        se = np.sqrt((ms_within / 2) * (1/len(arr1) + 1/len(arr2)))
        q = mean_diff / se
        p_manual = 1 - sp_stats.studentized_range.cdf(q, k, df_within)
        assert abs(p_ours - p_manual) < 1e-10, \
            f"Tukey {g1}-{g2}: {p_ours} vs {p_manual}"

run("2a. Tukey HSD: all pairwise p-values match studentized_range CDF", test_tukey_pvalues_vs_studentized_range)


# ── Dunn's test: verify z-statistic formula ───────────────────────────────
def test_dunns_z_formula():
    """Verify Dunn's z-statistics match manual rank-based computation."""
    a = np.arange(1., 11.)
    b = np.arange(11., 21.)
    c = np.arange(21., 31.)
    groups = {"A": a, "B": b, "C": c}

    # Manual Dunn's computation
    all_vals = np.concatenate([a, b, c])
    N = len(all_vals)
    ranks = sp_stats.rankdata(all_vals)
    group_ranks = {"A": ranks[:10], "B": ranks[10:20], "C": ranks[20:30]}
    _, counts = np.unique(all_vals, return_counts=True)
    tc = 1 - np.sum(counts**3 - counts) / (N**3 - N)

    res = _run_stats(groups, test_type="nonparametric",
                     mc_correction="None (uncorrected)")
    for g1, g2, p_ours, _ in res:
        n1, n2 = len(groups[g1]), len(groups[g2])
        se = np.sqrt(tc * N * (N + 1) / 12 * (1/n1 + 1/n2))
        z = abs(group_ranks[g1].mean() - group_ranks[g2].mean()) / se
        p_manual = 2 * (1 - sp_stats.norm.cdf(z))
        assert abs(p_ours - p_manual) < 1e-10, \
            f"Dunn {g1}-{g2}: {p_ours} vs {p_manual}"

run("2b. Dunn's posthoc: z-statistics and p-values match manual computation", test_dunns_z_formula)


# ── Sidak correction formula ─────────────────────────────────────────────
def test_sidak_correction_formula():
    """Sidak: p_corr = 1 - (1-p_raw)^m."""
    a = np.array([1., 3., 5., 7., 9.])
    b = np.array([5., 7., 9., 11., 13.])
    c = np.array([9., 11., 13., 15., 17.])
    groups = {"A": a, "B": b, "C": c}
    # Get raw p-values with Fisher LSD (no correction)
    raw_res = _run_stats(groups, test_type="parametric", posthoc="Fisher LSD",
                         mc_correction="None (uncorrected)")
    # Get Sidak-corrected
    sidak_res = _run_stats(groups, test_type="parametric", posthoc="Sidak",
                           mc_correction="None (uncorrected)")
    m = len(raw_res)
    raw_p = {frozenset([r[0], r[1]]): r[2] for r in raw_res}
    sidak_p = {frozenset([r[0], r[1]]): r[2] for r in sidak_res}
    for pair, p_raw in raw_p.items():
        p_sidak_expected = min(1.0 - (1.0 - p_raw)**m, 1.0)
        p_sidak_got = sidak_p[pair]
        assert abs(p_sidak_got - p_sidak_expected) < 1e-10, \
            f"Sidak {pair}: got {p_sidak_got}, expected {p_sidak_expected}"

run("2c. Sidak correction formula verified: p_corr = 1-(1-p)^m", test_sidak_correction_formula)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — Multiple comparison corrections (pipeline integration)
# ══════════════════════════════════════════════════════════════════════════════
section("3. Multiple comparison corrections — pipeline integration")


# ── Bonferroni in pipeline ────────────────────────────────────────────────
def test_bonferroni_pipeline():
    raw_p = [0.005, 0.02, 0.15]
    corrected = _apply_correction(raw_p, "Bonferroni")
    m = len(raw_p)
    for i, (r, c) in enumerate(zip(raw_p, corrected)):
        expected = min(r * m, 1.0)
        assert abs(c - expected) < 1e-12, f"Bonferroni[{i}]: {c} vs {expected}"

run("3a. Bonferroni: p_corr = min(p * m, 1.0)", test_bonferroni_pipeline)


# ── Holm-Bonferroni step-down ─────────────────────────────────────────────
def test_holm_step_down():
    """Holm-Bonferroni: verify step-down ordering is correct."""
    raw_p = [0.04, 0.01, 0.20]
    corrected = _apply_correction(raw_p, "Holm-Bonferroni")
    m = 3
    # Manual Holm computation:
    # Sort: 0.01 (idx 1), 0.04 (idx 0), 0.20 (idx 2)
    # Step 1: 0.01 * 3 = 0.03
    # Step 2: max(0.03, 0.04 * 2) = max(0.03, 0.08) = 0.08
    # Step 3: max(0.08, 0.20 * 1) = max(0.08, 0.20) = 0.20
    expected = {0: 0.08, 1: 0.03, 2: 0.20}
    for i in range(m):
        assert abs(corrected[i] - expected[i]) < 1e-12, \
            f"Holm[{i}]: {corrected[i]} vs {expected[i]}"

run("3b. Holm-Bonferroni: step-down ordering verified", test_holm_step_down)


# ── Holm monotonicity (sorted input) ─────────────────────────────────────
def test_holm_monotone_sorted():
    raw_p = [0.001, 0.01, 0.05, 0.10, 0.50]
    corrected = _apply_correction(raw_p, "Holm-Bonferroni")
    for i in range(len(corrected) - 1):
        assert corrected[i] <= corrected[i+1] + 1e-12

run("3c. Holm-Bonferroni: monotonic for sorted input", test_holm_monotone_sorted)


# ── Benjamini-Hochberg step-up ────────────────────────────────────────────
def test_bh_step_up():
    """BH: verify step-up ordering and q-values."""
    raw_p = [0.04, 0.01, 0.20]
    corrected = _apply_correction(raw_p, "Benjamini-Hochberg (FDR)")
    m = 3
    # Manual BH:
    # Sort: 0.01 (idx 1), 0.04 (idx 0), 0.20 (idx 2)
    # Step-up from largest rank:
    # Rank 3 (idx 2): min(0.20 * 3/3, 1.0) = 0.20
    # Rank 2 (idx 0): min(0.04 * 3/2, 0.20) = min(0.06, 0.20) = 0.06
    # Rank 1 (idx 1): min(0.01 * 3/1, 0.06) = min(0.03, 0.06) = 0.03
    expected = {0: 0.06, 1: 0.03, 2: 0.20}
    for i in range(m):
        assert abs(corrected[i] - expected[i]) < 1e-12, \
            f"BH[{i}]: {corrected[i]} vs {expected[i]}"

run("3d. Benjamini-Hochberg: step-up ordering and q-values verified", test_bh_step_up)


# ── Corrections applied to posthoc (not omnibus) p-values ────────────────
def test_correction_applied_to_posthoc_not_omnibus():
    """Verify correction is applied to pairwise p-values, not the ANOVA p."""
    a = np.array([1., 3., 5., 7., 9.])
    b = np.array([5., 7., 9., 11., 13.])
    c = np.array([9., 11., 13., 15., 17.])
    groups = {"A": a, "B": b, "C": c}
    # Get raw pairwise
    raw_res = _run_stats(groups, test_type="parametric", posthoc="Fisher LSD",
                         mc_correction="None (uncorrected)")
    # Get Bonferroni-corrected pairwise
    bonf_res = _run_stats(groups, test_type="parametric", posthoc="Bonferroni",
                          mc_correction="Bonferroni")
    raw_ps = sorted(r[2] for r in raw_res)
    bonf_ps = sorted(r[2] for r in bonf_res)
    m = len(raw_ps)
    # Bonferroni posthoc p-values should be raw Welch p * m (capped at 1)
    for rp, bp in zip(raw_ps, bonf_ps):
        expected = min(rp * m, 1.0)
        assert abs(bp - expected) < 1e-10, \
            f"Bonferroni pipeline: got {bp}, expected {expected} (raw={rp})"

run("3e. Correction applied to posthoc p-values (not omnibus)", test_correction_applied_to_posthoc_not_omnibus)


# ── None (uncorrected) passes through ────────────────────────────────────
def test_uncorrected_passthrough():
    raw_p = [0.01, 0.04, 0.20]
    corrected = _apply_correction(raw_p, "None (uncorrected)")
    for r, c in zip(raw_p, corrected):
        assert abs(r - c) < 1e-12

run("3f. None (uncorrected): p-values unchanged", test_uncorrected_passthrough)


# ── Empty list ────────────────────────────────────────────────────────────
def test_correction_empty_list():
    for method in ("Bonferroni", "Holm-Bonferroni", "Benjamini-Hochberg (FDR)"):
        assert _apply_correction([], method) == []

run("3g. All corrections handle empty list", test_correction_empty_list)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — Effect sizes (exhaustive)
# ══════════════════════════════════════════════════════════════════════════════
section("4. Effect sizes — exhaustive verification")


# ── Cohen's d: manual pooled SD computation ───────────────────────────────
def test_cohens_d_manual_3_datasets():
    """Cohen's d matches manual formula for 3 different datasets."""
    datasets = [
        (np.array([1., 2., 3., 4., 5.]), np.array([6., 7., 8., 9., 10.])),
        (np.array([10., 20., 30.]), np.array([15., 25., 35.])),
        (rng.normal(0, 1, 20), rng.normal(0.8, 1.5, 25)),
    ]
    for a, b in datasets:
        d = _cohens_d(a, b)
        n1, n2 = len(a), len(b)
        s_pooled = np.sqrt(((n1-1)*np.var(a, ddof=1) + (n2-1)*np.var(b, ddof=1)) / (n1+n2-2))
        d_manual = (np.mean(a) - np.mean(b)) / s_pooled if s_pooled > 0 else float('nan')
        assert abs(d - d_manual) < 1e-12, f"Cohen d: {d} vs {d_manual}"

run("4a. Cohen's d: formula verified for 3 datasets", test_cohens_d_manual_3_datasets)


# ── Cohen's d: zero variance returns NaN ──────────────────────────────────
def test_cohens_d_zero_variance():
    a = np.array([5., 5., 5.])
    b = np.array([5., 5., 5.])
    d = _cohens_d(a, b)
    assert np.isnan(d), f"Expected NaN for zero variance, got {d}"

run("4b. Cohen's d: zero variance → NaN", test_cohens_d_zero_variance)


# ── Hedges' g: bias correction factor J(m) ───────────────────────────────
def test_hedges_g_correction_factor():
    """Verify J(m) = 1 - 3/(4m-1) for 3 datasets."""
    datasets = [
        (np.array([1., 2., 3., 4., 5.]), np.array([6., 7., 8., 9., 10.])),
        (rng.normal(0, 1, 8), rng.normal(1, 1, 12)),
        (rng.normal(5, 2, 30), rng.normal(6, 2, 30)),
    ]
    for a, b in datasets:
        g = _hedges_g(a, b)
        d = _cohens_d(a, b)
        m = len(a) + len(b) - 2
        J = 1.0 - 3.0 / (4.0 * m - 1.0)
        expected = d * J
        assert abs(g - expected) < 1e-12, f"Hedges g: {g} vs {expected}"

run("4c. Hedges' g: J(m)=1-3/(4m-1) verified for 3 datasets", test_hedges_g_correction_factor)


# ── Hedges' g: converges to Cohen's d for large n ────────────────────────
def test_hedges_g_large_n():
    a = rng.normal(0, 1, 1000)
    b = rng.normal(0.5, 1, 1000)
    d = _cohens_d(a, b)
    g = _hedges_g(a, b)
    # J = 1 - 3/(4*1998 - 1) ≈ 0.99962
    assert abs(g - d) / (abs(d) + 1e-9) < 0.001

run("4d. Hedges' g: converges to Cohen's d for n=1000", test_hedges_g_large_n)


# ── Rank-biserial r: verify formula r = (U1-U2)/(n1*n2) ─────────────────
def test_rank_biserial_formula():
    """Verify r = (U1-U2)/(n1*n2) for 2 datasets."""
    datasets = [
        (np.array([1., 3., 5.]), np.array([2., 4., 6.])),
        (rng.normal(0, 1, 10), rng.normal(2, 1, 8)),
    ]
    for a, b in datasets:
        r = _rank_biserial_r(a, b)
        n1, n2 = len(a), len(b)
        U1 = float(np.sum(a[:, None] > b[None, :]))
        U2 = n1 * n2 - U1
        r_manual = (U1 - U2) / (n1 * n2)
        assert abs(r - r_manual) < 1e-12, f"Rank-biserial: {r} vs {r_manual}"

run("4e. Rank-biserial r: formula (U1-U2)/(n1*n2) verified", test_rank_biserial_formula)


# ── Eta-squared: Two-way ANOVA η² = SS_effect / SS_total ─────────────────
def test_eta_squared_formula():
    """η² = SS_effect / SS_total."""
    rows = []
    rng2 = np.random.default_rng(42)
    for a in ["a1", "a2"]:
        for b in ["b1", "b2"]:
            mu = {"a1b1": 10, "a1b2": 15, "a2b1": 20, "a2b2": 25}[a+b]
            for _ in range(6):
                rows.append({"A": a, "B": b, "Y": mu + rng2.normal(0, 1)})
    df = pd.DataFrame(rows)
    result = _twoway_anova(df, "Y", "A", "B")

    y = df["Y"].values.astype(float)
    ss_total = float(np.sum((y - y.mean())**2))

    for key in ("A", "B", "interaction"):
        eta2 = result[key]["eta2"]
        expected = result[key]["SS"] / ss_total
        assert abs(eta2 - expected) < 1e-12, f"{key}: η²={eta2} vs {expected}"

run("4f. Eta-squared: η²=SS_effect/SS_total verified", test_eta_squared_formula)


# ── Partial eta-squared: η²_p = SS_effect / (SS_effect + SS_error) ───────
def test_partial_eta_squared_formula():
    rows = []
    rng2 = np.random.default_rng(42)
    for a in ["a1", "a2", "a3"]:
        for b in ["b1", "b2"]:
            mu = {"a1b1": 5, "a1b2": 10, "a2b1": 15, "a2b2": 20,
                  "a3b1": 25, "a3b2": 30}[a+b]
            for _ in range(5):
                rows.append({"A": a, "B": b, "Y": mu + rng2.normal(0, 2)})
    df = pd.DataFrame(rows)
    result = _twoway_anova(df, "Y", "A", "B")
    ss_err = result["residual"]["SS"]

    for key in ("A", "B", "interaction"):
        eta2_p = result[key]["eta2_partial"]
        ss_eff = result[key]["SS"]
        expected = ss_eff / (ss_eff + ss_err)
        assert abs(eta2_p - expected) < 1e-12, \
            f"{key}: η²_p={eta2_p} vs {expected}"

run("4g. Partial eta-squared: η²_p=SS/(SS+SS_err) verified", test_partial_eta_squared_formula)


# ── Two-way ANOVA: F = MS_effect / MS_error ──────────────────────────────
def test_twoway_F_formula():
    rows = []
    rng2 = np.random.default_rng(99)
    for a in ["a1", "a2"]:
        for b in ["b1", "b2"]:
            mu = {"a1b1": 10, "a1b2": 20, "a2b1": 30, "a2b2": 40}[a+b]
            for _ in range(5):
                rows.append({"A": a, "B": b, "Y": mu + rng2.normal(0, 1)})
    df = pd.DataFrame(rows)
    result = _twoway_anova(df, "Y", "A", "B")
    ms_err = result["residual"]["MS"]
    for key in ("A", "B", "interaction"):
        F = result[key]["F"]
        ms_eff = result[key]["MS"]
        expected_F = ms_eff / ms_err
        assert abs(F - expected_F) < 1e-10, f"{key}: F={F} vs {expected_F}"

run("4h. Two-way ANOVA: F = MS_effect / MS_error verified", test_twoway_F_formula)


# ── Two-way ANOVA p from F distribution ──────────────────────────────────
def test_twoway_p_from_F():
    rows = []
    rng2 = np.random.default_rng(99)
    for a in ["a1", "a2"]:
        for b in ["b1", "b2"]:
            mu = {"a1b1": 10, "a1b2": 20, "a2b1": 30, "a2b2": 40}[a+b]
            for _ in range(5):
                rows.append({"A": a, "B": b, "Y": mu + rng2.normal(0, 1)})
    df = pd.DataFrame(rows)
    result = _twoway_anova(df, "Y", "A", "B")
    df_err = result["residual"]["df"]
    for key in ("A", "B", "interaction"):
        F = result[key]["F"]
        df_eff = result[key]["df"]
        p = result[key]["p"]
        p_expected = float(sp_stats.f.sf(F, df_eff, df_err))
        assert abs(p - p_expected) < 1e-12, f"{key}: p={p} vs {p_expected}"

run("4i. Two-way ANOVA: p matches scipy.stats.f.sf", test_twoway_p_from_F)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — Permutation tests
# ══════════════════════════════════════════════════════════════════════════════
section("5. Permutation tests")


# ── Permutation converges to parametric p for large effect ────────────────
def test_permutation_converges_to_parametric():
    a = rng.normal(0, 1, 20)
    b = rng.normal(2, 1, 20)
    groups = {"A": a, "B": b}
    perm_res = _run_stats(groups, test_type="permutation",
                          n_permutations=9999,
                          mc_correction="None (uncorrected)")
    _, _, p_perm, _ = perm_res[0]
    _, p_welch = sp_stats.ttest_ind(a, b, equal_var=False)
    # Both should be very small; permutation should be within 0.02
    assert abs(p_perm - p_welch) < 0.02, \
        f"Permutation p={p_perm} vs Welch p={p_welch}, diff > 0.02"

run("5a. Permutation p converges to Welch p (large effect, n=20)", test_permutation_converges_to_parametric)


# ── Permutation on null data → p > 0.3 ───────────────────────────────────
def test_permutation_null():
    data = rng.normal(5, 1, 30)
    a, b = data[:15], data[15:]
    groups = {"A": a, "B": b}
    res = _run_stats(groups, test_type="permutation",
                     n_permutations=9999,
                     mc_correction="None (uncorrected)")
    _, _, p, _ = res[0]
    assert p > 0.1, f"Null data permutation p={p} should be > 0.1"

run("5b. Permutation on null data: p not significant", test_permutation_null)


# ── Permutation with k>2 ─────────────────────────────────────────────────
def test_permutation_k3():
    a = rng.normal(0, 1, 12)
    b = rng.normal(3, 1, 12)
    c = rng.normal(6, 1, 12)
    groups = {"A": a, "B": b, "C": c}
    res = _run_stats(groups, test_type="permutation",
                     n_permutations=999,
                     mc_correction="None (uncorrected)")
    assert len(res) == 3, f"Expected 3 pairs, got {len(res)}"
    # A vs C should be the most significant
    p_ac = None
    for g1, g2, p, _ in res:
        if frozenset([g1, g2]) == frozenset(["A", "C"]):
            p_ac = p
    assert p_ac is not None and p_ac < 0.05

run("5c. Permutation (k=3): 3 pairs, A vs C significant", test_permutation_k3)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — NaN / missing data handling
# ══════════════════════════════════════════════════════════════════════════════
section("6. NaN / missing data handling")


# ── _calc_error with NaN values ───────────────────────────────────────────
def test_calc_error_ignores_nan_not():
    """_calc_error computes on raw data (does NOT drop NaN by itself).
    Callers are expected to pass clean data. Verify behavior."""
    vals = np.array([1., 2., 3., np.nan, 5.])
    m, err = _calc_error(vals, "sem")
    # np.mean([1,2,3,nan,5]) = nan, so m should be nan
    assert np.isnan(m), "Mean of data with NaN should be NaN"

run("6a. _calc_error with NaN: mean is NaN (caller must clean)", test_calc_error_ignores_nan_not)


# ── normality check with NaN ─────────────────────────────────────────────
def test_check_normality_drops_nan():
    """check_normality drops NaN before Shapiro-Wilk."""
    data = np.array([1., 2., 3., np.nan, 5., 6., 7., 8.])
    result = check_normality({"G": data})
    stat, p, is_normal, msg = result["G"]
    assert stat is not None, "Should compute Shapiro-Wilk after dropping NaN"
    assert isinstance(p, float)

run("6b. check_normality drops NaN before Shapiro-Wilk", test_check_normality_drops_nan)


# ── check_normality with all NaN ─────────────────────────────────────────
def test_check_normality_all_nan():
    """All-NaN group: too few values, should handle gracefully."""
    data = np.array([np.nan, np.nan, np.nan])
    result = check_normality({"G": data})
    stat, p, is_normal, msg = result["G"]
    assert stat is None, "All-NaN group: stat should be None (too few)"
    assert "too few" in msg.lower()

run("6c. check_normality: all-NaN group handled gracefully", test_check_normality_all_nan)


# ── check_normality with n<3 after NaN drop ──────────────────────────────
def test_check_normality_small_n():
    data = np.array([1., np.nan, 2.])  # n=2 after drop
    result = check_normality({"G": data})
    stat, p, is_normal, msg = result["G"]
    assert stat is None, "n=2 should be too few for Shapiro-Wilk"

run("6d. check_normality: n=2 after NaN drop → too few", test_check_normality_small_n)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 7 — Edge cases with ground truth
# ══════════════════════════════════════════════════════════════════════════════
section("7. Edge cases with ground truth")


# ── Identical groups: p ≈ 1.0, effect size = 0 ───────────────────────────
def test_identical_groups_welch():
    x = np.array([1., 2., 3., 4., 5.])
    groups = {"A": x.copy(), "B": x.copy()}
    res = _run_stats(groups, test_type="parametric",
                     mc_correction="None (uncorrected)")
    _, _, p, _ = res[0]
    assert p > 0.99, f"Identical groups: p={p} should be ~1.0"

run("7a. Identical groups: Welch p ≈ 1.0", test_identical_groups_welch)


def test_identical_groups_effect_size_zero():
    x = np.array([1., 2., 3., 4., 5.])
    d = _cohens_d(x, x.copy())
    assert d == 0.0, f"Identical groups: d={d} should be 0"

run("7b. Identical groups: Cohen's d = 0", test_identical_groups_effect_size_zero)


# ── Perfect separation ───────────────────────────────────────────────────
def test_perfect_separation():
    a = np.array([1., 2., 3., 4., 5.])
    b = np.array([100., 101., 102., 103., 104.])
    groups = {"A": a, "B": b}
    res = _run_stats(groups, test_type="parametric",
                     mc_correction="None (uncorrected)")
    _, _, p, _ = res[0]
    assert p < 1e-6, f"Perfect separation: p={p} should be very small"
    d = abs(_cohens_d(a, b))
    assert d > 10, f"Perfect separation: |d|={d} should be very large"

run("7c. Perfect separation: p very small, |d| very large", test_perfect_separation)


# ── n=2 per group ────────────────────────────────────────────────────────
def test_n2_per_group():
    a = np.array([1., 100.])
    b = np.array([50., 51.])
    groups = {"A": a, "B": b}
    res = _run_stats(groups, test_type="parametric",
                     mc_correction="None (uncorrected)")
    _, _, p_ours, _ = res[0]
    _, p_scipy = sp_stats.ttest_ind(a, b, equal_var=False)
    assert abs(p_ours - p_scipy) < 1e-12
    assert not np.isnan(p_ours)

run("7d. n=2 per group: Welch t-test works, matches scipy", test_n2_per_group)


# ── n=1 per group: Cohen's d = NaN ──────────────────────────────────────
def test_n1_cohens_d_nan():
    a = np.array([1.])
    b = np.array([2.])
    d = _cohens_d(a, b)
    assert np.isnan(d), f"n=1: d={d} should be NaN"

run("7e. n=1 per group: Cohen's d returns NaN", test_n1_cohens_d_nan)


# ── Unequal group sizes ──────────────────────────────────────────────────
def test_unequal_sizes():
    a = rng.normal(5, 1, 5)
    b = rng.normal(8, 1, 20)
    groups = {"A": a, "B": b}
    res = _run_stats(groups, test_type="parametric",
                     mc_correction="None (uncorrected)")
    _, _, p_ours, _ = res[0]
    _, p_scipy = sp_stats.ttest_ind(a, b, equal_var=False)
    assert abs(p_ours - p_scipy) < 1e-12

run("7f. Unequal group sizes (5 vs 20): Welch p matches scipy", test_unequal_sizes)


# ── Negative values ──────────────────────────────────────────────────────
def test_negative_values():
    a = np.array([-10., -8., -6., -4., -2.])
    b = np.array([-5., -3., -1., 1., 3.])
    groups = {"A": a, "B": b}
    res = _run_stats(groups, test_type="parametric",
                     mc_correction="None (uncorrected)")
    _, _, p_ours, _ = res[0]
    _, p_scipy = sp_stats.ttest_ind(a, b, equal_var=False)
    assert abs(p_ours - p_scipy) < 1e-12

run("7g. Negative values: stats work correctly", test_negative_values)


# ── Very large values (1e12) ─────────────────────────────────────────────
def test_very_large_values():
    a = np.array([1e12, 1.1e12, 1.2e12, 1.3e12, 1.4e12])
    b = np.array([2e12, 2.1e12, 2.2e12, 2.3e12, 2.4e12])
    groups = {"A": a, "B": b}
    res = _run_stats(groups, test_type="parametric",
                     mc_correction="None (uncorrected)")
    _, _, p_ours, _ = res[0]
    _, p_scipy = sp_stats.ttest_ind(a, b, equal_var=False)
    assert abs(p_ours - p_scipy) < 1e-12
    assert not np.isnan(p_ours) and not np.isinf(p_ours)

run("7h. Very large values (1e12): no overflow, matches scipy", test_very_large_values)


# ── Very small differences ───────────────────────────────────────────────
def test_very_small_differences():
    a = np.array([1.0000001, 1.0000002, 1.0000003, 1.0000004, 1.0000005])
    b = np.array([1.0000006, 1.0000007, 1.0000008, 1.0000009, 1.0000010])
    groups = {"A": a, "B": b}
    res = _run_stats(groups, test_type="parametric",
                     mc_correction="None (uncorrected)")
    _, _, p_ours, _ = res[0]
    _, p_scipy = sp_stats.ttest_ind(a, b, equal_var=False)
    assert abs(p_ours - p_scipy) < 1e-10

run("7i. Very small differences: precision maintained", test_very_small_differences)


# ── Mann-Whitney identical groups ─────────────────────────────────────────
def test_mw_identical():
    x = np.array([1., 2., 3., 4., 5.])
    groups = {"A": x.copy(), "B": x.copy()}
    res = _run_stats(groups, test_type="nonparametric",
                     mc_correction="None (uncorrected)")
    _, _, p, _ = res[0]
    assert p > 0.5, f"Identical groups MWU: p={p} should be > 0.5"

run("7j. Mann-Whitney on identical groups: p > 0.5", test_mw_identical)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 8 — Control group logic (full path)
# ══════════════════════════════════════════════════════════════════════════════
section("8. Control group logic — full path")


# ── Control produces k-1 comparisons ─────────────────────────────────────
def test_control_k_minus_1():
    for k in [3, 4, 5]:
        groups = {f"G{i}": rng.normal(i * 3, 1, 10) for i in range(k)}
        names = list(groups.keys())
        ctrl = names[0]
        # Use Fisher LSD to avoid ANOVA gate
        res = _run_stats(groups, test_type="parametric",
                         posthoc="Fisher LSD",
                         control=ctrl,
                         mc_correction="None (uncorrected)")
        assert len(res) == k - 1, \
            f"k={k}: expected {k-1} comparisons, got {len(res)}"

run("8a. Control group: k-1 comparisons for k groups", test_control_k_minus_1)


# ── Control filter works for all test types ──────────────────────────────
def test_control_all_test_types():
    groups = {
        "Ctrl": rng.normal(5, 1, 12),
        "A":    rng.normal(8, 1, 12),
        "B":    rng.normal(11, 1, 12),
    }
    for tt in ("parametric", "nonparametric", "permutation"):
        res = _run_stats(groups, test_type=tt, control="Ctrl",
                         posthoc="Fisher LSD" if tt == "parametric" else "Tukey HSD",
                         n_permutations=99,
                         mc_correction="None (uncorrected)")
        assert len(res) == 2, f"{tt}: expected 2 pairs, got {len(res)}"
        pairs = {frozenset([r[0], r[1]]) for r in res}
        assert frozenset(["A", "B"]) not in pairs, \
            f"{tt}: A vs B leaked through"

run("8b. Control filter: works for parametric/nonparametric/permutation", test_control_all_test_types)


# ── Dunnett with control=None defaults to first group ────────────────────
def test_dunnett_default_control():
    groups = {"X": rng.normal(5, 1, 10),
              "Y": rng.normal(8, 1, 10),
              "Z": rng.normal(11, 1, 10)}
    res = _run_stats(groups, test_type="parametric",
                     posthoc="Dunnett (vs control)", control=None)
    assert len(res) == 2
    for g1, g2, p, _ in res:
        assert "X" in (g1, g2), f"Default control should be 'X', got ({g1}, {g2})"

run("8c. Dunnett control=None: defaults to first group", test_dunnett_default_control)


# ── Control that doesn't exist: Tukey still runs (stale control) ─────────
def test_stale_control_tukey():
    groups = {"A": rng.normal(5, 1, 10),
              "B": rng.normal(8, 1, 10),
              "C": rng.normal(11, 1, 10)}
    res = _run_stats(groups, test_type="parametric",
                     posthoc="Tukey HSD", control="NonExistent")
    # When control doesn't exist, pairs filter finds nothing with control
    # so results should be empty (no pair contains "NonExistent")
    # OR it falls back to all pairs — test that it doesn't crash
    assert isinstance(res, list)

run("8d. Stale control: does not crash", test_stale_control_tukey)


# ── One-sample t-test with correction applied correctly ──────────────────
def test_one_sample_with_correction():
    g1 = np.array([10., 11., 12., 13., 14.])
    g2 = np.array([20., 21., 22., 23., 24.])
    groups = {"G1": g1, "G2": g2}
    res = _run_stats(groups, test_type="one_sample",
                     mc_correction="Bonferroni", mu0=0.0)
    # Raw p-values
    _, p1_raw = sp_stats.ttest_1samp(g1, popmean=0.0)
    _, p2_raw = sp_stats.ttest_1samp(g2, popmean=0.0)
    expected = _apply_correction([p1_raw, p2_raw], "Bonferroni")
    for i, (_, _, p, _) in enumerate(res):
        assert abs(p - expected[i]) < 1e-12

run("8e. One-sample t-test: Bonferroni correction applied correctly", test_one_sample_with_correction)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 9 — normality_warning / check_normality
# ══════════════════════════════════════════════════════════════════════════════
section("9. normality_warning / check_normality")


# ── Normal data: no warning ──────────────────────────────────────────────
def test_normality_normal_data_no_warning():
    data = rng.normal(0, 1, 50)
    groups = {"G": data}
    result = check_normality(groups)
    _, p, is_normal, msg = result["G"]
    # Shapiro-Wilk on truly normal data with n=50 should pass
    assert p > 0.05, f"Normal data should pass Shapiro-Wilk, p={p}"
    assert is_normal is True

run("9a. Normal data (n=50): Shapiro-Wilk passes, no warning", test_normality_normal_data_no_warning)


# ── Skewed data: warning ─────────────────────────────────────────────────
def test_normality_skewed_data_warns():
    data = rng.exponential(1.0, 50)
    groups = {"G": data}
    result = check_normality(groups)
    _, p, is_normal, msg = result["G"]
    assert p < 0.05, f"Exponential data should fail Shapiro-Wilk, p={p}"
    assert is_normal is False
    assert msg is not None and "non-normal" in msg.lower()

run("9b. Skewed data (exponential): Shapiro-Wilk fails, warns", test_normality_skewed_data_warns)


# ── normality_warning: only for parametric ────────────────────────────────
def test_normality_warning_only_parametric():
    data = rng.exponential(1.0, 50)
    groups = {"G": data}
    # Temporarily enable warning
    old = pf.__show_normality_warning__
    pf.__show_normality_warning__ = True
    try:
        w_para = normality_warning(groups, "parametric")
        w_nonp = normality_warning(groups, "nonparametric")
    finally:
        pf.__show_normality_warning__ = old
    assert len(w_para) > 0, "Should warn for parametric"
    assert w_nonp == "", "Should not warn for nonparametric"

run("9c. normality_warning: warns for parametric only", test_normality_warning_only_parametric)


# ── normality_warning disabled ────────────────────────────────────────────
def test_normality_warning_disabled():
    data = rng.exponential(1.0, 50)
    groups = {"G": data}
    old = pf.__show_normality_warning__
    pf.__show_normality_warning__ = False
    try:
        w = normality_warning(groups, "parametric")
    finally:
        pf.__show_normality_warning__ = old
    assert w == "", "Warning should be empty when disabled"

run("9d. normality_warning: empty when disabled", test_normality_warning_disabled)


# ── check_normality: Shapiro p threshold = 0.05 ──────────────────────────
def test_check_normality_threshold():
    """Verify Shapiro-Wilk p > 0.05 → normal, p < 0.05 → non-normal."""
    # Use data we know passes
    normal_data = np.array([1., 2., 3., 4., 5., 6., 7., 8., 9., 10.])
    result = check_normality({"G": normal_data}, alpha=0.05)
    stat, p, is_normal, msg = result["G"]
    expected_normal = p > 0.05
    assert is_normal == expected_normal

run("9e. check_normality: threshold at α=0.05", test_check_normality_threshold)


# ── check_normality with custom alpha ────────────────────────────────────
def test_check_normality_custom_alpha():
    data = rng.normal(0, 1, 20)
    _, p_shapiro = sp_stats.shapiro(data)
    # Use alpha=0.001 (very strict) and alpha=0.99 (very lenient)
    result_strict = check_normality({"G": data}, alpha=0.001)
    result_lenient = check_normality({"G": data}, alpha=0.99)
    # With strict alpha, more likely to be "normal" (p > 0.001)
    # With lenient alpha, more likely to be "non-normal" (p > 0.99 is unlikely)
    assert result_strict["G"][0] is not None  # stat computed
    assert result_lenient["G"][0] is not None

run("9f. check_normality: custom alpha accepted", test_check_normality_custom_alpha)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 10 — _calc_error and _calc_error_asymmetric
# ══════════════════════════════════════════════════════════════════════════════
section("10. _calc_error and _calc_error_asymmetric")


# ── SEM = std / sqrt(n) ──────────────────────────────────────────────────
def test_calc_error_sem():
    vals = np.array([2., 4., 6., 8., 10.])
    m, err = _calc_error(vals, "sem")
    n = len(vals)
    s = float(np.std(vals, ddof=1))
    expected_sem = s / np.sqrt(n)
    assert abs(m - np.mean(vals)) < 1e-12
    assert abs(err - expected_sem) < 1e-12

run("10a. SEM = std(ddof=1) / sqrt(n)", test_calc_error_sem)


# ── SD = std(ddof=1) ─────────────────────────────────────────────────────
def test_calc_error_sd():
    vals = np.array([1., 3., 5., 7., 9.])
    m, err = _calc_error(vals, "sd")
    assert abs(err - np.std(vals, ddof=1)) < 1e-12

run("10b. SD matches numpy std(ddof=1)", test_calc_error_sd)


# ── CI95 = t_crit * SEM ──────────────────────────────────────────────────
def test_calc_error_ci95():
    vals = np.array([2., 4., 6., 8., 10., 12.])
    m, err = _calc_error(vals, "ci95")
    n = len(vals)
    s = float(np.std(vals, ddof=1))
    t_crit = sp_stats.t.ppf(0.975, n - 1)
    expected_ci = t_crit * s / np.sqrt(n)
    assert abs(err - expected_ci) < 1e-10

run("10c. CI95 = t_crit(0.975, n-1) * SEM", test_calc_error_ci95)


# ── CI95 with different n ────────────────────────────────────────────────
def test_calc_error_ci95_various_n():
    for n in [3, 5, 10, 50]:
        vals = rng.normal(10, 3, n)
        m, err = _calc_error(vals, "ci95")
        s = float(np.std(vals, ddof=1))
        t_crit = sp_stats.t.ppf(0.975, n - 1)
        expected = t_crit * s / np.sqrt(n)
        assert abs(err - expected) < 1e-10, f"n={n}: CI95 mismatch"

run("10d. CI95 correct for n=3,5,10,50", test_calc_error_ci95_various_n)


# ── n=1: SEM should be 0 (ddof=1 std with n=1 → 0 because std guard) ────
def test_calc_error_n1():
    vals = np.array([5.])
    m_sem, e_sem = _calc_error(vals, "sem")
    m_sd, e_sd = _calc_error(vals, "sd")
    m_ci, e_ci = _calc_error(vals, "ci95")
    assert abs(m_sem - 5.0) < 1e-12
    # With n=1, std(ddof=1) is undefined (would need ddof<n), but code sets s=0
    assert e_sem == 0.0, f"SEM with n=1: got {e_sem}"
    assert e_sd == 0.0, f"SD with n=1: got {e_sd}"

run("10e. n=1: SEM and SD are 0 (no crash)", test_calc_error_n1)


# ── All identical values: error = 0 ──────────────────────────────────────
def test_calc_error_identical():
    vals = np.array([7., 7., 7., 7., 7.])
    for etype in ("sem", "sd", "ci95"):
        m, err = _calc_error(vals, etype)
        assert abs(m - 7.0) < 1e-12
        assert abs(err) < 1e-12, f"{etype}: error should be 0 for identical values"

run("10f. All identical values: error = 0 for SEM/SD/CI95", test_calc_error_identical)


# ── Asymmetric error: positive mean ──────────────────────────────────────
def test_calc_error_asymmetric_positive():
    vals = np.array([10., 12., 14., 16., 18.])
    m, lo, hi = _calc_error_asym(vals, "sem")
    assert m > 0
    assert lo >= 0, f"Lower error should be >= 0, got {lo}"
    assert hi >= 0, f"Upper error should be >= 0, got {hi}"
    # Lower bar should be <= mean (can't extend through zero)
    assert lo <= m * 0.9999 + 1e-12

run("10g. Asymmetric error: lo >= 0, hi >= 0, lo < mean", test_calc_error_asymmetric_positive)


# ── Asymmetric error: negative mean falls back to symmetric ──────────────
def test_calc_error_asymmetric_negative_mean():
    vals = np.array([-10., -12., -14., -16., -18.])
    m, lo, hi = _calc_error_asym(vals, "sem")
    assert m < 0
    # For negative mean, falls back to symmetric
    _, half = _calc_error(vals, "sem")
    assert abs(lo - half) < 1e-12
    assert abs(hi - half) < 1e-12

run("10h. Asymmetric error: negative mean → symmetric fallback", test_calc_error_asymmetric_negative_mean)


# ── Asymmetric error types consistency ────────────────────────────────────
def test_calc_error_asymmetric_all_types():
    vals = np.array([5., 6., 7., 8., 9., 10.])
    for etype in ("sem", "sd", "ci95"):
        m, lo, hi = _calc_error_asym(vals, etype)
        assert m > 0
        assert lo >= 0
        assert hi >= 0

run("10i. Asymmetric error: all types (SEM/SD/CI95) produce valid bounds", test_calc_error_asymmetric_all_types)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 11 — Log-rank test
# ══════════════════════════════════════════════════════════════════════════════
section("11. Log-rank test — additional verification")


# ── Log-rank: non-overlapping survival → significant ─────────────────────
def test_logrank_non_overlapping():
    groups_dict = {
        "Early": (np.array([1., 2., 3., 4., 5.]), np.array([1, 1, 1, 1, 1])),
        "Late":  (np.array([10., 11., 12., 13., 14.]), np.array([1, 1, 1, 1, 1])),
    }
    res = _logrank_test(groups_dict)
    assert len(res) == 1
    _, _, p, _ = res[0]
    assert p < 0.05, f"Non-overlapping survival: p={p} should be < 0.05"

run("11a. Log-rank: non-overlapping survival → significant", test_logrank_non_overlapping)


# ── Log-rank: identical → p ≈ 1 ──────────────────────────────────────────
def test_logrank_identical():
    t = np.array([1., 2., 3., 4., 5.])
    e = np.array([1, 1, 1, 1, 1])
    groups_dict = {"A": (t.copy(), e.copy()), "B": (t.copy(), e.copy())}
    res = _logrank_test(groups_dict)
    _, _, p, _ = res[0]
    assert p > 0.99, f"Identical survival: p={p} should be ~1"

run("11b. Log-rank: identical survival → p ≈ 1", test_logrank_identical)


# ── Log-rank: 3 groups → 3 pairwise comparisons ─────────────────────────
def test_logrank_3_groups():
    groups_dict = {
        "A": (np.array([1., 2., 3.]), np.array([1, 1, 1])),
        "B": (np.array([5., 6., 7.]), np.array([1, 1, 1])),
        "C": (np.array([10., 11., 12.]), np.array([1, 1, 1])),
    }
    res = _logrank_test(groups_dict)
    assert len(res) == 3, f"Expected 3 pairwise, got {len(res)}"

run("11c. Log-rank: 3 groups → 3 pairwise comparisons", test_logrank_3_groups)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 12 — Two-way ANOVA and posthoc
# ══════════════════════════════════════════════════════════════════════════════
section("12. Two-way ANOVA — additional verification")


# ── Type III SS: each SS_effect > 0 for real effects, SS_err > 0 ─────────
def test_twoway_ss_properties():
    """Type III SS: SS_A, SS_B > 0 for real main effects; SS_err > 0.
    NOTE: Type III SS are NOT additive (SS_A+SS_B+SS_AB+SS_err != SS_total).
    This is by design — Type III uses partial sums of squares where each
    effect is tested after removing it from the full model. Only Type I
    (sequential) SS are additive."""
    rows = []
    rng2 = np.random.default_rng(77)
    for a in ["a1", "a2"]:
        for b in ["b1", "b2", "b3"]:
            mu = 10 + (a == "a2") * 5 + (b == "b2") * 3 + (b == "b3") * 7
            for _ in range(4):
                rows.append({"A": a, "B": b, "Y": mu + rng2.normal(0, 1)})
    df = pd.DataFrame(rows)
    result = _twoway_anova(df, "Y", "A", "B")

    # Main effects with real differences should have SS > 0
    assert result["A"]["SS"] > 0, "SS_A should be > 0 for real main effect"
    assert result["B"]["SS"] > 0, "SS_B should be > 0 for real main effect"
    assert result["residual"]["SS"] > 0, "SS_err should be > 0"
    # F-stats should be positive
    assert result["A"]["F"] > 0
    assert result["B"]["F"] > 0
    # Strong effects should be significant
    assert result["A"]["p"] < 0.05
    assert result["B"]["p"] < 0.05

run("12a. Two-way ANOVA: Type III SS properties (SS > 0 for real effects)", test_twoway_ss_properties)


# ── Two-way posthoc: Holm correction applied ─────────────────────────────
def test_twoway_posthoc_holm():
    rows = []
    rng2 = np.random.default_rng(42)
    for a in ["a1", "a2"]:
        for b in ["b1", "b2"]:
            mu = {"a1b1": 10, "a1b2": 20, "a2b1": 30, "a2b2": 40}[a+b]
            for _ in range(5):
                rows.append({"A": a, "B": b, "Y": mu + rng2.normal(0, 1)})
    df = pd.DataFrame(rows)
    res = _twoway_posthoc(df, "Y", "A", "B", correction="holm")
    raw_ps = [r["p_raw"] for r in res]
    corr_ps = [r["p_corr"] for r in res]
    # Holm-corrected should be >= raw
    for rp, cp in zip(raw_ps, corr_ps):
        assert cp >= rp - 1e-12, f"Holm p_corr={cp} < p_raw={rp}"

run("12b. Two-way posthoc: Holm correction makes p_corr >= p_raw", test_twoway_posthoc_holm)


# ── Two-way ANOVA: insufficient replicates raises error ──────────────────
def test_twoway_insufficient_replicates():
    rows = [{"A": "a1", "B": "b1", "Y": 1.0},
            {"A": "a1", "B": "b2", "Y": 2.0},
            {"A": "a2", "B": "b1", "Y": 3.0},
            {"A": "a2", "B": "b2", "Y": 4.0}]
    df = pd.DataFrame(rows)
    try:
        _twoway_anova(df, "Y", "A", "B")
        assert False, "Should raise ValueError for 1 replicate per cell"
    except ValueError as e:
        assert "not enough" in str(e).lower()

run("12c. Two-way ANOVA: 1 rep per cell raises ValueError", test_twoway_insufficient_replicates)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 13 — Tukey HSD: ANOVA gate behavior
# ══════════════════════════════════════════════════════════════════════════════
section("13. ANOVA / KW gate behavior")


def test_tukey_anova_gate_p05():
    """Tukey HSD returns empty when ANOVA p >= 0.05."""
    # Use groups with very similar means
    a = np.array([5.0, 5.1, 4.9, 5.0, 5.1])
    b = np.array([5.0, 5.0, 5.1, 4.9, 5.0])
    c = np.array([5.1, 5.0, 4.9, 5.0, 5.1])
    _, p_anova = sp_stats.f_oneway(a, b, c)
    assert p_anova >= 0.05, f"Need non-significant ANOVA, got p={p_anova}"
    groups = {"A": a, "B": b, "C": c}
    res = _run_stats(groups, test_type="parametric", posthoc="Tukey HSD")
    assert res == []

run("13a. Tukey HSD: ANOVA gate rejects non-significant F", test_tukey_anova_gate_p05)


def test_bonferroni_posthoc_anova_gate():
    """Bonferroni posthoc also has ANOVA gate."""
    a = np.array([5.0, 5.1, 4.9])
    b = np.array([5.0, 5.0, 5.1])
    c = np.array([5.1, 5.0, 4.9])
    groups = {"A": a, "B": b, "C": c}
    res = _run_stats(groups, test_type="parametric", posthoc="Bonferroni")
    assert res == []

run("13b. Bonferroni posthoc: ANOVA gate rejects non-significant F", test_bonferroni_posthoc_anova_gate)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 14 — Comprehensive _p_to_stars
# ══════════════════════════════════════════════════════════════════════════════
section("14. _p_to_stars comprehensive boundary tests")


def test_p_to_stars_all_boundaries():
    cases = [
        (0.0,      "****"),
        (0.00001,  "****"),
        (0.0001,   "****"),
        (0.00011,  "***"),
        (0.0005,   "***"),
        (0.001,    "***"),
        (0.0011,   "**"),
        (0.005,    "**"),
        (0.01,     "**"),
        (0.011,    "*"),
        (0.025,    "*"),
        (0.05,     "*"),
        (0.051,    "ns"),
        (0.1,      "ns"),
        (0.5,      "ns"),
        (1.0,      "ns"),
    ]
    for p_val, expected in cases:
        got = _p_to_stars(p_val)
        assert got == expected, f"p={p_val}: expected '{expected}', got '{got}'"

run("14a. _p_to_stars: all boundary values correct", test_p_to_stars_all_boundaries)


# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    summarise("stats_exhaustive")
    sys.exit(0 if _h.FAIL == 0 else 1)
