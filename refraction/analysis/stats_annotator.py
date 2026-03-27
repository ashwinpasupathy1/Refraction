"""Build StatsBracket annotations from group data.

Thin wrapper around ``refraction.core.stats._run_stats`` — the canonical
statistical computation layer.  This module converts the raw
(group_a, group_b, p_value, stars) tuples into StatsBracket dataclass
instances that the chart renderers consume.

Architecture
------------
::

    Analyzer (bar.py, box.py, etc.)
        │
        ▼
    stats_annotator.build_stats_brackets()
        │  maps test names → _run_stats conventions
        ▼
    core.stats._run_stats()          ← all math lives here
        │
        ▼
    List[StatsBracket]               ← for rendering

All statistical math (t-tests, ANOVA, Tukey HSD, Dunnett, Dunn, Mann-
Whitney, corrections, etc.) lives in ``refraction/core/stats.py``.  This
module does **no math** — it only translates between the analyzer config
vocabulary and the core stats API.

Test name mapping
-----------------
Analyzers / the Swift UI send short test names.  This module normalises
them into the ``test_type`` + ``posthoc`` arguments that ``_run_stats``
expects:

    ============== ======================== ========================
    Input          _run_stats test_type      _run_stats posthoc
    ============== ======================== ========================
    auto           parametric               Tukey HSD
    parametric     parametric               <from config>
    t-test         parametric (2 groups)    —
    welch_t-test   parametric (2 groups)    —
    anova          parametric               <from config>
    welch_anova    parametric               <from config>
    paired         paired                   —
    nonparametric  nonparametric            —
    mann-whitney   nonparametric (2 grp)    —
    kruskal-wallis nonparametric            —
    none / ""      (skip)                   —
    ============== ======================== ========================

Post-hoc mapping:

    ============ ========================
    Input        _run_stats posthoc
    ============ ========================
    tukey        Tukey HSD
    games_howell Tukey HSD  (*)
    dunn         Tukey HSD  (nonparametric path handles this)
    dunnett      Dunnett (vs control)
    bonferroni   Bonferroni
    sidak        Sidak
    fisher_lsd   Fisher LSD
    ============ ========================

    (*) Games-Howell is not yet in core/stats.py.  Welch-based pairwise
        comparisons with Tukey HSD correction are used as the closest
        approximation.  See ASHWIN_TODO.md for the full stats rewrite plan.

Correction mapping:

    ============ ========================
    Input        _run_stats mc_correction
    ============ ========================
    holm         Holm-Bonferroni
    bonferroni   Bonferroni
    fdr_bh       Benjamini-Hochberg (FDR)
    none / ""    None (uncorrected)
    ============ ========================
"""

from __future__ import annotations

import numpy as np

from refraction.analysis.schema import StatsBracket
from refraction.core.stats import (
    _run_stats,
    _cohens_d as _core_cohens_d,
    _p_to_stars,
    check_normality as _core_check_normality,
)


# ── Name mapping tables ──────────────────────────────────────────────────

_POSTHOC_MAP = {
    "tukey": "Tukey HSD",
    "tukeyhsd": "Tukey HSD",
    "games_howell": "Tukey HSD",   # closest approx until core supports it
    "gameshowell": "Tukey HSD",
    "dunn": "Tukey HSD",           # nonparametric path ignores posthoc
    "dunnett": "Dunnett (vs control)",
    "bonferroni": "Bonferroni",
    "sidak": "Sidak",
    "fisher_lsd": "Fisher LSD",
    "fisherlsd": "Fisher LSD",
}

_CORRECTION_MAP = {
    "holm": "Holm-Bonferroni",
    "holmbonferroni": "Holm-Bonferroni",
    "bonferroni": "Bonferroni",
    "fdr_bh": "Benjamini-Hochberg (FDR)",
    "fdrbh": "Benjamini-Hochberg (FDR)",
    "fdr": "Benjamini-Hochberg (FDR)",
    "benjaminihochberg": "Benjamini-Hochberg (FDR)",
    "none": "None (uncorrected)",
    "": "Holm-Bonferroni",  # default
}


