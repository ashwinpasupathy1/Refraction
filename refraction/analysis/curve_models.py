"""Nonlinear curve fitting library — 100+ models organized by category.

Each model is a dict with:
    fn:        callable(x, *params) -> y
    params:    list of parameter names
    category:  str category name
    bounds:    tuple of (lower_bounds, upper_bounds) or None
    guess:     callable(x, y) -> list of initial guesses, or None
    doc:       short description
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np


def _safe_div(a, b, default=0.0):
    """Division with fallback for zero denominator."""
    return a / b if b != 0 else default


# ---------------------------------------------------------------------------
# Initial guess strategies
# ---------------------------------------------------------------------------

def _guess_linear(x, y):
    """Slope and intercept from endpoints."""
    if len(x) < 2:
        return [1.0, 0.0]
    slope = (y[-1] - y[0]) / (x[-1] - x[0]) if x[-1] != x[0] else 1.0
    intercept = y[0] - slope * x[0]
    return [slope, intercept]


def _guess_exponential_growth(x, y):
    y_pos = np.maximum(y, 1e-10)
    y0 = float(y_pos[0])
    if len(x) >= 2 and x[-1] != x[0]:
        k = float(np.log(y_pos[-1] / y_pos[0]) / (x[-1] - x[0]))
    else:
        k = 0.1
    return [y0, k]


def _guess_exponential_decay(x, y):
    y0, k = _guess_exponential_growth(x, y)
    return [y0, abs(k), float(np.min(y))]


def _guess_dose_response_4pl(x, y):
    top = float(np.max(y))
    bottom = float(np.min(y))
    ec50 = float(np.median(x))
    return [top, bottom, ec50, 1.0]


def _guess_michaelis_menten(x, y):
    vmax = float(np.max(y)) * 1.2
    km = float(np.median(x))
    return [vmax, km]


def _guess_gaussian(x, y):
    amp = float(np.max(y))
    mu = float(x[np.argmax(y)])
    sigma = float((np.max(x) - np.min(x)) / 6)
    return [amp, mu, max(sigma, 0.01)]


def _guess_logistic(x, y):
    L = float(np.max(y))
    k = 1.0
    x0 = float(np.median(x))
    return [L, k, x0]


def _guess_hill(x, y):
    vmax = float(np.max(y))
    kd = float(np.median(x))
    n = 1.0
    return [vmax, kd, n]


def _guess_gompertz(x, y):
    a = float(np.max(y))
    b = 2.0
    c = 0.5
    return [a, b, c]


def _guess_power(x, y):
    return [1.0, 1.0]


def _guess_biexponential(x, y):
    y0 = float(y[0]) if len(y) > 0 else 1.0
    return [y0 * 0.6, 0.1, y0 * 0.4, 0.01]


def _guess_one_site_binding(x, y):
    bmax = float(np.max(y))
    kd = float(np.median(x))
    return [bmax, kd]


def _guess_biphasic_dose_response(x, y):
    top = float(np.max(y))
    bottom = float(np.min(y))
    x_sorted = np.sort(x)
    ec50_1 = float(x_sorted[len(x_sorted) // 3])
    ec50_2 = float(x_sorted[2 * len(x_sorted) // 3])
    return [top, bottom, 0.5, ec50_1, 1.0, ec50_2, 1.0]


# ---------------------------------------------------------------------------
# Model functions
# ---------------------------------------------------------------------------

# Dose-response models
def _dose_response_4pl(x, top, bottom, ec50, hill):
    return bottom + (top - bottom) / (1.0 + (ec50 / np.maximum(x, 1e-15)) ** hill)

def _dose_response_3pl(x, top, bottom, ec50):
    return bottom + (top - bottom) / (1.0 + ec50 / np.maximum(x, 1e-15))

def _dose_response_5pl(x, top, bottom, ec50, hill, asym):
    return bottom + (top - bottom) / (1.0 + (ec50 / np.maximum(x, 1e-15)) ** hill) ** asym

def _log_dose_response_4pl(x, top, bottom, logec50, hill):
    return bottom + (top - bottom) / (1.0 + 10 ** ((logec50 - x) * hill))

def _log_dose_response_3pl(x, top, bottom, logec50):
    return bottom + (top - bottom) / (1.0 + 10 ** (logec50 - x))

def _biphasic_dose_response(x, top, bottom, frac1, ec50_1, hill1, ec50_2, hill2):
    r1 = frac1 * (top - bottom) / (1.0 + (ec50_1 / np.maximum(x, 1e-15)) ** hill1)
    r2 = (1 - frac1) * (top - bottom) / (1.0 + (ec50_2 / np.maximum(x, 1e-15)) ** hill2)
    return bottom + r1 + r2

# Enzyme kinetics
def _michaelis_menten(x, vmax, km):
    return vmax * x / (km + x)

def _competitive_inhibition(x, vmax, km, ki, i_conc):
    return vmax * x / (km * (1 + i_conc / ki) + x)

def _uncompetitive_inhibition(x, vmax, km, ki, i_conc):
    return vmax * x / (km + x * (1 + i_conc / ki))

def _noncompetitive_inhibition(x, vmax, km, ki, i_conc):
    return vmax * x / ((km + x) * (1 + i_conc / ki))

def _substrate_inhibition(x, vmax, km, ki):
    return vmax * x / (km + x + x ** 2 / ki)

def _allosteric_michaelis_menten(x, vmax, k_half, n):
    return vmax * x ** n / (k_half ** n + x ** n)

def _ping_pong(x, vmax, ka, kb):
    # simplified ping-pong: x is substrate concentration, assume co-substrate saturating
    return vmax * x / (ka + x)

# Growth curves
def _exponential_growth(x, y0, k):
    return y0 * np.exp(k * x)

def _exponential_plateau(x, y0, ymax, k):
    return ymax - (ymax - y0) * np.exp(-k * x)

def _logistic_growth(x, L, k, x0):
    return L / (1.0 + np.exp(-k * (x - x0)))

def _gompertz_growth(x, a, b, c):
    return a * np.exp(-b * np.exp(-c * x))

def _richards_growth(x, a, k, nu, x0):
    return a / (1.0 + nu * np.exp(-k * (x - x0))) ** (1.0 / nu)

def _von_bertalanffy(x, linf, k, t0):
    return linf * (1 - np.exp(-k * (x - t0)))

def _weibull_growth(x, a, b, c):
    return a * (1 - np.exp(-(x / b) ** c))

def _monomolecular(x, a, b):
    return a * (1 - np.exp(-b * x))

def _baranyi(x, ymax, y0, mu, lag):
    """Simplified Baranyi growth model."""
    A = x - lag + (1.0 / mu) * np.log(np.exp(-mu * (x - lag)) + np.exp(-mu * 0) - np.exp(-mu * (x - lag + 0)))
    return ymax + np.log10((-1 + np.exp(mu * np.maximum(A, 0)) + np.exp(mu * 0)) / (np.exp(mu * 0)))

def _ricker(x, a, b):
    return a * x * np.exp(-b * x)

def _beverton_holt(x, a, b):
    return a * x / (1 + b * x)

# Decay models
def _one_phase_decay(x, y0, k, plateau):
    return (y0 - plateau) * np.exp(-k * x) + plateau

def _two_phase_decay(x, a1, k1, a2, k2):
    return a1 * np.exp(-k1 * x) + a2 * np.exp(-k2 * x)

def _three_phase_decay(x, a1, k1, a2, k2, a3, k3):
    return a1 * np.exp(-k1 * x) + a2 * np.exp(-k2 * x) + a3 * np.exp(-k3 * x)

def _exponential_decay(x, y0, k):
    return y0 * np.exp(-k * x)

def _power_decay(x, a, b):
    return a * np.maximum(x, 1e-15) ** (-b)

def _stretched_exponential(x, a, k, beta):
    return a * np.exp(-(k * x) ** beta)

def _radioactive_decay(x, n0, half_life):
    return n0 * np.exp(-0.693147 * x / half_life)

# Binding models
def _one_site_binding(x, bmax, kd):
    return bmax * x / (kd + x)

def _two_site_binding(x, bmax1, kd1, bmax2, kd2):
    return bmax1 * x / (kd1 + x) + bmax2 * x / (kd2 + x)

def _one_site_binding_ns(x, bmax, kd, ns):
    return bmax * x / (kd + x) + ns * x

def _cooperative_binding(x, bmax, kd, n):
    return bmax * x ** n / (kd ** n + x ** n)

def _scatchard(x, bmax, kd):
    """Scatchard transform: bound/free vs bound."""
    return (bmax - x) / kd

def _langmuir_adsorption(x, qmax, kl):
    return qmax * kl * x / (1 + kl * x)

def _freundlich(x, kf, n):
    return kf * np.maximum(x, 1e-15) ** (1.0 / n)

def _hill_binding(x, bmax, kd, n):
    return bmax * x ** n / (kd ** n + x ** n)

# Polynomial models
def _linear(x, m, b):
    return m * x + b

def _quadratic(x, a, b, c):
    return a * x ** 2 + b * x + c

def _cubic(x, a, b, c, d):
    return a * x ** 3 + b * x ** 2 + c * x + d

def _quartic(x, a, b, c, d, e):
    return a * x ** 4 + b * x ** 3 + c * x ** 2 + d * x + e

def _quintic(x, a, b, c, d, e, f):
    return a * x ** 5 + b * x ** 4 + c * x ** 3 + d * x ** 2 + e * x + f

def _power_law(x, a, b):
    return a * np.maximum(x, 1e-15) ** b

def _inverse(x, a, b):
    return a / np.maximum(x, 1e-15) + b

def _inverse_square(x, a, b):
    return a / np.maximum(x ** 2, 1e-15) + b

def _proportional(x, a):
    return a * x

def _log_linear(x, a, b):
    return a * np.log(np.maximum(x, 1e-15)) + b

def _exp_linear(x, a, b, c):
    return a * np.exp(b * x) + c

def _reciprocal_quadratic(x, a, b, c):
    return 1.0 / (a * x ** 2 + b * x + c)

# Sigmoidal models
def _boltzmann(x, top, bottom, v50, slope):
    return bottom + (top - bottom) / (1.0 + np.exp((v50 - x) / slope))

def _hill_equation(x, vmax, kd, n):
    return vmax * x ** n / (kd ** n + x ** n)

def _logistic_4p(x, a, b, c, d):
    return d + (a - d) / (1.0 + (x / c) ** b)

def _logistic_5p(x, a, b, c, d, g):
    return d + (a - d) / (1.0 + (x / c) ** b) ** g

def _probit(x, a, b):
    from scipy.special import ndtr
    return ndtr(a + b * x)

def _weibull_sigmoid(x, a, b, c, d):
    return d + (a - d) * np.exp(-np.exp(-b * (x - c)))

def _log_logistic(x, a, b, c, d):
    return d + (a - d) / (1.0 + (np.maximum(x, 1e-15) / c) ** b)

def _tanh_sigmoid(x, a, b, c, d):
    return a * np.tanh(b * (x - c)) + d

# Gaussian / peak models
def _gaussian(x, amp, mu, sigma):
    return amp * np.exp(-0.5 * ((x - mu) / sigma) ** 2)

def _gaussian_offset(x, amp, mu, sigma, offset):
    return amp * np.exp(-0.5 * ((x - mu) / sigma) ** 2) + offset

def _sum_of_2_gaussians(x, a1, mu1, s1, a2, mu2, s2):
    return (a1 * np.exp(-0.5 * ((x - mu1) / s1) ** 2) +
            a2 * np.exp(-0.5 * ((x - mu2) / s2) ** 2))

def _sum_of_3_gaussians(x, a1, mu1, s1, a2, mu2, s2, a3, mu3, s3):
    return (a1 * np.exp(-0.5 * ((x - mu1) / s1) ** 2) +
            a2 * np.exp(-0.5 * ((x - mu2) / s2) ** 2) +
            a3 * np.exp(-0.5 * ((x - mu3) / s3) ** 2))

def _lorentzian(x, amp, x0, gamma):
    return amp * gamma ** 2 / (gamma ** 2 + (x - x0) ** 2)

def _voigt(x, amp, mu, sigma, gamma):
    """Pseudo-Voigt approximation."""
    g = amp * np.exp(-0.5 * ((x - mu) / sigma) ** 2)
    l = amp * gamma ** 2 / (gamma ** 2 + (x - mu) ** 2)
    eta = 0.5  # mixing parameter
    return eta * l + (1 - eta) * g

def _emg(x, amp, mu, sigma, tau):
    """Exponentially modified Gaussian."""
    from scipy.special import erfc
    z = (mu + sigma ** 2 / tau - x) / (sigma * np.sqrt(2))
    return (amp * sigma / tau) * np.sqrt(np.pi / 2) * np.exp(
        0.5 * (sigma / tau) ** 2 - (x - mu) / tau
    ) * erfc(z)

def _lognormal(x, amp, mu, sigma):
    safe_x = np.maximum(x, 1e-15)
    return amp / (safe_x * sigma * np.sqrt(2 * np.pi)) * np.exp(
        -0.5 * ((np.log(safe_x) - mu) / sigma) ** 2
    )

def _asymmetric_gaussian(x, amp, mu, sigma_l, sigma_r):
    result = np.where(
        x < mu,
        amp * np.exp(-0.5 * ((x - mu) / sigma_l) ** 2),
        amp * np.exp(-0.5 * ((x - mu) / sigma_r) ** 2),
    )
    return result

# Pharmacokinetics
def _one_compartment_oral(x, dose, ka, ke, v):
    return dose * ka / (v * (ka - ke)) * (np.exp(-ke * x) - np.exp(-ka * x))

def _one_compartment_iv(x, dose, ke, v):
    return (dose / v) * np.exp(-ke * x)

def _two_compartment_iv(x, a, alpha, b, beta):
    return a * np.exp(-alpha * x) + b * np.exp(-beta * x)

# Thermodynamics / physical chemistry
def _arrhenius(x, a, ea):
    """Arrhenius: k = A * exp(-Ea / (R*T)), x = 1/T."""
    R = 8.314
    return a * np.exp(-ea / (R * x))

def _van_t_hoff(x, dh, ds):
    """ln(K) = -dH/RT + dS/R, returns K. x = temperature in K."""
    R = 8.314
    return np.exp(-dh / (R * x) + ds / R)

# Miscellaneous
def _sinusoidal(x, amp, freq, phase, offset):
    return amp * np.sin(2 * np.pi * freq * x + phase) + offset

def _damped_sine(x, amp, freq, phase, decay, offset):
    return amp * np.exp(-decay * x) * np.sin(2 * np.pi * freq * x + phase) + offset

def _bilinear(x, a1, b1, a2, b2, x_break):
    """Two-segment piecewise linear."""
    return np.where(x < x_break, a1 * x + b1, a2 * x + b2)

def _segmented_linear_3(x, a1, b1, x1, a2, b2, x2, a3, b3):
    """Three-segment piecewise linear."""
    return np.where(x < x1, a1 * x + b1,
                    np.where(x < x2, a2 * x + b2, a3 * x + b3))

def _rectangular_hyperbola(x, a, b):
    return a * x / (b + x)

def _emax(x, e0, emax, ec50):
    return e0 + emax * x / (ec50 + x)

def _emax_sigmoidal(x, e0, emax, ec50, n):
    return e0 + emax * x ** n / (ec50 ** n + x ** n)

def _bliss_independence(x, a, b):
    """Simple Bliss model: E = a + b - a*b."""
    return a + b * x - a * b * x

def _four_param_log_logistic(x, b, c, d, e):
    return c + (d - c) / (1 + (np.maximum(x, 1e-15) / e) ** b)

def _brain_cousens(x, b, c, d, e, f):
    """Hormesis model (Brain-Cousens)."""
    return c + (d - c + f * x) / (1 + (np.maximum(x, 1e-15) / e) ** b)

def _cedergreen_ritz_streibig(x, b, c, d, e, f, alpha):
    """Hormesis model (Cedergreen-Ritz-Streibig)."""
    return c + (d - c + f * np.exp(-1.0 / (np.maximum(x, 1e-15) ** alpha))) / (
        1 + (np.maximum(x, 1e-15) / e) ** b
    )

# Saturation / clearance
def _eadie_hofstee(x, vmax, km):
    """Eadie-Hofstee linearization: v = Vmax - Km * (v/[S])."""
    return vmax - km * x

def _lineweaver_burk(x, vmax, km):
    """1/v = (Km/Vmax)(1/[S]) + 1/Vmax, x = 1/[S]."""
    return km / vmax * x + 1.0 / vmax

def _hanes_woolf(x, vmax, km):
    """[S]/v = [S]/Vmax + Km/Vmax, x = [S]."""
    return x / vmax + km / vmax


# Additional models to reach 100+

# More dose-response
def _gaddum_schild(x, emax, ec50, n, kb, b_conc):
    """Gaddum/Schild equation for competitive antagonism."""
    dr = 1 + b_conc / kb
    return emax * x ** n / ((ec50 * dr) ** n + x ** n)

# More enzyme kinetics
def _hill_kinetics(x, vmax, s50, n):
    return vmax * x ** n / (s50 ** n + x ** n)

def _ordered_bi_bi(x, vmax, ka, kb):
    """Simplified ordered Bi Bi mechanism."""
    return vmax * x / (ka * kb + kb * x + x)

# More growth
def _schnute(x, a, b, c, d):
    """Schnute growth model."""
    return (a + (b - a) * (1 - np.exp(-c * x)) / (1 - np.exp(-c * d))) if c != 0 else a

def _negative_exponential(x, a, b):
    return a * (1 - np.exp(-b * x))

def _theta_logistic(x, r, k, theta, n0):
    """Theta-logistic growth (simplified discrete approx)."""
    return k / (1 + ((k / n0) ** theta - 1) * np.exp(-r * x))

# More binding
def _bivalent_binding(x, bmax, kd1, kd2):
    return bmax * x / (kd1 + x) * (1 + x / (kd2 + x))

def _competition_binding(x, top, bottom, logki, logconc):
    """Competition binding curve."""
    return bottom + (top - bottom) / (1 + 10 ** (x - logki))

# More peak/spectral
def _pearson_vii(x, amp, x0, w, m):
    """Pearson VII peak shape."""
    return amp * (1 + ((x - x0) / w) ** 2 * (2 ** (1 / m) - 1)) ** (-m)

def _pseudo_voigt_full(x, amp, mu, sigma, eta):
    """Full pseudo-Voigt with mixing parameter eta."""
    g = amp * np.exp(-0.5 * ((x - mu) / sigma) ** 2)
    l = amp / (1 + ((x - mu) / sigma) ** 2)
    return eta * l + (1 - eta) * g

def _double_lorentzian(x, a1, x01, g1, a2, x02, g2):
    return (a1 * g1 ** 2 / (g1 ** 2 + (x - x01) ** 2) +
            a2 * g2 ** 2 / (g2 ** 2 + (x - x02) ** 2))

# More decay / relaxation
def _kohlrausch(x, a, tau, beta):
    """Kohlrausch stretched exponential relaxation."""
    return a * np.exp(-(x / tau) ** beta)

def _biexponential_rise_decay(x, a1, k_rise, a2, k_decay):
    """Rise then decay."""
    return a1 * (1 - np.exp(-k_rise * x)) * a2 * np.exp(-k_decay * x)

# More pharmacology
def _clark_equation(x, emax, kd):
    """Clark's occupation theory."""
    return emax * x / (kd + x)

