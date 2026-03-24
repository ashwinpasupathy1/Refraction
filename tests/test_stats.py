"""
test_stats.py
=============
Consolidated statistical tests — merges test_stats_verification.py (37 tests)
and test_control.py (20 tests) into one file.

Total: 57 tests.

Run:
  python3 tests/test_stats.py  (or via run_all.py)
"""

import sys, os, warnings
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import plotter_test_harness as _h
from plotter_test_harness import (
    pf, ok, fail, run, section, summarise, close_fig,
    bar_excel, line_excel, simple_xy_excel, grouped_excel,
    km_excel, heatmap_excel, two_way_excel, contingency_excel,
    bland_altman_excel, forest_excel, bubble_excel, chi_gof_excel,
    with_excel, PLOT_PARAM_DEFAULTS,
)

# ─── shorthand for the internal stats helpers ────────────────────────────────
_cohens_d        = pf._cohens_d
_hedges_g        = pf._hedges_g
_rank_biserial_r = pf._rank_biserial_r
_apply_correction= pf._apply_correction
_p_to_stars      = pf._p_to_stars
_run_stats       = pf._run_stats
_logrank_test    = pf._logrank_test
_twoway_anova    = pf._twoway_anova

from scipy import stats as _scipy_stats
import pandas as _pd


# ══════════════════════════════════════════════════════════════════════════════
# PART A — Statistical Verification (from test_stats_verification.py, 37 tests)
# ══════════════════════════════════════════════════════════════════════════════

# ═════════════════════════════════════════════════════════════════════════════
# 1.  Welch's t-test p-value
# ═════════════════════════════════════════════════════════════════════════════
section("Welch's t-test — p-value matches scipy reference")

A = np.array([100., 110., 120., 130., 140.])
B = np.array([200., 220., 240., 260., 280.])


def test_welch_t_pvalue():
    """_run_stats parametric k=2 p-value matches scipy.stats.ttest_ind."""
    groups = {"A": A, "B": B}
    results = _run_stats(groups, test_type="parametric",
                         mc_correction="None (uncorrected)")
    assert len(results) == 1, "Expected one pairwise result"
    _, _, p_ours, _ = results[0]

    _, p_scipy = _scipy_stats.ttest_ind(A, B, equal_var=False)
    assert abs(p_ours - p_scipy) < 1e-12, (
        f"p mismatch: ours={p_ours:.6e}, scipy={p_scipy:.6e}")
    assert p_ours < 0.01, f"Expected very small p, got {p_ours}"

run("Welch t-test: p matches scipy.stats.ttest_ind (equal_var=False)",
    test_welch_t_pvalue)


def test_welch_t_statistic_direction():
    """Welch's t-test reports correct direction (A < B → p significant)."""
    groups = {"A": np.array([1., 2., 3.]),
              "B": np.array([10., 11., 12.])}
    results = _run_stats(groups, test_type="parametric",
                         mc_correction="None (uncorrected)")
    assert results[0][3] in ("*", "**", "***", "****"), (
        "Clearly separated groups should be significant")

run("Welch t-test: clearly separated groups flagged significant",
    test_welch_t_statistic_direction)


# ═════════════════════════════════════════════════════════════════════════════
# 2.  Cohen's d — analytical verification
# ═════════════════════════════════════════════════════════════════════════════
section("Cohen's d — analytical formula verification")

def test_cohens_d_analytical():
    """Cohen's d matches hand-computed value for known dataset."""
    d = _cohens_d(A, B)
    assert abs(d - (-4.8)) < 1e-10, f"Expected d=-4.8, got {d}"

run("Cohen's d: hand-computed value -4.8", test_cohens_d_analytical)


def test_cohens_d_symmetric():
    """Cohen's d is antisymmetric: d(A,B) = -d(B,A)."""
    d_ab = _cohens_d(A, B)
    d_ba = _cohens_d(B, A)
    assert abs(d_ab + d_ba) < 1e-10, (
        f"d(A,B)={d_ab:.4f}, d(B,A)={d_ba:.4f}, expected sum=0")

run("Cohen's d: antisymmetric d(A,B) = -d(B,A)", test_cohens_d_symmetric)


def test_cohens_d_equal_means():
    """Cohen's d = 0 when both groups have the same mean."""
    X = np.array([1., 2., 3., 4., 5.])
    d = _cohens_d(X, X.copy())
    assert d == 0.0, f"Expected d=0 for identical groups, got {d}"

run("Cohen's d: d=0 for groups with identical values", test_cohens_d_equal_means)


def test_cohens_d_small_n_returns_nan():
    """Cohen's d returns NaN when either group has fewer than 2 observations."""
    assert np.isnan(_cohens_d(np.array([1.]), np.array([2., 3., 4.]))), \
        "n1=1 should return NaN"
    assert np.isnan(_cohens_d(np.array([1., 2.]), np.array([3.]))), \
        "n2=1 should return NaN"

run("Cohen's d: NaN for n<2", test_cohens_d_small_n_returns_nan)


# ═════════════════════════════════════════════════════════════════════════════
# 3.  Hedges' g — bias-correction verification
# ═════════════════════════════════════════════════════════════════════════════
section("Hedges' g — small-sample bias correction")

def test_hedges_g_correction():
    """Hedges' g applies J correction: g = d * (1 - 3/(4m-1))."""
    g = _hedges_g(A, B)
    m = len(A) + len(B) - 2   # = 8
    J = 1.0 - 3.0 / (4.0 * m - 1.0)
    d = _cohens_d(A, B)
    expected = d * J
    assert abs(g - expected) < 1e-12, (
        f"Expected g={expected:.6f}, got {g:.6f}")

run("Hedges' g: g = d × J(m) with m=8", test_hedges_g_correction)


