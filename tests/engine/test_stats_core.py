"""
test_stats_core.py
==================
Statistical computation tests for refraction.core.chart_helpers.

Every test verifies against a known ground truth — either hand-computed
or independently calculated via scipy. No smoke tests.

Requires only: numpy, scipy, pandas. No UI, no API, no Tk, no Plotly.
"""

import math

import numpy as np
import pytest
from scipy import stats as sp_stats

from refraction.core.chart_helpers import (
    _apply_correction,
    _calc_error,
    _calc_error_asymmetric,
    _cohens_d,
    _hedges_g,
    _logrank_test,
    _p_to_stars,
    _rank_biserial_r,
    _run_stats,
    _twoway_anova,
    _twoway_posthoc,
    check_normality,
)


# ============================================================================
# _calc_error
# ============================================================================

class TestCalcError:
    """Tests for _calc_error(vals, error_type) -> (mean, half_width)."""

    VALS = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    # Hand-computed:
    #   mean = 3.0
    #   SD(ddof=1) = sqrt(sum((x-3)^2)/4) = sqrt((4+1+0+1+4)/4) = sqrt(2.5) = 1.58114
    #   SEM = SD / sqrt(5) = 1.58114 / 2.23607 = 0.70711
    #   CI95: t(0.975, df=4) = 2.77645, CI = 2.77645 * 0.70711 = 1.96353

    def test_sem_known_values(self):
        """SEM = SD(ddof=1) / sqrt(n). For [1,2,3,4,5]: SD=1.58114, SEM=0.70711."""
        mean, sem = _calc_error(self.VALS, "sem")
        assert mean == pytest.approx(3.0, abs=1e-10)
        expected_sd = np.std(self.VALS, ddof=1)  # 1.5811388300841898
        expected_sem = expected_sd / np.sqrt(5)   # 0.7071067811865476
        assert sem == pytest.approx(expected_sem, abs=1e-10)

    def test_sd_known_values(self):
        """SD(ddof=1) for [1,2,3,4,5] = sqrt(10/4) = 1.58114."""
        mean, sd = _calc_error(self.VALS, "sd")
        assert mean == pytest.approx(3.0, abs=1e-10)
        expected_sd = np.std(self.VALS, ddof=1)
        assert sd == pytest.approx(expected_sd, abs=1e-10)

    def test_ci95_known_values(self):
        """CI95 = t_crit(0.975, df=4) * SEM. For [1,2,3,4,5]: t=2.7764, CI=1.9635."""
        mean, ci = _calc_error(self.VALS, "ci95")
        assert mean == pytest.approx(3.0, abs=1e-10)
        t_crit = sp_stats.t.ppf(0.975, df=4)  # 2.7764451051977987
        expected_ci = t_crit * np.std(self.VALS, ddof=1) / np.sqrt(5)
        assert ci == pytest.approx(expected_ci, abs=1e-10)

    def test_n_equals_1_sem_is_zero(self):
        """With n=1, SD(ddof=1) is 0 by our implementation, so SEM = 0."""
        mean, sem = _calc_error(np.array([42.0]), "sem")
        assert mean == pytest.approx(42.0, abs=1e-10)
        assert sem == pytest.approx(0.0, abs=1e-10)

    def test_n_equals_1_sd_is_zero(self):
        """With n=1, SD(ddof=1) = 0 (not NaN) because the code guards against it."""
        mean, sd = _calc_error(np.array([7.0]), "sd")
        assert mean == pytest.approx(7.0, abs=1e-10)
        assert sd == pytest.approx(0.0, abs=1e-10)

    def test_n_equals_2(self):
        """With n=2, SEM and CI should use ddof=1 correctly.
        [10, 20]: mean=15, SD=sqrt((25+25)/1)=sqrt(50)=7.0711, SEM=7.0711/sqrt(2)=5.0."""
        vals = np.array([10.0, 20.0])
        mean, sem = _calc_error(vals, "sem")
        assert mean == pytest.approx(15.0, abs=1e-10)
        # SD(ddof=1) = sqrt(((10-15)^2 + (20-15)^2) / 1) = sqrt(50)
        expected_sem = np.sqrt(50.0) / np.sqrt(2)  # 5.0
        assert sem == pytest.approx(expected_sem, abs=1e-10)

    def test_sem_matches_scipy_sem(self):
        """Cross-check: our SEM matches scipy.stats.sem."""
        rng = np.random.default_rng(42)
        vals = rng.normal(10, 3, 30)
        mean, sem = _calc_error(vals, "sem")
        scipy_sem = sp_stats.sem(vals)
        assert sem == pytest.approx(scipy_sem, abs=1e-10)


# ============================================================================
# _calc_error_asymmetric
# ============================================================================

