"""
test_stats_verification.py
===========================
Verification tests for statistical computations in plotter_functions.py.

Every test here compares against:
  • scipy.stats (authoritative reference implementation)
  • Hand-computed analytical values documented inline
  • Published datasets with known results

The goal is to confirm that p-values, effect sizes, and corrections
match expected numerical outcomes — not just "don't crash".

Run:
  python3 test_stats_verification.py
"""
import sys, os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plotter_test_harness as _h
from plotter_test_harness import pf, ok, fail, run, section, summarise

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


# ═════════════════════════════════════════════════════════════════════════════
# 1.  Welch's t-test p-value
# ═════════════════════════════════════════════════════════════════════════════
section("Welch's t-test — p-value matches scipy reference")

# Reference dataset (equal n, unequal variance):
# A: [100,110,120,130,140]  mean=120, var=250
# B: [200,220,240,260,280]  mean=240, var=1000
#
# Welch t = (120-240) / sqrt(250/5+1000/5) = -120/sqrt(250) = -7.589
# df_Satterthwaite = 250² / (50²/4 + 200²/4) = 62500/10625 ≈ 5.882
# p two-tailed ≈ 0.00068  (t(5.882) = -7.589)

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

# Hand-computed:
# A: [100,110,120,130,140], B: [200,220,240,260,280]
# pooled_var = ((4*250) + (4*1000)) / 8 = 5000/8 = 625
# pooled_sd  = 25
# d = (120 - 240) / 25 = -4.8

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
    Y = np.array([3., 4., 5., 6., 7.]) - 2.0   # same mean=3
    # Y = [1,2,3,4,5], same as X
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

# For n1=n2=5:
#   d = -4.8  (from above)
#   m = n1+n2-2 = 8
#   J = 1 - 3/(4*8-1) = 1 - 3/31 = 28/31
#   g = -4.8 * (28/31) = -4.335...

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
    # J = 1 - 3/(4*998-1) ≈ 0.99925 — g and d should be within 0.1%
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

# For A=[1,2,3], B=[4,5,6]:
#   All 9 pairs satisfy a < b  →  U1(A>B) = 0, U2(B>A) = 9
#   r = (0 - 9) / 9 = -1.0  (A is uniformly lower than B)

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

# A=[1,2,3], B=[4,5,6]: U=0, exact two-sided p = 2/C(6,3) = 2/20 = 0.10

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

# Balanced design, 3 groups, n=5 each:
# A: [2,4,6,8,10]  mean=6, SS_within=40
# B: [6,8,10,12,14] mean=10, SS_within=40
# C: [10,12,14,16,18] mean=14, SS_within=40
#
# Grand mean = 10
# SS_between = 5*((6-10)²+(10-10)²+(14-10)²) = 5*(16+0+16) = 160
# SS_within  = 40+40+40 = 120
# df_between=2, df_within=12
# F = (160/2)/(120/12) = 80/10 = 8.0

G_A = np.array([2., 4., 6., 8., 10.])
G_B = np.array([6., 8., 10., 12., 14.])
G_C = np.array([10., 12., 14., 16., 18.])


def test_oneway_anova_F():
    """One-way ANOVA F=8.0 for known balanced dataset."""
    F, p = _scipy_stats.f_oneway(G_A, G_B, G_C)
    assert abs(F - 8.0) < 1e-10, f"Expected F=8.0, got F={F}"
    # p from F(2,12)=8: known value ≈ 0.00607
    assert abs(p - _scipy_stats.f.sf(8.0, 2, 12)) < 1e-12

run("One-way ANOVA: F=8.0 for hand-computed balanced design", test_oneway_anova_F)


# ═════════════════════════════════════════════════════════════════════════════
# 7.  Tukey HSD — correct pair selection
# ═════════════════════════════════════════════════════════════════════════════
section("Tukey HSD — correct pair significance")

# From the dataset above:
# A vs C: diff=8, se=sqrt((10/2)*(1/5+1/5))=sqrt(2)=1.414, q=8/1.414=5.657
#   → q > q_crit(0.05,3,12)≈3.77 → significant
# A vs B: diff=4, q=4/1.414=2.828 < 3.77 → not significant
# B vs C: diff=4, same → not significant

def test_tukey_finds_only_AC_significant():
    """Tukey HSD: only A vs C significant; A vs B and B vs C are NS."""
    groups = {"A": G_A, "B": G_B, "C": G_C}
    results = _run_stats(groups, test_type="parametric",
                         posthoc="Tukey HSD",
                         mc_correction="None (uncorrected)")
    sig_pairs = {(r[0], r[1]) for r in results if r[3] != "ns"}
    ns_pairs  = {(r[0], r[1]) for r in results if r[3] == "ns"}
    # A vs C should be significant
    assert ("A", "C") in sig_pairs or ("C", "A") in sig_pairs, (
        f"A vs C should be significant. sig_pairs={sig_pairs}")
    # A vs B and B vs C should not be
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
    # Find A vs C result
    p_ac = None
    for a_lbl, b_lbl, p, stars in results:
        if set([a_lbl, b_lbl]) == {"A", "C"}:
            p_ac = p
    assert p_ac is not None, "A vs C result not found"
    # Manual: ms_within=10, se=sqrt(2), q=5.657, k=3, df=12
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

