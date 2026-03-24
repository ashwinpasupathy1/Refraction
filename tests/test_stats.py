"""
test_stats.py — pytest tests for statistical verification and control-group logic.

Total: 57 tests.
"""

import numpy as np
import pandas as pd
import pytest
from scipy import stats as _scipy_stats

from refraction.core import chart_helpers as pf

# ── shorthand for the internal stats helpers ──────────────────────────────
_cohens_d = pf._cohens_d
_hedges_g = pf._hedges_g
_rank_biserial_r = pf._rank_biserial_r
_apply_correction = pf._apply_correction
_p_to_stars = pf._p_to_stars
_run_stats = pf._run_stats
_logrank_test = pf._logrank_test
_twoway_anova = pf._twoway_anova

PLOT_PARAM_DEFAULTS = pf.PLOT_PARAM_DEFAULTS

# ── Known data for analytical verification ─────────────────────────────────
A = np.array([100., 110., 120., 130., 140.])
B = np.array([200., 220., 240., 260., 280.])

G_A = np.array([2., 4., 6., 8., 10.])
G_B = np.array([6., 8., 10., 12., 14.])
G_C = np.array([10., 12., 14., 16., 18.])

RAW_P = [0.01, 0.04, 0.20]


# =========================================================================
# PART A — Statistical Verification (37 tests)
# =========================================================================

# ── 1. Welch's t-test ─────────────────────────────────────────────────────

class TestWelchT:
    def test_pvalue(self):
        """_run_stats parametric k=2 p-value matches scipy.stats.ttest_ind."""
        groups = {"A": A, "B": B}
        results = _run_stats(groups, test_type="parametric",
                             mc_correction="None (uncorrected)")
        assert len(results) == 1, "Expected one pairwise result"
        _, _, p_ours, _ = results[0]
        _, p_scipy = _scipy_stats.ttest_ind(A, B, equal_var=False)
        assert abs(p_ours - p_scipy) < 1e-12
        assert p_ours < 0.01

    def test_statistic_direction(self):
        groups = {"A": np.array([1., 2., 3.]),
                  "B": np.array([10., 11., 12.])}
        results = _run_stats(groups, test_type="parametric",
                             mc_correction="None (uncorrected)")
        assert results[0][3] in ("*", "**", "***", "****")


# ── 2. Cohen's d ──────────────────────────────────────────────────────────

class TestCohensD:
    def test_analytical(self):
        d = _cohens_d(A, B)
        assert abs(d - (-4.8)) < 1e-10

    def test_symmetric(self):
        d_ab = _cohens_d(A, B)
        d_ba = _cohens_d(B, A)
        assert abs(d_ab + d_ba) < 1e-10

    def test_equal_means(self):
        X = np.array([1., 2., 3., 4., 5.])
        d = _cohens_d(X, X.copy())
        assert d == 0.0

    def test_small_n_returns_nan(self):
        assert np.isnan(_cohens_d(np.array([1.]), np.array([2., 3., 4.])))
        assert np.isnan(_cohens_d(np.array([1., 2.]), np.array([3.])))


# ── 3. Hedges' g ──────────────────────────────────────────────────────────

class TestHedgesG:
    def test_correction(self):
        g = _hedges_g(A, B)
        m = len(A) + len(B) - 2
        J = 1.0 - 3.0 / (4.0 * m - 1.0)
        d = _cohens_d(A, B)
        expected = d * J
        assert abs(g - expected) < 1e-12

    def test_smaller_than_cohens_d(self):
        g = _hedges_g(A, B)
        d = _cohens_d(A, B)
        assert abs(g) < abs(d)

    def test_large_n_converges_to_d(self):
        rng = np.random.default_rng(42)
        X = rng.normal(0, 1, 500)
        Y = rng.normal(0.5, 1, 500)
        d = _cohens_d(X, Y)
        g = _hedges_g(X, Y)
        assert abs(g - d) / (abs(d) + 1e-9) < 0.002

    def test_nan_propagation(self):
        assert np.isnan(_hedges_g(np.array([1.]), np.array([2., 3.])))


# ── 4. Rank-biserial r ────────────────────────────────────────────────────