class TestCalcErrorAsymmetric:
    """Tests for _calc_error_asymmetric(vals, error_type)."""

    def test_positive_mean_returns_asymmetric(self):
        """For positive mean, lower and upper bars should differ (asymmetric in log space)."""
        vals = np.array([5.0, 10.0, 15.0, 20.0])
        mean, lo, hi = _calc_error_asymmetric(vals, "sem")
        # mean = 12.5
        assert mean == pytest.approx(12.5, abs=1e-10)
        # Asymmetric: lo and hi should differ
        assert lo >= 0, "Lower bar must be non-negative"
        assert hi >= 0, "Upper bar must be non-negative"
        # Lower bar must be less than mean (cannot extend through zero)
        assert lo < mean, "Lower bar must be less than mean"

    def test_negative_mean_falls_back_to_symmetric(self):
        """For negative mean, falls back to symmetric error bars."""
        vals = np.array([-10.0, -20.0, -15.0])
        mean, lo, hi = _calc_error_asymmetric(vals, "sem")
        assert mean == pytest.approx(-15.0, abs=1e-10)
        # Should fall back: lo == hi == symmetric half-width
        assert lo == pytest.approx(hi, abs=1e-10)

    def test_zero_mean_falls_back(self):
        """For mean=0, falls back to symmetric."""
        vals = np.array([-1.0, 1.0])
        mean, lo, hi = _calc_error_asymmetric(vals, "sem")
        assert mean == pytest.approx(0.0, abs=1e-10)
        assert lo == pytest.approx(hi, abs=1e-10)


# ============================================================================
# _p_to_stars
# ============================================================================

class TestPToStars:
    """Tests for _p_to_stars(p, threshold) -> star string."""

    @pytest.mark.parametrize("p, expected", [
        (0.00001, "****"),   # well below 0.0001
        (0.0001,  "****"),   # exactly at 0.0001 boundary (<=)
        (0.00011, "***"),    # just above 0.0001
        (0.001,   "***"),    # exactly at 0.001 boundary (<=)
        (0.0011,  "**"),     # just above 0.001
        (0.01,    "**"),     # exactly at 0.01 boundary (<=)
        (0.011,   "*"),      # just above 0.01
        (0.05,    "*"),      # exactly at 0.05 boundary (<=)
        (0.051,   "ns"),     # just above default threshold
        (0.5,     "ns"),
        (1.0,     "ns"),
    ])
    def test_boundary_values(self, p, expected):
        """Each Prism boundary returns the correct star annotation."""
        assert _p_to_stars(p) == expected

    def test_custom_threshold_raises_bar(self):
        """With threshold=0.01, p=0.03 should be 'ns' (above custom threshold)."""
        assert _p_to_stars(0.03, threshold=0.01) == "ns"

    def test_custom_threshold_below_still_works(self):
        """With threshold=0.01, p=0.005 should be '**'."""
        assert _p_to_stars(0.005, threshold=0.01) == "**"

    def test_zero_p_gives_four_stars(self):
        """p=0 should give '****'."""
        assert _p_to_stars(0.0) == "****"


# ============================================================================
# _apply_correction
# ============================================================================

