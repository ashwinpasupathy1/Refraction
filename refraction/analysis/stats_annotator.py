"""Statistical annotation builder for ChartSpec.

Runs statistical tests on group data and returns Bracket + NormalityResult
objects ready to attach to a ChartSpec.annotations field.
"""

from __future__ import annotations

import itertools
import math
from typing import Any, Dict, List, Optional

import numpy as np
from scipy import stats as sp_stats

from refraction.analysis.schema import Bracket, NormalityResult


# ── Stars mapping ─────────────────────────────────────────────────────────────

def _p_to_stars(p: float) -> str:
    if p <= 0.0001:
        return "****"
    if p <= 0.001:
        return "***"
    if p <= 0.01:
        return "**"
    if p <= 0.05:
        return "*"
    return "ns"


# ── Cohen's d ─────────────────────────────────────────────────────────────────

def _cohens_d(a: np.ndarray, b: np.ndarray) -> Optional[float]:
    """Pooled-SD Cohen's d.  Returns None if either group has < 2 values."""
    n1, n2 = len(a), len(b)
    if n1 < 2 or n2 < 2:
        return None
    pooled_sd = math.sqrt(
        ((n1 - 1) * float(np.var(a, ddof=1)) +
         (n2 - 1) * float(np.var(b, ddof=1))) / (n1 + n2 - 2)
    )
    if pooled_sd == 0:
        return None
    return float((np.mean(a) - np.mean(b)) / pooled_sd)


# ── Normality ─────────────────────────────────────────────────────────────────

def check_normality(groups: Dict[str, np.ndarray],
                    alpha: float = 0.05) -> List[NormalityResult]:
    """Shapiro-Wilk normality test per group."""
    results: List[NormalityResult] = []
    for name, vals in groups.items():
        clean = vals[~np.isnan(vals)] if hasattr(vals, '__len__') else vals
        n = len(clean)
        if n < 3:
            results.append(NormalityResult(
                group=name, statistic=None, p_value=None, is_normal=None,
                warning=f"'{name}': too few values (n={n}) for normality test",
            ))
            continue
        stat, p = sp_stats.shapiro(clean)
        is_normal = p > alpha
        warning = (f"'{name}': non-normal (Shapiro-Wilk p={p:.4f})"
                   if not is_normal else None)
        results.append(NormalityResult(
            group=name, statistic=float(stat), p_value=float(p),
            is_normal=is_normal, warning=warning,
        ))
    return results


# ── Main annotator ────────────────────────────────────────────────────────────

def annotate(groups: Dict[str, np.ndarray],
             stats_test: Optional[str] = None,
             **kw) -> tuple[List[Bracket], List[NormalityResult]]:
    """Run stats on *groups* and return (brackets, normality_results).

    Parameters
    ----------
    groups : dict mapping group name -> 1-D numpy array of values
    stats_test : "parametric" | "nonparametric" | None
    """
    normality = check_normality(groups)

    if stats_test is None or len(groups) < 2:
        return [], normality

    labels = list(groups.keys())
    k = len(labels)
    brackets: List[Bracket] = []

    if stats_test == "parametric":
        if k == 2:
            a, b = labels
            _, p = sp_stats.ttest_ind(groups[a], groups[b], equal_var=False)
            p = float(p)
            d = _cohens_d(groups[a], groups[b])
            brackets.append(Bracket(
                group_a=a, group_b=b, p_value=p,
                stars=_p_to_stars(p), effect_size=d,
            ))
        else:
            # ANOVA omnibus then pairwise Welch t-tests (Tukey-style)
            _, p_anova = sp_stats.f_oneway(*[groups[g] for g in labels])
            if p_anova < 0.05:
                pairs = list(itertools.combinations(labels, 2))
                for a, b in pairs:
                    _, p = sp_stats.ttest_ind(groups[a], groups[b],
                                              equal_var=False)
                    p = float(p)
                    d = _cohens_d(groups[a], groups[b])
                    brackets.append(Bracket(
                        group_a=a, group_b=b, p_value=p,
                        stars=_p_to_stars(p), effect_size=d,
                    ))

    elif stats_test == "nonparametric":
        if k == 2:
            a, b = labels
            _, p = sp_stats.mannwhitneyu(groups[a], groups[b],
                                          alternative="two-sided")
            p = float(p)
            d = _cohens_d(groups[a], groups[b])
            brackets.append(Bracket(
                group_a=a, group_b=b, p_value=p,
                stars=_p_to_stars(p), effect_size=d,
            ))
        else:
            _, p_kw = sp_stats.kruskal(*[groups[g] for g in labels])
            if p_kw < 0.05:
                pairs = list(itertools.combinations(labels, 2))
                for a, b in pairs:
                    _, p = sp_stats.mannwhitneyu(groups[a], groups[b],
                                                  alternative="two-sided")
                    p = float(p)
                    d = _cohens_d(groups[a], groups[b])
                    brackets.append(Bracket(
                        group_a=a, group_b=b, p_value=p,
                        stars=_p_to_stars(p), effect_size=d,
                    ))

    # Sort by span width (narrow first) and assign stacking order
    label_idx = {name: i for i, name in enumerate(labels)}
    brackets.sort(key=lambda br: abs(label_idx.get(br.group_b, 0) -
                                      label_idx.get(br.group_a, 0)))
    for i, br in enumerate(brackets):
        br.stacking_order = i

    return brackets, normality