class TestRankBiserialR:
    def test_complete_separation(self):
        r = _rank_biserial_r(np.array([1., 2., 3.]), np.array([4., 5., 6.]))
        assert r == -1.0

    def test_reverse_separation(self):
        r = _rank_biserial_r(np.array([4., 5., 6.]), np.array([1., 2., 3.]))
        assert r == 1.0

    def test_antisymmetric(self):
        rng = np.random.default_rng(99)
        X = rng.normal(0, 1, 8)
        Y = rng.normal(1, 1, 8)
        r_xy = _rank_biserial_r(X, Y)
        r_yx = _rank_biserial_r(Y, X)
        assert abs(r_xy + r_yx) < 1e-10

    def test_range(self):
        rng = np.random.default_rng(7)
        for _ in range(20):
            X = rng.normal(0, 1, rng.integers(3, 15))
            Y = rng.normal(0, 1, rng.integers(3, 15))
            r = _rank_biserial_r(X, Y)
            assert -1.0 <= r <= 1.0


# ── 5. Mann-Whitney U ─────────────────────────────────────────────────────

class TestMannWhitney:
    def test_exact_pvalue(self):
        groups = {"A": np.array([1., 2., 3.]), "B": np.array([4., 5., 6.])}
        results = _run_stats(groups, test_type="nonparametric",
                             mc_correction="None (uncorrected)")
        assert len(results) == 1
        _, _, p_ours, _ = results[0]
        _, p_scipy = _scipy_stats.mannwhitneyu(
            groups["A"], groups["B"], alternative="two-sided")
        assert abs(p_ours - p_scipy) < 1e-12

    def test_complete_separation_significant(self):
        groups = {"A": np.arange(1., 9.), "B": np.arange(9., 17.)}
        results = _run_stats(groups, test_type="nonparametric",
                             mc_correction="None (uncorrected)")
        _, _, p, _ = results[0]
        assert p < 0.05


# ── 6. One-way ANOVA ──────────────────────────────────────────────────────

class TestOneWayAnova:
    def test_F_statistic(self):
        F, p = _scipy_stats.f_oneway(G_A, G_B, G_C)
        assert abs(F - 8.0) < 1e-10
        assert abs(p - _scipy_stats.f.sf(8.0, 2, 12)) < 1e-12


# ── 7. Tukey HSD ──────────────────────────────────────────────────────────

class TestTukeyHSD:
    def test_finds_only_AC_significant(self):
        groups = {"A": G_A, "B": G_B, "C": G_C}
        results = _run_stats(groups, test_type="parametric",
                             posthoc="Tukey HSD",
                             mc_correction="None (uncorrected)")
        sig_pairs = {(r[0], r[1]) for r in results if r[3] != "ns"}
        assert ("A", "C") in sig_pairs or ("C", "A") in sig_pairs
        ab_sig = ("A", "B") in sig_pairs or ("B", "A") in sig_pairs
        bc_sig = ("B", "C") in sig_pairs or ("C", "B") in sig_pairs
        assert not ab_sig, "A vs B should be NS"
        assert not bc_sig, "B vs C should be NS"

    def test_pvalue_vs_studentized_range(self):
        groups = {"A": G_A, "B": G_B, "C": G_C}
        results = _run_stats(groups, test_type="parametric",
                             posthoc="Tukey HSD",
                             mc_correction="None (uncorrected)")
        p_ac = None
        for a_lbl, b_lbl, p, stars in results:
            if set([a_lbl, b_lbl]) == {"A", "C"}:
                p_ac = p
        assert p_ac is not None
        q_manual = 8.0 / np.sqrt(2.0)
        p_manual = 1.0 - _scipy_stats.studentized_range.cdf(q_manual, 3, 12)
        assert abs(p_ac - p_manual) < 1e-10


# ── 8. Multiple comparison corrections ────────────────────────────────────

class TestCorrections:
    def test_bonferroni(self):
        corrected = _apply_correction(RAW_P, "Bonferroni")
        m = 3
        expected = [min(p * m, 1.0) for p in RAW_P]
        for got, exp in zip(corrected, expected):
            assert abs(got - exp) < 1e-12

    def test_holm_monotonicity(self):
        corrected = _apply_correction(RAW_P, "Holm-Bonferroni")
        for i in range(len(corrected) - 1):
            assert corrected[i] <= corrected[i + 1] + 1e-12

    def test_holm_geq_raw(self):
        corrected = _apply_correction(RAW_P, "Holm-Bonferroni")
        for raw, corr in zip(RAW_P, corrected):
            assert corr >= raw - 1e-12

    def test_bh_fdr_monotone(self):
        raw_sorted = sorted(RAW_P)
        corrected = _apply_correction(raw_sorted, "Benjamini-Hochberg (FDR)")
        for i in range(len(corrected) - 1):
            assert corrected[i] <= corrected[i + 1] + 1e-12

    def test_cap_at_one(self):
        high_p = [0.5, 0.6, 0.7, 0.8, 0.9]
        for method in ("Bonferroni", "Holm-Bonferroni", "Benjamini-Hochberg (FDR)"):
            corrected = _apply_correction(high_p, method)
            for cp in corrected:
                assert cp <= 1.0