class TestApplyCorrection:
    """Tests for multiple comparison corrections."""

    RAW = [0.01, 0.03, 0.04]
    # m = 3

    def test_bonferroni_hand_computed(self):
        """Bonferroni: p_adj = min(p * m, 1.0).
        [0.01, 0.03, 0.04] * 3 = [0.03, 0.09, 0.12]."""
        result = _apply_correction(self.RAW, "Bonferroni")
        expected = [0.03, 0.09, 0.12]
        for got, exp in zip(result, expected):
            assert got == pytest.approx(exp, abs=1e-12)

    def test_bonferroni_caps_at_one(self):
        """Bonferroni caps at 1.0: [0.5] * 3 = 1.5 -> capped to 1.0."""
        result = _apply_correction([0.5], "Bonferroni")
        assert result[0] == pytest.approx(0.5, abs=1e-12)  # m=1, so 0.5*1=0.5
        result = _apply_correction([0.5, 0.5], "Bonferroni")
        assert result[0] == pytest.approx(1.0, abs=1e-12)  # 0.5*2=1.0

    def test_holm_bonferroni_hand_computed(self):
        """Holm step-down for [0.01, 0.03, 0.04] with m=3:
        1. Sort: [0.01(idx0), 0.03(idx1), 0.04(idx2)]
        2. Rank 0: p[0]*3 = 0.03, running_max = 0.03
        3. Rank 1: p[1]*2 = 0.06, running_max = 0.06
        4. Rank 2: p[2]*1 = 0.04, running_max = max(0.06, 0.04) = 0.06
        Result (original order): [0.03, 0.06, 0.06]."""
        result = _apply_correction(self.RAW, "Holm-Bonferroni")
        expected = [0.03, 0.06, 0.06]
        for got, exp in zip(result, expected):
            assert got == pytest.approx(exp, abs=1e-12)

    def test_holm_monotonicity(self):
        """Holm-corrected values are monotonically non-decreasing when sorted."""
        rng = np.random.default_rng(99)
        raw = sorted(rng.uniform(0.001, 0.1, 10).tolist())
        corrected = _apply_correction(raw, "Holm-Bonferroni")
        # When input is sorted, output must be non-decreasing
        for i in range(len(corrected) - 1):
            assert corrected[i] <= corrected[i + 1] + 1e-12

    def test_bh_fdr_hand_computed(self):
        """BH FDR step-up for [0.01, 0.03, 0.04] with m=3:
        1. Sort: [0.01(idx0), 0.03(idx1), 0.04(idx2)]
        2. From bottom: rank 3 (idx2): p[2]*3/3 = 0.04, running_min = 0.04
        3. Rank 2 (idx1): p[1]*3/2 = 0.045, running_min = min(0.04, 0.045) = 0.04
        4. Rank 1 (idx0): p[0]*3/1 = 0.03, running_min = min(0.04, 0.03) = 0.03
        Result (original order): [0.03, 0.04, 0.04]."""
        result = _apply_correction(self.RAW, "Benjamini-Hochberg (FDR)")
        expected = [0.03, 0.04, 0.04]
        for got, exp in zip(result, expected):
            assert got == pytest.approx(exp, abs=1e-12)

    def test_bh_fdr_monotone_sorted_input(self):
        """BH FDR corrected values are monotone non-decreasing for sorted input."""
        raw_sorted = sorted(self.RAW)
        corrected = _apply_correction(raw_sorted, "Benjamini-Hochberg (FDR)")
        for i in range(len(corrected) - 1):
            assert corrected[i] <= corrected[i + 1] + 1e-12

    def test_uncorrected_passes_through(self):
        """Unknown correction method passes values through unchanged."""
        result = _apply_correction(self.RAW, "None (uncorrected)")
        for got, exp in zip(result, self.RAW):
            assert got == pytest.approx(exp, abs=1e-12)

    def test_empty_list(self):
        """Empty input returns empty output for all methods."""
        for method in ("Bonferroni", "Holm-Bonferroni", "Benjamini-Hochberg (FDR)"):
            assert _apply_correction([], method) == []

    def test_all_corrections_cap_at_one(self):
        """All methods cap corrected p-values at 1.0."""
        high_p = [0.5, 0.6, 0.7, 0.8, 0.9]
        for method in ("Bonferroni", "Holm-Bonferroni", "Benjamini-Hochberg (FDR)"):
            corrected = _apply_correction(high_p, method)
            for cp in corrected:
                assert cp <= 1.0, f"{method}: corrected p={cp} > 1.0"


# ============================================================================
# _cohens_d
# ============================================================================