def _operational_model(x, emax, kd, tau, n):
    """Black-Leff operational model."""
    return emax * (tau * x / kd) ** n / ((tau * x / kd) ** n + (1 + x / kd) ** n)

# More statistical distributions as curves
def _beta_pdf(x, a_param, b_param, scale):
    """Beta distribution PDF (scaled)."""
    from scipy.special import beta as beta_fn
    safe_x = np.clip(x, 1e-10, 1 - 1e-10)
    return scale * safe_x ** (a_param - 1) * (1 - safe_x) ** (b_param - 1) / beta_fn(a_param, b_param)

def _gamma_pdf(x, k_shape, theta, scale):
    """Gamma distribution PDF (scaled)."""
    from scipy.special import gamma as gamma_fn
    safe_x = np.maximum(x, 1e-15)
    return scale * safe_x ** (k_shape - 1) * np.exp(-safe_x / theta) / (theta ** k_shape * gamma_fn(k_shape))

def _weibull_pdf(x, k_shape, lam, scale):
    """Weibull distribution PDF (scaled)."""
    safe_x = np.maximum(x, 1e-15)
    return scale * (k_shape / lam) * (safe_x / lam) ** (k_shape - 1) * np.exp(-(safe_x / lam) ** k_shape)

def _rayleigh(x, sigma, scale):
    """Rayleigh distribution."""
    safe_x = np.maximum(x, 0)
    return scale * safe_x / sigma ** 2 * np.exp(-safe_x ** 2 / (2 * sigma ** 2))