# ── 9. p-to-stars ─────────────────────────────────────────────────────────

class TestPToStars:
    def test_exact_boundaries(self):
        cases = [
            (0.0001, "****"),
            (0.0002, "***"),
            (0.001, "***"),
            (0.0011, "**"),
            (0.01, "**"),
            (0.011, "*"),
            (0.05, "*"),
            (0.051, "ns"),
            (0.99, "ns"),
        ]
        for p, expected in cases:
            got = _p_to_stars(p)
            assert got == expected, f"p={p}: expected '{expected}', got '{got}'"


# ── 10. Chi-square GoF ────────────────────────────────────────────────────

class TestChiSquareGoF:
    def test_statistic(self):
        observed = np.array([20., 30., 50.])
        expected = np.full(3, 100.0 / 3.0)
        chi2, p = _scipy_stats.chisquare(observed, f_exp=expected)
        assert abs(chi2 - 14.0) < 1e-10
        assert p < 0.01

    def test_uniform_null(self):
        observed = np.array([10., 10., 10.])
        chi2, p = _scipy_stats.chisquare(observed)
        assert chi2 == 0.0
        assert p == 1.0


# ── 11. Log-rank test ─────────────────────────────────────────────────────

class TestLogrank:
    def test_hand_computed(self):
        groups_dict = {
            "A": (np.array([1., 2., 3.]), np.array([1, 1, 1])),
            "B": (np.array([5., 6., 7.]), np.array([1, 1, 1])),
        }
        results = _logrank_test(groups_dict)
        assert len(results) == 1
        a_lbl, b_lbl, p, stars = results[0]
        O1, E1 = 3.0, 1.15
        var = 0.6775
        chi2_expected = (O1 - E1) ** 2 / var
        p_expected = float(_scipy_stats.chi2.sf(chi2_expected, df=1))
        assert abs(p - p_expected) < 1e-8
        assert p < 0.05

    def test_identical_groups(self):
        t = np.array([1., 2., 3., 4., 5.])
        e = np.array([1, 1, 1, 1, 1])
        groups_dict = {"A": (t.copy(), e.copy()), "B": (t.copy(), e.copy())}
        results = _logrank_test(groups_dict)
        _, _, p, _ = results[0]
        assert p > 0.99


# ── 12. Two-way ANOVA ─────────────────────────────────────────────────────

def _make_twoway_df():
    rows = []
    rng2 = np.random.default_rng(0)
    for a in ["a1", "a2"]:
        for b in ["b1", "b2"]:
            mu = {"a1b1": 10, "a1b2": 20, "a2b1": 30, "a2b2": 40}[a + b]
            for _ in range(5):
                rows.append({"A": a, "B": b, "Y": mu + rng2.normal(0, 1)})
    return pd.DataFrame(rows)


class TestTwoWayAnova:
    def test_partial_eta2_range(self):
        df = _make_twoway_df()
        result = _twoway_anova(df, "Y", "A", "B")
        for key in ("A", "B", "interaction"):
            ep2 = result[key]["eta2_partial"]
            assert 0.0 <= ep2 <= 1.0

    def test_partial_eta2_formula(self):
        df = _make_twoway_df()
        result = _twoway_anova(df, "Y", "A", "B")
        SS_err = result["residual"]["SS"]
        for key in ("A", "B", "interaction"):
            SS_eff = result[key]["SS"]
            expected_ep2 = SS_eff / (SS_eff + SS_err)
            got_ep2 = result[key]["eta2_partial"]
            assert abs(got_ep2 - expected_ep2) < 1e-12

    def test_strong_main_effects_significant(self):
        df = _make_twoway_df()
        result = _twoway_anova(df, "Y", "A", "B")
        assert result["A"]["p"] < 0.05
        assert result["B"]["p"] < 0.05
        assert result["A"]["eta2_partial"] > 0.5
        assert result["B"]["eta2_partial"] > 0.5


# ── 13. Two-way post-hoc ──────────────────────────────────────────────────