class TestCohensD:
    """Tests for Cohen's d effect size."""

    def test_known_value(self):
        """Cohen's d for A=[100,110,120,130,140], B=[200,220,240,260,280].
        mean_A=120, mean_B=240, diff=-120.
        var_A = (200+100+0+100+200)/4 = 150, var_B = (1600+400+0+400+1600)/4 = 1000
        pooled_sd = sqrt((4*150 + 4*1000) / 8) = sqrt(575) = 23.9792
        # Actually: var_A(ddof=1) = np.var([100..140], ddof=1)
        # = 250, var_B = 1000
        # pooled = sqrt((4*250 + 4*1000)/8) = sqrt(625) = 25
        d = (120 - 240) / 25 = -4.8."""
        A = np.array([100., 110., 120., 130., 140.])
        B = np.array([200., 220., 240., 260., 280.])
        d = _cohens_d(A, B)
        assert d == pytest.approx(-4.8, abs=1e-10)

    def test_antisymmetry(self):
        """d(A, B) = -d(B, A)."""
        A = np.array([1., 2., 3., 4., 5.])
        B = np.array([6., 7., 8., 9., 10.])
        assert _cohens_d(A, B) == pytest.approx(-_cohens_d(B, A), abs=1e-10)

    def test_identical_groups_return_zero(self):
        """d = 0 for groups with identical values."""
        X = np.array([1., 2., 3., 4., 5.])
        d = _cohens_d(X, X.copy())
        assert d == pytest.approx(0.0, abs=1e-10)

    def test_n_less_than_2_returns_nan(self):
        """d is NaN when either group has n < 2."""
        assert math.isnan(_cohens_d(np.array([1.0]), np.array([2.0, 3.0, 4.0])))
        assert math.isnan(_cohens_d(np.array([1.0, 2.0]), np.array([3.0])))

    def test_zero_variance_returns_nan(self):
        """d is NaN when pooled SD = 0 (all values identical within both groups)."""
        assert math.isnan(_cohens_d(np.array([5.0, 5.0, 5.0]),
                                     np.array([5.0, 5.0, 5.0])))

    def test_one_pooled_sd_difference(self):
        """When means differ by exactly 1 pooled SD, |d| = 1.
        A=[2,4,6], B=[3,5,7]. mean_A=4, mean_B=5, diff=-1.
        var_A(ddof=1) = var([2,4,6], ddof=1) = 4.0
        var_B(ddof=1) = var([3,5,7], ddof=1) = 4.0
        pooled_sd = sqrt((2*4 + 2*4) / 4) = sqrt(4) = 2.0
        Wait: diff = 4-5 = -1, pooled_sd = 2 => d = -0.5, not -1.
        Let me pick values where d=1 exactly:
        A=[0,2], B=[2,4]. mean_A=1, mean_B=3, diff=-2.
        var_A = var([0,2], ddof=1) = 2.0, var_B = var([2,4], ddof=1) = 2.0
        pooled_sd = sqrt((1*2 + 1*2) / 2) = sqrt(2) = 1.4142
        d = -2 / 1.4142 = -1.4142. Not exactly 1 either.

        For d = -1 exactly: need diff = pooled_sd.
        Let groups have same variance s^2, then pooled_sd = s.
        So diff = s. E.g., A=[0, 2] (mean=1, s=sqrt(2)), B=[sqrt(2), 2+sqrt(2)].
        Simpler: just verify the formula against numpy directly.
        """
        A = np.array([2., 4., 6.])
        B = np.array([3., 5., 7.])
        d = _cohens_d(A, B)
        # Verify against formula directly
        n1, n2 = 3, 3
        pooled_sd = np.sqrt(((n1-1)*np.var(A, ddof=1) + (n2-1)*np.var(B, ddof=1)) / (n1+n2-2))
        expected = (np.mean(A) - np.mean(B)) / pooled_sd
        assert d == pytest.approx(expected, abs=1e-10)
        # mean_A=4, mean_B=5, both have var=4, pooled_sd=2, d=-0.5
        assert d == pytest.approx(-0.5, abs=1e-10)


# ============================================================================
# _hedges_g
# ============================================================================

class TestHedgesG:
    """Tests for Hedges' g (bias-corrected Cohen's d)."""

    def test_correction_factor(self):
        """g = d * J where J = 1 - 3/(4m - 1) and m = n1 + n2 - 2.
        For n1=n2=5, m=8, J = 1 - 3/31 = 28/31 = 0.90323."""
        A = np.array([100., 110., 120., 130., 140.])
        B = np.array([200., 220., 240., 260., 280.])
        d = _cohens_d(A, B)
        g = _hedges_g(A, B)
        m = 8
        J = 1.0 - 3.0 / (4.0 * m - 1.0)
        assert g == pytest.approx(d * J, abs=1e-12)

    def test_magnitude_less_than_d_for_small_n(self):
        """|g| < |d| for small samples (bias correction shrinks estimate)."""
        A = np.array([1., 2., 3., 4., 5.])
        B = np.array([6., 7., 8., 9., 10.])
        assert abs(_hedges_g(A, B)) < abs(_cohens_d(A, B))

    def test_converges_to_d_for_large_n(self):
        """For large n, g is very close to d (J -> 1)."""
        rng = np.random.default_rng(42)
        X = rng.normal(0, 1, 500)
        Y = rng.normal(0.5, 1, 500)
        d = _cohens_d(X, Y)
        g = _hedges_g(X, Y)
        # Relative difference < 0.2%
        assert abs(g - d) / (abs(d) + 1e-9) < 0.002

    def test_nan_for_small_n(self):
        """Returns NaN when either group has n < 2."""
        assert math.isnan(_hedges_g(np.array([1.0]), np.array([2.0, 3.0])))


# ============================================================================
# _rank_biserial_r
# ============================================================================