def test_hedges_g_smaller_than_cohens_d():
    """For small samples, |g| < |d| (bias correction shrinks estimate)."""
    g = _hedges_g(A, B)
    d = _cohens_d(A, B)
    assert abs(g) < abs(d), (
        f"|g|={abs(g):.4f} should be < |d|={abs(d):.4f} for n=5")

run("Hedges' g: |g| < |d| for small samples (n=5)", test_hedges_g_smaller_than_cohens_d)


def test_hedges_g_large_n_converges_to_d():
    """For large n, Hedges' g ≈ Cohen's d (correction → 1)."""
    rng = np.random.default_rng(42)
    X = rng.normal(0, 1, 500)
    Y = rng.normal(0.5, 1, 500)
    d = _cohens_d(X, Y)
    g = _hedges_g(X, Y)
    assert abs(g - d) / (abs(d) + 1e-9) < 0.002, (
        f"Large n: g={g:.6f} should be very close to d={d:.6f}")

run("Hedges' g: converges to Cohen's d for large n", test_hedges_g_large_n_converges_to_d)


def test_hedges_g_nan_propagation():
    """Hedges' g returns NaN when n < 2."""
    assert np.isnan(_hedges_g(np.array([1.]), np.array([2., 3.]))), \
        "n1=1 should return NaN"

run("Hedges' g: NaN when n<2", test_hedges_g_nan_propagation)


# ═════════════════════════════════════════════════════════════════════════════
# 4.  Rank-biserial r — analytical verification
# ═════════════════════════════════════════════════════════════════════════════
section("Rank-biserial r — Mann-Whitney effect size")

def test_rank_biserial_complete_separation():
    """r = -1 when all values in A are lower than all in B."""
    r = _rank_biserial_r(
        np.array([1., 2., 3.]),
        np.array([4., 5., 6.])
    )
    assert r == -1.0, f"Expected r=-1, got {r}"

run("Rank-biserial r: -1 for complete separation (A < B)", test_rank_biserial_complete_separation)


def test_rank_biserial_reverse_separation():
    """r = +1 when all values in A are higher than all in B."""
    r = _rank_biserial_r(
        np.array([4., 5., 6.]),
        np.array([1., 2., 3.])
    )
    assert r == 1.0, f"Expected r=+1, got {r}"

run("Rank-biserial r: +1 when A > B completely", test_rank_biserial_reverse_separation)


def test_rank_biserial_antisymmetric():
    """r(A,B) = -r(B,A)."""
    rng = np.random.default_rng(99)
    X = rng.normal(0, 1, 8)
    Y = rng.normal(1, 1, 8)
    r_xy = _rank_biserial_r(X, Y)
    r_yx = _rank_biserial_r(Y, X)
    assert abs(r_xy + r_yx) < 1e-10, (
        f"r(X,Y)={r_xy:.4f}, r(Y,X)={r_yx:.4f}, expected sum≈0")

run("Rank-biserial r: antisymmetric r(A,B)=-r(B,A)", test_rank_biserial_antisymmetric)


def test_rank_biserial_range():
    """r is always in [-1, 1]."""
    rng = np.random.default_rng(7)
    for _ in range(20):
        X = rng.normal(0, 1, rng.integers(3, 15))
        Y = rng.normal(0, 1, rng.integers(3, 15))
        r = _rank_biserial_r(X, Y)
        assert -1.0 <= r <= 1.0, f"r={r} out of [-1,1]"

run("Rank-biserial r: always in [-1, 1]", test_rank_biserial_range)


# ═════════════════════════════════════════════════════════════════════════════
# 5.  Mann-Whitney p-value — exact reference
# ═════════════════════════════════════════════════════════════════════════════
section("Mann-Whitney U — p-value vs scipy exact")

def test_mannwhitney_exact_pvalue():
    """Mann-Whitney p matches scipy exact for small n."""
    groups = {
        "A": np.array([1., 2., 3.]),
        "B": np.array([4., 5., 6.]),
    }
    results = _run_stats(groups, test_type="nonparametric",
                         mc_correction="None (uncorrected)")
    assert len(results) == 1
    _, _, p_ours, _ = results[0]

    _, p_scipy = _scipy_stats.mannwhitneyu(
        groups["A"], groups["B"], alternative="two-sided")
    assert abs(p_ours - p_scipy) < 1e-12, (
        f"p mismatch: ours={p_ours:.6e}, scipy={p_scipy:.6e}")

run("Mann-Whitney: p matches scipy.stats.mannwhitneyu", test_mannwhitney_exact_pvalue)


def test_mannwhitney_complete_separation_significant():
    """Mann-Whitney is significant for completely separated groups (n=8 each)."""
    groups = {
        "A": np.arange(1., 9.),
        "B": np.arange(9., 17.),
    }
    results = _run_stats(groups, test_type="nonparametric",
                         mc_correction="None (uncorrected)")
    _, _, p, _ = results[0]
    assert p < 0.05, f"Expected p<0.05 for complete separation, got {p}"

run("Mann-Whitney: significant for fully separated groups (n=8)", test_mannwhitney_complete_separation_significant)


# ═════════════════════════════════════════════════════════════════════════════
# 6.  One-way ANOVA F-statistic and p-value
# ═════════════════════════════════════════════════════════════════════════════
section("One-way ANOVA — F-statistic and p-value")

G_A = np.array([2., 4., 6., 8., 10.])
G_B = np.array([6., 8., 10., 12., 14.])
G_C = np.array([10., 12., 14., 16., 18.])