class TestTwoWayPosthoc:
    def test_welch(self):
        from refraction.core.chart_helpers import _twoway_posthoc
        df = _make_twoway_df()
        results = _twoway_posthoc(df, "Y", "A", "B", correction="none")
        for row in results:
            b_val = row["factor_b_level"]
            g1 = df[(df["B"] == b_val) & (df["A"] == row["group1"])]["Y"].values
            g2 = df[(df["B"] == b_val) & (df["A"] == row["group2"])]["Y"].values
            _, p_scipy = _scipy_stats.ttest_ind(g1, g2, equal_var=False)
            assert abs(row["p_raw"] - p_scipy) < 1e-12


# ── 14. One-sample t-test ─────────────────────────────────────────────────

class TestOneSample:
    def test_pvalue(self):
        grp = np.array([1., 2., 3., 4., 5.])
        mu0 = 0.0
        groups = {"grp": grp}
        results = _run_stats(groups, test_type="one_sample",
                             mc_correction="None (uncorrected)", mu0=mu0)
        assert len(results) == 1
        _, _, p_ours, _ = results[0]
        _, p_scipy = _scipy_stats.ttest_1samp(grp, popmean=mu0)
        assert abs(p_ours - p_scipy) < 1e-12
        assert p_ours < 0.05


# ── 15. Paired t-test ─────────────────────────────────────────────────────

class TestPairedT:
    def test_pvalue(self):
        pre = np.array([10., 12., 14., 16., 18.])
        post = np.array([12., 15., 17., 20., 22.])
        groups = {"pre": pre, "post": post}
        results = _run_stats(groups, test_type="paired",
                             mc_correction="None (uncorrected)")
        assert len(results) == 1
        _, _, p_ours, _ = results[0]
        _, p_scipy = _scipy_stats.ttest_rel(pre, post)
        assert abs(p_ours - p_scipy) < 1e-12
        assert p_ours < 0.05


# ── 16. Dunn's post-hoc ──────────────────────────────────────────────────

class TestDunns:
    def test_pvalue_vs_normal_cdf(self):
        groups = {
            "A": np.arange(1., 11.),
            "B": np.arange(21., 31.),
            "C": np.arange(41., 51.),
        }
        results = _run_stats(groups, test_type="nonparametric",
                             mc_correction="None (uncorrected)")
        sig_pairs = {frozenset([r[0], r[1]]) for r in results if r[3] != "ns"}
        assert frozenset(["A", "C"]) in sig_pairs

    def test_two_tailed_z(self):
        rng3 = np.random.default_rng(42)
        groups = {
            "X": rng3.normal(0, 1, 10),
            "Y": rng3.normal(0.5, 1, 10),
            "Z": rng3.normal(1.0, 1, 10),
        }
        results = _run_stats(groups, test_type="nonparametric",
                             mc_correction="None (uncorrected)")
        for _, _, p, _ in results:
            assert 0.0 <= p <= 1.0


# =========================================================================
# PART B — Control Group Tests (20 tests)
# =========================================================================

rng_ctrl = np.random.default_rng(7)

# ── Bug 1: Stale control name ─────────────────────────────────────────────

class TestStaleControl:
    def test_falls_back(self):
        groups = {"A": rng_ctrl.normal(5, 1, 10),
                  "B": rng_ctrl.normal(7, 1, 10),
                  "C": rng_ctrl.normal(9, 1, 10)}
        results = _run_stats(groups, test_type="parametric",
                             control="DoesNotExist",
                             mc_correction="Holm-Bonferroni",
                             posthoc="Tukey HSD")
        assert isinstance(results, list)

    def test_valid_control_works(self):
        groups = {"Ctrl": rng_ctrl.normal(5, 1, 12),
                  "TrtA": rng_ctrl.normal(8, 1, 12),
                  "TrtB": rng_ctrl.normal(11, 1, 12)}
        results = pf._run_stats(groups, test_type="parametric",
                                 posthoc="Tukey HSD", control="Ctrl")
        pairs = {(r[0], r[1]) for r in results} | {(r[1], r[0]) for r in results}
        assert ("Ctrl", "TrtA") in pairs or ("TrtA", "Ctrl") in pairs
        assert ("Ctrl", "TrtB") in pairs or ("TrtB", "Ctrl") in pairs
        assert not (("TrtA", "TrtB") in pairs or ("TrtB", "TrtA") in pairs)


