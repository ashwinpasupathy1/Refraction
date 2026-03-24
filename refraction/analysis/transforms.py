"""Column transformations for data preprocessing.

Each transform operates on a pandas Series and returns a new Series.
Used by the /transform API endpoint and the SwiftUI config panel.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

import numpy as np
import pandas as pd

_log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Transform registry
# ---------------------------------------------------------------------------

_TRANSFORMS: dict[str, dict[str, Any]] = {}


def _register(name: str, *, category: str, doc: str, params: list[str] | None = None):
    """Decorator to register a transform function."""
    def decorator(fn: Callable):
        _TRANSFORMS[name] = {
            "fn": fn,
            "category": category,
            "doc": doc,
            "params": params or [],
        }
        return fn
    return decorator


# ── Logarithmic transforms ────────────────────────────────────────────────

@_register("log10", category="Logarithmic", doc="Common logarithm (base 10)")
def _log10(s: pd.Series, **kw) -> pd.Series:
    return np.log10(s.clip(lower=1e-300))

@_register("ln", category="Logarithmic", doc="Natural logarithm")
def _ln(s: pd.Series, **kw) -> pd.Series:
    return np.log(s.clip(lower=1e-300))

@_register("log2", category="Logarithmic", doc="Logarithm base 2")
def _log2(s: pd.Series, **kw) -> pd.Series:
    return np.log2(s.clip(lower=1e-300))

@_register("exp", category="Logarithmic", doc="Exponential (e^x)")
def _exp(s: pd.Series, **kw) -> pd.Series:
    return np.exp(s)

@_register("exp10", category="Logarithmic", doc="Power of 10 (10^x)")
def _exp10(s: pd.Series, **kw) -> pd.Series:
    return 10.0 ** s

# ── Normalization ─────────────────────────────────────────────────────────

@_register("normalize_percent", category="Normalization",
           doc="Normalize to 0-100% of maximum")
def _normalize_percent(s: pd.Series, **kw) -> pd.Series:
    mx = s.max()
    return (s / mx) * 100 if mx != 0 else s * 0

@_register("normalize_zscore", category="Normalization",
           doc="Z-score normalization (mean=0, std=1)")
def _normalize_zscore(s: pd.Series, **kw) -> pd.Series:
    std = s.std()
    return (s - s.mean()) / std if std != 0 else s * 0

@_register("normalize_minmax", category="Normalization",
           doc="Min-max normalization to [0, 1]")
def _normalize_minmax(s: pd.Series, **kw) -> pd.Series:
    mn, mx = s.min(), s.max()
    rng = mx - mn
    return (s - mn) / rng if rng != 0 else s * 0

@_register("normalize_robust", category="Normalization",
           doc="Robust normalization using median and IQR",
           params=[])
def _normalize_robust(s: pd.Series, **kw) -> pd.Series:
    med = s.median()
    q1, q3 = s.quantile(0.25), s.quantile(0.75)
    iqr = q3 - q1
    return (s - med) / iqr if iqr != 0 else s * 0

@_register("normalize_fraction", category="Normalization",
           doc="Normalize as fraction of total (sum = 1)")
def _normalize_fraction(s: pd.Series, **kw) -> pd.Series:
    total = s.sum()
    return s / total if total != 0 else s * 0

# ── Arithmetic transforms ────────────────────────────────────────────────

@_register("reciprocal", category="Arithmetic", doc="Reciprocal (1/x)")
def _reciprocal(s: pd.Series, **kw) -> pd.Series:
    return 1.0 / s.replace(0, np.nan)

@_register("square_root", category="Arithmetic", doc="Square root")
def _square_root(s: pd.Series, **kw) -> pd.Series:
    return np.sqrt(s.clip(lower=0))

@_register("square", category="Arithmetic", doc="Square (x^2)")
def _square(s: pd.Series, **kw) -> pd.Series:
    return s ** 2

@_register("cube_root", category="Arithmetic", doc="Cube root")
def _cube_root(s: pd.Series, **kw) -> pd.Series:
    return np.cbrt(s)

@_register("abs", category="Arithmetic", doc="Absolute value")
def _abs(s: pd.Series, **kw) -> pd.Series:
    return np.abs(s)

@_register("negate", category="Arithmetic", doc="Negate (-x)")
def _negate(s: pd.Series, **kw) -> pd.Series:
    return -s

@_register("add_constant", category="Arithmetic", doc="Add a constant",
           params=["value"])
def _add_constant(s: pd.Series, *, value: float = 0, **kw) -> pd.Series:
    return s + value

@_register("multiply_constant", category="Arithmetic", doc="Multiply by a constant",
           params=["value"])
def _multiply_constant(s: pd.Series, *, value: float = 1, **kw) -> pd.Series:
    return s * value

@_register("power", category="Arithmetic", doc="Raise to power",
           params=["exponent"])
def _power(s: pd.Series, *, exponent: float = 2, **kw) -> pd.Series:
    return s ** exponent

# ── Statistical / rank ────────────────────────────────────────────────────

@_register("rank", category="Statistical", doc="Rank transform")
def _rank(s: pd.Series, **kw) -> pd.Series:
    return s.rank()

@_register("percentile_rank", category="Statistical",
           doc="Percentile rank (0-100)")
def _percentile_rank(s: pd.Series, **kw) -> pd.Series:
    return s.rank(pct=True) * 100

@_register("cumsum", category="Statistical", doc="Cumulative sum")
def _cumsum(s: pd.Series, **kw) -> pd.Series:
    return s.cumsum()

@_register("diff", category="Statistical", doc="First difference")
def _diff(s: pd.Series, **kw) -> pd.Series:
    return s.diff()

@_register("pct_change", category="Statistical",
           doc="Percent change from previous value")
def _pct_change(s: pd.Series, **kw) -> pd.Series:
    return s.pct_change() * 100

@_register("rolling_mean", category="Statistical",
           doc="Rolling mean (moving average)",
           params=["window"])
def _rolling_mean(s: pd.Series, *, window: int = 3, **kw) -> pd.Series:
    return s.rolling(max(int(window), 1), min_periods=1).mean()

@_register("rolling_median", category="Statistical",
           doc="Rolling median",
           params=["window"])
def _rolling_median(s: pd.Series, *, window: int = 3, **kw) -> pd.Series:
    return s.rolling(max(int(window), 1), min_periods=1).median()

@_register("rolling_std", category="Statistical",
           doc="Rolling standard deviation",
           params=["window"])
def _rolling_std(s: pd.Series, *, window: int = 3, **kw) -> pd.Series:
    return s.rolling(max(int(window), 1), min_periods=1).std()

@_register("ewm_mean", category="Statistical",
           doc="Exponentially weighted moving average",
           params=["span"])
def _ewm_mean(s: pd.Series, *, span: int = 3, **kw) -> pd.Series:
    return s.ewm(span=max(int(span), 1)).mean()

# ── Baseline / reference ─────────────────────────────────────────────────

@_register("subtract_baseline", category="Baseline",
           doc="Subtract first value (baseline correction)")
def _subtract_baseline(s: pd.Series, **kw) -> pd.Series:
    first = s.dropna().iloc[0] if len(s.dropna()) > 0 else 0
    return s - first

@_register("fold_change", category="Baseline",
           doc="Fold change relative to reference value",
           params=["reference"])
def _fold_change(s: pd.Series, *, reference: float | None = None, **kw) -> pd.Series:
    if reference is None:
        first = s.dropna().iloc[0] if len(s.dropna()) > 0 else 1
        reference = float(first)
    return s / reference if reference != 0 else s * np.nan

@_register("subtract_mean", category="Baseline",
           doc="Subtract group mean (center at zero)")
def _subtract_mean(s: pd.Series, **kw) -> pd.Series:
    return s - s.mean()

@_register("subtract_median", category="Baseline",
           doc="Subtract group median")
def _subtract_median(s: pd.Series, **kw) -> pd.Series:
    return s - s.median()

@_register("log2_fold_change", category="Baseline",
           doc="Log2 fold change vs reference",
           params=["reference"])
def _log2_fold_change(s: pd.Series, *, reference: float | None = None, **kw) -> pd.Series:
    if reference is None:
        first = s.dropna().iloc[0] if len(s.dropna()) > 0 else 1
        reference = float(first)
    ratio = s / reference if reference != 0 else s * np.nan
    return np.log2(ratio.clip(lower=1e-300))

# ── Winsorization / outlier handling ──────────────────────────────────────

@_register("winsorize", category="Outlier handling",
           doc="Winsorize at given percentile",
           params=["percentile"])
def _winsorize(s: pd.Series, *, percentile: float = 5, **kw) -> pd.Series:
    lo = s.quantile(percentile / 100)
    hi = s.quantile(1 - percentile / 100)
    return s.clip(lower=lo, upper=hi)

@_register("clip", category="Outlier handling",
           doc="Clip values to [lower, upper]",
           params=["lower", "upper"])
def _clip(s: pd.Series, *, lower: float = 0, upper: float = 100, **kw) -> pd.Series:
    return s.clip(lower=lower, upper=upper)

@_register("replace_outliers_nan", category="Outlier handling",
           doc="Replace outliers (>3 SD from mean) with NaN")
def _replace_outliers_nan(s: pd.Series, **kw) -> pd.Series:
    mean, std = s.mean(), s.std()
    if std == 0:
        return s.copy()
    return s.where(np.abs(s - mean) <= 3 * std, np.nan)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def transform_column(
    df: pd.DataFrame,
    col: str | int,
    operation: str,
    **kwargs,
) -> pd.Series:
    """Apply a named transformation to a DataFrame column.

    Args:
        df: Source DataFrame.
        col: Column name or index.
        operation: Transform name (key from the registry).
        **kwargs: Extra params for transforms that accept them.

    Returns:
        Transformed pd.Series.

    Raises:
        ValueError: If operation is unknown or column not found.
    """
    if operation not in _TRANSFORMS:
        raise ValueError(f"Unknown transform: {operation}")

    if isinstance(col, int):
        if col >= len(df.columns):
            raise ValueError(f"Column index {col} out of range")
        series = pd.to_numeric(df.iloc[:, col], errors="coerce")
    else:
        if col not in df.columns:
            raise ValueError(f"Column '{col}' not found in DataFrame")
        series = pd.to_numeric(df[col], errors="coerce")

    fn = _TRANSFORMS[operation]["fn"]
    return fn(series, **kwargs)


def list_transforms() -> dict[str, list[dict]]:
    """Return available transforms grouped by category."""
    result: dict[str, list[dict]] = {}
    for name, info in _TRANSFORMS.items():
        cat = info["category"]
        if cat not in result:
            result[cat] = []
        result[cat].append({
            "key": name,
            "doc": info["doc"],
            "params": info["params"],
        })
    return result


def transform_count() -> int:
    """Return total number of registered transforms."""
    return len(_TRANSFORMS)
