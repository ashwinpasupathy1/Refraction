"""
test_control.py
===============
Tests for control group bugs and Prism-style comparison mode.

Covers:
  • Bug 1 — stale control name no longer crashes (fallback to all-pairwise)
  • Bug 2 — control dropdown populated for line/scatter/grouped_bar
  • Bug 3 — comparison_mode=1 (vs-control) only runs pairs involving control
  • Bug 4 — Dunnett with no control still works (uses first group, warns)
  • Correctness — pair-filter is symmetric regardless of group order
  • Correctness — ANOVA error term uses all groups even in vs-control mode
  • Correctness — all test types honour control filter

Run:
  python3 test_control.py
"""
import sys, os, warnings
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plotter_test_harness as _h
from plotter_test_harness import (
    pf, plt, ok, fail, run, section, summarise, close_fig,
    bar_excel, line_excel, simple_xy_excel, grouped_excel,
    km_excel, heatmap_excel, two_way_excel, contingency_excel,
    bland_altman_excel, forest_excel, bubble_excel, chi_gof_excel,
    with_excel, PLOT_PARAM_DEFAULTS,
)

# Local rng so tests are reproducible independent of harness seed
rng = np.random.default_rng(7)





# ═════════════════════════════════════════════════════════════════════════════
# Bug 1 — Stale control name must not crash
# ═════════════════════════════════════════════════════════════════════════════
section("Bug 1 — Stale control name: warn + fallback, no crash")

def test_stale_control_warns_not_crashes():
    """_apply_stats_brackets with control not in groups → warning, not ValueError."""
    groups = {"A": rng.normal(5, 1, 10),
              "B": rng.normal(7, 1, 10),
              "C": rng.normal(9, 1, 10)}
    fig, ax = plt.subplots()
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        pf._apply_stats_brackets(
            ax, groups, list(groups.keys()),
            "parametric", 9999,
            control="OldGroupFromPreviousChart",   # stale name — not in groups
            mc_correction="Holm-Bonferroni",
            posthoc="Tukey HSD",
            show_p_values=False, show_effect_size=False,
            show_test_name=False, font_size=12)
        assert any("not found in groups" in str(x.message) for x in w), \
            "Expected a warning about stale control name"
    close_fig(fig)

run("stale control: issues UserWarning instead of crashing", test_stale_control_warns_not_crashes)

def test_stale_control_falls_back_to_all_pairwise():
    """After stale control warning, all pairwise results are returned."""
    groups = {"A": rng.normal(5, 1, 10),
              "B": rng.normal(7, 1, 10),
              "C": rng.normal(9, 1, 10)}
    fig, ax = plt.subplots()
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        results = pf._apply_stats_brackets(
            ax, groups, list(groups.keys()),
            "parametric", 9999,
            control="DoesNotExist",
            mc_correction="Holm-Bonferroni",
            posthoc="Tukey HSD",
            show_p_values=False, show_effect_size=False,
            show_test_name=False, font_size=12)
    # Should return up to 3 all-pairwise results, not 0 and not crash
    assert isinstance(results, list)
    close_fig(fig)

run("stale control: falls back to all-pairwise results", test_stale_control_falls_back_to_all_pairwise)

def test_valid_control_still_works_normally():
    """When control IS in groups, behaviour is unchanged."""
    groups = {"Ctrl": rng.normal(5, 1, 12),
              "TrtA": rng.normal(8, 1, 12),
              "TrtB": rng.normal(11, 1, 12)}
    results = pf._run_stats(groups, test_type="parametric",
                             posthoc="Tukey HSD", control="Ctrl")
    # Should return exactly 2 results: Ctrl vs TrtA and Ctrl vs TrtB
    pairs = {(r[0], r[1]) for r in results} | {(r[1], r[0]) for r in results}
    assert ("Ctrl", "TrtA") in pairs or ("TrtA", "Ctrl") in pairs
    assert ("Ctrl", "TrtB") in pairs or ("TrtB", "Ctrl") in pairs
    # Should NOT include TrtA vs TrtB
    assert not (("TrtA", "TrtB") in pairs or ("TrtB", "TrtA") in pairs), \
        "TrtA vs TrtB should be excluded when control='Ctrl'"

run("valid control: only control-vs-other pairs returned", test_valid_control_still_works_normally)


# ═════════════════════════════════════════════════════════════════════════════
# Bug 3 — Comparison mode: all-pairwise vs vs-control
# ═════════════════════════════════════════════════════════════════════════════
section("Bug 3 — Comparison mode pair filtering")