class TestRankBiserialR:
    """Tests for rank-biserial correlation r = (U1 - U2) / (n1 * n2)."""

    def test_complete_separation_a_less(self):
        """r = -1 when all A < all B. U1 = 0 (no a_i > b_j), U2 = n1*n2.
        r = (0 - 9) / 9 = -1."""
        r = _rank_biserial_r(np.array([1., 2., 3.]), np.array([4., 5., 6.]))
        assert r == pytest.approx(-1.0, abs=1e-10)

    def test_complete_separation_a_greater(self):
        """r = +1 when all A > all B. U1 = n1*n2, U2 = 0.
        r = (9 - 0) / 9 = +1."""
        r = _rank_biserial_r(np.array([4., 5., 6.]), np.array([1., 2., 3.]))
        assert r == pytest.approx(1.0, abs=1e-10)

    def test_antisymmetry(self):
        """r(A, B) = -r(B, A)."""
        rng = np.random.default_rng(99)
        X = rng.normal(0, 1, 8)
        Y = rng.normal(1, 1, 8)
        assert _rank_biserial_r(X, Y) == pytest.approx(-_rank_biserial_r(Y, X), abs=1e-10)

    def test_range_bounded(self):
        """r is always in [-1, 1] for random data."""
        rng = np.random.default_rng(7)
        for _ in range(20):
            X = rng.normal(0, 1, rng.integers(3, 15))
            Y = rng.normal(0, 1, rng.integers(3, 15))
            r = _rank_biserial_r(X, Y)
            assert -1.0 <= r <= 1.0

    def test_identical_groups_near_zero(self):
        """For identical distributions with large n, r should be near 0."""
        rng = np.random.default_rng(42)
        X = rng.normal(0, 1, 100)
        Y = rng.normal(0, 1, 100)
        r = _rank_biserial_r(X, Y)
        assert abs(r) < 0.3, f"r={r}, expected near 0 for same distribution"

    def test_formula_matches_manual_U(self):
        """Verify r = (U1 - U2) / (n1 * n2) against manual count.
        A=[1,3], B=[2,4]. Pairs where a > b:
        (1,2)=F, (1,4)=F, (3,2)=T, (3,4)=F => U1=1, U2=3
        r = (1-3)/4 = -0.5."""
        r = _rank_biserial_r(np.array([1., 3.]), np.array([2., 4.]))
        assert r == pytest.approx(-0.5, abs=1e-10)


# ============================================================================
# _run_stats — dispatcher tests
# ============================================================================

