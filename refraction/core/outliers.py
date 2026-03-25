"""ROUT outlier detection — GraphPad Prism's default method.

ROUT (Robust regression and OUtlier removal) identifies outliers using
a two-phase approach:

1. Fit a robust regression (using iteratively reweighted least squares
   with a bisquare weight function) to down-weight extreme points.
2. Compute residuals from the robust fit, then flag points whose
   absolute residuals exceed a threshold based on an FDR criterion.

This implementation supports both 1-D data (group-based, using the
robust location/scale) and X-Y data (robust linear regression).

Reference:
    Motulsky HJ, Brown RE (2006) BMC Bioinformatics 7:123.
    "Detecting outliers when fitting data with nonlinear regression —
    a new method based on robust nonlinear regression and the false
    discovery rate."
"""

from __future__ import annotations

import numpy as np
from scipy import stats as sp_stats


def _bisquare_weights(residuals: np.ndarray, c: float = 4.685) -> np.ndarray:
    """Tukey bisquare (biweight) weights for IRLS.

    Points with |r/MAD| > c get zero weight.
    """
    mad = np.median(np.abs(residuals - np.median(residuals)))
    if mad == 0:
        mad = 1e-12  # avoid division by zero
    u = residuals / (c * mad)
    w = np.where(np.abs(u) <= 1, (1 - u ** 2) ** 2, 0.0)
    return w


def rout_1d(
    values: np.ndarray,
    q: float = 1.0,
) -> dict:
    """ROUT outlier detection for a single group of values.

    Parameters
    ----------
    values : 1-D array of observations.
    q : FDR threshold (percent). Default 1.0 means Q=1% (Prism default).
        Higher Q → more aggressive outlier removal.

    Returns
    -------
    dict with keys:
        outlier_mask : bool array, True for outlier indices
        n_outliers : int
        robust_mean : float (robust location estimate)
        robust_sd : float (robust scale estimate)
    """
    vals = np.asarray(values, dtype=float)
    n = len(vals)
    if n < 4:
        return {
            "outlier_mask": np.zeros(n, dtype=bool),
            "n_outliers": 0,
            "robust_mean": float(np.mean(vals)) if n > 0 else float("nan"),
            "robust_sd": float(np.std(vals, ddof=1)) if n > 1 else 0.0,
        }

    # Phase 1: Robust location/scale via IRLS
    mu = np.median(vals)
    for _ in range(50):  # IRLS iterations
        residuals = vals - mu
        w = _bisquare_weights(residuals)
        w_sum = w.sum()
        if w_sum == 0:
            break
        mu_new = np.sum(w * vals) / w_sum
        if abs(mu_new - mu) < 1e-10:
            mu = mu_new
            break
        mu = mu_new

    # Robust scale: MAD-based (consistent with normal: multiply by 1.4826)
    residuals = vals - mu
    mad = np.median(np.abs(residuals))
    robust_sd = mad * 1.4826  # scale estimator consistent for normal

    if robust_sd == 0:
        return {
            "outlier_mask": np.zeros(n, dtype=bool),
            "n_outliers": 0,
            "robust_mean": float(mu),
            "robust_sd": 0.0,
        }

    # Phase 2: FDR-based outlier flagging
    # Use t-distribution with df = n - 1 for p-values
    df = n - 1
    abs_t = np.abs(residuals) / robust_sd
    p_values = 2.0 * sp_stats.t.sf(abs_t, df)

    # Benjamini-Hochberg FDR at level Q/100
    alpha = q / 100.0
    outlier_mask = _bh_fdr(p_values, alpha)

    return {
        "outlier_mask": outlier_mask,
        "n_outliers": int(outlier_mask.sum()),
        "robust_mean": float(mu),
        "robust_sd": float(robust_sd),
    }


def rout_xy(
    x: np.ndarray,
    y: np.ndarray,
    q: float = 1.0,
) -> dict:
    """ROUT outlier detection for X-Y (regression) data.

    Parameters
    ----------
    x, y : 1-D arrays of equal length.
    q : FDR threshold (percent). Default 1.0 (Q=1%).

    Returns
    -------
    dict with keys:
        outlier_mask : bool array
        n_outliers : int
        robust_slope : float
        robust_intercept : float
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    n = len(x)
    if n < 4:
        return {
            "outlier_mask": np.zeros(n, dtype=bool),
            "n_outliers": 0,
            "robust_slope": float("nan"),
            "robust_intercept": float("nan"),
        }

    # Phase 1: Robust linear regression via IRLS with bisquare weights
    # Initialize with OLS
    slope, intercept = np.polyfit(x, y, 1)
    for _ in range(50):
        residuals = y - (slope * x + intercept)
        w = _bisquare_weights(residuals)
        w_sum = w.sum()
        if w_sum < 2:
            break
        # Weighted least squares
        wx = w * x
        wy = w * y
        sw = w_sum
        sx = wx.sum()
        sy = wy.sum()
        sxx = (w * x * x).sum()
        sxy = (w * x * y).sum()
        denom = sw * sxx - sx * sx
        if abs(denom) < 1e-30:
            break
        slope_new = (sw * sxy - sx * sy) / denom
        intercept_new = (sy - slope_new * sx) / sw
        if abs(slope_new - slope) < 1e-10 and abs(intercept_new - intercept) < 1e-10:
            slope, intercept = slope_new, intercept_new
            break
        slope, intercept = slope_new, intercept_new

    # Phase 2: FDR-based outlier flagging
    residuals = y - (slope * x + intercept)
    mad = np.median(np.abs(residuals))
    robust_se = mad * 1.4826

    if robust_se == 0:
        return {
            "outlier_mask": np.zeros(n, dtype=bool),
            "n_outliers": 0,
            "robust_slope": float(slope),
            "robust_intercept": float(intercept),
        }

    df = max(n - 2, 1)
    abs_t = np.abs(residuals) / robust_se
    p_values = 2.0 * sp_stats.t.sf(abs_t, df)

    alpha = q / 100.0
    outlier_mask = _bh_fdr(p_values, alpha)

    return {
        "outlier_mask": outlier_mask,
        "n_outliers": int(outlier_mask.sum()),
        "robust_slope": float(slope),
        "robust_intercept": float(intercept),
    }


def _bh_fdr(p_values: np.ndarray, alpha: float) -> np.ndarray:
    """Benjamini-Hochberg FDR procedure. Returns bool mask of rejected hypotheses."""
    m = len(p_values)
    if m == 0:
        return np.zeros(0, dtype=bool)

    order = np.argsort(p_values)
    rejected = np.zeros(m, dtype=bool)

    # Find largest k such that p_(k) <= k/m * alpha
    threshold = np.arange(1, m + 1) / m * alpha
    sorted_p = p_values[order]

    # Find the cutoff
    below = sorted_p <= threshold
    if below.any():
        k = np.max(np.where(below)[0])
        rejected[order[:k + 1]] = True

    return rejected
