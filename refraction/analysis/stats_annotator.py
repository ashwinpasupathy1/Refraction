"""Converts raw _run_stats output into renderer-independent annotations."""

from __future__ import annotations

import numpy as np
from refraction.analysis.schema import (
    Bracket, Comparison, NormalityResult, StatsResult,
)


def annotate_stats(
    groups: dict[str, list[float]],
    *,
    stats_test: str = "parametric",
    posthoc: str = "Tukey HSD",
    mc_correction: str = "Holm-Bonferroni",
    control: str | None = None,
    n_permutations: int = 9999,
    mu0: float = 0.0,
    p_threshold: float = 0.05,
    show_ns: bool = False,
) -> tuple[StatsResult, list[Bracket]]:
    """Run statistical tests and return a StatsResult + bracket list.

    Args:
        groups: {name: [values]} dict of group data.
        stats_test: "parametric" | "nonparametric" | "paired" | "permutation" | "one_sample"
        posthoc: posthoc method name
        mc_correction: multiple comparison correction method
        control: control group name for vs-control comparisons
        n_permutations: number of permutation resamples
        mu0: null hypothesis mean for one-sample test
        p_threshold: significance threshold
        show_ns: include non-significant brackets

    Returns:
        (StatsResult, list[Bracket])
    """
    from refraction.core.chart_helpers import (
        _run_stats, check_normality, _cohens_d, _hedges_g,
        _rank_biserial_r,
    )

    # Convert lists to numpy arrays for _run_stats
    np_groups = {k: np.array(v, dtype=float) for k, v in groups.items()}

    # Run stats
    raw_results = _run_stats(
        np_groups,
        test_type=stats_test,
        posthoc=posthoc,
        mc_correction=mc_correction,
        control=control,
        n_permutations=n_permutations,
        mu0=mu0,
    )

    # Build comparisons with effect sizes
    comparisons = []
    for result_tuple in raw_results:
        ga, gb, p_adj, stars = result_tuple
        # Compute effect size if both groups exist
        effect_size = None
        effect_type = None
        if ga in np_groups and gb in np_groups:
            a, b = np_groups[ga], np_groups[gb]
            if stats_test in ("parametric", "paired"):
                effect_size = float(_cohens_d(a, b))
                effect_type = "Cohen's d"
            elif stats_test == "nonparametric":
                effect_size = float(_rank_biserial_r(a, b))
                effect_type = "rank-biserial r"

        comparisons.append(Comparison(
            group_a=str(ga),
            group_b=str(gb),
            p_raw=float(p_adj),  # _run_stats already applies correction
            p_adjusted=float(p_adj),
            stars=stars,
            effect_size=effect_size,
            effect_type=effect_type,
        ))

    # Build normality results
    # check_normality returns {name: (stat, p, is_normal, warning_msg)}
    normality_raw = check_normality(np_groups)
    normality = {}
    for k, v in normality_raw.items():
        _stat, _p, _is_normal, _msg = v
        if _p is not None:
            normality[k] = NormalityResult(shapiro_p=float(_p), normal=bool(_is_normal))
        else:
            normality[k] = NormalityResult(shapiro_p=0.0, normal=True)

    stats_result = StatsResult(
        test=_test_display_name(stats_test, posthoc, len(groups)),
        posthoc=posthoc if len(groups) > 2 else None,
        correction=mc_correction,
        comparisons=comparisons,
        normality=normality,
    )

    # Build brackets (only significant unless show_ns)
    brackets = []
    for comp in comparisons:
        if comp.stars == "ns" and not show_ns:
            continue
        brackets.append(Bracket(
            group_a=comp.group_a,
            group_b=comp.group_b,
            label=comp.stars,
            p=comp.p_adjusted,
        ))

    return stats_result, brackets


def _test_display_name(test_type: str, posthoc: str, k: int) -> str:
    """Human-readable test name for the stats result."""
    if test_type == "one_sample":
        return "One-sample t-test"
    if test_type == "paired":
        return "Paired t-test" if k == 2 else "Pairwise paired t-tests"
    if test_type == "parametric":
        if k == 2:
            return "Welch t-test"
        return f"One-way ANOVA + {posthoc}"
    if test_type == "nonparametric":
        if k == 2:
            return "Mann-Whitney U"
        return "Kruskal-Wallis + Dunn's"
    if test_type == "permutation":
        return "Permutation test"
    return test_type