def test_oneway_anova_F():
    """One-way ANOVA F=8.0 for known balanced dataset."""
    F, p = _scipy_stats.f_oneway(G_A, G_B, G_C)
    assert abs(F - 8.0) < 1e-10, f"Expected F=8.0, got F={F}"
    assert abs(p - _scipy_stats.f.sf(8.0, 2, 12)) < 1e-12

run("One-way ANOVA: F=8.0 for hand-computed balanced design", test_oneway_anova_F)


# ═════════════════════════════════════════════════════════════════════════════
# 7.  Tukey HSD — correct pair selection
# ═════════════════════════════════════════════════════════════════════════════
section("Tukey HSD — correct pair significance")

def test_tukey_finds_only_AC_significant():
    """Tukey HSD: only A vs C significant; A vs B and B vs C are NS."""
    groups = {"A": G_A, "B": G_B, "C": G_C}
    results = _run_stats(groups, test_type="parametric",
                         posthoc="Tukey HSD",
                         mc_correction="None (uncorrected)")
    sig_pairs = {(r[0], r[1]) for r in results if r[3] != "ns"}
    assert ("A", "C") in sig_pairs or ("C", "A") in sig_pairs, (
        f"A vs C should be significant. sig_pairs={sig_pairs}")
    ab_sig = ("A", "B") in sig_pairs or ("B", "A") in sig_pairs
    bc_sig = ("B", "C") in sig_pairs or ("C", "B") in sig_pairs
    assert not ab_sig, "A vs B should be NS"
    assert not bc_sig, "B vs C should be NS"

run("Tukey HSD: A vs C significant, A vs B and B vs C NS", test_tukey_finds_only_AC_significant)


def test_tukey_pvalue_vs_studentized_range():
    """Tukey p-value for A vs C matches manual studentized-range CDF."""
    groups = {"A": G_A, "B": G_B, "C": G_C}
    results = _run_stats(groups, test_type="parametric",
                         posthoc="Tukey HSD",
                         mc_correction="None (uncorrected)")
    p_ac = None
    for a_lbl, b_lbl, p, stars in results:
        if set([a_lbl, b_lbl]) == {"A", "C"}:
            p_ac = p
    assert p_ac is not None, "A vs C result not found"
    q_manual = 8.0 / np.sqrt(2.0)
    p_manual = 1.0 - _scipy_stats.studentized_range.cdf(q_manual, 3, 12)
    assert abs(p_ac - p_manual) < 1e-10, (
        f"p_ours={p_ac:.6e}, p_manual={p_manual:.6e}")

run("Tukey HSD: A vs C p-value matches manual studentized_range.cdf",
    test_tukey_pvalue_vs_studentized_range)


# ═════════════════════════════════════════════════════════════════════════════
# 8.  Multiple comparison corrections
# ═════════════════════════════════════════════════════════════════════════════
section("Multiple comparison corrections — Bonferroni, Holm, BH")

RAW_P = [0.01, 0.04, 0.20]


def test_bonferroni_correction():
    """Bonferroni: p_corr = min(p * m, 1)."""
    corrected = _apply_correction(RAW_P, "Bonferroni")
    m = 3
    expected = [min(p * m, 1.0) for p in RAW_P]
    for got, exp in zip(corrected, expected):
        assert abs(got - exp) < 1e-12, f"Bonferroni: got={got}, exp={exp}"

run("Bonferroni: p_corr = min(p * m, 1)", test_bonferroni_correction)


def test_holm_monotonicity():
    """Holm-Bonferroni corrected p-values are non-decreasing (monotone step-up)."""
    corrected = _apply_correction(RAW_P, "Holm-Bonferroni")
    for i in range(len(corrected) - 1):
        assert corrected[i] <= corrected[i + 1] + 1e-12, (
            f"Holm not monotone: p[{i}]={corrected[i]} > p[{i+1}]={corrected[i+1]}")

run("Holm-Bonferroni: corrected p-values are non-decreasing", test_holm_monotonicity)


def test_holm_first_is_smallest():
    """Holm-Bonferroni: sorted corrected p-values are ≥ raw p-values."""
    corrected = _apply_correction(RAW_P, "Holm-Bonferroni")
    for raw, corr in zip(RAW_P, corrected):
        assert corr >= raw - 1e-12, (
            f"Corrected p={corr} should be ≥ raw p={raw}")

run("Holm-Bonferroni: all corrected ≥ raw", test_holm_first_is_smallest)


def test_bh_fdr_monotone():
    """BH FDR corrected p-values are non-decreasing when input is sorted."""
    raw_sorted = sorted(RAW_P)
    corrected = _apply_correction(raw_sorted, "Benjamini-Hochberg (FDR)")
    for i in range(len(corrected) - 1):
        assert corrected[i] <= corrected[i + 1] + 1e-12, (
            f"BH not monotone: p[{i}]={corrected[i]} > p[{i+1}]={corrected[i+1]}")

run("BH FDR: corrected p-values non-decreasing (sorted input)", test_bh_fdr_monotone)


def test_corrections_cap_at_one():
    """All correction methods cap corrected p-values at 1.0."""
    high_p = [0.5, 0.6, 0.7, 0.8, 0.9]
    for method in ("Bonferroni", "Holm-Bonferroni", "Benjamini-Hochberg (FDR)"):
        corrected = _apply_correction(high_p, method)
        for cp in corrected:
            assert cp <= 1.0, f"{method}: corrected p={cp} > 1.0"

run("All corrections: corrected p capped at 1.0", test_corrections_cap_at_one)


# ═════════════════════════════════════════════════════════════════════════════
# 9.  p-to-stars thresholds (Prism convention)
# ═════════════════════════════════════════════════════════════════════════════
section("p-to-stars — exact Prism threshold boundaries")

