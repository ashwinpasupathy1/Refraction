"""
refraction.core.stats
=====================
Shared statistical computation functions for both the matplotlib chart
path (chart_helpers.py) and the Plotly spec builders (refraction/specs/).

This module extracts reusable statistical primitives so that spec builders
do not need to hand-roll their own SEM / mean / SD calculations.
"""

from __future__ import annotations

import math
from typing import List, Optional, Sequence, Tuple, Union

import numpy as np


# ---------------------------------------------------------------------------
# Descriptive statistics
# ---------------------------------------------------------------------------

def calc_mean(vals: Sequence[float]) -> float:
    """Return the arithmetic mean, or NaN if empty."""
    if len(vals) == 0:
        return float("nan")
    return float(np.mean(vals))


def calc_sd(vals: Sequence[float], ddof: int = 1) -> float:
    """Return sample standard deviation (Bessel-corrected by default).

    Returns 0.0 when n <= ddof to avoid division-by-zero.
    """
    n = len(vals)
    if n <= ddof:
        return 0.0
    return float(np.std(vals, ddof=ddof))


def calc_sem(vals: Sequence[float]) -> float:
    """Return standard error of the mean.

    SEM = SD / sqrt(n).  Returns 0.0 when n < 2.
    """
    n = len(vals)
    if n < 2:
        return 0.0
    sd = calc_sd(vals)
    return sd / math.sqrt(n)


def calc_error(vals: Sequence[float], error_type: str = "sem") -> Tuple[float, float]:
    """Return (mean, error_bar_half_width) for a given error type.

    error_type: "sem", "sd", or "ci95".
    """
    from scipy import stats as _stats

    n = len(vals)
    m = calc_mean(vals)
    sd = calc_sd(vals)
    if error_type == "sem":
        return m, sd / math.sqrt(n) if n > 0 else 0.0
    elif error_type == "sd":
        return m, sd
    else:  # ci95
        ci = _stats.t.ppf(0.975, df=max(n - 1, 1)) * sd / math.sqrt(max(n, 1))
        return m, float(ci)


def descriptive_stats(vals: Sequence[float]) -> dict:
    """Return a dict of common descriptive statistics for a numeric array.

    Keys: n, mean, sd, sem, min, median, max.
    """
    arr = np.asarray(vals, dtype=float)
    n = len(arr)
    if n == 0:
        nan = float("nan")
        return dict(n=0, mean=nan, sd=nan, sem=nan, min=nan, median=nan, max=nan)
    m = float(np.mean(arr))
    sd = float(np.std(arr, ddof=1)) if n > 1 else float("nan")
    sem = sd / math.sqrt(n) if n > 1 else float("nan")
    return dict(
        n=n,
        mean=m,
        sd=sd,
        sem=sem,
        min=float(np.min(arr)),
        median=float(np.median(arr)),
        max=float(np.max(arr)),
    )