def _exponential_pdf(x, lam, scale):
    """Exponential distribution PDF."""
    return scale * lam * np.exp(-lam * np.maximum(x, 0))


# ---------------------------------------------------------------------------
# Master model registry
# ---------------------------------------------------------------------------

CURVE_MODELS: dict[str, dict[str, Any]] = {
    # ── Dose-response (6 models) ──
    "dose_response_4pl": {
        "fn": _dose_response_4pl,
        "params": ["Top", "Bottom", "EC50", "HillSlope"],
        "category": "Dose-response",
        "bounds": ([-np.inf, -np.inf, 0, -np.inf], [np.inf, np.inf, np.inf, np.inf]),
        "guess": _guess_dose_response_4pl,
        "doc": "Four-parameter logistic dose-response curve",
    },
    "dose_response_3pl": {
        "fn": _dose_response_3pl,
        "params": ["Top", "Bottom", "EC50"],
        "category": "Dose-response",
        "bounds": ([-np.inf, -np.inf, 0], [np.inf, np.inf, np.inf]),
        "guess": lambda x, y: _guess_dose_response_4pl(x, y)[:3],
        "doc": "Three-parameter logistic (Hill slope fixed at 1)",
    },
    "dose_response_5pl": {
        "fn": _dose_response_5pl,
        "params": ["Top", "Bottom", "EC50", "HillSlope", "Asymmetry"],
        "category": "Dose-response",
        "bounds": ([-np.inf, -np.inf, 0, -np.inf, 0], [np.inf, np.inf, np.inf, np.inf, np.inf]),
        "guess": lambda x, y: _guess_dose_response_4pl(x, y) + [1.0],
        "doc": "Five-parameter logistic with asymmetry factor",
    },
    "log_dose_response_4pl": {
        "fn": _log_dose_response_4pl,
        "params": ["Top", "Bottom", "LogEC50", "HillSlope"],
        "category": "Dose-response",
        "bounds": None,
        "guess": lambda x, y: [float(np.max(y)), float(np.min(y)), float(np.median(x)), 1.0],
        "doc": "4PL dose-response with log(concentration) on X axis",
    },
    "log_dose_response_3pl": {
        "fn": _log_dose_response_3pl,
        "params": ["Top", "Bottom", "LogEC50"],
        "category": "Dose-response",
        "bounds": None,
        "guess": lambda x, y: [float(np.max(y)), float(np.min(y)), float(np.median(x))],
        "doc": "3PL dose-response with log(concentration) on X axis",
    },
    "biphasic_dose_response": {
        "fn": _biphasic_dose_response,
        "params": ["Top", "Bottom", "Fraction1", "EC50_1", "Hill1", "EC50_2", "Hill2"],
        "category": "Dose-response",
        "bounds": ([-np.inf, -np.inf, 0, 0, -np.inf, 0, -np.inf],
                   [np.inf, np.inf, 1, np.inf, np.inf, np.inf, np.inf]),
        "guess": _guess_biphasic_dose_response,
        "doc": "Biphasic dose-response with two EC50 values",
    },

    # ── Enzyme kinetics (8 models) ──
    "michaelis_menten": {
        "fn": _michaelis_menten,
        "params": ["Vmax", "Km"],
        "category": "Enzyme kinetics",
        "bounds": ([0, 0], [np.inf, np.inf]),
        "guess": _guess_michaelis_menten,
        "doc": "Michaelis-Menten enzyme kinetics: V = Vmax*[S]/(Km+[S])",
    },
    "competitive_inhibition": {
        "fn": _competitive_inhibition,
        "params": ["Vmax", "Km", "Ki", "I_conc"],
        "category": "Enzyme kinetics",
        "bounds": ([0, 0, 0, 0], [np.inf, np.inf, np.inf, np.inf]),
        "guess": lambda x, y: list(_guess_michaelis_menten(x, y)) + [1.0, 0.1],
        "doc": "Competitive inhibition kinetics",
    },
    "uncompetitive_inhibition": {
        "fn": _uncompetitive_inhibition,
        "params": ["Vmax", "Km", "Ki", "I_conc"],
        "category": "Enzyme kinetics",
        "bounds": ([0, 0, 0, 0], [np.inf, np.inf, np.inf, np.inf]),
        "guess": lambda x, y: list(_guess_michaelis_menten(x, y)) + [1.0, 0.1],
        "doc": "Uncompetitive inhibition kinetics",
    },
    "noncompetitive_inhibition": {
        "fn": _noncompetitive_inhibition,
        "params": ["Vmax", "Km", "Ki", "I_conc"],
        "category": "Enzyme kinetics",
        "bounds": ([0, 0, 0, 0], [np.inf, np.inf, np.inf, np.inf]),
        "guess": lambda x, y: list(_guess_michaelis_menten(x, y)) + [1.0, 0.1],
        "doc": "Noncompetitive inhibition kinetics",
    },
    "substrate_inhibition": {
        "fn": _substrate_inhibition,
        "params": ["Vmax", "Km", "Ki"],
        "category": "Enzyme kinetics",
        "bounds": ([0, 0, 0], [np.inf, np.inf, np.inf]),
        "guess": lambda x, y: list(_guess_michaelis_menten(x, y)) + [float(np.max(x)) * 2],
        "doc": "Substrate inhibition: V = Vmax*[S]/(Km + [S] + [S]^2/Ki)",
    },
    "allosteric_michaelis_menten": {
        "fn": _allosteric_michaelis_menten,
        "params": ["Vmax", "K_half", "n"],
        "category": "Enzyme kinetics",
        "bounds": ([0, 0, 0.1], [np.inf, np.inf, 20]),
        "guess": lambda x, y: list(_guess_michaelis_menten(x, y)) + [1.0],
        "doc": "Allosteric Michaelis-Menten with Hill coefficient",
    },
    "eadie_hofstee": {
        "fn": _eadie_hofstee,
        "params": ["Vmax", "Km"],
        "category": "Enzyme kinetics",
        "bounds": None,
        "guess": _guess_michaelis_menten,
        "doc": "Eadie-Hofstee linearization",
    },
    "lineweaver_burk": {
        "fn": _lineweaver_burk,
        "params": ["Vmax", "Km"],
        "category": "Enzyme kinetics",
        "bounds": ([0, 0], [np.inf, np.inf]),
        "guess": _guess_michaelis_menten,
        "doc": "Lineweaver-Burk double-reciprocal plot",
    },

    # ── Growth curves (12 models) ──
    "exponential_growth": {
        "fn": _exponential_growth,
        "params": ["Y0", "K"],
        "category": "Growth",
        "bounds": ([0, -np.inf], [np.inf, np.inf]),
        "guess": _guess_exponential_growth,
        "doc": "Exponential growth: Y = Y0 * exp(K*X)",
    },
    "exponential_plateau": {
        "fn": _exponential_plateau,
        "params": ["Y0", "Ymax", "K"],
        "category": "Growth",
        "bounds": None,
        "guess": lambda x, y: [float(y[0]), float(np.max(y)), 0.1],
        "doc": "Exponential approach to plateau",
    },
    "logistic_growth": {
        "fn": _logistic_growth,
        "params": ["L", "k", "x0"],
        "category": "Growth",
        "bounds": ([0, 0, -np.inf], [np.inf, np.inf, np.inf]),
        "guess": _guess_logistic,
        "doc": "Logistic growth: L / (1 + exp(-k*(x-x0)))",
    },
    "gompertz": {
        "fn": _gompertz_growth,
        "params": ["a", "b", "c"],
        "category": "Growth",
        "bounds": ([0, 0, 0], [np.inf, np.inf, np.inf]),
        "guess": _guess_gompertz,
        "doc": "Gompertz growth curve: a * exp(-b * exp(-c*x))",
    },
    "richards_growth": {
        "fn": _richards_growth,
        "params": ["a", "k", "nu", "x0"],
        "category": "Growth",
        "bounds": ([0, 0, 0.01, -np.inf], [np.inf, np.inf, 100, np.inf]),
        "guess": lambda x, y: [float(np.max(y)), 1.0, 1.0, float(np.median(x))],
        "doc": "Richards growth (generalized logistic)",
    },
    "von_bertalanffy": {
        "fn": _von_bertalanffy,
        "params": ["Linf", "K", "t0"],
        "category": "Growth",
        "bounds": ([0, 0, -np.inf], [np.inf, np.inf, np.inf]),
        "guess": lambda x, y: [float(np.max(y)) * 1.2, 0.1, float(np.min(x))],
        "doc": "Von Bertalanffy growth",
    },
    "weibull_growth": {
        "fn": _weibull_growth,
        "params": ["a", "b", "c"],
        "category": "Growth",
        "bounds": ([0, 0, 0], [np.inf, np.inf, np.inf]),
        "guess": lambda x, y: [float(np.max(y)), float(np.median(x)), 1.0],
        "doc": "Weibull growth curve",
    },
    "monomolecular": {
        "fn": _monomolecular,
        "params": ["a", "b"],
        "category": "Growth",
        "bounds": ([0, 0], [np.inf, np.inf]),
        "guess": lambda x, y: [float(np.max(y)), 0.1],
        "doc": "Monomolecular growth: a*(1-exp(-b*x))",
    },
    "ricker": {
        "fn": _ricker,
        "params": ["a", "b"],
        "category": "Growth",
        "bounds": ([0, 0], [np.inf, np.inf]),
        "guess": lambda x, y: [float(np.max(y)), 0.1],
        "doc": "Ricker population model",
    },
    "beverton_holt": {
        "fn": _beverton_holt,
        "params": ["a", "b"],
        "category": "Growth",
        "bounds": ([0, 0], [np.inf, np.inf]),
        "guess": lambda x, y: [2.0, 0.01],
        "doc": "Beverton-Holt population model",
    },
    "power_growth": {
        "fn": _power_law,
        "params": ["a", "b"],
        "category": "Growth",
        "bounds": ([0, 0], [np.inf, np.inf]),
        "guess": _guess_power,
        "doc": "Power-law growth: a * x^b",
    },
    "log_linear_growth": {
        "fn": _log_linear,
        "params": ["a", "b"],
        "category": "Growth",
        "bounds": None,
        "guess": lambda x, y: [1.0, float(y[0])],
        "doc": "Log-linear growth: a*ln(x) + b",
    },

    # ── Decay (7 models) ──
    "one_phase_decay": {
        "fn": _one_phase_decay,
        "params": ["Y0", "K", "Plateau"],
        "category": "Decay",
        "bounds": None,
        "guess": _guess_exponential_decay,
        "doc": "One-phase exponential decay to plateau",
    },
    "two_phase_decay": {
        "fn": _two_phase_decay,
        "params": ["A1", "K1", "A2", "K2"],
        "category": "Decay",
        "bounds": ([0, 0, 0, 0], [np.inf, np.inf, np.inf, np.inf]),
        "guess": _guess_biexponential,
        "doc": "Two-phase (biexponential) decay",
    },
    "three_phase_decay": {
        "fn": _three_phase_decay,
        "params": ["A1", "K1", "A2", "K2", "A3", "K3"],
        "category": "Decay",
        "bounds": ([0, 0, 0, 0, 0, 0], [np.inf] * 6),
        "guess": lambda x, y: [float(y[0]) * 0.5, 0.5, float(y[0]) * 0.3, 0.1, float(y[0]) * 0.2, 0.01],
        "doc": "Three-phase exponential decay",
    },
    "exponential_decay": {
        "fn": _exponential_decay,
        "params": ["Y0", "K"],
        "category": "Decay",
        "bounds": ([0, 0], [np.inf, np.inf]),
        "guess": lambda x, y: [float(y[0]), 0.1],
        "doc": "Simple exponential decay: Y0*exp(-K*x)",
    },
    "power_decay": {
        "fn": _power_decay,
        "params": ["a", "b"],
        "category": "Decay",
        "bounds": ([0, 0], [np.inf, np.inf]),
        "guess": lambda x, y: [float(y[0]), 1.0],
        "doc": "Power-law decay: a * x^(-b)",
    },
    "stretched_exponential": {
        "fn": _stretched_exponential,
        "params": ["A", "K", "Beta"],
        "category": "Decay",
        "bounds": ([0, 0, 0], [np.inf, np.inf, 2]),
        "guess": lambda x, y: [float(y[0]), 0.1, 1.0],
        "doc": "Stretched exponential (Kohlrausch-Williams-Watts)",
    },
    "radioactive_decay": {
        "fn": _radioactive_decay,
        "params": ["N0", "HalfLife"],
        "category": "Decay",
        "bounds": ([0, 0], [np.inf, np.inf]),
        "guess": lambda x, y: [float(y[0]), float((x[-1] - x[0]) / 3)],
        "doc": "Radioactive decay with half-life parameter",
    },

    # ── Binding (8 models) ──
    "one_site_binding": {
        "fn": _one_site_binding,
        "params": ["Bmax", "Kd"],
        "category": "Binding",
        "bounds": ([0, 0], [np.inf, np.inf]),
        "guess": _guess_one_site_binding,
        "doc": "One-site specific binding: Bmax*X/(Kd+X)",
    },
    "two_site_binding": {
        "fn": _two_site_binding,
        "params": ["Bmax1", "Kd1", "Bmax2", "Kd2"],
        "category": "Binding",
        "bounds": ([0, 0, 0, 0], [np.inf, np.inf, np.inf, np.inf]),
        "guess": lambda x, y: [float(np.max(y)) * 0.6, float(np.median(x)) * 0.5,
                                float(np.max(y)) * 0.4, float(np.median(x)) * 2],
        "doc": "Two-site binding",
    },
    "one_site_binding_ns": {
        "fn": _one_site_binding_ns,
        "params": ["Bmax", "Kd", "NS"],
        "category": "Binding",
        "bounds": ([0, 0, -np.inf], [np.inf, np.inf, np.inf]),
        "guess": lambda x, y: list(_guess_one_site_binding(x, y)) + [0.01],
        "doc": "One-site binding + nonspecific linear component",
    },
    "cooperative_binding": {
        "fn": _cooperative_binding,
        "params": ["Bmax", "Kd", "n"],
        "category": "Binding",
        "bounds": ([0, 0, 0.1], [np.inf, np.inf, 20]),
        "guess": lambda x, y: list(_guess_one_site_binding(x, y)) + [1.0],
        "doc": "Cooperative binding (Hill equation for binding)",
    },
    "hill_binding": {
        "fn": _hill_binding,
        "params": ["Bmax", "Kd", "n"],
        "category": "Binding",
        "bounds": ([0, 0, 0.1], [np.inf, np.inf, 20]),
        "guess": _guess_hill,
        "doc": "Hill binding equation",
    },
    "langmuir_adsorption": {
        "fn": _langmuir_adsorption,
        "params": ["Qmax", "KL"],
        "category": "Binding",
        "bounds": ([0, 0], [np.inf, np.inf]),
        "guess": _guess_one_site_binding,
        "doc": "Langmuir adsorption isotherm",
    },
    "freundlich": {
        "fn": _freundlich,
        "params": ["Kf", "n"],
        "category": "Binding",
        "bounds": ([0, 0.1], [np.inf, 20]),
        "guess": lambda x, y: [1.0, 1.0],
        "doc": "Freundlich adsorption isotherm",
    },
    "scatchard": {
        "fn": _scatchard,
        "params": ["Bmax", "Kd"],
        "category": "Binding",
        "bounds": ([0, 0], [np.inf, np.inf]),
        "guess": _guess_one_site_binding,
        "doc": "Scatchard transform for binding data",
    },

    # ── Polynomial (12 models) ──
    "linear": {
        "fn": _linear,
        "params": ["Slope", "Intercept"],
        "category": "Polynomial",
        "bounds": None,
        "guess": _guess_linear,
        "doc": "Linear: y = m*x + b",
    },
    "proportional": {
        "fn": _proportional,
        "params": ["Slope"],
        "category": "Polynomial",
        "bounds": None,
        "guess": lambda x, y: [float(np.mean(y / np.maximum(x, 1e-15)))],
        "doc": "Proportional (through origin): y = a*x",
    },
    "quadratic": {
        "fn": _quadratic,
        "params": ["a", "b", "c"],
        "category": "Polynomial",
        "bounds": None,
        "guess": lambda x, y: [0.0, 1.0, 0.0],
        "doc": "Quadratic: y = ax^2 + bx + c",
    },
    "cubic": {
        "fn": _cubic,
        "params": ["a", "b", "c", "d"],
        "category": "Polynomial",
        "bounds": None,
        "guess": lambda x, y: [0.0, 0.0, 1.0, 0.0],
        "doc": "Cubic polynomial",
    },
    "quartic": {
        "fn": _quartic,
        "params": ["a", "b", "c", "d", "e"],
        "category": "Polynomial",
        "bounds": None,
        "guess": lambda x, y: [0.0, 0.0, 0.0, 1.0, 0.0],
        "doc": "Quartic polynomial",
    },
    "quintic": {
        "fn": _quintic,
        "params": ["a", "b", "c", "d", "e", "f"],
        "category": "Polynomial",
        "bounds": None,
        "guess": lambda x, y: [0.0, 0.0, 0.0, 0.0, 1.0, 0.0],
        "doc": "Quintic polynomial",
    },
    "power_law": {
        "fn": _power_law,
        "params": ["a", "b"],
        "category": "Polynomial",
        "bounds": ([0, -np.inf], [np.inf, np.inf]),
        "guess": _guess_power,
        "doc": "Power law: y = a * x^b",
    },
    "inverse": {
        "fn": _inverse,
        "params": ["a", "b"],
        "category": "Polynomial",
        "bounds": None,
        "guess": lambda x, y: [1.0, 0.0],
        "doc": "Inverse: y = a/x + b",
    },
    "inverse_square": {
        "fn": _inverse_square,
        "params": ["a", "b"],
        "category": "Polynomial",
        "bounds": None,
        "guess": lambda x, y: [1.0, 0.0],
        "doc": "Inverse square: y = a/x^2 + b",
    },
    "log_linear": {
        "fn": _log_linear,
        "params": ["a", "b"],
        "category": "Polynomial",
        "bounds": None,
        "guess": lambda x, y: [1.0, 0.0],
        "doc": "Log-linear: y = a*ln(x) + b",
    },
    "exp_linear": {
        "fn": _exp_linear,
        "params": ["a", "b", "c"],
        "category": "Polynomial",
        "bounds": None,
        "guess": lambda x, y: [1.0, 0.1, 0.0],
        "doc": "Exponential-linear: y = a*exp(b*x) + c",
    },
    "reciprocal_quadratic": {
        "fn": _reciprocal_quadratic,
        "params": ["a", "b", "c"],
        "category": "Polynomial",
        "bounds": None,
        "guess": lambda x, y: [0.01, 0.1, 1.0],
        "doc": "Reciprocal quadratic: y = 1/(ax^2+bx+c)",
    },

    # ── Sigmoidal (8 models) ──
    "boltzmann": {
        "fn": _boltzmann,
        "params": ["Top", "Bottom", "V50", "Slope"],
        "category": "Sigmoidal",
        "bounds": None,
        "guess": lambda x, y: [float(np.max(y)), float(np.min(y)), float(np.median(x)),
                                float((np.max(x) - np.min(x)) / 10)],
        "doc": "Boltzmann sigmoidal",
    },
    "hill_equation": {
        "fn": _hill_equation,
        "params": ["Vmax", "Kd", "n"],
        "category": "Sigmoidal",
        "bounds": ([0, 0, 0.1], [np.inf, np.inf, 20]),
        "guess": _guess_hill,
        "doc": "Hill equation: Vmax*x^n/(Kd^n+x^n)",
    },
    "logistic_4p": {
        "fn": _logistic_4p,
        "params": ["a", "b", "c", "d"],
        "category": "Sigmoidal",
        "bounds": None,
        "guess": lambda x, y: [float(np.max(y)), 1.0, float(np.median(x)), float(np.min(y))],
        "doc": "4-parameter logistic",
    },
    "logistic_5p": {
        "fn": _logistic_5p,
        "params": ["a", "b", "c", "d", "g"],
        "category": "Sigmoidal",
        "bounds": None,
        "guess": lambda x, y: [float(np.max(y)), 1.0, float(np.median(x)), float(np.min(y)), 1.0],
        "doc": "5-parameter logistic with asymmetry",
    },
    "weibull_sigmoid": {
        "fn": _weibull_sigmoid,
        "params": ["a", "b", "c", "d"],
        "category": "Sigmoidal",
        "bounds": None,
        "guess": lambda x, y: [float(np.max(y)), 1.0, float(np.median(x)), float(np.min(y))],
        "doc": "Weibull sigmoidal function",
    },
    "log_logistic": {
        "fn": _log_logistic,
        "params": ["a", "b", "c", "d"],
        "category": "Sigmoidal",
        "bounds": None,
        "guess": lambda x, y: [float(np.max(y)), 1.0, float(np.median(x)), float(np.min(y))],
        "doc": "Log-logistic sigmoidal",
    },
    "tanh_sigmoid": {
        "fn": _tanh_sigmoid,
        "params": ["a", "b", "c", "d"],
        "category": "Sigmoidal",
        "bounds": None,
        "guess": lambda x, y: [float((np.max(y) - np.min(y)) / 2), 1.0,
                                float(np.median(x)), float(np.mean(y))],
        "doc": "Hyperbolic tangent sigmoidal",
    },
    "four_param_log_logistic": {
        "fn": _four_param_log_logistic,
        "params": ["b", "c", "d", "e"],
        "category": "Sigmoidal",
        "bounds": None,
        "guess": lambda x, y: [1.0, float(np.min(y)), float(np.max(y)), float(np.median(x))],
        "doc": "Four-parameter log-logistic (LL.4)",
    },

    # ── Gaussian / peak (8 models) ──
    "gaussian": {
        "fn": _gaussian,
        "params": ["Amplitude", "Mean", "Sigma"],
        "category": "Gaussian",
        "bounds": ([0, -np.inf, 0], [np.inf, np.inf, np.inf]),
        "guess": _guess_gaussian,
        "doc": "Gaussian peak",
    },
    "gaussian_offset": {
        "fn": _gaussian_offset,
        "params": ["Amplitude", "Mean", "Sigma", "Offset"],
        "category": "Gaussian",
        "bounds": ([0, -np.inf, 0, -np.inf], [np.inf, np.inf, np.inf, np.inf]),
        "guess": lambda x, y: list(_guess_gaussian(x, y)) + [float(np.min(y))],
        "doc": "Gaussian peak with baseline offset",
    },
    "sum_of_2_gaussians": {
        "fn": _sum_of_2_gaussians,
        "params": ["A1", "Mu1", "Sigma1", "A2", "Mu2", "Sigma2"],
        "category": "Gaussian",
        "bounds": ([0, -np.inf, 0, 0, -np.inf, 0], [np.inf] * 6),
        "guess": lambda x, y: [float(np.max(y)), float(x[np.argmax(y)]),
                                float((np.max(x) - np.min(x)) / 10),
                                float(np.max(y)) * 0.5, float(np.mean(x)),
                                float((np.max(x) - np.min(x)) / 10)],
        "doc": "Sum of two Gaussian peaks",
    },
    "sum_of_3_gaussians": {
        "fn": _sum_of_3_gaussians,
        "params": ["A1", "Mu1", "S1", "A2", "Mu2", "S2", "A3", "Mu3", "S3"],
        "category": "Gaussian",
        "bounds": ([0, -np.inf, 0] * 3, [np.inf] * 9),
        "guess": lambda x, y: [float(np.max(y)), float(x[np.argmax(y)]),
                                float((np.max(x) - np.min(x)) / 12)] * 3,
        "doc": "Sum of three Gaussian peaks",
    },
    "lorentzian": {
        "fn": _lorentzian,
        "params": ["Amplitude", "Center", "Gamma"],
        "category": "Gaussian",
        "bounds": ([0, -np.inf, 0], [np.inf, np.inf, np.inf]),
        "guess": _guess_gaussian,
        "doc": "Lorentzian (Cauchy) peak",
    },
    "voigt": {
        "fn": _voigt,
        "params": ["Amplitude", "Center", "Sigma", "Gamma"],
        "category": "Gaussian",
        "bounds": ([0, -np.inf, 0, 0], [np.inf, np.inf, np.inf, np.inf]),
        "guess": lambda x, y: list(_guess_gaussian(x, y)) + [float((np.max(x) - np.min(x)) / 10)],
        "doc": "Pseudo-Voigt profile (Gaussian-Lorentzian mix)",
    },
    "lognormal": {
        "fn": _lognormal,
        "params": ["Amplitude", "Mu", "Sigma"],
        "category": "Gaussian",
        "bounds": ([0, -np.inf, 0], [np.inf, np.inf, np.inf]),
        "guess": lambda x, y: [float(np.max(y)) * float(np.median(x)), float(np.log(np.median(x) + 1e-15)), 1.0],
        "doc": "Log-normal distribution peak",
    },
    "asymmetric_gaussian": {
        "fn": _asymmetric_gaussian,
        "params": ["Amplitude", "Center", "Sigma_left", "Sigma_right"],
        "category": "Gaussian",
        "bounds": ([0, -np.inf, 0, 0], [np.inf, np.inf, np.inf, np.inf]),
        "guess": lambda x, y: [float(np.max(y)), float(x[np.argmax(y)]),
                                float((np.max(x) - np.min(x)) / 6),
                                float((np.max(x) - np.min(x)) / 6)],
        "doc": "Asymmetric Gaussian with different left/right widths",
    },

    # ── Pharmacokinetics (3 models) ──
    "one_compartment_oral": {
        "fn": _one_compartment_oral,
        "params": ["Dose", "Ka", "Ke", "V"],
        "category": "Pharmacokinetics",
        "bounds": ([0, 0, 0, 0], [np.inf, np.inf, np.inf, np.inf]),
        "guess": lambda x, y: [100.0, 1.0, 0.1, 10.0],
        "doc": "One-compartment oral absorption PK model",
    },
    "one_compartment_iv": {
        "fn": _one_compartment_iv,
        "params": ["Dose", "Ke", "V"],
        "category": "Pharmacokinetics",
        "bounds": ([0, 0, 0], [np.inf, np.inf, np.inf]),
        "guess": lambda x, y: [float(np.max(y)) * 10, 0.1, 10.0],
        "doc": "One-compartment IV bolus PK model",
    },
    "two_compartment_iv": {
        "fn": _two_compartment_iv,
        "params": ["A", "Alpha", "B", "Beta"],
        "category": "Pharmacokinetics",
        "bounds": ([0, 0, 0, 0], [np.inf, np.inf, np.inf, np.inf]),
        "guess": _guess_biexponential,
        "doc": "Two-compartment IV PK model",
    },

    # ── Physical chemistry (2 models) ──
    "arrhenius": {
        "fn": _arrhenius,
        "params": ["A", "Ea"],
        "category": "Physical chemistry",
        "bounds": ([0, 0], [np.inf, np.inf]),
        "guess": lambda x, y: [float(np.max(y)), 50000.0],
        "doc": "Arrhenius equation: k = A*exp(-Ea/RT)",
    },
    "van_t_hoff": {
        "fn": _van_t_hoff,
        "params": ["dH", "dS"],
        "category": "Physical chemistry",
        "bounds": None,
        "guess": lambda x, y: [-50000.0, 100.0],
        "doc": "Van't Hoff equation for temperature dependence of K",
    },

    # ── Miscellaneous (8 models) ──
    "sinusoidal": {
        "fn": _sinusoidal,
        "params": ["Amplitude", "Frequency", "Phase", "Offset"],
        "category": "Miscellaneous",
        "bounds": None,
        "guess": lambda x, y: [float((np.max(y) - np.min(y)) / 2), 1.0, 0.0, float(np.mean(y))],
        "doc": "Sinusoidal: A*sin(2*pi*f*x + phi) + offset",
    },
    "damped_sine": {
        "fn": _damped_sine,
        "params": ["Amplitude", "Frequency", "Phase", "Decay", "Offset"],
        "category": "Miscellaneous",
        "bounds": None,
        "guess": lambda x, y: [float((np.max(y) - np.min(y)) / 2), 1.0, 0.0, 0.1, float(np.mean(y))],
        "doc": "Damped sinusoidal",
    },
    "bilinear": {
        "fn": _bilinear,
        "params": ["Slope1", "Intercept1", "Slope2", "Intercept2", "Breakpoint"],
        "category": "Miscellaneous",
        "bounds": None,
        "guess": lambda x, y: [1.0, float(y[0]), -1.0, float(y[-1]), float(np.median(x))],
        "doc": "Bilinear (piecewise linear with breakpoint)",
    },
    "rectangular_hyperbola": {
        "fn": _rectangular_hyperbola,
        "params": ["a", "b"],
        "category": "Miscellaneous",
        "bounds": ([0, 0], [np.inf, np.inf]),
        "guess": _guess_michaelis_menten,
        "doc": "Rectangular hyperbola: a*x/(b+x)",
    },
    "emax": {
        "fn": _emax,
        "params": ["E0", "Emax", "EC50"],
        "category": "Miscellaneous",
        "bounds": None,
        "guess": lambda x, y: [float(np.min(y)), float(np.max(y) - np.min(y)), float(np.median(x))],
        "doc": "Emax pharmacodynamic model",
    },
    "emax_sigmoidal": {
        "fn": _emax_sigmoidal,
        "params": ["E0", "Emax", "EC50", "n"],
        "category": "Miscellaneous",
        "bounds": None,
        "guess": lambda x, y: [float(np.min(y)), float(np.max(y) - np.min(y)), float(np.median(x)), 1.0],
        "doc": "Sigmoidal Emax model",
    },
    "brain_cousens": {
        "fn": _brain_cousens,
        "params": ["b", "c", "d", "e", "f"],
        "category": "Miscellaneous",
        "bounds": None,
        "guess": lambda x, y: [1.0, float(np.min(y)), float(np.max(y)), float(np.median(x)), 0.1],
        "doc": "Brain-Cousens hormesis model",
    },
    "hanes_woolf": {
        "fn": _hanes_woolf,
        "params": ["Vmax", "Km"],
        "category": "Miscellaneous",
        "bounds": ([0, 0], [np.inf, np.inf]),
        "guess": _guess_michaelis_menten,
        "doc": "Hanes-Woolf linearization for enzyme kinetics",
    },

    # ── Additional models (to reach 100+) ──

    "gaddum_schild": {
        "fn": _gaddum_schild,
        "params": ["Emax", "EC50", "n", "Kb", "B_conc"],
        "category": "Dose-response",
        "bounds": ([0, 0, 0, 0, 0], [np.inf] * 5),
        "guess": lambda x, y: [float(np.max(y)), float(np.median(x)), 1.0, 1.0, 0.1],
        "doc": "Gaddum/Schild equation for competitive antagonism",
    },
    "hill_kinetics": {
        "fn": _hill_kinetics,
        "params": ["Vmax", "S50", "n"],
        "category": "Enzyme kinetics",
        "bounds": ([0, 0, 0.1], [np.inf, np.inf, 20]),
        "guess": lambda x, y: [float(np.max(y)), float(np.median(x)), 1.0],
        "doc": "Hill kinetics (sigmoidal enzyme kinetics)",
    },
    "ordered_bi_bi": {
        "fn": _ordered_bi_bi,
        "params": ["Vmax", "Ka", "Kb"],
        "category": "Enzyme kinetics",
        "bounds": ([0, 0, 0], [np.inf] * 3),
        "guess": lambda x, y: [float(np.max(y)), float(np.median(x)), float(np.median(x))],
        "doc": "Ordered Bi Bi mechanism (simplified)",
    },
    "negative_exponential": {
        "fn": _negative_exponential,
        "params": ["a", "b"],
        "category": "Growth",
        "bounds": ([0, 0], [np.inf, np.inf]),
        "guess": lambda x, y: [float(np.max(y)), 0.1],
        "doc": "Negative exponential (asymptotic growth)",
    },
    "theta_logistic": {
        "fn": _theta_logistic,
        "params": ["r", "K", "theta", "N0"],
        "category": "Growth",
        "bounds": ([0, 0, 0.01, 0], [np.inf, np.inf, 100, np.inf]),
        "guess": lambda x, y: [0.5, float(np.max(y)), 1.0, float(y[0])],
        "doc": "Theta-logistic growth model",
    },
    "bivalent_binding": {
        "fn": _bivalent_binding,
        "params": ["Bmax", "Kd1", "Kd2"],
        "category": "Binding",
        "bounds": ([0, 0, 0], [np.inf] * 3),
        "guess": lambda x, y: [float(np.max(y)), float(np.median(x)), float(np.median(x)) * 5],
        "doc": "Bivalent ligand binding model",
    },
    "competition_binding": {
        "fn": _competition_binding,
        "params": ["Top", "Bottom", "LogKi", "LogConc"],
        "category": "Binding",
        "bounds": None,
        "guess": lambda x, y: [float(np.max(y)), float(np.min(y)), float(np.median(x)), 0.0],
        "doc": "Competition binding curve",
    },
    "pearson_vii": {
        "fn": _pearson_vii,
        "params": ["Amplitude", "Center", "Width", "Shape"],
        "category": "Gaussian",
        "bounds": ([0, -np.inf, 0, 0.5], [np.inf, np.inf, np.inf, 100]),
        "guess": lambda x, y: [float(np.max(y)), float(x[np.argmax(y)]),
                                float((np.max(x) - np.min(x)) / 6), 2.0],
        "doc": "Pearson VII peak shape",
    },
    "pseudo_voigt_full": {
        "fn": _pseudo_voigt_full,
        "params": ["Amplitude", "Center", "Width", "Eta"],
        "category": "Gaussian",
        "bounds": ([0, -np.inf, 0, 0], [np.inf, np.inf, np.inf, 1]),
        "guess": lambda x, y: [float(np.max(y)), float(x[np.argmax(y)]),
                                float((np.max(x) - np.min(x)) / 6), 0.5],
        "doc": "Pseudo-Voigt with explicit mixing parameter",
    },
    "double_lorentzian": {
        "fn": _double_lorentzian,
        "params": ["A1", "Center1", "Gamma1", "A2", "Center2", "Gamma2"],
        "category": "Gaussian",
        "bounds": ([0, -np.inf, 0, 0, -np.inf, 0], [np.inf] * 6),
        "guess": lambda x, y: [float(np.max(y)), float(x[np.argmax(y)]),
                                float((np.max(x) - np.min(x)) / 10),
                                float(np.max(y)) * 0.5, float(np.mean(x)),
                                float((np.max(x) - np.min(x)) / 10)],
        "doc": "Double Lorentzian peaks",
    },
    "kohlrausch": {
        "fn": _kohlrausch,
        "params": ["A", "Tau", "Beta"],
        "category": "Decay",
        "bounds": ([0, 0, 0], [np.inf, np.inf, 2]),
        "guess": lambda x, y: [float(y[0]) if len(y) > 0 else 1.0, float(np.median(x)), 1.0],
        "doc": "Kohlrausch stretched exponential relaxation",
    },
    "biexponential_rise_decay": {
        "fn": _biexponential_rise_decay,
        "params": ["A_rise", "K_rise", "A_decay", "K_decay"],
        "category": "Decay",
        "bounds": ([0, 0, 0, 0], [np.inf] * 4),
        "guess": lambda x, y: [1.0, 1.0, float(np.max(y)), 0.1],
        "doc": "Biexponential rise-then-decay",
    },
    "clark_equation": {
        "fn": _clark_equation,
        "params": ["Emax", "Kd"],
        "category": "Pharmacokinetics",
        "bounds": ([0, 0], [np.inf, np.inf]),
        "guess": _guess_michaelis_menten,
        "doc": "Clark's receptor occupation theory",
    },
    "operational_model": {
        "fn": _operational_model,
        "params": ["Emax", "Kd", "Tau", "n"],
        "category": "Pharmacokinetics",
        "bounds": ([0, 0, 0, 0.1], [np.inf, np.inf, np.inf, 20]),
        "guess": lambda x, y: [float(np.max(y)), float(np.median(x)), 1.0, 1.0],
        "doc": "Black-Leff operational model of agonism",
    },
    "beta_pdf": {
        "fn": _beta_pdf,
        "params": ["a", "b", "Scale"],
        "category": "Distributions",
        "bounds": ([0.1, 0.1, 0], [100, 100, np.inf]),
        "guess": lambda x, y: [2.0, 2.0, float(np.max(y))],
        "doc": "Beta distribution PDF (scaled)",
    },
    "gamma_pdf": {
        "fn": _gamma_pdf,
        "params": ["Shape", "Scale_param", "Amplitude"],
        "category": "Distributions",
        "bounds": ([0.1, 0.01, 0], [100, np.inf, np.inf]),
        "guess": lambda x, y: [2.0, float(np.mean(x)), float(np.max(y))],
        "doc": "Gamma distribution PDF (scaled)",
    },
    "weibull_pdf": {
        "fn": _weibull_pdf,
        "params": ["Shape", "Scale_param", "Amplitude"],
        "category": "Distributions",
        "bounds": ([0.1, 0.01, 0], [100, np.inf, np.inf]),
        "guess": lambda x, y: [2.0, float(np.mean(x)), float(np.max(y))],
        "doc": "Weibull distribution PDF (scaled)",
    },
    "rayleigh": {
        "fn": _rayleigh,
        "params": ["Sigma", "Scale"],
        "category": "Distributions",
        "bounds": ([0.01, 0], [np.inf, np.inf]),
        "guess": lambda x, y: [float(np.std(x)), float(np.max(y))],
        "doc": "Rayleigh distribution",
    },
    "exponential_pdf": {
        "fn": _exponential_pdf,
        "params": ["Lambda", "Scale"],
        "category": "Distributions",
        "bounds": ([0, 0], [np.inf, np.inf]),
        "guess": lambda x, y: [0.5, float(np.max(y))],
        "doc": "Exponential distribution PDF",
    },
}


def list_models_by_category() -> dict[str, list[dict]]:
    """Return models grouped by category with metadata."""
    result: dict[str, list[dict]] = {}
    for key, model in CURVE_MODELS.items():
        cat = model["category"]
        if cat not in result:
            result[cat] = []
        result[cat].append({
            "key": key,
            "params": model["params"],
            "doc": model["doc"],
            "n_params": len(model["params"]),
        })
    return result


def get_model(name: str) -> dict | None:
    """Look up a model by name. Returns None if not found."""
    return CURVE_MODELS.get(name)


def model_count() -> int:
    """Return total number of registered models."""
    return len(CURVE_MODELS)