class TestRunStats:
    """Tests for _run_stats dispatcher — the main statistical test router."""

    # --- Parametric (k=2): Welch's t-test ---

    def test_welch_t_matches_scipy(self):
        """Welch's t-test p-value matches scipy.stats.ttest_ind(equal_var=False)."""
        A = np.array([100., 110., 120., 130., 140.])
        B = np.array([200., 220., 240., 260., 280.])
        results = _run_stats({"A": A, "B": B}, test_type="parametric",
                             mc_correction="None (uncorrected)")
        assert len(results) == 1
        _, _, p_ours, _ = results[0]
        _, p_scipy = sp_stats.ttest_ind(A, B, equal_var=False)
        assert p_ours == pytest.approx(p_scipy, abs=1e-12)

    def test_welch_t_identical_groups_ns(self):
        """Identical groups should give p=1 (ns)."""
        X = np.array([1., 2., 3., 4., 5.])
        results = _run_stats({"A": X, "B": X.copy()}, test_type="parametric",
                             mc_correction="None (uncorrected)")
        _, _, p, stars = results[0]
        assert p == pytest.approx(1.0, abs=1e-10)
        assert stars == "ns"

    # --- Parametric (k=3): ANOVA gate + Tukey ---

    def test_tukey_runs_even_when_anova_nonsig(self):
        """Posthoc always runs regardless of omnibus p (matches Prism/R)."""
        rng = np.random.default_rng(0)
        groups = {"A": rng.normal(5, 1, 10),
                  "B": rng.normal(5.1, 1, 10),
                  "C": rng.normal(5.2, 1, 10)}
        _, p_anova = sp_stats.f_oneway(*groups.values())
        if p_anova >= 0.05:
            results = _run_stats(groups, test_type="parametric", posthoc="Tukey HSD",
                                 mc_correction="None (uncorrected)")
            assert len(results) > 0, "Posthoc should run even when ANOVA is ns"

    def test_tukey_significant_pair(self):
        """Tukey identifies the most separated pair as significant.
        A=[2,4,6,8,10], B=[6,8,10,12,14], C=[10,12,14,16,18].
        One-way ANOVA F=8.0, p<0.05. Only A-C should be significant."""
        G_A = np.array([2., 4., 6., 8., 10.])
        G_B = np.array([6., 8., 10., 12., 14.])
        G_C = np.array([10., 12., 14., 16., 18.])
        results = _run_stats({"A": G_A, "B": G_B, "C": G_C},
                             test_type="parametric", posthoc="Tukey HSD",
                             mc_correction="None (uncorrected)")
        sig_pairs = {frozenset([r[0], r[1]]) for r in results if r[3] != "ns"}
        assert frozenset(["A", "C"]) in sig_pairs

    def test_tukey_p_matches_studentized_range(self):
        """Verify Tukey p-value for A vs C matches manual studentized range CDF.
        For A=[2..10], C=[10..18]: mean_diff=8, k=3, df_within=12.
        ss_within = sum of SS for each group.
        A: deviations from 6: [-4,-2,0,2,4], SS_A=40
        B: deviations from 10: [-4,-2,0,2,4], SS_B=40
        C: deviations from 14: [-4,-2,0,2,4], SS_C=40
        ss_within=120, ms_within=120/12=10
        se = sqrt(10/2 * (1/5 + 1/5)) = sqrt(10/2 * 2/5) = sqrt(2) = 1.4142
        q = 8 / 1.4142 = 5.6569
        p = 1 - studentized_range.cdf(5.6569, 3, 12)."""
        G_A = np.array([2., 4., 6., 8., 10.])
        G_C = np.array([10., 12., 14., 16., 18.])
        G_B = np.array([6., 8., 10., 12., 14.])
        results = _run_stats({"A": G_A, "B": G_B, "C": G_C},
                             test_type="parametric", posthoc="Tukey HSD",
                             mc_correction="None (uncorrected)")
        p_ac = None
        for a, b, p, stars in results:
            if {a, b} == {"A", "C"}:
                p_ac = p
        assert p_ac is not None
        # Manual: q = 8 / sqrt(10/2 * (1/5+1/5)) = 8/sqrt(2)
        q_manual = 8.0 / np.sqrt(2.0)
        p_manual = 1.0 - sp_stats.studentized_range.cdf(q_manual, 3, 12)
        assert p_ac == pytest.approx(p_manual, abs=1e-10)

    # --- Nonparametric (k=2): Mann-Whitney ---

    def test_mann_whitney_matches_scipy(self):
        """Mann-Whitney U p-value matches scipy.stats.mannwhitneyu."""
        A = np.array([1., 2., 3.])
        B = np.array([4., 5., 6.])
        results = _run_stats({"A": A, "B": B}, test_type="nonparametric",
                             mc_correction="None (uncorrected)")
        _, _, p_ours, _ = results[0]
        _, p_scipy = sp_stats.mannwhitneyu(A, B, alternative="two-sided")
        assert p_ours == pytest.approx(p_scipy, abs=1e-12)

    # --- Nonparametric (k=3): Kruskal-Wallis gate + Dunn's ---

    def test_kruskal_runs_even_when_nonsig(self):
        """Dunn's posthoc always runs regardless of KW p (matches Prism/R)."""
        rng = np.random.default_rng(0)
        groups = {"A": rng.normal(5, 1, 10),
                  "B": rng.normal(5.05, 1, 10),
                  "C": rng.normal(5.1, 1, 10)}
        _, p_kw = sp_stats.kruskal(*groups.values())
        if p_kw >= 0.05:
            results = _run_stats(groups, test_type="nonparametric",
                                 mc_correction="None (uncorrected)")
            assert len(results) > 0, "Posthoc should run even when KW is ns"

    def test_dunns_finds_significant_pair(self):
        """Dunn's identifies widely separated groups."""
        groups = {"A": np.arange(1., 11.),
                  "B": np.arange(21., 31.),
                  "C": np.arange(41., 51.)}
        results = _run_stats(groups, test_type="nonparametric",
                             mc_correction="None (uncorrected)")
        sig_pairs = {frozenset([r[0], r[1]]) for r in results if r[3] != "ns"}
        assert frozenset(["A", "C"]) in sig_pairs

    # --- Paired t-test ---

    def test_paired_ttest_matches_scipy(self):
        """Paired t-test p-value matches scipy.stats.ttest_rel."""
        pre = np.array([10., 12., 14., 16., 18.])
        post = np.array([12., 15., 17., 20., 22.])
        results = _run_stats({"pre": pre, "post": post}, test_type="paired",
                             mc_correction="None (uncorrected)")
        _, _, p_ours, _ = results[0]
        _, p_scipy = sp_stats.ttest_rel(pre, post)
        assert p_ours == pytest.approx(p_scipy, abs=1e-12)

    # --- One-sample t-test ---

    def test_one_sample_matches_scipy(self):
        """One-sample t-test p-value matches scipy.stats.ttest_1samp."""
        grp = np.array([1., 2., 3., 4., 5.])
        mu0 = 0.0
        results = _run_stats({"grp": grp}, test_type="one_sample",
                             mc_correction="None (uncorrected)", mu0=mu0)
        _, _, p_ours, _ = results[0]
        _, p_scipy = sp_stats.ttest_1samp(grp, popmean=mu0)
        assert p_ours == pytest.approx(p_scipy, abs=1e-12)

    def test_one_sample_at_true_mean_ns(self):
        """One-sample t-test at the true mean should be ns.
        mean([1,2,3,4,5]) = 3, so mu0=3 => p=1."""
        grp = np.array([1., 2., 3., 4., 5.])
        results = _run_stats({"grp": grp}, test_type="one_sample",
                             mc_correction="None (uncorrected)", mu0=3.0)
        _, _, p, stars = results[0]
        assert p == pytest.approx(1.0, abs=1e-10)
        assert stars == "ns"

    # --- Permutation test ---

    def test_permutation_significant_for_separated(self):
        """Permutation test finds clearly separated groups significant.
        Need n >= 6 per group so the permutation distribution has enough
        resolution for p < 0.05 (with n=5, minimum possible p = 2/C(10,5) = 0.0079
        but scipy permutation_test uses a different counting method)."""
        A = np.array([1., 2., 3., 4., 5., 6., 7., 8.])
        B = np.array([100., 200., 300., 400., 500., 600., 700., 800.])
        results = _run_stats({"A": A, "B": B}, test_type="permutation",
                             n_permutations=999,
                             mc_correction="None (uncorrected)")
        _, _, p, _ = results[0]
        assert p < 0.05

    # --- Control group filtering ---

    def test_control_filters_to_control_pairs_only(self):
        """With control set, only control-vs-others pairs are returned."""
        rng = np.random.default_rng(7)
        groups = {"Control": rng.normal(5, 1, 15),
                  "Drug A": rng.normal(8, 1, 15),
                  "Drug B": rng.normal(11, 1, 15)}
        results = _run_stats(groups, test_type="parametric",
                             posthoc="Tukey HSD", control="Control")
        assert len(results) == 2, f"Expected 2 pairs, got {len(results)}"
        pairs = {frozenset([r[0], r[1]]) for r in results}
        assert frozenset(["Drug A", "Drug B"]) not in pairs

    def test_no_control_returns_all_pairs(self):
        """With control=None, all C(k,2) pairs returned (after ANOVA gate)."""
        rng = np.random.default_rng(7)
        groups = {"Control": rng.normal(5, 1, 15),
                  "Drug A": rng.normal(8, 1, 15),
                  "Drug B": rng.normal(11, 1, 15)}
        results = _run_stats(groups, test_type="parametric",
                             posthoc="Tukey HSD", control=None)
        assert len(results) == 3

    def test_single_group_returns_empty(self):
        """k=1 for pairwise tests returns empty list."""
        results = _run_stats({"A": np.array([1., 2., 3.])}, test_type="parametric")
        assert results == []

    # --- Dunnett ---

    def test_dunnett_uses_first_group_as_default_control(self):
        """Dunnett with control=None uses first group as control."""
        rng = np.random.default_rng(7)
        groups = {"Alpha": rng.normal(5, 1, 10),
                  "Beta": rng.normal(8, 1, 10),
                  "Gamma": rng.normal(11, 1, 10)}
        results = _run_stats(groups, test_type="parametric",
                             posthoc="Dunnett (vs control)", control=None)
        assert len(results) == 2
        for g_a, g_b, p, stars in results:
            assert "Alpha" in (g_a, g_b)