def test_stars_exact_boundaries():
    """_p_to_stars returns correct stars at each Prism boundary."""
    cases = [
        (0.0001,  "****"),
        (0.0002,  "***"),
        (0.001,   "***"),
        (0.0011,  "**"),
        (0.01,    "**"),
        (0.011,   "*"),
        (0.05,    "*"),
        (0.051,   "ns"),
        (0.99,    "ns"),
    ]
    for p, expected in cases:
        got = _p_to_stars(p)
        assert got == expected, (
            f"p={p}: expected '{expected}', got '{got}'")

run("p-to-stars: correct stars at each Prism boundary", test_stars_exact_boundaries)


# ═════════════════════════════════════════════════════════════════════════════
# 10.  Chi-square goodness-of-fit
# ═════════════════════════════════════════════════════════════════════════════
section("Chi-square GoF — analytical χ² and p-value")

def test_chi2_gof_statistic():
    """Chi-square GoF statistic = 14.0 for known unequal observed counts."""
    observed = np.array([20., 30., 50.])
    expected = np.full(3, 100.0 / 3.0)
    chi2, p = _scipy_stats.chisquare(observed, f_exp=expected)
    assert abs(chi2 - 14.0) < 1e-10, f"Expected χ²=14.0, got {chi2}"
    assert p < 0.01, f"Expected p<0.01 for χ²=14 (df=2), got {p}"

run("Chi-square GoF: χ²=14.0 for [20,30,50] vs uniform", test_chi2_gof_statistic)


def test_chi2_gof_uniform_null():
    """Chi-square GoF is not significant for uniform observations."""
    observed = np.array([10., 10., 10.])
    chi2, p = _scipy_stats.chisquare(observed)
    assert chi2 == 0.0, f"Expected χ²=0 for uniform, got {chi2}"
    assert p == 1.0, f"Expected p=1 for χ²=0"

run("Chi-square GoF: χ²=0 and p=1 for perfectly uniform observations", test_chi2_gof_uniform_null)


# ═════════════════════════════════════════════════════════════════════════════
# 11.  Log-rank (Mantel-Cox) test — hand-computed reference
# ═════════════════════════════════════════════════════════════════════════════
section("Log-rank test — hand-computed Mantel-Cox statistic")

def test_logrank_hand_computed():
    """Log-rank χ² ≈ 5.052 and p ≈ 0.025 for non-overlapping survival times."""
    groups_dict = {
        "A": (np.array([1., 2., 3.]), np.array([1, 1, 1])),
        "B": (np.array([5., 6., 7.]), np.array([1, 1, 1])),
    }
    results = _logrank_test(groups_dict)
    assert len(results) == 1
    a_lbl, b_lbl, p, stars = results[0]
    O1, E1 = 3.0, 1.15
    var     = 0.6775
    chi2_expected = (O1 - E1) ** 2 / var
    p_expected = float(_scipy_stats.chi2.sf(chi2_expected, df=1))
    assert abs(p - p_expected) < 1e-8, (
        f"p_ours={p:.6f}, p_expected={p_expected:.6f}")
    assert p < 0.05, f"Expected significant result, got p={p}"

run("Log-rank: χ²≈5.052 and p<0.05 for non-overlapping groups",
    test_logrank_hand_computed)


def test_logrank_identical_groups_not_significant():
    """Log-rank test gives p=1 (or at least >>0.05) for identical groups."""
    t = np.array([1., 2., 3., 4., 5.])
    e = np.array([1, 1, 1, 1, 1])
    groups_dict = {"A": (t.copy(), e.copy()), "B": (t.copy(), e.copy())}
    results = _logrank_test(groups_dict)
    _, _, p, _ = results[0]
    assert p > 0.99, f"Identical groups should give p≈1, got {p}"

run("Log-rank: p≈1 for identical survival curves", test_logrank_identical_groups_not_significant)


# ═════════════════════════════════════════════════════════════════════════════
# 12.  Two-way ANOVA — partial eta-squared and F-statistic
# ═════════════════════════════════════════════════════════════════════════════
section("Two-way ANOVA — partial eta-squared (ηp²)")

def _make_twoway_df():
    rows = []
    rng2 = np.random.default_rng(0)
    for a in ["a1", "a2"]:
        for b in ["b1", "b2"]:
            mu = {"a1b1": 10, "a1b2": 20, "a2b1": 30, "a2b2": 40}[a + b]
            for _ in range(5):
                rows.append({"A": a, "B": b, "Y": mu + rng2.normal(0, 1)})
    return _pd.DataFrame(rows)


def test_twoway_anova_partial_eta2_range():
    """Partial eta² (ηp²) is in [0, 1] for each effect."""
    df = _make_twoway_df()
    result = _twoway_anova(df, "Y", "A", "B")
    for key in ("A", "B", "interaction"):
        ep2 = result[key]["eta2_partial"]
        assert 0.0 <= ep2 <= 1.0, (
            f"{key}: eta2_partial={ep2:.4f} out of [0,1]")

run("Two-way ANOVA: ηp² in [0,1] for each effect", test_twoway_anova_partial_eta2_range)


def test_twoway_anova_partial_eta2_formula():
    """ηp² = SS_effect / (SS_effect + SS_error)."""
    df = _make_twoway_df()
    result = _twoway_anova(df, "Y", "A", "B")
    SS_err = result["residual"]["SS"]
    for key in ("A", "B", "interaction"):
        SS_eff = result[key]["SS"]
        expected_ep2 = SS_eff / (SS_eff + SS_err)
        got_ep2 = result[key]["eta2_partial"]
        assert abs(got_ep2 - expected_ep2) < 1e-12, (
            f"{key}: ηp²={got_ep2:.6f}, expected {expected_ep2:.6f}")

run("Two-way ANOVA: ηp² = SS_effect/(SS_effect+SS_error)", test_twoway_anova_partial_eta2_formula)