# ── Bug 3: Comparison mode pair filtering ─────────────────────────────────

GROUPS_3 = {
    "Control": rng_ctrl.normal(5, 1, 15),
    "Drug A": rng_ctrl.normal(8, 1, 15),
    "Drug B": rng_ctrl.normal(11, 1, 15),
}


class TestComparisonMode:
    def test_all_pairwise_returns_three_pairs(self):
        results = pf._run_stats(GROUPS_3, test_type="parametric",
                                 posthoc="Tukey HSD", control=None)
        assert len(results) == 3

    def test_vs_control_returns_two_pairs(self):
        results = pf._run_stats(GROUPS_3, test_type="parametric",
                                 posthoc="Tukey HSD", control="Control")
        assert len(results) == 2

    def test_vs_control_excludes_treatment_pair(self):
        results = pf._run_stats(GROUPS_3, test_type="parametric",
                                 posthoc="Tukey HSD", control="Control")
        pairs = {frozenset([r[0], r[1]]) for r in results}
        assert frozenset(["Drug A", "Drug B"]) not in pairs

    def test_pair_filter_symmetric(self):
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
            assert len(results) == 2
            pairs = {frozenset([r[0], r[1]]) for r in results}
            assert frozenset(["Drug A", "Drug B"]) not in pairs

    def test_vs_control_all_test_types(self):
        groups = {
            "Ctrl": rng_ctrl.normal(5, 1, 12),
            "TrtA": rng_ctrl.normal(8, 1, 12),
            "TrtB": rng_ctrl.normal(11, 1, 12),
        }
        for test_type in ("parametric", "nonparametric", "permutation"):
            results = pf._run_stats(groups, test_type=test_type,
                                     posthoc="Tukey HSD", control="Ctrl",
                                     n_permutations=99)
            assert len(results) == 2
            pairs = {frozenset([r[0], r[1]]) for r in results}
            assert frozenset(["TrtA", "TrtB"]) not in pairs

    def test_control_none_all_pairs_nonparametric(self):
        groups = {"A": rng_ctrl.normal(5, 1, 10),
                  "B": rng_ctrl.normal(7, 1, 10),
                  "C": rng_ctrl.normal(9, 1, 10),
                  "D": rng_ctrl.normal(11, 1, 10)}
        results = pf._run_stats(groups, test_type="nonparametric", control=None)
        assert len(results) == 6


# ── Bug 4: Dunnett ────────────────────────────────────────────────────────

class TestDunnett:
    def test_no_control_uses_first_group(self):
        groups = {"Alpha": rng_ctrl.normal(5, 1, 10),
                  "Beta": rng_ctrl.normal(8, 1, 10),
                  "Gamma": rng_ctrl.normal(11, 1, 10)}
        results = pf._run_stats(groups, test_type="parametric",
                                 posthoc="Dunnett (vs control)", control=None)
        assert len(results) == 2
        for g_a, g_b, p, stars in results:
            assert "Alpha" in (g_a, g_b)

    def test_explicit_control(self):
        groups = {"Drug": rng_ctrl.normal(5, 1, 10),
                  "Placebo": rng_ctrl.normal(5, 1, 10),
                  "Vehicle": rng_ctrl.normal(5, 1, 10)}
        results = pf._run_stats(groups, test_type="parametric",
                                 posthoc="Dunnett (vs control)", control="Placebo")
        assert len(results) == 2
        for g_a, g_b, p, stars in results:
            assert "Placebo" in (g_a, g_b)

    def test_no_double_mc_correction(self):
        from scipy.stats import dunnett as _dunnett
        ctrl = rng_ctrl.normal(5, 1, 20)
        trt_a = rng_ctrl.normal(8, 1, 20)
        trt_b = rng_ctrl.normal(11, 1, 20)
        groups = {"Ctrl": ctrl, "A": trt_a, "B": trt_b}

        scipy_res = _dunnett(trt_a, trt_b, control=ctrl)
        our_res = pf._run_stats(groups, test_type="parametric",
                                 posthoc="Dunnett (vs control)", control="Ctrl")

        scipy_p = sorted(float(p) for p in scipy_res.pvalue)
        our_p = sorted(r[2] for r in our_res)
        for sp, op in zip(scipy_p, our_p):
            assert abs(sp - op) < 1e-10


# ── ANOVA error term ──────────────────────────────────────────────────────