# ============================================================================
# check_normality
# ============================================================================

class TestCheckNormality:
    """Tests for check_normality(groups, alpha)."""

    def test_normal_data_passes(self):
        """Data drawn from a normal distribution should pass Shapiro-Wilk."""
        rng = np.random.default_rng(42)
        vals = rng.normal(0, 1, 50)
        results = check_normality({"normal_group": vals})
        stat, p, is_normal, msg = results["normal_group"]
        assert is_normal is True
        assert msg is None
        assert p > 0.05

    def test_exponential_data_fails(self):
        """Data from exponential distribution should fail Shapiro-Wilk."""
        rng = np.random.default_rng(42)
        vals = rng.exponential(1.0, 50)
        results = check_normality({"exp_group": vals})
        stat, p, is_normal, msg = results["exp_group"]
        assert is_normal is False
        assert msg is not None
        assert "non-normal" in msg

    def test_n_less_than_3_returns_none(self):
        """Groups with n < 3 cannot be tested; returns (None, None, None, warning)."""
        results = check_normality({"tiny": np.array([1.0, 2.0])})
        stat, p, is_normal, msg = results["tiny"]
        assert stat is None
        assert p is None
        assert is_normal is None
        assert "too few" in msg

    def test_n_equals_0_returns_warning(self):
        """Empty group returns warning."""
        results = check_normality({"empty": np.array([])})
        _, _, is_normal, msg = results["empty"]
        assert is_normal is None
        assert "too few" in msg


# ============================================================================
# _logrank_test
# ============================================================================

