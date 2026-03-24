"""Linked results tables — descriptive stats, normality tests, and
statistical comparisons returned alongside chart specs.

Each analyzer can call these helpers to build a standardized results
section that the Swift frontend renders as a table beneath the chart.
"""

from __future__ import annotations

from typing import Any

import numpy as np


def descriptive_stats(values: list[float] | np.ndarray, group_name: str = "") -> dict:
    """Compute descriptive statistics for a single group.

    Returns dict with keys: group, n, mean, sd, sem, median, min, max,
    q1, q3, iqr, ci95_lower, ci95_upper.
    """
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    n = len(arr)
    if n == 0:
        return {
            "group": group_name,
            "n": 0,
            "mean": None,
            "sd": None,
            "sem": None,
            "median": None,
            "min": None,
            "max": None,
            "q1": None,
            "q3": None,
            "iqr": None,
            "ci95_lower": None,
            "ci95_upper": None,
        }

    mean = float(np.mean(arr))
    sd = float(np.std(arr, ddof=1)) if n > 1 else 0.0
    sem = sd / np.sqrt(n) if n > 1 else 0.0
    q1 = float(np.percentile(arr, 25))
    q3 = float(np.percentile(arr, 75))

    # 95% CI on the mean using t-distribution
    from scipy.stats import t as t_dist
    if n > 1:
        t_val = t_dist.ppf(0.975, n - 1)
        ci95_lower = mean - t_val * sem
        ci95_upper = mean + t_val * sem
    else:
        ci95_lower = mean
        ci95_upper = mean

    return {
        "group": group_name,
        "n": n,
        "mean": round(mean, 6),
        "sd": round(sd, 6),
        "sem": round(sem, 6),
        "median": round(float(np.median(arr)), 6),
        "min": round(float(np.min(arr)), 6),
        "max": round(float(np.max(arr)), 6),
        "q1": round(q1, 6),
        "q3": round(q3, 6),
        "iqr": round(q3 - q1, 6),
        "ci95_lower": round(ci95_lower, 6),
        "ci95_upper": round(ci95_upper, 6),
    }


def normality_test(values: list[float] | np.ndarray, group_name: str = "") -> dict:
    """Run Shapiro-Wilk normality test on a group.

    Returns dict with keys: group, test, statistic, p, normal (bool).
    """
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    n = len(arr)

    if n < 3:
        return {
            "group": group_name,
            "test": "Shapiro-Wilk",
            "statistic": None,
            "p": None,
            "normal": None,
        }

    from scipy.stats import shapiro
    stat, p = shapiro(arr)
    return {
        "group": group_name,
        "test": "Shapiro-Wilk",
        "statistic": round(float(stat), 6),
        "p": round(float(p), 6),
        "normal": bool(p > 0.05),
    }


def two_group_test(
    values_a: list[float] | np.ndarray,
    values_b: list[float] | np.ndarray,
    group_a: str = "A",
    group_b: str = "B",
    paired: bool = False,
) -> dict:
    """Run appropriate two-sample test (Welch t-test or paired t-test).

    Returns dict with: test, groups, statistic, p, effect_size, effect_type.
    """
    a = np.asarray(values_a, dtype=float)
    b = np.asarray(values_b, dtype=float)
    a = a[np.isfinite(a)]
    b = b[np.isfinite(b)]

    from scipy.stats import ttest_ind, ttest_rel

    if paired and len(a) == len(b) and len(a) >= 2:
        stat, p = ttest_rel(a, b)
        test_name = "Paired t-test"
        # Effect size: Cohen's d for paired
        diff = a - b
        d = float(np.mean(diff) / np.std(diff, ddof=1)) if np.std(diff, ddof=1) > 0 else 0.0
    else:
        stat, p = ttest_ind(a, b, equal_var=False)
        test_name = "Welch t-test"
        # Cohen's d pooled
        pooled_std = np.sqrt(
            ((len(a) - 1) * np.var(a, ddof=1) + (len(b) - 1) * np.var(b, ddof=1))
            / (len(a) + len(b) - 2)
        ) if len(a) + len(b) > 2 else 1.0
        d = float((np.mean(a) - np.mean(b)) / pooled_std) if pooled_std > 0 else 0.0

    return {
        "test": test_name,
        "groups": [group_a, group_b],
        "statistic": round(float(stat), 6),
        "p": round(float(p), 6),
        "effect_size": round(abs(d), 4),
        "effect_type": "Cohen's d",
    }


def multi_group_test(
    groups: dict[str, list[float] | np.ndarray],
) -> dict:
    """Run one-way ANOVA (or Kruskal-Wallis if non-normal).

    Returns dict with: test, statistic, p, groups.
    """
    from scipy.stats import f_oneway, kruskal

    arrays = []
    names = list(groups.keys())
    for name in names:
        arr = np.asarray(groups[name], dtype=float)
        arr = arr[np.isfinite(arr)]
        if len(arr) >= 2:
            arrays.append(arr)

    if len(arrays) < 2:
        return {"test": "One-way ANOVA", "statistic": None, "p": None, "groups": names}

    try:
        stat, p = f_oneway(*arrays)
        return {
            "test": "One-way ANOVA",
            "statistic": round(float(stat), 6),
            "p": round(float(p), 6),
            "groups": names,
        }
    except Exception:
        try:
            stat, p = kruskal(*arrays)
            return {
                "test": "Kruskal-Wallis",
                "statistic": round(float(stat), 6),
                "p": round(float(p), 6),
                "groups": names,
            }
        except Exception:
            return {"test": "One-way ANOVA", "statistic": None, "p": None, "groups": names}


def build_results_section(
    groups: dict[str, list[float] | np.ndarray],
    *,
    paired: bool = False,
) -> dict:
    """Build a complete results section for grouped data.

    Returns dict with keys: descriptive, normality, tests.
    """
    group_names = list(groups.keys())

    # Descriptive stats
    desc = [descriptive_stats(groups[g], g) for g in group_names]

    # Normality tests
    norm = [normality_test(groups[g], g) for g in group_names]

    # Statistical tests
    tests = []
    if len(group_names) == 2:
        tests.append(
            two_group_test(
                groups[group_names[0]],
                groups[group_names[1]],
                group_names[0],
                group_names[1],
                paired=paired,
            )
        )
    elif len(group_names) > 2:
        tests.append(multi_group_test(groups))
        # Also pairwise comparisons
        for i in range(len(group_names)):
            for j in range(i + 1, len(group_names)):
                tests.append(
                    two_group_test(
                        groups[group_names[i]],
                        groups[group_names[j]],
                        group_names[i],
                        group_names[j],
                        paired=paired,
                    )
                )

    return {
        "descriptive": desc,
        "normality": norm,
        "tests": tests,
    }
