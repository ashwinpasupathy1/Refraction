"""Build StatsBracket annotations from group data.

Runs the requested statistical test (t-test, ANOVA, etc.) and returns
a list of StatsBracket dataclass instances ready to attach to a ChartSpec.
"""

from __future__ import annotations

from refraction.analysis.schema import StatsBracket


def _p_to_label(p: float) -> str:
    """Convert a p-value to a significance label."""
    if p <= 0.001:
        return "***"
    if p <= 0.01:
        return "**"
    if p <= 0.05:
        return "*"
    return "ns"


def build_stats_brackets(
    groups: dict[str, list[float]],
    stats_test: str,
    posthoc: str = "",
    correction: str = "",
) -> list[StatsBracket]:
    """Compute pairwise comparisons and return StatsBracket list.

    Args:
        groups: Mapping of group name -> list of numeric values.
        stats_test: Name of the test (e.g. "t-test", "anova", "mann-whitney").
        posthoc: Post-hoc test name (for ANOVA).
        correction: Multiple-comparison correction method.

    Returns:
        List of StatsBracket instances, sorted by stacking_order.
    """
    if not stats_test:
        return []

    group_names = list(groups.keys())
    if len(group_names) < 2:
        return []

    brackets: list[StatsBracket] = []

    try:
        from scipy import stats as sp_stats
    except ImportError:
        return []

    test = stats_test.lower().replace("-", "").replace("_", "").replace(" ", "")

    if test in ("ttest", "unpairedttest", "studentttest"):
        # Pairwise t-tests between all pairs
        order = 0
        for i in range(len(group_names)):
            for j in range(i + 1, len(group_names)):
                a_vals = groups[group_names[i]]
                b_vals = groups[group_names[j]]
                if len(a_vals) < 2 or len(b_vals) < 2:
                    continue
                _, p = sp_stats.ttest_ind(a_vals, b_vals)
                brackets.append(StatsBracket(
                    group_a=group_names[i],
                    group_b=group_names[j],
                    p_value=p,
                    label=_p_to_label(p),
                    stacking_order=order,
                ))
                order += 1

    elif test in ("mannwhitney", "mannwhitneyutest", "mannwhitneyu"):
        order = 0
        for i in range(len(group_names)):
            for j in range(i + 1, len(group_names)):
                a_vals = groups[group_names[i]]
                b_vals = groups[group_names[j]]
                if len(a_vals) < 1 or len(b_vals) < 1:
                    continue
                _, p = sp_stats.mannwhitneyu(a_vals, b_vals, alternative="two-sided")
                brackets.append(StatsBracket(
                    group_a=group_names[i],
                    group_b=group_names[j],
                    p_value=p,
                    label=_p_to_label(p),
                    stacking_order=order,
                ))
                order += 1

    elif test in ("anova", "onewayanova"):
        all_vals = [groups[g] for g in group_names if len(groups[g]) >= 2]
        if len(all_vals) >= 2:
            _, p_omnibus = sp_stats.f_oneway(*all_vals)
            if p_omnibus <= 0.05:
                # Pairwise post-hoc (Tukey-like using t-tests as fallback)
                order = 0
                for i in range(len(group_names)):
                    for j in range(i + 1, len(group_names)):
                        a_vals = groups[group_names[i]]
                        b_vals = groups[group_names[j]]
                        if len(a_vals) < 2 or len(b_vals) < 2:
                            continue
                        _, p = sp_stats.ttest_ind(a_vals, b_vals)
                        brackets.append(StatsBracket(
                            group_a=group_names[i],
                            group_b=group_names[j],
                            p_value=p,
                            label=_p_to_label(p),
                            stacking_order=order,
                        ))
                        order += 1

    elif test in ("pairedttest", "pairedt"):
        # Only works for exactly 2 groups with matched observations
        if len(group_names) == 2:
            a_vals = groups[group_names[0]]
            b_vals = groups[group_names[1]]
            n = min(len(a_vals), len(b_vals))
            if n >= 2:
                _, p = sp_stats.ttest_rel(a_vals[:n], b_vals[:n])
                brackets.append(StatsBracket(
                    group_a=group_names[0],
                    group_b=group_names[1],
                    p_value=p,
                    label=_p_to_label(p),
                    stacking_order=0,
                ))

    elif test in ("kruskalwallis", "kruskal"):
        all_vals = [groups[g] for g in group_names if len(groups[g]) >= 1]
        if len(all_vals) >= 2:
            _, p_omnibus = sp_stats.kruskal(*all_vals)
            if p_omnibus <= 0.05:
                order = 0
                for i in range(len(group_names)):
                    for j in range(i + 1, len(group_names)):
                        a_vals = groups[group_names[i]]
                        b_vals = groups[group_names[j]]
                        if len(a_vals) < 1 or len(b_vals) < 1:
                            continue
                        _, p = sp_stats.mannwhitneyu(
                            a_vals, b_vals, alternative="two-sided"
                        )
                        brackets.append(StatsBracket(
                            group_a=group_names[i],
                            group_b=group_names[j],
                            p_value=p,
                            label=_p_to_label(p),
                            stacking_order=order,
                        ))
                        order += 1

    return brackets