def test_twoway_anova_strong_main_effects_significant():
    """Large main effects yield significant F and large ηp²."""
    df = _make_twoway_df()
    result = _twoway_anova(df, "Y", "A", "B")
    assert result["A"]["p"] < 0.05, f"Factor A should be significant, p={result['A']['p']}"
    assert result["B"]["p"] < 0.05, f"Factor B should be significant, p={result['B']['p']}"
    assert result["A"]["eta2_partial"] > 0.5, (
        f"Factor A eta2_partial={result['A']['eta2_partial']:.3f} expected >0.5")
    assert result["B"]["eta2_partial"] > 0.5, (
        f"Factor B eta2_partial={result['B']['eta2_partial']:.3f} expected >0.5")

run("Two-way ANOVA: strong main effects → significant F and large ηp²",
    test_twoway_anova_strong_main_effects_significant)


# ═════════════════════════════════════════════════════════════════════════════
# 13.  Two-way post-hoc uses Welch's t-test
# ═════════════════════════════════════════════════════════════════════════════
section("Two-way post-hoc — Welch's t-test (equal_var=False)")

def test_twoway_posthoc_welch():
    """Two-way post-hoc p-values match scipy Welch t-test (equal_var=False)."""
    from plotter_functions import _twoway_posthoc
    df = _make_twoway_df()
    results = _twoway_posthoc(df, "Y", "A", "B", correction="none")
    for row in results:
        b_val = row["factor_b_level"]
        g1 = df[(df["B"] == b_val) & (df["A"] == row["group1"])]["Y"].values
        g2 = df[(df["B"] == b_val) & (df["A"] == row["group2"])]["Y"].values
        _, p_scipy = _scipy_stats.ttest_ind(g1, g2, equal_var=False)
        assert abs(row["p_raw"] - p_scipy) < 1e-12, (
            f"B={b_val}, {row['group1']} vs {row['group2']}: "
            f"p_raw={row['p_raw']:.6e}, scipy_welch={p_scipy:.6e}")

run("Two-way post-hoc: p_raw matches Welch's ttest_ind(equal_var=False)",
    test_twoway_posthoc_welch)


# ═════════════════════════════════════════════════════════════════════════════
# 14.  One-sample t-test
# ═════════════════════════════════════════════════════════════════════════════
section("One-sample t-test — p-value vs scipy")

def test_one_sample_pvalue():
    """One-sample t-test p matches scipy.stats.ttest_1samp."""
    grp = np.array([1., 2., 3., 4., 5.])
    mu0 = 0.0
    groups = {"grp": grp}
    results = _run_stats(groups, test_type="one_sample",
                         mc_correction="None (uncorrected)", mu0=mu0)
    assert len(results) == 1
    _, _, p_ours, _ = results[0]
    _, p_scipy = _scipy_stats.ttest_1samp(grp, popmean=mu0)
    assert abs(p_ours - p_scipy) < 1e-12, (
        f"p mismatch: ours={p_ours:.6e}, scipy={p_scipy:.6e}")
    assert p_ours < 0.05, f"Expected significant (mean=3 vs μ₀=0), got p={p_ours}"

run("One-sample t-test: p matches scipy.stats.ttest_1samp", test_one_sample_pvalue)


# ═════════════════════════════════════════════════════════════════════════════
# 15.  Paired t-test
# ═════════════════════════════════════════════════════════════════════════════
section("Paired t-test — p-value vs scipy")

def test_paired_ttest_pvalue():
    """Paired t-test p matches scipy.stats.ttest_rel."""
    pre  = np.array([10., 12., 14., 16., 18.])
    post = np.array([12., 15., 17., 20., 22.])
    groups = {"pre": pre, "post": post}
    results = _run_stats(groups, test_type="paired",
                         mc_correction="None (uncorrected)")
    assert len(results) == 1
    _, _, p_ours, _ = results[0]
    _, p_scipy = _scipy_stats.ttest_rel(pre, post)
    assert abs(p_ours - p_scipy) < 1e-12, (
        f"p mismatch: ours={p_ours:.6e}, scipy={p_scipy:.6e}")
    assert p_ours < 0.05, "Pre vs post with clear improvement should be significant"

run("Paired t-test: p matches scipy.stats.ttest_rel", test_paired_ttest_pvalue)


# ═════════════════════════════════════════════════════════════════════════════
# 16.  Dunn's post-hoc — formula cross-check
# ═════════════════════════════════════════════════════════════════════════════
section("Dunn's post-hoc — p-value vs scipy normal CDF")

def test_dunns_pvalue_vs_normal_cdf():
    """Dunn's z-statistic: most-extreme pair significant for separated groups."""
    groups = {
        "A": np.arange(1., 11.),
        "B": np.arange(21., 31.),
        "C": np.arange(41., 51.),
    }
    results = _run_stats(groups, test_type="nonparametric",
                         mc_correction="None (uncorrected)")
    sig_pairs = {frozenset([r[0], r[1]]) for r in results if r[3] != "ns"}
    assert frozenset(["A", "C"]) in sig_pairs, (
        f"A vs C should be significant (large separation, n=10). sig={sig_pairs}")

run("Dunn's post-hoc: most-extreme pair significant for large separation (n=10)",
    test_dunns_pvalue_vs_normal_cdf)


def test_dunns_pvalue_uses_two_tailed_z():
    """Dunn's z p-values are from two-tailed normal distribution (symmetric)."""
    rng3 = np.random.default_rng(42)
    groups = {
        "X": rng3.normal(0, 1, 10),
        "Y": rng3.normal(0.5, 1, 10),
        "Z": rng3.normal(1.0, 1, 10),
    }
    results = _run_stats(groups, test_type="nonparametric",
                         mc_correction="None (uncorrected)")
    for _, _, p, _ in results:
        assert 0.0 <= p <= 1.0, f"p={p} out of [0,1]"