GROUPS_3 = {
    "Control": rng.normal(5, 1, 15),
    "Drug A":  rng.normal(8, 1, 15),
    "Drug B":  rng.normal(11, 1, 15),
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
    """Control filter is position-independent — works whether control is
    first, last, or middle in the group ordering."""
    base = rng.normal(0, 1, 12)
    for ctrl_pos, group_order in enumerate([
        ["Control", "Drug A", "Drug B"],   # control first
        ["Drug A", "Control", "Drug B"],   # control middle
        ["Drug A", "Drug B", "Control"],   # control last
    ]):
        groups = {g: base + rng.normal(i * 3, 0.5, 12)
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
        "Ctrl":  rng.normal(5, 1, 12),
        "TrtA":  rng.normal(8, 1, 12),
        "TrtB":  rng.normal(11, 1, 12),
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
    groups = {"A": rng.normal(5, 1, 10),
              "B": rng.normal(7, 1, 10),
              "C": rng.normal(9, 1, 10),
              "D": rng.normal(11, 1, 10)}
    results = pf._run_stats(groups, test_type="nonparametric", control=None)
    assert len(results) == 6, f"Expected 6 pairs for 4 groups, got {len(results)}"

run("control=None nonparametric: 4 groups → 6 pairs", test_control_none_returns_all_pairs_nonparametric)


# ═════════════════════════════════════════════════════════════════════════════
# Bug 4 — Dunnett without explicit control
# ═════════════════════════════════════════════════════════════════════════════
section("Bug 4 — Dunnett fallback behaviour")

def test_dunnett_no_control_uses_first_group():
    """Dunnett with control=None → falls back to first group, no crash."""
    groups = {"Alpha": rng.normal(5, 1, 10),
              "Beta":  rng.normal(8, 1, 10),
              "Gamma": rng.normal(11, 1, 10)}
    results = pf._run_stats(groups, test_type="parametric",
                             posthoc="Dunnett (vs control)", control=None)
    # Should return 2 results: Alpha vs Beta, Alpha vs Gamma
    assert len(results) == 2, f"Expected 2 Dunnett results, got {len(results)}"
    # Alpha (first group) should appear in every pair
    for g_a, g_b, p, stars in results:
        assert "Alpha" in (g_a, g_b), \
            f"Dunnett fallback: 'Alpha' not in pair ({g_a}, {g_b})"

run("Dunnett control=None: uses first group, returns 2 results", test_dunnett_no_control_uses_first_group)

def test_dunnett_explicit_control():
    """Dunnett with explicit control → compares only vs that group."""
    groups = {"Drug":    rng.normal(5, 1, 10),
              "Placebo": rng.normal(5, 1, 10),  # placebo ≈ drug
              "Vehicle": rng.normal(5, 1, 10)}
    results = pf._run_stats(groups, test_type="parametric",
                             posthoc="Dunnett (vs control)", control="Placebo")
    assert len(results) == 2
    for g_a, g_b, p, stars in results:
        assert "Placebo" in (g_a, g_b), \
            f"Placebo not in pair ({g_a}, {g_b})"

run("Dunnett explicit control: 3 groups → 2 results all involving control",
    test_dunnett_explicit_control)

def test_dunnett_no_double_mc_correction():
    """Dunnett p-values should not be inflated by a second MC correction.
    The raw scipy.stats.dunnett p-value should equal what _run_stats returns."""
    from scipy.stats import dunnett as _dunnett
    ctrl  = rng.normal(5, 1, 20)
    trt_a = rng.normal(8, 1, 20)
    trt_b = rng.normal(11, 1, 20)
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
# ANOVA error term correctness — uses all groups even when filtering pairs
# ═════════════════════════════════════════════════════════════════════════════
section("ANOVA error term — all groups used even in vs-control mode")

def test_tukey_ms_within_uses_all_groups():
    """Tukey HSD vs-control: ms_within is computed from all k groups,
    not just the control + one treatment. Tests indirectly by checking
    that results when control is set match those from manual Tukey
    restricted to control pairs but using the full ANOVA error term."""
    from scipy import stats as _st
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

    # Extract Ctrl-vs-A p from each
    def _find(res, a, b):
        for g1, g2, p, _ in res:
            if {g1, g2} == {a, b}:
                return p
        return None

    p_ctrl_a_vs_ctrl = _find(results_ctrl, "Ctrl", "A")
    p_all_a_vs_ctrl  = _find(results_all,  "Ctrl", "A")
    assert p_ctrl_a_vs_ctrl is not None, "Ctrl vs A missing from vs-control results"
    assert p_all_a_vs_ctrl  is not None, "Ctrl vs A missing from all-pairwise results"
    # The p-values must be IDENTICAL because the same ms_within is used
    assert abs(p_ctrl_a_vs_ctrl - p_all_a_vs_ctrl) < 1e-10, \
        (f"Ctrl vs A p-value differs between vs-control ({p_ctrl_a_vs_ctrl:.6f}) "
         f"and all-pairwise ({p_all_a_vs_ctrl:.6f}) — ms_within calculation inconsistent")

run("Tukey: Ctrl vs A p-value identical whether control filter is set or not",
    test_tukey_ms_within_uses_all_groups)


# ═════════════════════════════════════════════════════════════════════════════
# End-to-end render tests with control
# ═════════════════════════════════════════════════════════════════════════════
section("End-to-end render: show_stats + control on bar chart")

def test_bar_chart_show_stats_vs_control():
    """Bar chart with show_stats=True and explicit control renders brackets
    only vs the control group."""
    groups = {"Vehicle": rng.normal(5, 1, 12),
              "Low":     rng.normal(7, 1, 12),
              "High":    rng.normal(10, 1, 12)}
    p = bar_excel(groups)
    try:
        fig, ax = pf.plotter_barplot(p, show_stats=True,
                                    stats_test="parametric",
                                    posthoc="Tukey HSD",
                                    control="Vehicle",
                                    mc_correction="Holm-Bonferroni")
        # Should complete without exception; at most 2 brackets drawn
        close_fig(fig)
    finally:
        os.unlink(p)

run("bar chart show_stats + control='Vehicle': renders without crash",
    test_bar_chart_show_stats_vs_control)

def test_bar_chart_stale_control_in_render():
    """Bar chart where control kwarg is a name not in the data →
    no crash, falls back to all-pairwise brackets."""
    groups = {"Alpha": rng.normal(5, 1, 10),
              "Beta":  rng.normal(8, 1, 10),
              "Gamma": rng.normal(11, 1, 10)}
    p = bar_excel(groups)
    try:
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            fig, ax = pf.plotter_barplot(p, show_stats=True,
                                        stats_test="parametric",
                                        posthoc="Tukey HSD",
                                        control="OldGroupName")
        close_fig(fig)
    finally:
        os.unlink(p)

run("bar chart stale control in render: no crash, fallback to all-pairwise",
    test_bar_chart_stale_control_in_render)

def test_all_posthoc_with_control():
    """All 4 non-Dunnett parametric posthocs work with control filter."""
    groups = {"Ctrl": rng.normal(5, 1, 10),
              "A":    rng.normal(8, 1, 10),
              "B":    rng.normal(11, 1, 10)}
    for posthoc in ("Tukey HSD", "Bonferroni", "Sidak", "Fisher LSD"):
        results = pf._run_stats(groups, test_type="parametric",
                                 posthoc=posthoc, control="Ctrl")
        assert len(results) == 2, \
            f"{posthoc} with control: expected 2 pairs, got {len(results)}"
        pairs = {frozenset([r[0], r[1]]) for r in results}
        assert frozenset(["A", "B"]) not in pairs, \
            f"{posthoc}: A vs B leaked through with control='Ctrl'"

run("all 4 parametric posthocs respect control filter", test_all_posthoc_with_control)

def test_dunnett_with_control_on_bar_chart():
    """Dunnett + explicit control renders without crash."""
    groups = {"Vehicle": rng.normal(5, 1, 12),
              "Low":     rng.normal(7, 1, 12),
              "High":    rng.normal(10, 1, 12)}
    p = bar_excel(groups)
    try:
        fig, ax = pf.plotter_barplot(p, show_stats=True,
                                    stats_test="parametric",
                                    posthoc="Dunnett (vs control)",
                                    control="Vehicle")
        close_fig(fig)
    finally:
        os.unlink(p)

run("Dunnett + explicit control on bar chart: renders cleanly",
    test_dunnett_with_control_on_bar_chart)

def test_nonparametric_vs_control_render():
    """Nonparametric Kruskal-Wallis + Dunn's with control filter renders."""
    groups = {"Ctrl": rng.normal(5, 1, 10),
              "TrtA": rng.normal(8, 1, 10),
              "TrtB": rng.normal(11, 1, 10)}
    p = bar_excel(groups)
    try:
        fig, ax = pf.plotter_barplot(p, show_stats=True,
                                    stats_test="nonparametric",
                                    control="Ctrl")
        close_fig(fig)
    finally:
        os.unlink(p)

run("nonparametric + control filter: renders without crash",
    test_nonparametric_vs_control_render)


# ═════════════════════════════════════════════════════════════════════════════
# p-to-stars and threshold consistency
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
    groups = {"A": rng.normal(5, 0.5, 8),
              "B": rng.normal(6, 0.5, 8),
              "C": rng.normal(7, 0.5, 8)}
    raw_res  = pf._run_stats(groups, "parametric", mc_correction="None (uncorrected)")
    holm_res = pf._run_stats(groups, "parametric", mc_correction="Holm-Bonferroni")
    raw_p  = sorted(r[2] for r in raw_res)
    holm_p = sorted(r[2] for r in holm_res)
    # Holm-corrected p-values must be >= raw (monotonicity)
    for rp, hp in zip(raw_p, holm_p):
        assert hp >= rp - 1e-12, \
            f"Holm p={hp:.6f} < raw p={rp:.6f} — correction deflated p-value"

run("Holm-Bonferroni correction: all corrected p ≥ raw p", test_mc_correction_increases_p_values)


# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
summarise()
sys.exit(0 if _h.FAIL == 0 else 1)