class TestAnovaErrorTerm:
    def test_tukey_ms_within_uses_all_groups(self):
        rng2 = np.random.default_rng(99)
        groups = {
            "Ctrl": rng2.normal(5, 1, 10),
            "A": rng2.normal(7, 1, 10),
            "B": rng2.normal(9, 1, 10),
        }
        results_ctrl = pf._run_stats(groups, test_type="parametric",
                                      posthoc="Tukey HSD", control="Ctrl")
        results_all = pf._run_stats(groups, test_type="parametric",
                                     posthoc="Tukey HSD", control=None)

        def _find(res, a, b):
            for g1, g2, p, _ in res:
                if {g1, g2} == {a, b}:
                    return p
            return None

        p_ctrl = _find(results_ctrl, "Ctrl", "A")
        p_all = _find(results_all, "Ctrl", "A")
        assert p_ctrl is not None
        assert p_all is not None
        assert abs(p_ctrl - p_all) < 1e-10


# ── End-to-end render tests with control ──────────────────────────────────

class TestStatsWithControl:
    def test_with_control(self):
        groups = {"Vehicle": rng_ctrl.normal(5, 1, 12),
                  "Low": rng_ctrl.normal(7, 1, 12),
                  "High": rng_ctrl.normal(10, 1, 12)}
        results = _run_stats(groups, test_type="parametric",
                             posthoc="Tukey HSD", control="Vehicle",
                             mc_correction="Holm-Bonferroni")
        assert len(results) == 2

    def test_stale_control(self):
        groups = {"Alpha": rng_ctrl.normal(5, 1, 10),
                  "Beta": rng_ctrl.normal(8, 1, 10),
                  "Gamma": rng_ctrl.normal(11, 1, 10)}
        results = _run_stats(groups, test_type="parametric",
                             posthoc="Tukey HSD", control="OldGroupName")
        assert isinstance(results, list)

    def test_all_posthoc_with_control(self):
        groups = {"Ctrl": rng_ctrl.normal(5, 1, 10),
                  "A": rng_ctrl.normal(8, 1, 10),
                  "B": rng_ctrl.normal(11, 1, 10)}
        for posthoc in ("Tukey HSD", "Bonferroni", "Sidak", "Fisher LSD"):
            results = pf._run_stats(groups, test_type="parametric",
                                     posthoc=posthoc, control="Ctrl")
            assert len(results) == 2
            pairs = {frozenset([r[0], r[1]]) for r in results}
            assert frozenset(["A", "B"]) not in pairs

    def test_dunnett_with_control(self):
        groups = {"Vehicle": rng_ctrl.normal(5, 1, 12),
                  "Low": rng_ctrl.normal(7, 1, 12),
                  "High": rng_ctrl.normal(10, 1, 12)}
        results = _run_stats(groups, test_type="parametric",
                             posthoc="Dunnett (vs control)",
                             control="Vehicle")
        assert len(results) == 2

    def test_nonparametric_vs_control(self):
        groups = {"Ctrl": rng_ctrl.normal(5, 1, 10),
                  "TrtA": rng_ctrl.normal(8, 1, 10),
                  "TrtB": rng_ctrl.normal(11, 1, 10)}
        results = _run_stats(groups, test_type="nonparametric",
                             control="Ctrl")
        assert len(results) == 2


# ── p-to-stars and threshold consistency ──────────────────────────────────

class TestPToStarsControl:
    def test_thresholds(self):
        cases = [
            (0.00001, "****"), (0.0001, "****"),
            (0.00011, "***"), (0.001, "***"),
            (0.0011, "**"), (0.01, "**"),
            (0.011, "*"), (0.05, "*"),
            (0.051, "ns"), (0.99, "ns"),
        ]
        for p_val, expected in cases:
            got = pf._p_to_stars(p_val)
            assert got == expected, f"p={p_val}: expected {expected!r}, got {got!r}"

    def test_mc_correction_increases_p(self):
        groups = {"A": rng_ctrl.normal(5, 0.5, 8),
                  "B": rng_ctrl.normal(6, 0.5, 8),
                  "C": rng_ctrl.normal(7, 0.5, 8)}
        raw_res = pf._run_stats(groups, "parametric", mc_correction="None (uncorrected)")
        holm_res = pf._run_stats(groups, "parametric", mc_correction="Holm-Bonferroni")
        raw_p = sorted(r[2] for r in raw_res)
        holm_p = sorted(r[2] for r in holm_res)
        for rp, hp in zip(raw_p, holm_p):
            assert hp >= rp - 1e-12