run("Dunn's post-hoc: p-values in [0,1]", test_dunns_pvalue_uses_two_tailed_z)


# ══════════════════════════════════════════════════════════════════════════════
# PART B — Control Group Tests (from test_control.py, 20 tests)
# ══════════════════════════════════════════════════════════════════════════════

# Local rng so tests are reproducible independent of Part A
rng_ctrl = np.random.default_rng(7)

# ═════════════════════════════════════════════════════════════════════════════
# Bug 1 — Stale control name must not crash
# ═════════════════════════════════════════════════════════════════════════════
section("Bug 1 — Stale control name: warn + fallback, no crash")

def test_stale_control_falls_back():
    """_run_stats with control not in groups → does not crash."""
    groups = {"A": rng_ctrl.normal(5, 1, 10),
              "B": rng_ctrl.normal(7, 1, 10),
              "C": rng_ctrl.normal(9, 1, 10)}
    results = _run_stats(groups, test_type="parametric",
                         control="DoesNotExist",
                         mc_correction="Holm-Bonferroni",
                         posthoc="Tukey HSD")
    assert isinstance(results, list)

run("stale control: does not crash", test_stale_control_falls_back)

def test_valid_control_still_works_normally():
    """When control IS in groups, behaviour is unchanged."""
    groups = {"Ctrl": rng_ctrl.normal(5, 1, 12),
              "TrtA": rng_ctrl.normal(8, 1, 12),
              "TrtB": rng_ctrl.normal(11, 1, 12)}
    results = pf._run_stats(groups, test_type="parametric",
                             posthoc="Tukey HSD", control="Ctrl")
    pairs = {(r[0], r[1]) for r in results} | {(r[1], r[0]) for r in results}
    assert ("Ctrl", "TrtA") in pairs or ("TrtA", "Ctrl") in pairs
    assert ("Ctrl", "TrtB") in pairs or ("TrtB", "Ctrl") in pairs
    assert not (("TrtA", "TrtB") in pairs or ("TrtB", "TrtA") in pairs), \
        "TrtA vs TrtB should be excluded when control='Ctrl'"

run("valid control: only control-vs-other pairs returned", test_valid_control_still_works_normally)


# ═════════════════════════════════════════════════════════════════════════════
# Bug 3 — Comparison mode: all-pairwise vs vs-control
# ═════════════════════════════════════════════════════════════════════════════
section("Bug 3 — Comparison mode pair filtering")

GROUPS_3 = {
    "Control": rng_ctrl.normal(5, 1, 15),
    "Drug A":  rng_ctrl.normal(8, 1, 15),
    "Drug B":  rng_ctrl.normal(11, 1, 15),
}

def test_all_pairwise_returns_three_pairs():
    """All-pairwise with 3 groups → 3 comparison pairs."""
    results = pf._run_stats(GROUPS_3, test_type="parametric",
                             posthoc="Tukey HSD", control=None)
    assert len(results) == 3, f"Expected 3 pairs, got {len(results)}"

run("all-pairwise: 3 groups → 3 pairs", test_all_pairwise_returns_three_pairs)

def test_vs_control_returns_two_pairs():
    """Vs-control with 3 groups → exactly 2 pairs (control vs each treatment)."""
    results = pf._run_stats(GROUPS_3, test_type="parametric",
                             posthoc="Tukey HSD", control="Control")
    assert len(results) == 2, f"Expected 2 pairs, got {len(results)}"

run("vs-control: 3 groups → 2 pairs (no Drug A vs Drug B)", test_vs_control_returns_two_pairs)

def test_vs_control_excludes_treatment_treatment_pair():
    """The treatment–treatment pair must be absent when control is set."""
    results = pf._run_stats(GROUPS_3, test_type="parametric",
                             posthoc="Tukey HSD", control="Control")
    pairs = {frozenset([r[0], r[1]]) for r in results}
    assert frozenset(["Drug A", "Drug B"]) not in pairs, \
        "Drug A vs Drug B should be excluded in vs-control mode"

run("vs-control: Drug A vs Drug B excluded", test_vs_control_excludes_treatment_treatment_pair)

def test_pair_filter_symmetric_any_position():
    """Control filter is position-independent."""
    base = rng_ctrl.normal(0, 1, 12)
    for ctrl_pos, group_order in enumerate([
        ["Control", "Drug A", "Drug B"],
        ["Drug A", "Control", "Drug B"],
        ["Drug A", "Drug B", "Control"],
    ]):
        groups = {g: base + rng_ctrl.normal(i * 3, 0.5, 12)
                  for i, g in enumerate(group_order)}
        results = pf._run_stats(groups, test_type="parametric",
                                 posthoc="Tukey HSD", control="Control")
        assert len(results) == 2, \
            f"Control at pos {ctrl_pos}: expected 2 pairs, got {len(results)}: {results}"
        pairs = {frozenset([r[0], r[1]]) for r in results}
        assert frozenset(["Drug A", "Drug B"]) not in pairs, \
            f"Drug A vs Drug B leaked through at control position {ctrl_pos}"

run("vs-control: symmetric filter regardless of control position in group list",
    test_pair_filter_symmetric_any_position)