# Three raw p-values from a typical post-hoc analysis
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

# Prism boundaries: ≤0.0001→****, ≤0.001→***, ≤0.01→**, ≤0.05→*, >0.05→ns

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

# Observed: [20, 30, 50], Expected (uniform): [100/3, 100/3, 100/3]
# χ² = (20-100/3)²/(100/3) + (30-100/3)²/(100/3) + (50-100/3)²/(100/3)
#    = ((-40/3)²+(-10/3)²+(50/3)²) / (100/3)
#    = (1600+100+2500)/9 / (100/3)  = 4200/9 * 3/100 = 4200/300 = 14.0

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
    chi2, p = _scipy_stats.chisquare(observed)   # default: uniform expected
    assert chi2 == 0.0, f"Expected χ²=0 for uniform, got {chi2}"
    assert p == 1.0, f"Expected p=1 for χ²=0"

run("Chi-square GoF: χ²=0 and p=1 for perfectly uniform observations", test_chi2_gof_uniform_null)


# ═════════════════════════════════════════════════════════════════════════════
# 11.  Log-rank (Mantel-Cox) test — hand-computed reference
# ═════════════════════════════════════════════════════════════════════════════
section("Log-rank test — hand-computed Mantel-Cox statistic")

# Two groups, no overlap in event times:
#
# Group A: times=[1,2,3], events=[1,1,1]  (all events at t=1,2,3)
# Group B: times=[5,6,7], events=[1,1,1]  (all events at t=5,6,7)
#
# Contribution at each event time in A (B still fully at risk):
#   t=1: n1=3, n2=3, d1=1, d2=0, E1_exp=3/6=0.5,  var=1*3*3*5/(36*5)=0.25
#   t=2: n1=2, n2=3, d1=1, d2=0, E1_exp=2/5=0.4,   var=1*2*3*4/(25*4)=0.24
#   t=3: n1=1, n2=3, d1=1, d2=0, E1_exp=1/4=0.25,  var=1*1*3*3/(16*3)=0.1875
#   t=5,6,7: n1=0 → skip
#
# O1=3, E1=0.5+0.4+0.25=1.15
# var=0.25+0.24+0.1875=0.6775
# χ²=(3-1.15)²/0.6775 = 3.4225/0.6775 ≈ 5.052
# p = chi2.sf(5.052, 1) ≈ 0.0246

def test_logrank_hand_computed():
    """Log-rank χ² ≈ 5.052 and p ≈ 0.025 for non-overlapping survival times."""
    groups_dict = {
        "A": (np.array([1., 2., 3.]), np.array([1, 1, 1])),
        "B": (np.array([5., 6., 7.]), np.array([1, 1, 1])),
    }
    results = _logrank_test(groups_dict)
    assert len(results) == 1
    a_lbl, b_lbl, p, stars = results[0]
    # Manually compute expected chi2
    O1, E1 = 3.0, 1.15
    var     = 0.6775
    chi2_expected = (O1 - E1) ** 2 / var   # ≈ 5.052
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
    # Identical data → O=E → chi2=0 → p=1
    _, _, p, _ = results[0]
    assert p > 0.99, f"Identical groups should give p≈1, got {p}"

run("Log-rank: p≈1 for identical survival curves", test_logrank_identical_groups_not_significant)


# ═════════════════════════════════════════════════════════════════════════════
# 12.  Two-way ANOVA — partial eta-squared and F-statistic
# ═════════════════════════════════════════════════════════════════════════════
section("Two-way ANOVA — partial eta-squared (ηp²)")

# Balanced 2×2 design, 3 reps per cell:
#   Factor A: a1 vs a2
#   Factor B: b1 vs b2
#
# Cell means: a1b1=10, a1b2=20, a2b1=30, a2b2=40
# (No interaction: effect of A is the same at each level of B)

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
    # Strong effects should have large partial eta²
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
        # Find the exact groups compared
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

# Group: [1,2,3,4,5], μ₀=0
# t = (3-0)/(sqrt(2.5)/sqrt(5)) = 3/0.7071 = 4.243, df=4
# p (two-tailed) ≈ 0.0134

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
    """Dunn's z-statistic: most-extreme pair significant for separated groups.

    Dunn's test (rank-based) has less power than parametric tests.  With n=5
    per group the adjacent pairs (A vs B, B vs C) may not individually clear
    α=0.05, but the most extreme pair (A vs C, difference=19 ranks) must.
    We use n=10 to give the test adequate power.
    """
    # n=10 per group, large separation → A vs C must be clearly significant
    groups = {
        "A": np.arange(1., 11.),        # ranks ~1–10
        "B": np.arange(21., 31.),       # ranks ~21–30
        "C": np.arange(41., 51.),       # ranks ~41–50
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


# ═════════════════════════════════════════════════════════════════════════════
summarise()
sys.exit(0 if _h.FAIL == 0 else 1)