def _normalise(s: str) -> str:
    """Lowercase, strip hyphens/underscores/spaces."""
    return s.lower().replace("-", "").replace("_", "").replace(" ", "")


def build_stats_brackets(
    groups: dict[str, list[float]],
    stats_test: str,
    posthoc: str = "",
    correction: str = "",
) -> list[StatsBracket]:
    """Compute pairwise comparisons and return StatsBracket list.

    This is the **only** stats entry point for dedicated analyzers.

    Parameters
    ----------
    groups : dict[str, list[float]]
        Mapping of group name → list of numeric values.
    stats_test : str
        Test name from the UI (see mapping table in module docstring).
    posthoc : str, optional
        Post-hoc method name (e.g. "tukey", "dunnett", "bonferroni").
    correction : str, optional
        Multiple-comparison correction (e.g. "holm", "bonferroni", "fdr_bh").

    Returns
    -------
    list[StatsBracket]
        Brackets sorted by stacking_order, ready for rendering.
    """
    if not stats_test or stats_test.lower() == "none":
        return []

    group_names = list(groups.keys())
    if len(group_names) < 2:
        return []

    # Convert list values to numpy arrays (what _run_stats expects)
    np_groups = {k: np.array(v, dtype=float) for k, v in groups.items()}

    # Resolve test_type for _run_stats
    test_type = _resolve_test_type(stats_test, len(group_names))

    # Resolve posthoc and correction
    ph_norm = _normalise(posthoc)
    core_posthoc = _POSTHOC_MAP.get(ph_norm, "Tukey HSD")

    corr_norm = _normalise(correction)
    core_correction = _CORRECTION_MAP.get(corr_norm, "Holm-Bonferroni")

    # Call the canonical stats engine
    raw_results = _run_stats(
        np_groups,
        test_type=test_type,
        posthoc=core_posthoc,
        mc_correction=core_correction,
    )

    # Convert (group_a, group_b, p_value, stars) → StatsBracket
    brackets = []
    for order, (ga, gb, p, stars) in enumerate(raw_results):
        brackets.append(StatsBracket(
            group_a=str(ga),
            group_b=str(gb),
            p_value=float(p),
            label=stars,
            stacking_order=order,
        ))

    return brackets


def _resolve_test_type(stats_test: str, n_groups: int) -> str:
    """Map a UI test name to a core _run_stats test_type string."""
    t = _normalise(stats_test)

    # Direct parametric tests
    if t in ("ttest", "unpairedttest", "studentttest", "welchttest", "welcht"):
        return "parametric"
    if t in ("anova", "onewayanova", "welchanova", "welchsanova"):
        return "parametric"
    if t in ("parametric", "auto"):
        return "parametric"

    # Paired
    if t in ("paired", "pairedttest", "pairedt"):
        return "paired"

    # Non-parametric
    if t in ("nonparametric", "mannwhitney", "mannwhitneyutest",
             "mannwhitneyu", "kruskalwallis", "kruskal"):
        return "nonparametric"

    # Permutation
    if t in ("permutation",):
        return "permutation"

    # One-sample
    if t in ("onesample",):
        return "one_sample"

    # Fallback
    return "parametric"


# ── Re-exported helpers (used by analyzers) ──────────────────────────────

def check_normality(values: list[float]) -> tuple[bool, float]:
    """Check if values follow a normal distribution (Shapiro-Wilk).

    Returns (is_normal, p_value).  Wraps ``core.stats.check_normality``
    with the simpler single-group signature that analyzers expect.
    """
    if len(values) < 3:
        return True, 1.0
    result = _core_check_normality({"_": np.array(values, dtype=float)})
    stat, p, is_normal, _ = result["_"]
    return is_normal, p


def _cohens_d(group_a: list[float], group_b: list[float]) -> float:
    """Cohen's d effect size.  Wraps ``core.stats._cohens_d``."""
    return float(_core_cohens_d(np.array(group_a), np.array(group_b)))


# Backward compatibility alias
annotate = build_stats_brackets