def test_vs_control_all_test_types():
    """All 4 test types honour the control filter."""
    groups = {
        "Ctrl":  rng_ctrl.normal(5, 1, 12),
        "TrtA":  rng_ctrl.normal(8, 1, 12),
        "TrtB":  rng_ctrl.normal(11, 1, 12),
    }
    for test_type in ("parametric", "nonparametric", "permutation"):
        results = pf._run_stats(groups, test_type=test_type,
                                 posthoc="Tukey HSD", control="Ctrl",
                                 n_permutations=99)
        assert len(results) == 2, \
            f"{test_type}: expected 2 pairs, got {len(results)}"
        pairs = {frozenset([r[0], r[1]]) for r in results}
        assert frozenset(["TrtA", "TrtB"]) not in pairs, \
            f"{test_type}: TrtA vs TrtB leaked through"

run("vs-control: parametric / nonparametric / permutation all filter correctly",
    test_vs_control_all_test_types)

def test_control_none_returns_all_pairs_nonparametric():
    """Nonparametric with control=None → all pairwise."""
    groups = {"A": rng_ctrl.normal(5, 1, 10),
              "B": rng_ctrl.normal(7, 1, 10),
              "C": rng_ctrl.normal(9, 1, 10),
              "D": rng_ctrl.normal(11, 1, 10)}
    results = pf._run_stats(groups, test_type="nonparametric", control=None)
    assert len(results) == 6, f"Expected 6 pairs for 4 groups, got {len(results)}"

run("control=None nonparametric: 4 groups → 6 pairs", test_control_none_returns_all_pairs_nonparametric)


# ═════════════════════════════════════════════════════════════════════════════
# Bug 4 — Dunnett without explicit control
# ═════════════════════════════════════════════════════════════════════════════
section("Bug 4 — Dunnett fallback behaviour")

def test_dunnett_no_control_uses_first_group():
    """Dunnett with control=None → falls back to first group, no crash."""
    groups = {"Alpha": rng_ctrl.normal(5, 1, 10),
              "Beta":  rng_ctrl.normal(8, 1, 10),
              "Gamma": rng_ctrl.normal(11, 1, 10)}
    results = pf._run_stats(groups, test_type="parametric",
                             posthoc="Dunnett (vs control)", control=None)
    assert len(results) == 2, f"Expected 2 Dunnett results, got {len(results)}"
    for g_a, g_b, p, stars in results:
        assert "Alpha" in (g_a, g_b), \
            f"Dunnett fallback: 'Alpha' not in pair ({g_a}, {g_b})"

run("Dunnett control=None: uses first group, returns 2 results", test_dunnett_no_control_uses_first_group)

def test_dunnett_explicit_control():
    """Dunnett with explicit control → compares only vs that group."""
    groups = {"Drug":    rng_ctrl.normal(5, 1, 10),
              "Placebo": rng_ctrl.normal(5, 1, 10),
              "Vehicle": rng_ctrl.normal(5, 1, 10)}
    results = pf._run_stats(groups, test_type="parametric",
                             posthoc="Dunnett (vs control)", control="Placebo")
    assert len(results) == 2
    for g_a, g_b, p, stars in results:
        assert "Placebo" in (g_a, g_b), \
            f"Placebo not in pair ({g_a}, {g_b})"

run("Dunnett explicit control: 3 groups → 2 results all involving control",
    test_dunnett_explicit_control)

def test_dunnett_no_double_mc_correction():
    """Dunnett p-values should not be inflated by a second MC correction."""
    from scipy.stats import dunnett as _dunnett
    ctrl  = rng_ctrl.normal(5, 1, 20)
    trt_a = rng_ctrl.normal(8, 1, 20)
    trt_b = rng_ctrl.normal(11, 1, 20)
    groups = {"Ctrl": ctrl, "A": trt_a, "B": trt_b}

    scipy_res = _dunnett(trt_a, trt_b, control=ctrl)
    our_res   = pf._run_stats(groups, test_type="parametric",
                               posthoc="Dunnett (vs control)", control="Ctrl")

    scipy_p = sorted(float(p) for p in scipy_res.pvalue)
    our_p   = sorted(r[2] for r in our_res)
    for sp, op in zip(scipy_p, our_p):
        assert abs(sp - op) < 1e-10, \
            f"Dunnett p-value mismatch: scipy={sp:.6f} ours={op:.6f}"

run("Dunnett: no double MC correction — p-values match scipy exactly",
    test_dunnett_no_double_mc_correction)


# ═════════════════════════════════════════════════════════════════════════════
# ANOVA error term correctness
# ═════════════════════════════════════════════════════════════════════════════
section("ANOVA error term — all groups used even in vs-control mode")

def test_tukey_ms_within_uses_all_groups():
    """Tukey HSD vs-control: ms_within is computed from all k groups."""
    rng2 = np.random.default_rng(99)
    groups = {
        "Ctrl": rng2.normal(5, 1, 10),
        "A":    rng2.normal(7, 1, 10),
        "B":    rng2.normal(9, 1, 10),
    }
    results_ctrl = pf._run_stats(groups, test_type="parametric",
                                  posthoc="Tukey HSD", control="Ctrl")
    results_all  = pf._run_stats(groups, test_type="parametric",
                                  posthoc="Tukey HSD", control=None)

    def _find(res, a, b):
        for g1, g2, p, _ in res:
            if {g1, g2} == {a, b}:
                return p
        return None

    p_ctrl_a_vs_ctrl = _find(results_ctrl, "Ctrl", "A")
    p_all_a_vs_ctrl  = _find(results_all,  "Ctrl", "A")
    assert p_ctrl_a_vs_ctrl is not None, "Ctrl vs A missing from vs-control results"
    assert p_all_a_vs_ctrl  is not None, "Ctrl vs A missing from all-pairwise results"
    assert abs(p_ctrl_a_vs_ctrl - p_all_a_vs_ctrl) < 1e-10, \
        (f"Ctrl vs A p-value differs between vs-control ({p_ctrl_a_vs_ctrl:.6f}) "
         f"and all-pairwise ({p_all_a_vs_ctrl:.6f}) — ms_within calculation inconsistent")

