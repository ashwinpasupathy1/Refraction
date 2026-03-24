"""Nonlinear curve fitting engine using scipy.optimize.curve_fit.

Wraps the models in curve_models.py with proper fitting, goodness-of-fit
metrics, confidence intervals, and residual analysis.
"""

from __future__ import annotations

import logging
import warnings
from dataclasses import dataclass, field, asdict
from typing import Any

import numpy as np

_log = logging.getLogger(__name__)


@dataclass
class FitResult:
    """Result of a curve fit operation."""
    model_name: str
    params: dict[str, float]           # {param_name: fitted_value}
    param_errors: dict[str, float]     # {param_name: standard_error}
    param_ci_lower: dict[str, float]   # 95% CI lower bound
    param_ci_upper: dict[str, float]   # 95% CI upper bound
    r_squared: float
    adjusted_r_squared: float
    aic: float
    bic: float
    rmse: float
    residuals: list[float]
    x_fit: list[float]                 # Dense x values for plotting
    y_fit: list[float]                 # Predicted y at x_fit
    n_data: int
    n_params: int
    converged: bool
    message: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def fit_curve(
    x: np.ndarray,
    y: np.ndarray,
    model_name: str,
    *,
    initial_params: list[float] | None = None,
    max_iterations: int = 10000,
    confidence_level: float = 0.95,
) -> FitResult:
    """Fit a named model to (x, y) data.

    Args:
        x: Independent variable values (1-D array).
        y: Dependent variable values (1-D array, same length as x).
        model_name: Key from CURVE_MODELS dict.
        initial_params: Override initial parameter guesses.
        max_iterations: Maximum iterations for optimizer.
        confidence_level: Confidence level for parameter CIs (default 0.95).

    Returns:
        FitResult dataclass with fit parameters and diagnostics.

    Raises:
        ValueError: If model_name is unknown or data is insufficient.
    """
    from scipy.optimize import curve_fit
    from scipy.stats import t as t_dist
    from refraction.analysis.curve_models import CURVE_MODELS

    model = CURVE_MODELS.get(model_name)
    if model is None:
        raise ValueError(f"Unknown model: {model_name}")

    fn = model["fn"]
    param_names = model["params"]
    n_params = len(param_names)

    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)

    # Remove NaN
    mask = np.isfinite(x) & np.isfinite(y)
    x = x[mask]
    y = y[mask]

    n = len(x)
    if n < n_params:
        raise ValueError(
            f"Model '{model_name}' has {n_params} params but only {n} data points"
        )

    # Sort by x for cleaner output
    sort_idx = np.argsort(x)
    x = x[sort_idx]
    y = y[sort_idx]

    # Initial guesses
    if initial_params is not None:
        p0 = list(initial_params)
    elif model.get("guess"):
        try:
            p0 = model["guess"](x, y)
        except Exception:
            p0 = [1.0] * n_params
    else:
        p0 = [1.0] * n_params

    bounds = model.get("bounds")
    if bounds is None:
        bounds = (-np.inf, np.inf)

    # Fit
    converged = True
    message = ""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            popt, pcov = curve_fit(
                fn, x, y,
                p0=p0,
                bounds=bounds,
                maxfev=max_iterations,
                full_output=False,
            )
    except Exception as e:
        _log.debug("curve_fit failed for %s: %s", model_name, e)
        converged = False
        message = str(e)
        popt = np.array(p0, dtype=float)
        pcov = np.full((n_params, n_params), np.inf)

    # Predicted values and residuals
    y_pred = fn(x, *popt)
    residuals = y - y_pred

    # R-squared
    ss_res = float(np.sum(residuals ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    adj_r2 = 1.0 - (1.0 - r2) * (n - 1) / (n - n_params - 1) if n > n_params + 1 else float("nan")

    # RMSE
    rmse = float(np.sqrt(ss_res / n))

    # AIC and BIC
    if n > 0 and ss_res > 0:
        log_likelihood = -n / 2 * (np.log(2 * np.pi * ss_res / n) + 1)
        aic = float(2 * n_params - 2 * log_likelihood)
        bic = float(n_params * np.log(n) - 2 * log_likelihood)
    else:
        aic = float("nan")
        bic = float("nan")

    # Parameter standard errors and confidence intervals
    param_dict = {}
    param_errors = {}
    param_ci_lower = {}
    param_ci_upper = {}

    alpha = 1.0 - confidence_level
    dof = max(n - n_params, 1)
    t_val = t_dist.ppf(1.0 - alpha / 2, dof)

    for i, name in enumerate(param_names):
        param_dict[name] = float(popt[i])
        if np.isfinite(pcov[i, i]) and pcov[i, i] >= 0:
            se = float(np.sqrt(pcov[i, i]))
        else:
            se = float("nan")
        param_errors[name] = se
        param_ci_lower[name] = float(popt[i] - t_val * se)
        param_ci_upper[name] = float(popt[i] + t_val * se)

    # Dense x for plotting
    x_fit = np.linspace(float(x.min()), float(x.max()), 200)
    try:
        y_fit = fn(x_fit, *popt)
    except Exception:
        y_fit = np.full_like(x_fit, np.nan)

    return FitResult(
        model_name=model_name,
        params=param_dict,
        param_errors=param_errors,
        param_ci_lower=param_ci_lower,
        param_ci_upper=param_ci_upper,
        r_squared=r2,
        adjusted_r_squared=adj_r2,
        aic=aic,
        bic=bic,
        rmse=rmse,
        residuals=residuals.tolist(),
        x_fit=x_fit.tolist(),
        y_fit=y_fit.tolist() if isinstance(y_fit, np.ndarray) else [float(v) for v in y_fit],
        n_data=n,
        n_params=n_params,
        converged=converged,
        message=message,
    )


def compare_models(
    x: np.ndarray,
    y: np.ndarray,
    model_names: list[str],
    **fit_kwargs,
) -> list[FitResult]:
    """Fit multiple models and return results sorted by AIC (best first)."""
    results = []
    for name in model_names:
        try:
            r = fit_curve(x, y, name, **fit_kwargs)
            results.append(r)
        except Exception as e:
            _log.debug("compare_models: skipping %s (%s)", name, e)
    results.sort(key=lambda r: r.aic if np.isfinite(r.aic) else 1e18)
    return results