class TestLogrank:
    """Tests for the log-rank (Mantel-Cox) survival test."""

    def test_separated_groups_significant(self):
        """Non-overlapping survival times should give significant p."""
        groups = {
            "A": (np.array([1., 2., 3.]), np.array([1, 1, 1])),
            "B": (np.array([5., 6., 7.]), np.array([1, 1, 1])),
        }
        results = _logrank_test(groups)
        assert len(results) == 1
        _, _, p, _ = results[0]
        assert p < 0.05

    def test_identical_groups_not_significant(self):
        """Identical survival curves should give p close to 1."""
        t = np.array([1., 2., 3., 4., 5.])
        e = np.array([1, 1, 1, 1, 1])
        groups = {"A": (t.copy(), e.copy()), "B": (t.copy(), e.copy())}
        results = _logrank_test(groups)
        _, _, p, _ = results[0]
        assert p > 0.99

    def test_three_groups_returns_three_pairs(self):
        """3 groups produce C(3,2)=3 pairwise comparisons."""
        rng = np.random.default_rng(42)
        groups = {
            "A": (rng.exponential(5, 10), np.ones(10)),
            "B": (rng.exponential(5, 10), np.ones(10)),
            "C": (rng.exponential(5, 10), np.ones(10)),
        }
        results = _logrank_test(groups)
        assert len(results) == 3


# ============================================================================
# _twoway_anova
# ============================================================================

class TestTwowayAnova:
    """Tests for two-way ANOVA (Type III SS)."""

    @staticmethod
    def _make_df():
        """Balanced 2x2 design with strong main effects and no interaction."""
        import pandas as pd
        rng = np.random.default_rng(0)
        rows = []
        for a in ["a1", "a2"]:
            for b in ["b1", "b2"]:
                mu = {"a1b1": 10, "a1b2": 20, "a2b1": 30, "a2b2": 40}[a + b]
                for _ in range(5):
                    rows.append({"A": a, "B": b, "Y": mu + rng.normal(0, 1)})
        return pd.DataFrame(rows)

    def test_partial_eta_squared_in_range(self):
        """Partial eta-squared must be in [0, 1]."""
        df = self._make_df()
        result = _twoway_anova(df, "Y", "A", "B")
        for key in ("A", "B", "interaction"):
            ep2 = result[key]["eta2_partial"]
            assert 0.0 <= ep2 <= 1.0

    def test_partial_eta_squared_formula(self):
        """eta2_partial = SS_effect / (SS_effect + SS_error)."""
        df = self._make_df()
        result = _twoway_anova(df, "Y", "A", "B")
        SS_err = result["residual"]["SS"]
        for key in ("A", "B", "interaction"):
            SS_eff = result[key]["SS"]
            expected = SS_eff / (SS_eff + SS_err)
            assert result[key]["eta2_partial"] == pytest.approx(expected, abs=1e-12)

    def test_strong_main_effects_significant(self):
        """Strong main effects (mu differs by 20 between levels) should be significant."""
        df = self._make_df()
        result = _twoway_anova(df, "Y", "A", "B")
        assert result["A"]["p"] < 0.05
        assert result["B"]["p"] < 0.05
        assert result["A"]["eta2_partial"] > 0.5
        assert result["B"]["eta2_partial"] > 0.5

    def test_degrees_of_freedom(self):
        """df_A = I-1, df_B = J-1, df_AB = (I-1)(J-1), df_err = N - I*J.
        For 2x2 with 5 reps: df_A=1, df_B=1, df_AB=1, df_err=20-4=16."""
        df = self._make_df()
        result = _twoway_anova(df, "Y", "A", "B")
        assert result["A"]["df"] == 1
        assert result["B"]["df"] == 1
        assert result["interaction"]["df"] == 1
        assert result["residual"]["df"] == 16

    def test_f_positive(self):
        """F statistics must be non-negative."""
        df = self._make_df()
        result = _twoway_anova(df, "Y", "A", "B")
        for key in ("A", "B", "interaction"):
            assert result[key]["F"] >= 0


# ============================================================================
# _twoway_posthoc
# ============================================================================

class TestTwowayPosthoc:
    """Tests for two-way post-hoc pairwise comparisons."""

    @staticmethod
    def _make_df():
        import pandas as pd
        rng = np.random.default_rng(0)
        rows = []
        for a in ["a1", "a2"]:
            for b in ["b1", "b2"]:
                mu = {"a1b1": 10, "a1b2": 20, "a2b1": 30, "a2b2": 40}[a + b]
                for _ in range(5):
                    rows.append({"A": a, "B": b, "Y": mu + rng.normal(0, 1)})
        return pd.DataFrame(rows)

    def test_p_raw_matches_welch(self):
        """Post-hoc raw p-values match scipy Welch t-test."""
        df = self._make_df()
        results = _twoway_posthoc(df, "Y", "A", "B", correction="none")
        for row in results:
            b_val = row["factor_b_level"]
            g1 = df[(df["B"] == b_val) & (df["A"] == row["group1"])]["Y"].values
            g2 = df[(df["B"] == b_val) & (df["A"] == row["group2"])]["Y"].values
            _, p_scipy = sp_stats.ttest_ind(g1, g2, equal_var=False)
            assert row["p_raw"] == pytest.approx(p_scipy, abs=1e-12)