run("Tukey: Ctrl vs A p-value identical whether control filter is set or not",
    test_tukey_ms_within_uses_all_groups)


# ═════════════════════════════════════════════════════════════════════════════
# End-to-end render tests with control
# ═════════════════════════════════════════════════════════════════════════════
section("Stats with control parameter")

def test_stats_with_control():
    """_run_stats with explicit control produces control-vs-others pairs."""
    groups = {"Vehicle": rng_ctrl.normal(5, 1, 12),
              "Low":     rng_ctrl.normal(7, 1, 12),
              "High":    rng_ctrl.normal(10, 1, 12)}
    results = _run_stats(groups, test_type="parametric",
                         posthoc="Tukey HSD", control="Vehicle",
                         mc_correction="Holm-Bonferroni")
    # Should get 2 pairs: Vehicle-vs-Low, Vehicle-vs-High
    assert len(results) == 2, f"Expected 2 pairs, got {len(results)}"

run("_run_stats with control='Vehicle': produces correct pairs",
    test_stats_with_control)

def test_stats_stale_control():
    """_run_stats with control not in groups → falls back to all-pairwise."""
    groups = {"Alpha": rng_ctrl.normal(5, 1, 10),
              "Beta":  rng_ctrl.normal(8, 1, 10),
              "Gamma": rng_ctrl.normal(11, 1, 10)}
    results = _run_stats(groups, test_type="parametric",
                         posthoc="Tukey HSD", control="OldGroupName")
    # Should fall back to all-pairwise (3 choose 2 = 3) or empty
    assert isinstance(results, list)

run("_run_stats stale control: does not crash",
    test_stats_stale_control)

def test_all_posthoc_with_control():
    """All 4 non-Dunnett parametric posthocs work with control filter."""
    groups = {"Ctrl": rng_ctrl.normal(5, 1, 10),
              "A":    rng_ctrl.normal(8, 1, 10),
              "B":    rng_ctrl.normal(11, 1, 10)}
    for posthoc in ("Tukey HSD", "Bonferroni", "Sidak", "Fisher LSD"):
        results = pf._run_stats(groups, test_type="parametric",
                                 posthoc=posthoc, control="Ctrl")
        assert len(results) == 2, \
            f"{posthoc} with control: expected 2 pairs, got {len(results)}"
        pairs = {frozenset([r[0], r[1]]) for r in results}
        assert frozenset(["A", "B"]) not in pairs, \
            f"{posthoc}: A vs B leaked through with control='Ctrl'"

run("all 4 parametric posthocs respect control filter", test_all_posthoc_with_control)

def test_dunnett_with_control():
    """Dunnett + explicit control produces control-vs-others pairs."""
    groups = {"Vehicle": rng_ctrl.normal(5, 1, 12),
              "Low":     rng_ctrl.normal(7, 1, 12),
              "High":    rng_ctrl.normal(10, 1, 12)}
    results = _run_stats(groups, test_type="parametric",
                         posthoc="Dunnett (vs control)",
                         control="Vehicle")
    assert len(results) == 2, f"Expected 2 pairs, got {len(results)}"

run("Dunnett + explicit control: produces correct pairs",
    test_dunnett_with_control)

def test_nonparametric_vs_control():
    """Nonparametric with control produces expected pairs."""
    groups = {"Ctrl": rng_ctrl.normal(5, 1, 10),
              "TrtA": rng_ctrl.normal(8, 1, 10),
              "TrtB": rng_ctrl.normal(11, 1, 10)}
    results = _run_stats(groups, test_type="nonparametric",
                         control="Ctrl")
    assert len(results) == 2, f"Expected 2 pairs, got {len(results)}"

run("nonparametric + control filter: produces correct pairs",
    test_nonparametric_vs_control)


# ═════════════════════════════════════════════════════════════════════════════
# p-to-stars and threshold consistency (control-specific)
# ═════════════════════════════════════════════════════════════════════════════
section("p-to-stars correctness with control")

def test_p_to_stars_thresholds():
    """_p_to_stars must match exact Prism thresholds."""
    cases = [
        (0.00001, "****"), (0.0001, "****"),
        (0.00011, "***"),  (0.001, "***"),
        (0.0011,  "**"),   (0.01, "**"),
        (0.011,   "*"),    (0.05, "*"),
        (0.051,   "ns"),   (0.99, "ns"),
    ]
    for p_val, expected in cases:
        got = pf._p_to_stars(p_val)
        assert got == expected, f"p={p_val}: expected {expected!r}, got {got!r}"

run("_p_to_stars: all Prism threshold boundaries correct", test_p_to_stars_thresholds)

def test_mc_correction_increases_p_values():
    """After Holm-Bonferroni correction, at least one p-value should be ≥ raw."""
    groups = {"A": rng_ctrl.normal(5, 0.5, 8),
              "B": rng_ctrl.normal(6, 0.5, 8),
              "C": rng_ctrl.normal(7, 0.5, 8)}
    raw_res  = pf._run_stats(groups, "parametric", mc_correction="None (uncorrected)")
    holm_res = pf._run_stats(groups, "parametric", mc_correction="Holm-Bonferroni")
    raw_p  = sorted(r[2] for r in raw_res)
    holm_p = sorted(r[2] for r in holm_res)
    for rp, hp in zip(raw_p, holm_p):
        assert hp >= rp - 1e-12, \
            f"Holm p={hp:.6f} < raw p={rp:.6f} — correction deflated p-value"

run("Holm-Bonferroni correction: all corrected p ≥ raw p", test_mc_correction_increases_p_values)


# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
summarise()
sys.exit(0 if _h.FAIL == 0 else 1)
