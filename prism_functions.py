"""
prism_functions.py
------------------
Plots GraphPad Prism-style bar and line graphs.
Extracted from prism_barplot_final_updated.ipynb.
"""

import itertools
import warnings
import numpy as np
import pandas as pd

# scipy, matplotlib, and seaborn are imported lazily inside each function
# so the module loads in ~50ms instead of ~800ms.
# They are guaranteed to be available by the time any plot function is called
# because _do_import sets matplotlib.use("Agg") and imports this module on
# a background thread before the user can click Generate Plot.

def _ensure_imports():
    """Import the heavy libraries once and cache them as module-level names."""
    global plt, sns, stats, _imports_done
    if _imports_done:
        return
    import matplotlib.pyplot as _plt
    import seaborn as _sns
    from scipy import stats as _stats
    plt   = _plt
    sns   = _sns
    stats = _stats
    _imports_done = True
    _plt.rcParams["figure.dpi"] = _DPI

_imports_done = False
plt   = None
sns   = None
stats = None

# Module-level flags — set by the app before calling plot functions
__show_ns__                  = False
__show_normality_warning__   = True
# Significance threshold: pairs with p > this value are treated as "ns".
# Default 0.05 (Prism standard). App sets this before each plot run.
__p_sig_threshold__          = 0.05

# High-DPI rendering for all plots — 120 DPI balances sharpness and speed
# Applied lazily after matplotlib is loaded
_DPI = 144

# ---------------------------------------------------------------------------
# Style constants — change once here to affect the whole codebase
# ---------------------------------------------------------------------------

_FONT        = "Arial"          # plot axis/tick font
_LW_AXIS     = 0.8              # spine + tick linewidth
_LW_ERR      = 1.0              # error bar default linewidth
_LW_GRID     = 0.6              # gridline linewidth
_LW_REF      = 1.0              # reference line linewidth
_CAP_SIZE    = 4                # error bar cap size (pts)
_LABEL_PAD   = 6                # axis label padding (pts)
_TITLE_PAD   = 8                # title padding (pts)
_TIGHT_PAD   = 1.2              # tight_layout pad
_ALPHA_BAR   = 0.85             # default bar alpha
_ALPHA_POINT = 0.80             # default scatter point alpha
_ALPHA_CI    = 0.15             # confidence band alpha
_ALPHA_LINE  = 0.55             # subject connecting line alpha
_PT_SIZE     = 18               # default scatter point size (s=)
_PT_LW       = 1.2              # point edge linewidth
_DARKEN      = 0.65             # default darken factor for edges
_COLOR_ANNOT = "dimgray"        # annotation text color
_COLOR_WARN  = "darkorange"     # normality warning color
_COLOR_SUBJ  = "#aaaaaa"        # subject line color
_COLOR_BOX   = "#444444"        # box plot whisker/cap color
_COLOR_ANNO_SUBTLE = "#888888"  # subtle annotation color
_COLOR_HDR       = "#2274A5"        # table header color
_COLOR_WARN_FILL = "#FFA50055"       # normality-fail cell highlight
_COLOR_BG        = "white"           # plot / figure background

# Marker cycle for multi-series XY charts (line, scatter, curve fit)
MARKER_CYCLE = ["o", "s", "^", "D", "v", "*", "P", "X", "h"]

# Shared paired / subcolumn drawing constants
_MEAN_TICK_HALF  = 0.18   # half-width of mean tick line (data units)
_MEAN_TICK_LW    = 2.5    # linewidth of mean tick
_PAIR_ERR_LW     = 1.8    # elinewidth for paired error bars
_PAIR_CAP_SIZE   = 6      # capsize for paired error bars
_SUBJ_LINE_LW    = 0.8    # subject connecting line linewidth
_SUBJ_LINE_ALPHA = 0.55   # subject connecting line alpha




# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

PRISM_PALETTE = [
    "#E8453C", "#2274A5", "#32936F", "#F18F01", "#A846A0",
    "#6B4226", "#048A81", "#D4AC0D", "#3B1F2B", "#44BBA4",
]


# ---------------------------------------------------------------------------
# Shared plot helpers
# ---------------------------------------------------------------------------

def _assign_colors(n, color):
    """Return a list of exactly n colors from a palette name, single color, or list."""
    _ensure_imports()

    # ── Curated preset aliases ────────────────────────────────────────────────
    _PRESETS = {
        "Pastel":    ["#AEC6CF", "#FFD1DC", "#B5EAD7", "#FFDAC1", "#C9C9FF",
                      "#F2C6DE", "#B5D5C5", "#FAEBD7", "#D5E8D4", "#DAE8FC"],
        "Vivid":     ["#E8453C", "#2274A5", "#32936F", "#F18F01", "#A846A0",
                      "#048A81", "#D4AC0D", "#E84855", "#3BCEAC", "#F72585"],
        "CB-safe":   ["#E69F00", "#56B4E9", "#009E73", "#F0E442", "#0072B2",
                      "#D55E00", "#CC79A7", "#999999"],
        "Grayscale": ["#222222", "#555555", "#888888", "#aaaaaa", "#cccccc",
                      "#dddddd", "#444444", "#777777"],
        "Blues":     None,   # handled by seaborn
        "Reds":      None,
        "Greens":    None,
        "RdBu":      None,
    }
    _SEABORN_ALIASES = {
        "Blues":  "Blues_d",
        "Reds":   "Reds_d",
        "Greens": "Greens_d",
        "RdBu":   "RdBu_r",
        # Sequential perceptually-uniform palettes (seaborn >= 0.12)
        "mako":   "mako",
        "rocket": "rocket",
        "flare":  "flare",
        "crest":  "crest",
    }

    if color is None:
        base = PRISM_PALETTE
        return [base[i % len(base)] for i in range(n)]
    elif isinstance(color, str):
        preset_colors = _PRESETS.get(color)
        if preset_colors is not None:
            return [preset_colors[i % len(preset_colors)] for i in range(n)]
        # Remap sequential/diverging preset names to seaborn names
        pal_name = _SEABORN_ALIASES.get(color, color)
        try:
            pal = sns.color_palette(pal_name, n)
            return [f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
                    for r, g, b in pal]
        except Exception:
            return [color] * n
    else:
        c = list(color)
        while len(c) < n:
            c += c
        return c[:n]


def _calc_error(vals, error_type):
    """Return (mean, error_bar_half_width) for a given error type."""
    n = len(vals)
    m = float(np.mean(vals))
    s = float(np.std(vals, ddof=1)) if n > 1 else 0.0
    if error_type == "sem":
        return m, s / np.sqrt(n) if n > 0 else 0.0
    elif error_type == "sd":
        return m, s
    else:  # ci95
        ci = stats.t.ppf(0.975, df=max(n - 1, 1)) * s / np.sqrt(max(n, 1))
        return m, float(ci)


def _calc_error_asymmetric(vals, error_type):
    """Return (mean, err_down, err_up) with asymmetric bounds for log-scale plots.

    On a log axis, symmetric error bars in data units look wrong because the
    lower bar can cross zero or go negative.  This computes the error in log
    space and maps it back: the lower bar = mean - 10^(log10(mean) - e_log) and
    the upper bar = 10^(log10(mean) + e_log) - mean, ensuring both bars stay
    positive and the lower bar never exceeds the mean (which would
    extend through zero on a log axis).  Falls back to symmetric if mean <= 0."""
    m, half = _calc_error(vals, error_type)
    if m <= 0:
        return m, half, half
    try:
        log_m   = np.log10(m)
        log_err = np.log10(m + half) - log_m          # upper log offset
        lo_raw = m - 10 ** (log_m - log_err)          # lower asymmetric bar
        hi     = 10 ** (log_m + log_err) - m          # upper asymmetric bar
        # Clamp: lower bar must be < m — never extend through zero on log scale
        lo = float(np.clip(lo_raw, 0.0, m * 0.9999))
        return m, lo, max(float(hi), 0.0)
    except Exception:
        return m, half, half


def _draw_bar_errorbar(ax, x, vals, error_type, yscale, *,
                       ecolor="black", elw=1.0, cap_size=4.0, zorder=4):
    """Draw one error bar for a bar-chart bar and return the mean.

    Handles both symmetric (linear scale) and asymmetric (log scale) cases so
    callers don't have to duplicate the if/else branch themselves.
    """
    if yscale == "log":
        m, lo, hi = _calc_error_asymmetric(vals, error_type)
        ax.errorbar(x, m, yerr=[[lo], [hi]], fmt="none", ecolor=ecolor,
                    elinewidth=elw, capsize=cap_size, capthick=elw, zorder=zorder)
    else:
        m, half = _calc_error(vals, error_type)
        ax.errorbar(x, m, yerr=half, fmt="none", ecolor=ecolor,
                    elinewidth=elw, capsize=cap_size, capthick=elw, zorder=zorder)
    return m


# ---------------------------------------------------------------------------
# Axis style / tick direction constants — used by _apply_prism_style
# ---------------------------------------------------------------------------

AXIS_STYLES = {
    "Open (Prism default)": "open",
    "Closed box":           "closed",
    "Floating":             "floating",
    "None":                 "none",
}

TICK_DIRS = {
    "Outward (default)": "out",
    "Inward":            "in",
    "Both":              "inout",
    "None":              "",
}

LEGEND_POSITIONS = {
    "Auto (best fit)": "best",
    "Upper right":     "upper right",
    "Upper left":      "upper left",
    "Lower right":     "lower right",
    "Lower left":      "lower left",
    "Outside right":   "outside",
    "None (hidden)":   "none",
}


def _apply_prism_style(
    ax,
    font_size: float,
    axis_style: str = "open",
    tick_dir: str = "out",
    minor_ticks: bool = False,
    fig_bg: str = "white",
    spine_width: float = 0.8,
    **_,                          # absorb ytick_interval, xtick_interval, etc.
):
    """Apply Prism-style axis aesthetics (spines, ticks, background).

    Parameters
    ----------
    axis_style : ``"open"`` (Prism default — left+bottom only),
                 ``"closed"`` (all 4 spines),
                 ``"floating"`` (left+bottom offset outward 5 px),
                 ``"none"`` (no spines, no ticks).
    tick_dir   : ``"out"`` | ``"in"`` | ``"inout"`` | ``""`` (hidden).
    minor_ticks: If True, enable AutoMinorLocator on both axes.
    fig_bg     : Background color for both axes and figure patch.
    """
    # ── Spine visibility ──────────────────────────────────────────────────────
    if axis_style == "closed":
        for sp in ax.spines.values():
            sp.set_visible(True)
            sp.set_linewidth(spine_width)
    elif axis_style == "floating":
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_linewidth(spine_width)
        ax.spines["bottom"].set_linewidth(spine_width)
        ax.spines["left"].set_position(("outward", 5))
        ax.spines["bottom"].set_position(("outward", 5))
    elif axis_style == "none":
        for sp in ax.spines.values():
            sp.set_visible(False)
        ax.tick_params(axis="both", which="both",
                       length=0, labelsize=font_size)
        ax.set_facecolor(fig_bg)
        ax.figure.patch.set_facecolor(fig_bg)
        return
    else:  # "open" — Prism default
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_linewidth(spine_width)
        ax.spines["bottom"].set_linewidth(spine_width)

    # ── Tick direction ────────────────────────────────────────────────────────
    _td = tick_dir if tick_dir else "out"
    _tick_len = 0 if tick_dir == "" else 5
    _tick_lw  = max(0.4, spine_width * 0.8)   # tick linewidth tracks spine width
    ax.tick_params(axis="both", which="major",
                   direction=_td, length=_tick_len, width=_tick_lw,
                   labelsize=font_size, top=False, right=False)
    ax.tick_params(axis="x", which="major", bottom=(tick_dir != ""))
    ax.tick_params(axis="y", which="major", left=(tick_dir != ""))

    # ── Minor ticks ───────────────────────────────────────────────────────────
    if minor_ticks:
        from matplotlib.ticker import AutoMinorLocator
        ax.xaxis.set_minor_locator(AutoMinorLocator())
        ax.yaxis.set_minor_locator(AutoMinorLocator())
        ax.tick_params(which="minor", direction=_td,
                       length=3, width=max(0.3, _tick_lw * 0.6), top=False, right=False)
    else:
        ax.tick_params(axis="both", which="minor",
                       direction=_td, length=2, width=max(0.3, _tick_lw * 0.6),
                       top=False, right=False)

    ax.set_facecolor(fig_bg)
    ax.figure.patch.set_facecolor(fig_bg)


def _apply_legend(ax, legend_pos: str = "best", font_size: float = 12):
    """Apply legend positioning.  Handles the special 'outside' and 'none' cases.

    After placing the legend, automatically expands the y-axis if the legend
    would overlap any plotted data (bars, lines, scatter points, etc.).
    'outside' legends are exempt — they sit beyond the axes boundary.
    """
    if legend_pos == "none":
        leg = ax.get_legend()
        if leg:
            leg.remove()
        return
    if legend_pos == "outside":
        ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5),
                  frameon=False, fontsize=font_size)
    else:
        ax.legend(loc=legend_pos, frameon=False, fontsize=font_size)
        # Auto-expand y-scale so legend never covers data
        fig = ax.get_figure()
        if fig is not None:
            _fix_legend_overlap(ax, fig)

# ---------------------------------------------------------------------------
# Stats helpers
# ---------------------------------------------------------------------------

def _p_to_stars(p: float) -> str:
    """Convert a p-value to Prism-style asterisk annotation.

    Uses the module-level __p_sig_threshold__ so the app can raise or lower
    the significance cutoff (e.g. 0.01 to show only ** and above).
    Pairs with p > threshold are returned as 'ns' and will be hidden unless
    __show_ns__ is True.
    """
    if p > __p_sig_threshold__: return "ns"
    if p <= 0.0001:  return "****"
    elif p <= 0.001: return "***"
    elif p <= 0.01:  return "**"
    else:            return "*"


def _apply_correction(raw_p_list, method):
    """Apply multiple comparison correction to a list of raw p-values.
    Returns corrected p-values in the same order."""
    m = len(raw_p_list)
    if m == 0:
        return []
    p = np.array(raw_p_list, dtype=float)

    if method == "Bonferroni":
        return list(np.minimum(p * m, 1.0))

    elif method == "Holm-Bonferroni":
        order       = np.argsort(p)
        corrected   = np.empty(m)
        running_max = 0.0
        for rank_i, orig_i in enumerate(order):
            cp = min(p[orig_i] * (m - rank_i), 1.0)
            running_max = max(running_max, cp)
            corrected[orig_i] = running_max
        return list(corrected)

    elif method == "Benjamini-Hochberg (FDR)":
        order     = np.argsort(p)
        corrected = np.empty(m)
        running_min = 1.0
        for rank_i in range(m - 1, -1, -1):
            orig_i = order[rank_i]
            cp = min(p[orig_i] * m / (rank_i + 1), 1.0)
            running_min = min(running_min, cp)
            corrected[orig_i] = running_min
        return list(corrected)

    else:  # None / uncorrected
        return list(p)


def _run_stats(
    groups: dict,
    test_type: str = "parametric",
    n_permutations: int = 9999,
    control=None,
    mc_correction: str = "Holm-Bonferroni",
    posthoc: str = "Tukey HSD",
    mu0: float = 0.0,
) -> list:
    """
    Run statistical tests and return (group_a, group_b, p_value, stars) tuples.

    test_type ``"one_sample"`` compares each group's mean to *mu0* using a
    one-sample t-test.  Returns (group_name, f"μ₀={mu0}", p, stars) tuples.
    """
    labels  = list(groups.keys())
    results = []
    k       = len(labels)

    # ── One-sample t-test ─────────────────────────────────────────────────────
    if test_type == "one_sample":
        raw_p = []
        for g in labels:
            _, p = stats.ttest_1samp(groups[g], popmean=mu0)
            raw_p.append(p)
        corrected = _apply_correction(raw_p, mc_correction)
        for g, cp in zip(labels, corrected):
            results.append((g, f"μ₀={mu0:g}", cp, _p_to_stars(cp)))
        return results

    # Need at least 2 groups for any pairwise comparison
    if k < 2:
        return []

    # ── Parametric ────────────────────────────────────────────────────────────
    if test_type == "paired":
        # Paired t-test: groups must have same length
        if k == 2:
            a, b = labels
            n = min(len(groups[a]), len(groups[b]))
            _, p = stats.ttest_rel(groups[a][:n], groups[b][:n])
            corrected = _apply_correction([p], mc_correction)[0]
            results.append((a, b, corrected, _p_to_stars(corrected)))
        else:
            # Repeated-measures style: pairwise paired t-tests
            pairs = list(itertools.combinations(labels, 2))
            raw_p = []
            for a, b in pairs:
                n = min(len(groups[a]), len(groups[b]))
                _, p = stats.ttest_rel(groups[a][:n], groups[b][:n])
                raw_p.append(p)
            corrected = _apply_correction(raw_p, mc_correction)
            for i, (a, b) in enumerate(pairs):
                results.append((a, b, corrected[i], _p_to_stars(corrected[i])))

    elif test_type == "parametric":
        if k == 2:
            a, b = labels
            # Welch's t-test (equal_var=False) — Prism default since v8.
            # Does not assume equal variances; more robust for real-world data.
            _, p = stats.ttest_ind(groups[a], groups[b], equal_var=False)
            corrected = _apply_correction([p], mc_correction)[0]
            results.append((a, b, corrected, _p_to_stars(corrected)))

        elif posthoc == "Dunnett (vs control)":
            # Dunnett's test: each treatment vs a single control reference.
            # scipy.stats.dunnett already controls the family-wise error rate
            # internally — applying an additional MC correction would be
            # double-penalising (overly conservative).  Prism uses Dunnett
            # p-values directly without a second correction step.
            ctrl = control if control is not None else labels[0]
            treatments       = [g for g in labels if g != ctrl]
            treatment_arrays = [groups[g] for g in treatments]
            from scipy.stats import dunnett as _dunnett
            res = _dunnett(*treatment_arrays, control=groups[ctrl])
            for i, trt in enumerate(treatments):
                p = float(res.pvalue[i])
                results.append((ctrl, trt, p, _p_to_stars(p)))

        elif posthoc == "Tukey HSD":
            _, p_anova = stats.f_oneway(*[groups[g] for g in labels])
            if p_anova >= 0.05:
                return []
            all_vals  = np.concatenate(list(groups.values()))
            ss_within = sum(np.sum((v - v.mean()) ** 2) for v in groups.values())
            df_within = len(all_vals) - k
            ms_within = ss_within / df_within
            all_pairs = list(itertools.combinations(labels, 2))
            # Filter to control-vs-others only if a control is set
            pairs = [p for p in all_pairs
                     if control is None or p[0] == control or p[1] == control]
            raw_p = []
            for a, b in pairs:
                mean_diff = abs(groups[a].mean() - groups[b].mean())
                se        = np.sqrt((ms_within / 2) * (1/len(groups[a]) + 1/len(groups[b])))
                q         = mean_diff / se
                raw_p.append(1 - stats.studentized_range.cdf(q, k, df_within))
            corrected = (_apply_correction(raw_p, mc_correction)
                         if mc_correction not in ("Holm-Bonferroni", "None (uncorrected)")
                         else raw_p)
            for i, (a, b) in enumerate(pairs):
                results.append((a, b, corrected[i], _p_to_stars(corrected[i])))

        elif posthoc in ("Bonferroni", "Sidak", "Fisher LSD"):
            _, p_anova = stats.f_oneway(*[groups[g] for g in labels])
            if p_anova >= 0.05:
                return []
            all_pairs = list(itertools.combinations(labels, 2))
            pairs = [p for p in all_pairs
                     if control is None or p[0] == control or p[1] == control]
            raw_p = []
            for a, b in pairs:
                # Welch's t-test for pairwise comparisons (Prism default)
                _, p = stats.ttest_ind(groups[a], groups[b], equal_var=False)
                raw_p.append(p)
            if posthoc == "Sidak":
                m = len(raw_p)
                corrected = [min(1.0 - (1.0 - p) ** m, 1.0) for p in raw_p]
            elif posthoc == "Fisher LSD":
                corrected = raw_p
            else:
                corrected = _apply_correction(raw_p, mc_correction)
            for i, (a, b) in enumerate(pairs):
                results.append((a, b, corrected[i], _p_to_stars(corrected[i])))

    # ── Nonparametric ─────────────────────────────────────────────────────────
    elif test_type == "nonparametric":
        if k == 2:
            a, b = labels
            _, p = stats.mannwhitneyu(groups[a], groups[b], alternative="two-sided")
            corrected = _apply_correction([p], mc_correction)[0]
            results.append((a, b, corrected, _p_to_stars(corrected)))
        else:
            _, p_kw = stats.kruskal(*[groups[g] for g in labels])
            if p_kw >= 0.05:
                return []
            all_vals    = np.concatenate(list(groups.values()))
            ranks       = stats.rankdata(all_vals)
            group_ranks = {}
            idx = 0
            for g in labels:
                n = len(groups[g])
                group_ranks[g] = ranks[idx:idx + n]
                idx += n
            _, counts = np.unique(all_vals, return_counts=True)
            tc        = 1 - np.sum(counts**3 - counts) / (len(all_vals)**3 - len(all_vals))
            all_pairs = list(itertools.combinations(labels, 2))
            pairs     = [p for p in all_pairs
                         if control is None or p[0] == control or p[1] == control]
            raw_p = []
            for a, b in pairs:
                se = np.sqrt(tc * len(all_vals) * (len(all_vals) + 1) / 12
                             * (1/len(groups[a]) + 1/len(groups[b])))
                z  = abs(group_ranks[a].mean() - group_ranks[b].mean()) / se
                raw_p.append(2 * (1 - stats.norm.cdf(z)))
            corrected = _apply_correction(raw_p, mc_correction)
            for i, (a, b) in enumerate(pairs):
                results.append((a, b, corrected[i], _p_to_stars(corrected[i])))

    # ── Permutation ───────────────────────────────────────────────────────────
    elif test_type == "permutation":
        def _diff_of_means(x, y):
            return np.mean(x) - np.mean(y)
        all_pairs = list(itertools.combinations(labels, 2))
        pairs     = [p for p in all_pairs
                     if control is None or p[0] == control or p[1] == control]
        raw_p = []
        for a, b in pairs:
            res = stats.permutation_test(
                (groups[a], groups[b]), _diff_of_means,
                permutation_type="samples", n_resamples=n_permutations,
                alternative="two-sided")
            raw_p.append(res.pvalue)
        corrected = _apply_correction(raw_p, mc_correction)
        for i, (a, b) in enumerate(pairs):
            results.append((a, b, corrected[i], _p_to_stars(corrected[i])))

    return results


def _draw_ref_vline(ax, x, font_size=12, label=None):
    """Draw a dashed vertical reference line at x with an optional label.
    Useful for scatter, line, and curve-fit charts where a specific x value
    is meaningful (e.g. EC50, dose threshold, baseline time-point).
    """
    ax.axvline(x=x, color="black", linewidth=_LW_REF,
               linestyle="--", alpha=0.6, zorder=1)
    y_top = ax.get_ylim()[1]
    display_label = label if label else f" x={x:g}"
    ax.text(x, y_top, display_label,
            va="bottom", ha="left", fontsize=font_size - 2,
            color="gray", clip_on=False, rotation=90)


def _draw_significance_brackets(ax, sig_results, x_positions, bar_tops,
                                 bracket_gap=0.04, tip_height=0.02,
                                 show_p_values=False,
                                 bracket_style: str = "lines"):
    """Draw Prism-style significance brackets above bars.

    Parameters
    ----------
    bracket_style : ``"lines"``          — horizontal line + descending tips (default)
                    ``"bracket"``        — square bracket (right-angle descents)
                    ``"asterisks_only"`` — text only, no lines drawn

    Brackets are guaranteed never to intersect.  Instead of the old per-column
    ceiling dict (which only tracked the highest point under each bar), we keep
    a list of *placed intervals* — each stored as (x_lo, x_hi, y_top).  Before
    placing a new bracket we query every already-placed interval whose x-range
    overlaps the new bracket's span, take their maximum y_top, and start the new
    bracket above that.  This is exact and requires no hardcoding.

    Bracket heights are also tracked so ``_fix_legend_overlap`` can account for
    them when deciding whether to expand the y-axis for the legend.
    """
    # Work in data coordinates throughout.
    y_lo, y_hi = ax.get_ylim()
    y_range   = y_hi - y_lo

    def _gap(y_rng):   return y_rng * bracket_gap
    def _tip(y_rng):   return y_rng * tip_height

    # Sort shortest spans first so narrow brackets stay low and wide ones
    # naturally clear them.
    sig_sorted = sorted(
        sig_results,
        key=lambda r: abs(x_positions.get(r[1], 0) - x_positions.get(r[0], 0)))

    # placed: list of (x_lo, x_hi, y_top) for every bracket drawn so far
    placed: list = []
    # Expose placed brackets on the axes object so _fix_legend_overlap can read them
    if not hasattr(ax, "_bracket_tops"):
        ax._bracket_tops = []

    def _ceiling_over(xa, xb):
        """Highest y_top of any already-placed bracket that overlaps [xa,xb]."""
        lo, hi = min(xa, xb), max(xa, xb)
        best = y_lo
        for (px_lo, px_hi, py_top) in placed:
            if px_lo <= hi and px_hi >= lo:
                best = max(best, py_top)
        return best

    for (a, b, p, stars) in sig_sorted:
        xa = x_positions.get(a)
        xb = x_positions.get(b)
        if xa is None or xb is None:
            continue

        # The bracket must clear both the raw bar tops and any placed brackets
        raw_top = max(
            (bar_tops.get(lbl, y_lo)
             for lbl in x_positions
             if min(xa, xb) - 1e-9 <= x_positions[lbl] <= max(xa, xb) + 1e-9),
            default=y_lo
        )
        ceil = max(raw_top, _ceiling_over(xa, xb))

        # Re-compute gap/tip using current ylim (may have grown from prior iter)
        cur_y_range = ax.get_ylim()[1] - ax.get_ylim()[0]
        gap  = _gap(cur_y_range)
        tip  = _tip(cur_y_range)

        bracket_y = ceil + gap

        # ── Draw bracket lines based on style ─────────────────────────────────
        if bracket_style == "asterisks_only":
            pass   # no lines — just the text below
        elif bracket_style == "bracket":
            # Square bracket: full-height vertical descents
            ax.plot([xa, xa, xb, xb],
                    [ceil + gap * 0.2, bracket_y, bracket_y, ceil + gap * 0.2],
                    lw=1.0, color="black", clip_on=False)
        else:  # "lines" — default Prism style with short tips
            ax.plot([xa, xa, xb, xb],
                    [bracket_y - tip, bracket_y, bracket_y, bracket_y - tip],
                    lw=1.0, color="black", clip_on=False)

        if show_p_values:
            p_str      = "p<0.0001" if p < 0.0001 else f"p={p:.4f}"
            label_text = f"ns ({p_str})" if stars == "ns" else f"{stars} ({p_str})"
            fs = 9
        else:
            label_text = stars
            fs = 13 if stars != "ns" else 11

        if bracket_style == "asterisks_only":
            # Place text directly above the midpoint of the two bar tops
            mid_y = max(bar_tops.get(a, y_lo), bar_tops.get(b, y_lo)) + gap * 0.5
            ax.text((xa + xb) / 2, mid_y, label_text,
                    ha="center", va="bottom",
                    fontsize=fs, fontfamily=_get_font(), fontweight="bold", color="black")
            label_top = mid_y + gap * 1.5
        else:
            ax.text((xa + xb) / 2, bracket_y + tip * 0.4, label_text,
                    ha="center", va="bottom",
                    fontsize=fs, fontfamily=_get_font(), fontweight="bold", color="black")
            label_top = bracket_y + gap * 2.0

        placed.append((min(xa, xb), max(xa, xb), label_top))
        ax._bracket_tops.append(label_top)

        # Expand y-axis if the bracket + label would be clipped
        needed = bracket_y + gap * 2.5
        if needed > ax.get_ylim()[1]:
            ax.set_ylim(top=needed)


def _apply_log_formatting(ax):
    """Apply Prism-style tick labels and minor ticks to a log-scale Y axis.

    Prism shows: major ticks at each power of 10 with superscript labels
    (10⁰, 10¹, 10², 10³ …), minor ticks at 2–9× each decade without labels,
    and slightly shorter minor tick marks.

    Also clamps the lower y-limit so values < 1 are not clipped by matplotlib's
    default log auto-range (which can bottom out at 0 or go negative).
    """
    import matplotlib.ticker as ticker
    from matplotlib.ticker import LogLocator, NullFormatter
    import math

    # ── Auto-range lower-limit guard ─────────────────────────────────────────
    # After set_yscale("log"), matplotlib's default auto-range may set ymin=0
    # or a negative value if any data is <= 0, which crashes the log scale.
    # Force a sensible lower bound based on the data actually in the axes.
    try:
        ymin_auto, ymax_auto = ax.get_ylim()
        data_min = None
        for line in ax.get_lines():
            ydata = line.get_ydata()
            pos = ydata[ydata > 0] if hasattr(ydata, '__len__') else []
            if len(pos):
                data_min = float(np.min(pos)) if data_min is None else min(data_min, float(np.min(pos)))
        for coll in ax.collections:
            try:
                offsets = coll.get_offsets()
                pos = offsets[:, 1][offsets[:, 1] > 0]
                if len(pos):
                    data_min = float(np.min(pos)) if data_min is None else min(data_min, float(np.min(pos)))
            except Exception:
                pass
        if data_min is not None and data_min > 0:
            safe_lo = max(data_min * 0.5, 1e-10)
        else:
            safe_lo = max(ymin_auto, 1e-10) if ymin_auto > 0 else 1e-10
        if ymin_auto <= 0 or ymin_auto > safe_lo * 10:
            ax.set_ylim(bottom=safe_lo)
    except Exception:
        pass  # best-effort; never crash plot generation

    # ── Superscript helper ────────────────────────────────────────────────────
    _SUP = str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹")

    def _log_label(x, _):
        if x <= 0:
            return ""
        exp = math.log10(x)
        if abs(exp - round(exp)) > 1e-6:
            return ""  # not a power of 10 — suppress
        e = int(round(exp))
        return "10" + str(e).translate(_SUP)

    # Major ticks: one per decade
    ax.yaxis.set_major_locator(LogLocator(base=10.0, numticks=12))
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(_log_label))

    # Minor ticks: at 2, 3, 4, 5, 6, 7, 8, 9 × each decade — no labels
    ax.yaxis.set_minor_locator(LogLocator(base=10.0, subs=np.arange(2, 10), numticks=100))
    ax.yaxis.set_minor_formatter(NullFormatter())

    # Minor ticks shorter than major
    ax.tick_params(axis="y", which="minor", length=2, width=0.6, left=True)


def _apply_grid(ax, grid_style: str, gridlines: bool = False):
    """Draw grid lines based on grid_style string or legacy bool.

    grid_style: "none" | "horizontal" | "full"
    gridlines:  legacy bool — True maps to "horizontal" when grid_style is "none"
    """
    # Resolve legacy bool
    effective = grid_style if grid_style and grid_style != "none" else (
        "horizontal" if gridlines else "none")
    if effective == "none":
        ax.yaxis.grid(False)
        ax.xaxis.grid(False)
    elif effective == "horizontal":
        ax.yaxis.grid(True, linestyle="--", linewidth=_LW_GRID, alpha=0.5, zorder=0)
        ax.xaxis.grid(False)
        ax.set_axisbelow(True)
    elif effective == "full":
        ax.yaxis.grid(True, linestyle="--", linewidth=_LW_GRID, alpha=0.5, zorder=0)
        ax.xaxis.grid(True, linestyle="--", linewidth=_LW_GRID, alpha=0.4, zorder=0)
        ax.set_axisbelow(True)


def _draw_ref_line(ax, y, font_size=12, label=None):
    """Draw a dashed horizontal reference line at y with an optional custom label."""
    ax.axhline(y=y, color="black", linewidth=_LW_REF,
               linestyle="--", alpha=0.6, zorder=1)
    display_label = label if label else f" y={y:g}"
    ax.text(ax.get_xlim()[1], y, display_label,
            va="center", ha="left", fontsize=font_size - 2,
            color="gray", clip_on=False)


def _set_axis_labels(ax, xlabel, ytitle, title, font_size, title_fs=None):
    """Apply axis labels and title with consistent Prism styling.
    title_fs overrides the default (font_size+4) for charts that need
    a larger title (KM, heatmap, two-way ANOVA use font_size+6).
    """
    if title:
        ax.set_title(title,
                     fontsize=(title_fs if title_fs is not None else font_size+4),
                     fontfamily=_get_font(), pad=_TITLE_PAD, fontweight="bold")
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=font_size+2, fontfamily=_get_font(),
                      labelpad=_LABEL_PAD, fontweight="bold")
    if ytitle:
        ax.set_ylabel(ytitle, fontsize=font_size+2, fontfamily=_get_font(),
                      labelpad=_LABEL_PAD, fontweight="bold")


def _fmt_bar_label(v: float) -> str:
    """Format a bar-top value label with 3 significant figures, no trailing zeros."""
    if v != v:          # NaN guard
        return ""
    if v == 0:
        return "0"
    abs_v = abs(v)
    if abs_v >= 1000 or abs_v < 0.001:
        return f"{v:.2e}"
    if abs_v >= 100:
        return f"{v:.0f}"
    if abs_v >= 10:
        return f"{v:.1f}"
    return f"{v:.2f}"


def _darken_color(c, factor=0.65):
    """Return a darkened version of a color for bar edges."""
    import matplotlib.colors as mcolors
    try:
        r, g, b, *_ = mcolors.to_rgba(c)
        return (r * factor, g * factor, b * factor)
    except Exception:
        return "black"


def _smart_xrotation(group_order):
    """Return (rotation, ha) for x-axis tick labels.
    Uses n_groups × max_label_length as a combined measure of crowding.
    Labels only stay horizontal when the product is small enough that
    there is no risk of overlap at typical figure widths.
    """
    max_len = max((len(str(g)) for g in group_order), default=0)
    crowding = len(group_order) * max_len
    if crowding > 12 or len(group_order) > 4:
        return 45, "right"
    return 0, "center"


def _scale_errorbar_lw(bar_width: float) -> float:
    """Return an error-bar linewidth that scales proportionally with bar width.
    At bar_width=0.6 (default) the line is 1.0 pt; scales linearly."""
    return max(0.5, round(bar_width / 0.6, 2))


def _n_labels(group_order, groups, font_size):
    """Return tick labels with n= appended: ['Control\nn=6', ...]"""
    return [f"{g}\nn={len(groups[g])}" for g in group_order]


def _test_name_annotation(ax, stats_test, posthoc, k, font_size):
    """Add a small italic footnote below the plot naming the test used."""
    if stats_test == "paired":
        name = "Paired t-test"
    elif stats_test == "parametric":
        if k == 2:
            name = "Unpaired t-test"
        elif posthoc == "Tukey HSD":
            name = "One-way ANOVA with Tukey's HSD"
        elif posthoc == "Bonferroni":
            name = "One-way ANOVA with Bonferroni correction"
        elif posthoc == "Sidak":
            name = "One-way ANOVA with Sidak correction"
        elif posthoc == "Fisher LSD":
            name = "One-way ANOVA with Fisher's LSD"
        elif posthoc == "Dunnett (vs control)":
            name = "One-way ANOVA with Dunnett's test"
        else:
            name = "One-way ANOVA"
    elif stats_test == "nonparametric":
        name = "Mann-Whitney test" if k == 2 else "Kruskal-Wallis with Dunn's test"
    elif stats_test == "permutation":
        name = "Permutation test"
    else:
        return
    ax.annotate(name, xy=(0.5, -0.18), xycoords="axes fraction",
                ha="center", va="top", fontsize=font_size - 2,
                fontstyle="italic", color=_COLOR_ANNO_SUBTLE, fontfamily=_get_font())


def _base_plot_setup(excel_path, sheet, color, n_groups_or_list, figsize,
                     dpi=_DPI, as_palette=True):
    """
    Read an Excel file (row-1-as-header format) and return
    (group_order, groups_dict, bar_colors, fig, ax).
    Pass n_groups_or_list as int or a pre-built list of group names.
    """
    _ensure_imports()
    raw         = pd.read_excel(excel_path, sheet_name=sheet, header=0)
    group_order = list(raw.columns)
    groups      = {}
    for col in group_order:
        vals = pd.to_numeric(raw[col], errors="coerce").dropna().values
        if len(vals) == 0:
            raise ValueError(f"Column \'{col}\' contains no numeric data.")
        groups[col] = vals
    n      = len(group_order)
    colors = _assign_colors(n, color) if as_palette else None
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    return group_order, groups, colors, fig, ax


def _base_plot_finish(ax, fig, title, xlabel, ytitle, yscale, ylim,
                      font_size, ref_line, n_groups=None, ref_line_label="",
                      axis_style: str = "open", tick_dir: str = "out",
                      minor_ticks: bool = False,
                      ytick_interval: float = 0.0,
                      xtick_interval: float = 0.0,
                      fig_bg: str = "white",
                      spine_width: float = 0.8):
    """Apply shared axis labels, scale, limits, tight_layout."""
    if yscale == "log":
        ax.set_yscale("log")
        _apply_log_formatting(ax)
    if ylim is not None:
        ax.set_ylim(ylim)
    _set_axis_labels(ax, xlabel, ytitle, title, font_size)
    if ref_line is not None:
        _draw_ref_line(ax, ref_line, font_size, label=ref_line_label or None)
    _apply_prism_style(ax, font_size,
                       axis_style=axis_style,
                       tick_dir=tick_dir,
                       minor_ticks=minor_ticks,
                       fig_bg=fig_bg,
                       spine_width=spine_width)
    # Custom tick intervals (0 or None = auto)
    if ytick_interval and ytick_interval > 0 and yscale != "log":
        from matplotlib.ticker import MultipleLocator
        ax.yaxis.set_major_locator(MultipleLocator(ytick_interval))
    if xtick_interval and xtick_interval > 0:
        from matplotlib.ticker import MultipleLocator
        ax.xaxis.set_major_locator(MultipleLocator(xtick_interval))
    fig.patch.set_facecolor(fig_bg)
    fig.tight_layout(pad=_TIGHT_PAD)
    _fix_legend_overlap(ax, fig)




# ---------------------------------------------------------------------------
# PlotParams — centralised default registry for all shared function params
# ---------------------------------------------------------------------------
# Adding a new universal param (e.g. a future "spine_width") requires only:
#   1. Add its default here in PLOT_PARAM_DEFAULTS
#   2. Add extraction in _style_kwargs() if it feeds _apply_prism_style
#   3. Add the param to the function signatures that use it
# No changes needed at call sites — _style_kwargs(locals()) handles the rest.
# ---------------------------------------------------------------------------

PLOT_PARAM_DEFAULTS: dict = {
    # ── Axis / tick style ──────────────────────────────────────────────────
    "axis_style":  "open",    # "open" | "closed" | "floating" | "none"
    "tick_dir":    "out",     # "out" | "in" | "inout" | ""
    "minor_ticks": False,     # bool
    # ── Data point style ──────────────────────────────────────────────────
    "point_size":  6.0,       # marker diameter in pts; area = size²
    "point_alpha": 0.80,      # transparency 0–1
    # ── Error bar style ───────────────────────────────────────────────────
    "cap_size":    4.0,       # error bar cap width in pts
    # ── Legend ────────────────────────────────────────────────────────────
    "legend_pos":  "upper right",  # matplotlib loc string or "outside"/"none"
    # ── Tick intervals (0 = auto) ─────────────────────────────────────────
    "ytick_interval": 0.0,
    "xtick_interval": 0.0,
    # ── Background color ─────────────────────────────────────────────────
    "fig_bg": "white",
    # ── Spine / tick width ────────────────────────────────────────────────
    "spine_width": 0.8,
    # ── Grid style ────────────────────────────────────────────────────────
    "grid_style": "none",   # "none" | "horizontal" | "full"
    # ── Bracket style ─────────────────────────────────────────────────────
    "bracket_style": "lines",  # "lines" | "bracket" | "asterisks_only"
    # ── Layout ────────────────────────────────────────────────────────────
    "figsize":     (5, 5),
    "font_size":   12.0,
    # ── Labels ────────────────────────────────────────────────────────────
    "title":       "",
    "xlabel":      "",
    "ytitle":      "",
    "yscale":      "linear",
    "ylim":        None,
    "ref_line":    None,
    "ref_line_label": "",
}


def _style_kwargs(kw: dict) -> dict:
    """Extract the presentation style keys from a locals() / kwargs dict.

    Usage in any plot function::

        _sk = _style_kwargs(locals())
        _apply_prism_style(ax, font_size, **_sk)
        # …
        _base_plot_finish(ax, fig, …, **_sk)

    Centralising the key list here means adding a new style param requires
    only one change (PLOT_PARAM_DEFAULTS above + the function signature)
    rather than editing every call site.

    The function deliberately returns only the three keys that
    ``_apply_prism_style`` / ``_base_plot_finish`` accept, so it is safe to
    unpack with ** into those helpers without leaking unrelated keys.
    """
    return {
        "axis_style":     kw.get("axis_style",     PLOT_PARAM_DEFAULTS["axis_style"]),
        "tick_dir":       kw.get("tick_dir",       PLOT_PARAM_DEFAULTS["tick_dir"]),
        "minor_ticks":    kw.get("minor_ticks",    PLOT_PARAM_DEFAULTS["minor_ticks"]),
        "ytick_interval": kw.get("ytick_interval", PLOT_PARAM_DEFAULTS["ytick_interval"]),
        "xtick_interval": kw.get("xtick_interval", PLOT_PARAM_DEFAULTS["xtick_interval"]),
        "fig_bg":         kw.get("fig_bg",         PLOT_PARAM_DEFAULTS["fig_bg"]),
        "spine_width":    kw.get("spine_width",    PLOT_PARAM_DEFAULTS["spine_width"]),
    }


def _param(kw: dict, key: str):
    """Retrieve *key* from *kw* (typically locals()), falling back to
    PLOT_PARAM_DEFAULTS.  Useful in function bodies to avoid repetitive
    ``kw.get("x", some_literal)`` calls.

    Example::

        cap = _param(locals(), "cap_size")  # → float from arg or default
    """
    return kw.get(key, PLOT_PARAM_DEFAULTS.get(key))


def _resolve_font() -> str:
    """Return Arial if available, otherwise the best available sans-serif.
    Called once at plot time; result is lightweight to cache."""
    import matplotlib.font_manager as _fm
    available = {f.name for f in _fm.fontManager.ttflist}
    for candidate in ("Arial", "Helvetica Neue", "Helvetica",
                      "DejaVu Sans", "Liberation Sans", "FreeSans"):
        if candidate in available:
            return candidate
    return "sans-serif"


def _get_font() -> str:
    """Return the resolved plot font, caching after first call."""
    global _FONT
    if _FONT == "Arial":
        _FONT = _resolve_font()
    return _FONT


# ---------------------------------------------------------------------------
# Shared drawing helpers — eliminate repetition across chart functions
# ---------------------------------------------------------------------------

def _set_categorical_xticks(ax, group_order, groups, font_size,
                             show_n_labels: bool = False,
                             xtick_labels: list = None):
    """Set categorical x-axis ticks with smart rotation and optional n= labels.
    Called by every chart that has a categorical x-axis.
    xtick_labels overrides the display names if provided (must match length).
    Note: n= counts always use the original group_order keys.
    """
    if xtick_labels and len(xtick_labels) == len(group_order):
        display_names = list(xtick_labels)
    else:
        display_names = list(group_order)

    if show_n_labels:
        # n= counts come from original group keys, display uses overridden labels
        tick_labels = [f"{name}\nn={len(groups[orig])}"
                       for name, orig in zip(display_names, group_order)]
    else:
        tick_labels = display_names

    rot, ha = _smart_xrotation(display_names)
    ax.set_xticks(range(len(group_order)))
    ax.set_xticklabels(tick_labels, fontsize=font_size, fontfamily=_get_font(),
                       rotation=rot, ha=ha, fontweight="bold")
    ax.set_xlim(-0.6, len(group_order) - 0.4)


def _draw_jitter_points(ax, g_idx: int, vals, color,
                        jitter_amount: float = 0.15,
                        open_points: bool = False,
                        point_size: float = 6.0,
                        point_alpha: float = None):
    """Scatter jittered individual data points above/around a bar or box.

    Parameters
    ----------
    point_size  : marker diameter in pts; area = point_size ** 2.
    point_alpha : transparency 0–1; defaults to module constant _ALPHA_POINT.
    """
    alpha = point_alpha if point_alpha is not None else _ALPHA_POINT
    s     = point_size ** 2
    xs    = np.full(len(vals), g_idx, dtype=float)
    xs   += (np.random.rand(len(vals)) - 0.5) * jitter_amount
    fc    = "none" if open_points else color
    ax.scatter(xs, vals,
               color=fc, edgecolors=_darken_color(color),
               linewidths=_PT_LW, s=s, alpha=alpha, zorder=5)


def _draw_normality_warning(ax, norm_warn: str, font_size: float):
    """Draw the orange normality-violation warning text box on the axes."""
    if not norm_warn:
        return
    ax.text(0.02, 0.98, norm_warn,
            transform=ax.transAxes,
            ha="left", va="top",
            fontsize=max(font_size - 3, 7),
            color=_COLOR_WARN, fontfamily=_get_font(),
            bbox=dict(boxstyle="round,pad=0.3", fc="white",
                      ec="orange", alpha=0.85),
            zorder=10)


def _apply_stats_brackets(ax, groups: dict, group_order: list,
                           stats_test: str, n_permutations: int,
                           control, mc_correction: str, posthoc: str,
                           show_p_values: bool, show_effect_size: bool,
                           show_test_name: bool, font_size: float,
                           bar_tops: dict = None,
                           mu0: float = 0.0,
                           bracket_style: str = "lines"):
    """Run stats, filter ns brackets, draw brackets + optional effect sizes.

    bar_tops: dict mapping group name -> y value for bracket placement.
              Defaults to group max values if not supplied.
    Returns the (possibly empty) sig_results list.

    Control-group validation:
      • If control is set but not found in groups, falls back to all-pairwise
        with a warning rather than crashing.
      • Stacked bar / grouped bar whole-chart comparisons do not support a
        control group (stats are run per-category cluster instead); callers
        should pass control=None for those chart types.
    """
    if len(groups) < 1:
        return []
    # one_sample doesn't need a pairwise second group
    if stats_test != "one_sample" and len(groups) < 2:
        return []
    if control is not None and control not in groups:
        # Stale control name (e.g. after chart-type switch) — fall back gracefully
        # rather than crashing. Log the mismatch and run all-pairwise instead.
        import warnings as _w
        _w.warn(f"control {control!r} not found in groups {list(groups.keys())} "
                f"— falling back to all-pairwise", stacklevel=2)
        control = None

    sig_results = _run_stats(groups, test_type=stats_test,
                             n_permutations=n_permutations, control=control,
                             mc_correction=mc_correction, posthoc=posthoc,
                             mu0=mu0)
    sig_results = [r for r in sig_results if r[3] != "ns" or __show_ns__]

    if sig_results:
        tops = bar_tops or {g: float(groups[g].max()) for g in group_order}
        # For one_sample the second "group" is a mu0 label — only draw if
        # both labels are real group names (i.e., pairwise tests).
        if stats_test == "one_sample":
            # Annotate each bar with its p-value directly instead of bracket
            for g_name, null_lbl, p, stars in sig_results:
                if g_name in group_order:
                    g_idx = group_order.index(g_name)
                    y_top = tops.get(g_name, 0)
                    y_range = ax.get_ylim()[1] - ax.get_ylim()[0]
                    lbl = (f"p={p:.4f}" if show_p_values else stars)
                    ax.text(g_idx, y_top + y_range * 0.03, lbl,
                            ha="center", va="bottom",
                            fontsize=font_size - 1, fontfamily=_get_font(),
                            fontweight="bold" if stars != "ns" else "normal")
        else:
            _draw_significance_brackets(
                ax, sig_results,
                {g: float(i) for i, g in enumerate(group_order)},
                tops,
                show_p_values=show_p_values,
                bracket_style=bracket_style)

    if show_effect_size and sig_results:
        add_effect_sizes(ax, sig_results, groups,
                         {g: float(i) for i, g in enumerate(group_order)},
                         font_size=font_size)

    if show_test_name:
        _test_name_annotation(ax, stats_test, posthoc, len(groups), font_size)

    return sig_results



def _draw_subject_lines(ax, group_order, aligned, x_pos):
    """Draw thin gray connecting lines between repeated-measure subjects.
    Used by prism_before_after and prism_repeated_measures.
    """
    max_n = max(len(v) for v in aligned.values())
    for subj_i in range(max_n):
        xs, ys = [], []
        for g in group_order:
            y = aligned[g][subj_i]
            if not np.isnan(y):
                xs.append(x_pos[g])
                ys.append(y)
        if len(xs) > 1:
            ax.plot(xs, ys, color=_COLOR_SUBJ, linewidth=_SUBJ_LINE_LW,
                    alpha=_SUBJ_LINE_ALPHA, zorder=2)


def _draw_mean_errorbar(ax, x, vals, color, error_type, yscale):
    """Draw a mean tick + error bar for paired/subcolumn/repeated-measures plots.
    Returns the mean value for use in bracket placement.
    """
    c = _darken_color(color, 0.55)
    if yscale == "log":
        m, lo, hi = _calc_error_asymmetric(vals, error_type)
        ax.errorbar(x, m, yerr=[[lo], [hi]], fmt="none",
                    ecolor=c, elinewidth=_PAIR_ERR_LW,
                    capsize=_PAIR_CAP_SIZE, capthick=_PAIR_ERR_LW, zorder=5)
    else:
        m, err = _calc_error(vals, error_type)
        ax.errorbar(x, m, yerr=err, fmt="none",
                    ecolor=c, elinewidth=_PAIR_ERR_LW,
                    capsize=_PAIR_CAP_SIZE, capthick=_PAIR_ERR_LW, zorder=5)
    ax.plot([x - _MEAN_TICK_HALF, x + _MEAN_TICK_HALF], [m, m],
            color=c, linewidth=_MEAN_TICK_LW, zorder=6)
    return m


# ---------------------------------------------------------------------------
# prism_barplot
# ---------------------------------------------------------------------------

def prism_barplot(
    excel_path: str,
    sheet=0,
    error: str = "sem",
    show_points: bool = True,
    color=None,
    title: str = "",
    xlabel: str = "",
    ylabel: str = "",
    ytitle: str = "",
    yscale: str = "linear",
    ylim=None,
    show_stats: bool = False,
    stats_test: str = "parametric",
    n_permutations: int = 9999,
    control=None,
    mc_correction: str = "Holm-Bonferroni",
    posthoc: str = "Tukey HSD",
    figsize=(5, 5),
    bar_width: float = 0.6,
    font_size: float = 12.0,
    jitter_amount: float = 0.15,
    show_p_values: bool = False,
    show_effect_size: bool = False,
    show_n_labels: bool = True,
    show_test_name: bool = True,
    error_below_bar: bool = False,
    show_median: bool = False,
    alpha: float = 0.85,
    open_points: bool = False,
    gridlines: bool = False,
    grid_style: str = "none",
    horizontal: bool = False,
    xscale: str = "linear",
    ref_line=None,
    ref_line_label: str = "",
    # ── Priority-1 styling params ─────────────────────────────────────────
    axis_style: str = "open",
    tick_dir: str = "out",
    minor_ticks: bool = False,
    point_size: float = 6.0,
    point_alpha: float = 0.80,
    cap_size: float = 4.0,
    ytick_interval: float = 0.0,
    xtick_interval: float = 0.0,
    fig_bg: str = "white",
    spine_width: float = 0.8,
    mu0: float = 0.0,
    show_value_labels: bool = False,
    bracket_style: str = "lines",
    xtick_labels: list = None,
):
    """Plot a GraphPad Prism-style bar graph with significance brackets."""

    group_order, groups, bar_colors, _, _ = _base_plot_setup(
        excel_path, sheet, color, None, figsize)
    n_groups = len(group_order)

    plot_df = pd.DataFrame([
        {"group": g, "value": v}
        for g, vals in groups.items() for v in vals
    ])
    plot_df["group"] = pd.Categorical(
        plot_df["group"], categories=group_order, ordered=True)

    fig, ax = plt.subplots(figsize=figsize, dpi=_DPI)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FutureWarning)
        sns.barplot(data=plot_df, x="group", y="value", order=group_order,
                    palette=bar_colors,
                    edgecolor=[_darken_color(c) for c in bar_colors], linewidth=0.8,
                    errorbar=None,          # we draw error bars manually below
                    width=bar_width,
                    alpha=alpha,
                    zorder=3, ax=ax)

    _sk = _style_kwargs(locals())

    # Always draw error bars manually so we can use asymmetric bounds on log scale
    elw = _scale_errorbar_lw(bar_width)
    for g_idx, g in enumerate(group_order):
        vals = groups[g]
        _draw_bar_errorbar(ax, g_idx, vals, error, yscale,
                           elw=elw, cap_size=cap_size)

    # Optionally extend error bars below the bar (down to 0 or data min)
    if error_below_bar:
        elw = _scale_errorbar_lw(bar_width)
        for g_idx, g in enumerate(group_order):
            vals = groups[g]
            m, err_val2 = _calc_error(vals, error)
            bar_base = 0.0
            ax.errorbar(g_idx, bar_base, yerr=[[m - bar_base], [0]],
                        fmt="none", ecolor="black",
                        elinewidth=elw, capsize=cap_size, capthick=elw,
                        zorder=4)

    # Show median tick
    if show_median:
        for g_idx, g in enumerate(group_order):
            med = float(np.median(groups[g]))
            ax.plot([g_idx - bar_width*0.35, g_idx + bar_width*0.35], [med, med],
                    color="white", linewidth=2.0, zorder=6)

    # Value labels on top of each bar
    if show_value_labels:
        for g_idx, g in enumerate(group_order):
            vals = groups[g]
            if yscale == "log":
                m, lo, hi = _calc_error_asymmetric(vals, error)
                y_top = m + hi
            else:
                m, half = _calc_error(vals, error)
                y_top = m + half
            label_txt = _fmt_bar_label(float(m))
            if label_txt:
                ax.text(g_idx, y_top, label_txt,
                        ha="center", va="bottom",
                        fontsize=font_size * 0.82, fontfamily=_get_font(),
                        color=_COLOR_ANNOT, zorder=8)

    if show_points:
        for g_idx, g in enumerate(group_order):
            _draw_jitter_points(ax, g_idx, groups[g], bar_colors[g_idx],
                                jitter_amount=jitter_amount, open_points=open_points,
                                point_size=point_size, point_alpha=point_alpha)

    _set_categorical_xticks(ax, group_order, groups, font_size,
                            show_n_labels=show_n_labels,
                            xtick_labels=xtick_labels)
    ax.set_xlabel("")
    ax.set_yscale(yscale)
    _apply_prism_style(ax, font_size, **_sk)
    if xscale == "log":
        ax.set_xscale("log")

    _apply_grid(ax, grid_style, gridlines)

    if horizontal:
        # Flip axes for horizontal bar chart
        ax.set_xlabel(ytitle or ylabel or "", fontsize=font_size+2,
                      fontfamily=_get_font(), labelpad=_LABEL_PAD, fontweight="bold")
        ax.set_ylabel("", fontsize=font_size+2, fontfamily=_get_font(), labelpad=_LABEL_PAD)
        for container in ax.containers:
            try:
                for bar_ in container:
                    xy = bar_.get_xy() if hasattr(bar_, 'get_xy') else None
            except Exception:
                pass
        # Invert using barh — re-draw horizontally
        ax.cla()
        bar_tops_h = {}
        for g_idx, g in enumerate(group_order):
            vals = groups[g]
            m, err_h = _calc_error(vals, error)
            c = bar_colors[g_idx]
            ax.barh(g_idx, m, height=bar_width,
                    color=c, edgecolor=_darken_color(c), linewidth=0.8,
                    alpha=alpha, zorder=3)
            ax.errorbar(m, g_idx, xerr=err_h, fmt="none",
                        ecolor="black", elinewidth=_scale_errorbar_lw(bar_width),
                        capsize=cap_size, capthick=_scale_errorbar_lw(bar_width), zorder=4)
            if show_points:
                jy = np.full(len(vals), g_idx) + (np.random.rand(len(vals))-0.5)*jitter_amount
                fc = "none" if open_points else c
                ax.scatter(vals, jy, color=fc, edgecolors=_darken_color(c),
                           linewidths=_PT_LW, s=point_size**2, alpha=point_alpha, zorder=5)
            bar_tops_h[g] = float(vals.max())
        ax.set_yticks(range(n_groups))
        _h_tick_labels = (_n_labels(group_order, groups, font_size)
                          if show_n_labels else group_order)
        ax.set_yticklabels(_h_tick_labels, fontsize=font_size,
                           fontfamily=_get_font(), fontweight="bold")
        if xlim := ylim:
            ax.set_xlim(xlim)
        else:
            ax.set_xlim(left=0)
        _apply_prism_style(ax, font_size, **_sk)
        _apply_grid(ax, grid_style, gridlines)

    if ylim is not None and not horizontal:
        ax.set_ylim(ylim)
    elif not horizontal:
        if yscale == "log":
            all_vals = np.concatenate(list(groups.values()))
            pos_vals = all_vals[all_vals > 0]
            log_bottom = (10 ** (np.floor(np.log10(pos_vals.min())) - 0.2)
                          if len(pos_vals) else 0.1)
            ax.set_ylim(bottom=log_bottom)
        else:
            ax.set_ylim(bottom=0)

    if not horizontal:
        ax.set_xlim(-0.6, n_groups - 0.4)

    if title:  ax.set_title(title, fontsize=font_size+4, fontfamily=_get_font(), pad=_TITLE_PAD, fontweight="bold")
    if not horizontal:
        if xlabel: ax.set_xlabel(xlabel, fontsize=font_size+2, fontfamily=_get_font(), labelpad=_LABEL_PAD, fontweight="bold")
        if ytitle:
            ax.set_ylabel(ytitle, fontsize=font_size+2, fontfamily=_get_font(), labelpad=_LABEL_PAD, fontweight="bold")
        elif ylabel:
            err_label = {"sem": "SEM", "sd": "SD", "ci95": "95% CI"}[error]
            ax.set_ylabel(f"{ylabel} ± {err_label}", fontsize=font_size+2,
                          fontfamily=_get_font(), labelpad=_LABEL_PAD, fontweight="bold")

    norm_warn = normality_warning(groups, stats_test)

    if show_stats:
        _apply_stats_brackets(ax, groups, group_order,
                              stats_test, n_permutations, control,
                              mc_correction, posthoc,
                              show_p_values, show_effect_size, show_test_name,
                              font_size, mu0=mu0, bracket_style=bracket_style)

    _draw_normality_warning(ax, norm_warn, font_size)

    _base_plot_finish(ax, fig, title, xlabel, ytitle, yscale, ylim,
                      font_size, ref_line, n_groups, ref_line_label=ref_line_label,
                      **_sk)
    return fig, ax


# ---------------------------------------------------------------------------
# prism_linegraph
# ---------------------------------------------------------------------------

def prism_linegraph(
    excel_path: str,
    sheet=0,
    error: str = "sem",
    show_points: bool = True,
    color=None,
    title: str = "",
    xlabel: str = "",
    ytitle: str = "",
    yscale: str = "linear",
    ylim=None,
    show_stats: bool = False,
    stats_test: str = "parametric",
    n_permutations: int = 9999,
    control=None,
    figsize=(5, 5),
    font_size: float = 12.0,
    jitter_amount: float = 0.15,
    line_width: float = 1.5,
    marker_style: str = "o",
    marker_size: float = 7.0,
    gridlines: bool = False,
    grid_style: str = "none",
    ref_line=None,
    ref_line_label: str = "",
    # ── Priority-1 styling params ─────────────────────────────────────────
    axis_style: str = "open",
    tick_dir: str = "out",
    minor_ticks: bool = False,
    point_size: float = 6.0,
    point_alpha: float = 0.80,
    cap_size: float = 4.0,
    ytick_interval: float = 0.0,
    xtick_interval: float = 0.0,
    fig_bg: str = "white",
    spine_width: float = 0.8,
    legend_pos: str = "best",
    twin_y_series: list = None,   # P19: series names to plot on right Y axis
    ref_vline=None,               # vertical reference line (x value)
    ref_vline_label: str = "",
):
    """
    Plot a GraphPad Prism-style multi-series line graph with numeric X axis.

    Expected Excel layout:
      Row 1  : Col 1 = X-axis label (or blank), Cols 2+ = series names
               (repeat the series name across its replicate columns)
      Rows 2+: Col 1 = numeric X value, Cols 2+ = replicate Y values

    Example:
      Time | Control | Control | Control | Drug | Drug | Drug
      0    |   1.2   |   1.5   |   1.1   | 2.1  | 2.3  | 1.9
      24   |   3.4   |   3.1   |   3.8   | 4.2  | 4.5  | 4.1
    """

    _ensure_imports()

    # Uses module-level _calc_error and _assign_colors

    # Load data
    df_raw    = pd.read_excel(excel_path, sheet_name=sheet, header=None)
    row1      = df_raw.iloc[0]
    data_rows = df_raw.iloc[1:].reset_index(drop=True)

    # X values: column 1, rows 2+
    x_vals = pd.to_numeric(data_rows.iloc[:, 0], errors="coerce").values

    # Series names: row 1, columns 2+
    series_hdrs   = [str(h) if pd.notna(h) else "" for h in row1.iloc[1:]]
    unique_series = list(dict.fromkeys(h for h in series_hdrs if h))

    # X axis label: row 1 col 1 (if present)
    x_axis_label = str(row1.iloc[0]) if pd.notna(row1.iloc[0]) else ""

    # Group columns by series name
    series_cols = {}
    for col_i, h in enumerate(series_hdrs, start=1):
        if h:
            series_cols.setdefault(h, []).append(col_i)

    colors = _assign_colors(len(unique_series), color)

    fig, ax = plt.subplots(figsize=figsize, dpi=_DPI)

    for s_idx, s_name in enumerate(unique_series):
        col_idxs    = series_cols[s_name]
        this_marker = MARKER_CYCLE[s_idx % len(MARKER_CYCLE)] if marker_style == "auto" else marker_style
        means, errs, valid_x, raw_vals_list = [], [], [], []

        for row_i, xv in enumerate(x_vals):
            if np.isnan(xv):
                continue
            vals = pd.to_numeric(
                data_rows.iloc[row_i, col_idxs], errors="coerce").dropna().values
            if len(vals) == 0:
                continue
            m, e = _calc_error(vals, error)
            means.append(m); errs.append(e)
            valid_x.append(xv); raw_vals_list.append(vals)

        c = colors[s_idx]

        if len(valid_x) > 1:
            ax.plot(valid_x, means, color=c, linewidth=line_width,
                    zorder=3, solid_capstyle="round")

        for i, (xv, m, e) in enumerate(zip(valid_x, means, errs)):
            if yscale == "log":
                _, lo, hi = _calc_error_asymmetric(raw_vals_list[i], error)
                ax.errorbar(xv, m, yerr=[[lo], [hi]], fmt="none", ecolor=c,
                            elinewidth=1.0, capsize=4, capthick=1.0,
                            zorder=4, alpha=0.8)
            else:
                ax.errorbar(xv, m, yerr=e, fmt="none", ecolor=c,
                            elinewidth=1.0, capsize=4, capthick=1.0,
                            zorder=4, alpha=0.8)
            ax.plot(xv, m, marker=this_marker, markersize=marker_size,
                    color=c, markeredgecolor="white", markeredgewidth=0.8,
                    zorder=5, label=s_name if xv == valid_x[0] else "")

        if show_points:
            for row_i, xv in enumerate(x_vals):
                if np.isnan(xv): continue
                vals = pd.to_numeric(
                    data_rows.iloc[row_i, col_idxs], errors="coerce").dropna().values
                if len(vals) == 0: continue
                jitter = (np.random.rand(len(vals)) - 0.5) * jitter_amount
                ax.scatter(xv + jitter, vals, color=c,
                           s=16, alpha=0.55, zorder=2)

    # ── P19: Twin Y-axis for specified series ────────────────────────────────
    ax2 = None
    if twin_y_series:
        twin_set = set(twin_y_series)
        ax2 = ax.twinx()
        twin_colors = _assign_colors(len(unique_series), color)
        for s_idx, s_name in enumerate(unique_series):
            if s_name not in twin_set:
                continue
            col_idxs = series_cols[s_name]
            c = twin_colors[s_idx]
            this_marker = MARKER_CYCLE[s_idx % len(MARKER_CYCLE)] if marker_style == "auto" else marker_style
            means2, errs2, valid_x2 = [], [], []
            for row_i, xv in enumerate(x_vals):
                if np.isnan(xv):
                    continue
                vals = pd.to_numeric(data_rows.iloc[row_i, col_idxs], errors="coerce").dropna().values
                if len(vals) == 0:
                    continue
                m2, e2 = _calc_error(vals, error)
                means2.append(m2); errs2.append(e2); valid_x2.append(xv)
            if len(valid_x2) > 1:
                ax2.plot(valid_x2, means2, color=c, linewidth=line_width,
                         linestyle="--", zorder=3, solid_capstyle="round")
            for xv, m2, e2 in zip(valid_x2, means2, errs2):
                ax2.errorbar(xv, m2, yerr=e2, fmt="none", ecolor=c,
                             elinewidth=1.0, capsize=4, capthick=1.0, zorder=4, alpha=0.8)
                ax2.plot(xv, m2, marker=this_marker, markersize=marker_size,
                         color=c, markeredgecolor="white", markeredgewidth=0.8,
                         zorder=5, label=f"{s_name} (right)")
        # Style right axis
        ax2.spines["right"].set_linewidth(spine_width)
        ax2.tick_params(axis="y", which="major", labelsize=font_size,
                        direction="out", length=5, width=max(0.4, spine_width * 0.8))
        # Collect combined legend
        h1, l1 = ax.get_legend_handles_labels()
        h2, l2 = ax2.get_legend_handles_labels()
        if h1 or h2:
            ax.legend(h1 + h2, l1 + l2, frameon=False, fontsize=font_size, loc=legend_pos if legend_pos != "best" else "upper left")
    else:
        handles, labels_leg = ax.get_legend_handles_labels()
        if handles:
            _apply_legend(ax, legend_pos, font_size)

    # Axis styling
    _apply_prism_style(ax, font_size, **_style_kwargs(locals()))

    if yscale == "log":  ax.set_yscale("log")
    if ylim is not None: ax.set_ylim(ylim)

    effective_xlabel = xlabel if xlabel else x_axis_label
    _set_axis_labels(ax, effective_xlabel, ytitle, title, font_size)

    if yscale == "log": _apply_log_formatting(ax)
    _apply_grid(ax, grid_style, gridlines)
    if ref_line is not None: _draw_ref_line(ax, ref_line, font_size, label=ref_line_label or None)
    if ref_vline is not None: _draw_ref_vline(ax, ref_vline, font_size, label=ref_vline_label or None)
    fig.tight_layout(pad=_TIGHT_PAD)
    return fig, ax


# ---------------------------------------------------------------------------
# prism_grouped_barplot
# ---------------------------------------------------------------------------

def prism_grouped_barplot(
    excel_path: str,
    sheet=0,
    error: str = "sem",
    show_points: bool = True,
    color=None,
    title: str = "",
    xlabel: str = "",
    ytitle: str = "",
    yscale: str = "linear",
    ylim=None,
    show_stats: bool = False,
    stats_test: str = "parametric",
    n_permutations: int = 9999,
    mc_correction: str = "Holm-Bonferroni",
    posthoc: str = "Tukey HSD",
    figsize=(7, 5),
    bar_width: float = 0.6,
    font_size: float = 12.0,
    jitter_amount: float = 0.15,
    show_p_values: bool = False,
    show_effect_size: bool = False,
    show_anova_per_group: bool = False,
    ref_line=None,
    ref_line_label: str = "",
    # ── Priority-1 styling params ─────────────────────────────────────────
    axis_style: str = "open",
    tick_dir: str = "out",
    minor_ticks: bool = False,
    point_size: float = 6.0,
    point_alpha: float = 0.80,
    cap_size: float = 4.0,
    ytick_interval: float = 0.0,
    xtick_interval: float = 0.0,
    fig_bg: str = "white",
    spine_width: float = 0.8,
    legend_pos: str = "best",
    show_value_labels: bool = False,
    horizontal: bool = False,
):
    """
    Plot a GraphPad Prism-style grouped bar chart.

    Expected Excel layout:
      Row 1  : x-axis category names (one per column, repeated across subgroups)
      Row 2  : subgroup names within each category
      Rows 3+: replicate values

    Example:
      Control | Control | Drug A | Drug A
      Male    | Female  | Male   | Female
      1.2     | 2.3     | 3.4    | 4.5
      1.5     | 2.1     | 3.1    | 4.2

    Statistics: within-group comparisons only (subgroups within each category).
    """
    _ensure_imports()

    # ── Load & parse ──────────────────────────────────────────────────────────
    df_raw    = pd.read_excel(excel_path, sheet_name=sheet, header=None)
    row1      = [str(h) if pd.notna(h) else "" for h in df_raw.iloc[0]]
    row2      = [str(h) if pd.notna(h) else "" for h in df_raw.iloc[1]]
    data      = df_raw.iloc[2:].reset_index(drop=True)

    n_cols = df_raw.shape[1]

    # Unique categories (row 1) and subgroups (row 2), preserving order
    categories = list(dict.fromkeys(c for c in row1 if c))
    subgroups  = list(dict.fromkeys(s for s in row2 if s))
    n_cats     = len(categories)
    n_subs     = len(subgroups)

    # Map (category, subgroup) -> list of column indices
    col_map = {}
    for col_i in range(n_cols):
        cat = row1[col_i]; sub = row2[col_i]
        if cat and sub:
            col_map.setdefault((cat, sub), []).append(col_i)

    # Gather numeric data per (category, subgroup)
    def _get_vals(cat, sub):
        idxs = col_map.get((cat, sub), [])
        if not idxs:
            return np.array([])
        return pd.to_numeric(
            data.iloc[:, idxs].values.flatten(), errors="coerce"
        ).astype(float)

    # ── Colors (one per subgroup) ─────────────────────────────────────────────
    sub_colors = _assign_colors(n_subs, color)

    # ── Layout: cluster positions ─────────────────────────────────────────────
    # Each category gets a cluster of n_subs bars, centred on an integer x
    group_gap   = 1.0          # gap between category clusters
    cluster_w   = bar_width * n_subs
    offsets     = np.linspace(
        -cluster_w / 2 + bar_width / 2,
         cluster_w / 2 - bar_width / 2,
        n_subs
    )
    cat_centres = np.arange(n_cats) * (cluster_w + group_gap)

    fig, ax = plt.subplots(figsize=figsize, dpi=_DPI)

    for s_idx, sub in enumerate(subgroups):
        bar_xs = cat_centres + offsets[s_idx]
        means, errs_list = [], []
        for cat in categories:
            vals = _get_vals(cat, sub)
            vals = vals[~np.isnan(vals)]
            means.append(float(np.mean(vals)) if len(vals) > 0 else 0.0)
            _, e = _calc_error(vals[~np.isnan(vals)], error)
            errs_list.append(e)

        c = sub_colors[s_idx]
        ax.bar(bar_xs, means, width=bar_width,
               color=c, edgecolor="black", linewidth=0.8,
               label=sub, zorder=3)

        # Draw error bars — per-bar for log scale (asymmetric), vectorised otherwise
        if yscale == "log":
            for xi, cat in zip(bar_xs, categories):
                vals = _get_vals(cat, sub)
                vals = vals[~np.isnan(vals)]
                if len(vals) == 0:
                    continue
                _draw_bar_errorbar(ax, xi, vals, error, yscale, cap_size=cap_size)
        else:
            ax.errorbar(bar_xs, means, yerr=errs_list,
                        fmt="none", ecolor="black", elinewidth=1.0,
                        capsize=cap_size, capthick=1.0, zorder=4)

        if show_points:
            for xi, cat in zip(bar_xs, categories):
                vals = _get_vals(cat, sub)
                vals = vals[~np.isnan(vals)]
                if len(vals) == 0: continue
                jitter = (np.random.rand(len(vals)) - 0.5) * jitter_amount
                ax.scatter(xi + jitter, vals, color="black",
                           s=18, alpha=0.75, linewidths=1.2, edgecolors='white', zorder=5)

        # Value labels on top of each bar in this subgroup
        if show_value_labels:
            for xi, mean_v, err_v in zip(bar_xs, means, errs_list):
                if yscale == "log" and mean_v <= 0:
                    continue
                y_top = mean_v + err_v
                label_txt = _fmt_bar_label(float(mean_v))
                if label_txt:
                    ax.text(xi, y_top, label_txt,
                            ha="center", va="bottom",
                            fontsize=font_size * 0.78, fontfamily=_get_font(),
                            color=_COLOR_ANNOT, zorder=8)

    # ── Within-group significance brackets ───────────────────────────────────
    if show_stats and n_subs >= 2:
        for cat_i, cat in enumerate(categories):
            cat_groups = {}
            for sub in subgroups:
                vals = _get_vals(cat, sub)
                vals = vals[~np.isnan(vals)]
                if len(vals) >= 2:
                    cat_groups[sub] = vals

            if len(cat_groups) < 2:
                continue

            sig_results = _run_stats(cat_groups, test_type=stats_test,
                                     n_permutations=n_permutations,
                                     mc_correction=mc_correction, posthoc=posthoc)
            sig_results = [r for r in sig_results
                           if r[3] != "ns" or __show_ns__]
            if not sig_results:
                continue

            # x positions for this category's bars
            x_pos = {sub: float(cat_centres[cat_i] + offsets[s_idx])
                     for s_idx, sub in enumerate(subgroups)}
            bar_tops = {sub: float(np.max(_get_vals(cat, sub)[~np.isnan(_get_vals(cat, sub))]))
                        for sub in subgroups
                        if len(_get_vals(cat, sub)[~np.isnan(_get_vals(cat, sub))]) > 0}

            _draw_significance_brackets(ax, sig_results, x_pos, bar_tops,
                                         show_p_values=show_p_values)

    # ── Per-category one-way ANOVA annotation ────────────────────────────────
    if show_anova_per_group and n_subs >= 2:
        for cat_i, cat in enumerate(categories):
            arrays = []
            for sub in subgroups:
                vals = _get_vals(cat, sub)
                vals = vals[~np.isnan(vals)]
                if len(vals) >= 2:
                    arrays.append(vals)

            if len(arrays) < 2:
                continue

            F_val, p_val = stats.f_oneway(*arrays)
            stars = _p_to_stars(p_val)
            p_str = ("p<0.0001" if p_val < 0.0001
                     else f"p={p_val:.4f}" if p_val < 0.001
                     else f"p={p_val:.3f}")

            # Find the top of the tallest bar+error in this cluster
            cluster_top = ax.get_ylim()[1]
            for sub in subgroups:
                vals = _get_vals(cat, sub)
                vals = vals[~np.isnan(vals)]
                if len(vals) == 0:
                    continue
                m, e = _calc_error(vals, error)
                cluster_top = max(cluster_top, m + e)

            # Position annotation just above the cluster
            y_range = ax.get_ylim()[1] - ax.get_ylim()[0]
            ann_y   = cluster_top + y_range * 0.03

            ax.text(
                cat_centres[cat_i], ann_y,
                f"F={F_val:.2f}\n{p_str}  {stars}",
                ha="center", va="bottom",
                fontsize=font_size - 3,
                fontfamily=_get_font(),
                color=_COLOR_ANNOT,
                bbox=dict(boxstyle="round,pad=0.25", fc="white",
                          ec="lightgray", alpha=0.85),
                zorder=6,
            )
            # Expand ylim to fit annotation if needed
            needed = ann_y + y_range * 0.12
            if needed > ax.get_ylim()[1]:
                ax.set_ylim(top=needed)

    # ── Axes styling ──────────────────────────────────────────────────────────
    if horizontal:
        # Re-draw the entire chart horizontally using barh
        ax.cla()
        for s_idx, sub in enumerate(subgroups):
            bar_ys = cat_centres + offsets[s_idx]
            means_h, errs_h = [], []
            for cat in categories:
                vals = _get_vals(cat, sub)
                vals = vals[~np.isnan(vals)]
                means_h.append(float(np.mean(vals)) if len(vals) > 0 else 0.0)
                _, e = _calc_error(vals, error)
                errs_h.append(e)
            c = sub_colors[s_idx]
            ax.barh(bar_ys, means_h, height=bar_width,
                    color=c, edgecolor="black", linewidth=0.8,
                    label=sub, zorder=3)
            ax.errorbar(means_h, bar_ys, xerr=errs_h,
                        fmt="none", ecolor="black", elinewidth=1.0,
                        capsize=cap_size, capthick=1.0, zorder=4)
            if show_points:
                for yi, cat in zip(bar_ys, categories):
                    vals = _get_vals(cat, sub)
                    vals = vals[~np.isnan(vals)]
                    if len(vals) == 0: continue
                    jitter = (np.random.rand(len(vals)) - 0.5) * jitter_amount
                    ax.scatter(vals, yi + jitter, color="black",
                               s=18, alpha=0.75, linewidths=1.2,
                               edgecolors="white", zorder=5)
            if show_value_labels:
                for yi, mv, ev in zip(bar_ys, means_h, errs_h):
                    label_txt = _fmt_bar_label(float(mv))
                    if label_txt:
                        ax.text(mv + ev, yi, label_txt,
                                ha="left", va="center",
                                fontsize=font_size * 0.78,
                                fontfamily=_get_font(),
                                color=_COLOR_ANNOT, zorder=8)

        ax.set_yticks(cat_centres)
        _rot, _ha = _smart_xrotation(categories)
        ax.set_yticklabels(categories, fontsize=font_size,
                           fontfamily=_get_font(), fontweight="bold")
        ax.set_ylim(cat_centres[0] - cluster_w, cat_centres[-1] + cluster_w)
        ax.set_xlim(left=0)
        if ylim is not None:
            ax.set_xlim(ylim)
        _apply_prism_style(ax, font_size, **_style_kwargs(locals()))
        _apply_legend(ax, legend_pos, font_size)
        # Swap axis labels for horizontal orientation
        eff_xlabel = ytitle or ""
        eff_ytitle = xlabel or ""
        _base_plot_finish(ax, fig, title, eff_xlabel, eff_ytitle, yscale, None,
                          font_size, ref_line, ref_line_label=ref_line_label,
                          **_style_kwargs(locals()))
        return fig, ax

    ax.set_xticks(cat_centres)
    _rot, _ha = _smart_xrotation(categories)
    ax.set_xticklabels(categories, fontsize=font_size, fontfamily=_get_font(),
                       rotation=_rot, ha=_ha, fontweight="bold")
    ax.set_xlim(cat_centres[0] - cluster_w, cat_centres[-1] + cluster_w)
    ax.set_ylim(bottom=0)

    _apply_prism_style(ax, font_size, **_style_kwargs(locals()))
    ax.set_yscale(yscale)
    if ylim is not None: ax.set_ylim(ylim)

    _apply_legend(ax, legend_pos, font_size)

    _base_plot_finish(ax, fig, title, xlabel, ytitle, yscale, ylim,
                      font_size, ref_line, ref_line_label=ref_line_label,
                      **_style_kwargs(locals()))
    return fig, ax


def _fix_legend_overlap(ax, fig):
    """
    Ensure the legend never covers plotted data by expanding the y-axis if needed.

    Improvements over the previous version:
      • Uses proper display→data coordinate transform instead of fragile
        fractional estimates — works for any legend position, any axis scale.
      • Checks ax.patches (bars) in addition to ax.lines and ax.collections.
      • Legend height in data coords is measured directly, not approximated.
      • Only fires when legend_pos != "outside" (caller's responsibility).
    """
    try:
        legend = ax.get_legend()
        if legend is None:
            return
        fig.canvas.draw()          # must draw to get accurate bounding boxes
        renderer = fig.canvas.get_renderer()

        leg_bb = legend.get_window_extent(renderer)   # display (pixel) coords
        ax_bb  = ax.get_window_extent(renderer)

        if ax_bb.height == 0 or ax_bb.width == 0:
            return

        # ── Convert legend bbox corners to data coordinates ──────────────────
        inv = ax.transData.inverted()

        def _disp_to_data(x, y):
            return inv.transform((x, y))

        leg_data_x0, leg_data_y0 = _disp_to_data(leg_bb.x0, leg_bb.y0)
        leg_data_x1, leg_data_y1 = _disp_to_data(leg_bb.x1, leg_bb.y1)
        leg_xmin = min(leg_data_x0, leg_data_x1)
        leg_xmax = max(leg_data_x0, leg_data_x1)
        leg_ymin = min(leg_data_y0, leg_data_y1)
        leg_ymax = max(leg_data_y0, leg_data_y1)

        # ── Collect max data-y for every artist whose x falls in legend span ─
        max_y_in_leg_x = None

        def _check_y(xd, yd):
            nonlocal max_y_in_leg_x
            xd = np.asarray(xd, dtype=float)
            yd = np.asarray(yd, dtype=float)
            mask = (xd >= leg_xmin) & (xd <= leg_xmax)
            if np.any(mask):
                v = float(np.nanmax(yd[mask]))
                if max_y_in_leg_x is None or v > max_y_in_leg_x:
                    max_y_in_leg_x = v

        # Lines (line charts, scatter regression lines, KM curves, …)
        for line in ax.lines:
            _check_y(line.get_xdata(), line.get_ydata())

        # Collections (scatter points, violin bodies, fill_between bands, …)
        for coll in ax.collections:
            try:
                for path in coll.get_paths():
                    verts = path.vertices
                    _check_y(verts[:, 0], verts[:, 1])
            except Exception:
                pass

        # Patches (bars, box whisker caps, histogram bins, …)
        for patch in ax.patches:
            try:
                b = patch.get_bbox()
                bar_cx = (b.x0 + b.x1) / 2.0
                if leg_xmin <= bar_cx <= leg_xmax:
                    v = float(b.y1)
                    if max_y_in_leg_x is None or v > max_y_in_leg_x:
                        max_y_in_leg_x = v
            except Exception:
                pass

        if max_y_in_leg_x is None:
            return   # no data falls inside the legend's x-span

        # Also consider significance bracket tops drawn on this axes
        bracket_tops = getattr(ax, "_bracket_tops", [])
        if bracket_tops:
            max_bracket = max(bracket_tops)
            if max_y_in_leg_x is None or max_bracket > max_y_in_leg_x:
                max_y_in_leg_x = max_bracket

        # ── Push y-top up if any data would be hidden behind the legend ───────
        if max_y_in_leg_x >= leg_ymin:
            ylim = ax.get_ylim()
            y_range = ylim[1] - ylim[0]
            leg_height_data = abs(leg_ymax - leg_ymin)
            # Clear: data top + legend height + 8% padding
            new_top = max_y_in_leg_x + leg_height_data + y_range * 0.08
            if new_top > ylim[1]:
                ax.set_ylim(ylim[0], new_top)
                fig.canvas.draw()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Normality check
# ---------------------------------------------------------------------------

def check_normality(groups: dict, alpha: float = 0.05) -> dict:
    """
    Run Shapiro-Wilk normality test on each group.
    Returns {group_name: (stat, p, is_normal, warning_msg)}
    """
    results = {}
    for name, vals in groups.items():
        vals = vals[~np.isnan(vals)] if hasattr(vals, '__len__') else vals
        n = len(vals)
        if n < 3:
            results[name] = (None, None, None,
                             f"'{name}': too few values (n={n}) for normality test")
            continue
        stat, p = stats.shapiro(vals)
        is_normal = p > alpha
        if not is_normal:
            results[name] = (stat, p, False,
                             f"'{name}': non-normal (Shapiro-Wilk p={p:.4f})")
        else:
            results[name] = (stat, p, True, None)
    return results


def normality_warning(groups: dict, test_type: str) -> str:
    """
    Return a warning string if normality is violated and a parametric test is selected.
    Returns empty string if no warning needed or if the flag is disabled.
    """
    if not __show_normality_warning__:
        return ""
    if test_type != "parametric":
        return ""
    results = check_normality(groups)
    warnings_list = [v[3] for v in results.values() if v[3] is not None]
    if warnings_list:
        return ("Normality assumption may be violated:\n" +
                "\n".join(warnings_list) +
                "\nConsider using a non-parametric test.")
    return ""


# ---------------------------------------------------------------------------
# Effect size
# ---------------------------------------------------------------------------

def _cohens_d(a: np.ndarray, b: np.ndarray) -> float:
    """Cohen's d for two independent groups (pooled SD)."""
    n1, n2 = len(a), len(b)
    if n1 < 2 or n2 < 2:
        return float("nan")
    pooled_sd = np.sqrt(((n1 - 1) * np.var(a, ddof=1) +
                          (n2 - 1) * np.var(b, ddof=1)) / (n1 + n2 - 2))
    if pooled_sd == 0:
        return float("nan")
    return float((np.mean(a) - np.mean(b)) / pooled_sd)


def _effect_label(d: float) -> str:
    """Rough verbal label for Cohen's d magnitude."""
    ad = abs(d)
    if ad < 0.2:  return "negligible"
    if ad < 0.5:  return "small"
    if ad < 0.8:  return "medium"
    return "large"


def add_effect_sizes(ax, sig_results, groups, x_positions, font_size=10):
    """
    Annotate a corner text box with Cohen's d for each significant pair.
    Only used for 2-group comparisons or when explicitly requested.
    """
    lines = []
    for (a, b, p, stars) in sig_results:
        if a in groups and b in groups:
            d = _cohens_d(groups[a], groups[b])
            if not np.isnan(d):
                lines.append(f"{a} vs {b}: d={d:.2f} ({_effect_label(d)})")
    if lines:
        ax.text(0.98, 0.98, "\n".join(lines),
                transform=ax.transAxes,
                ha="right", va="top",
                fontsize=font_size - 2,
                fontfamily=_get_font(),
                color=_COLOR_ANNOT,
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="lightgray", alpha=0.8))


# ---------------------------------------------------------------------------
# prism_boxplot
# ---------------------------------------------------------------------------

def prism_boxplot(
    excel_path: str,
    sheet=0,
    show_points: bool = True,
    color=None,
    title: str = "",
    xlabel: str = "",
    ytitle: str = "",
    yscale: str = "linear",
    ylim=None,
    show_stats: bool = False,
    stats_test: str = "parametric",
    n_permutations: int = 9999,
    control=None,
    mc_correction: str = "Holm-Bonferroni",
    posthoc: str = "Tukey HSD",
    figsize=(5, 5),
    font_size: float = 12.0,
    jitter_amount: float = 0.15,
    show_p_values: bool = False,
    show_effect_size: bool = False,
    show_n_labels: bool = True,
    show_test_name: bool = True,
    ref_line=None,
    ref_line_label: str = "",
    notch: bool = False,
    gridlines: bool = False,
    grid_style: str = "none",
    open_points: bool = False,
    # ── Priority-1 styling params ─────────────────────────────────────────
    axis_style: str = "open",
    tick_dir: str = "out",
    minor_ticks: bool = False,
    point_size: float = 6.0,
    point_alpha: float = 0.80,
    cap_size: float = 4.0,
    ytick_interval: float = 0.0,
    xtick_interval: float = 0.0,
    fig_bg: str = "white",
    spine_width: float = 0.8,
    bracket_style: str = "lines",
    xtick_labels: list = None,
):
    """
    Plot a GraphPad Prism-style box-and-whisker plot.

    Same Excel layout as bar chart:
      Row 1  : group/category names
      Rows 2+: replicate values

    Box: IQR (25th–75th percentile)
    Whiskers: 1.5×IQR (Tukey style)
    Line: median
    Notch: optional 95% CI on median (set notch=True)
    """

    group_order, groups, box_colors, _, _ = _base_plot_setup(
        excel_path, sheet, color, None, figsize)
    n_groups = len(group_order)

    # Normality check
    norm_warn = normality_warning(groups, stats_test)

    plot_df = pd.DataFrame([
        {"group": g, "value": v}
        for g, vals in groups.items() for v in vals
    ])
    plot_df["group"] = pd.Categorical(
        plot_df["group"], categories=group_order, ordered=True)

    fig, ax = plt.subplots(figsize=figsize, dpi=_DPI)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FutureWarning)
        sns.boxplot(
            data=plot_df, x="group", y="value", order=group_order,
            palette=box_colors, width=0.5, linewidth=0.8,
            notch=notch, fliersize=0,
            medianprops={"color": "black", "linewidth": 1.5},
            whiskerprops={"linewidth": 0.8},
            capprops={"linewidth": 0.8},
            boxprops={"edgecolor": "black"},
            zorder=3, ax=ax)

    if show_points:
        for g_idx, g in enumerate(group_order):
            _draw_jitter_points(ax, g_idx, groups[g], box_colors[g_idx],
                                jitter_amount=jitter_amount, open_points=open_points,
                                point_size=point_size, point_alpha=point_alpha)

    _set_categorical_xticks(ax, group_order, groups, font_size,
                            show_n_labels=show_n_labels,
                            xtick_labels=xtick_labels)
    ax.set_xlabel("")
    ax.set_yscale(yscale)
    _apply_prism_style(ax, font_size, **_style_kwargs(locals()))

    _apply_grid(ax, grid_style, gridlines)

    if ylim is not None:
        ax.set_ylim(ylim)

    ax.set_xlim(-0.6, n_groups - 0.4)

    _set_axis_labels(ax, xlabel, ytitle, title, font_size)

    if show_stats:
        box_tops = {}
        for g in group_order:
            v = groups[g]
            q75 = np.percentile(v, 75)
            iqr = q75 - np.percentile(v, 25)
            box_tops[g] = min(q75 + 1.5 * iqr, v.max())
        _apply_stats_brackets(ax, groups, group_order,
                              stats_test, n_permutations, control,
                              mc_correction, posthoc,
                              show_p_values, show_effect_size, show_test_name,
                              font_size, bar_tops=box_tops,
                              bracket_style=bracket_style)

    _draw_normality_warning(ax, norm_warn, font_size)

    if yscale == "log": _apply_log_formatting(ax)
    if ref_line is not None: _draw_ref_line(ax, ref_line, font_size, label=ref_line_label or None)
    fig.tight_layout(pad=_TIGHT_PAD)
    return fig, ax



def _best_annotation_corner(ax, all_xs, all_ys):
    """Return (x_frac, y_frac, ha, va) for the annotation box corner that has
    fewest data points, so the box is least likely to overlap the data.

    Evaluates four corners: top-left, top-right, bottom-left, bottom-right.
    Uses normalised axis-fraction coordinates so it works on any scale.
    """
    try:
        x_lo, x_hi = ax.get_xlim()
        y_lo, y_hi = ax.get_ylim()
        if x_hi <= x_lo or y_hi <= y_lo:
            raise ValueError("degenerate axis")

        xs_n = np.array([(x - x_lo) / (x_hi - x_lo) for x in all_xs])
        ys_n = np.array([(y - y_lo) / (y_hi - y_lo) for y in all_ys])

        # Count points in each corner quadrant (normalised [0,1]²)
        CORNERS = {
            "tl": (xs_n < 0.45) & (ys_n > 0.55),   # top-left
            "tr": (xs_n > 0.55) & (ys_n > 0.55),   # top-right
            "bl": (xs_n < 0.45) & (ys_n < 0.45),   # bottom-left
            "br": (xs_n > 0.55) & (ys_n < 0.45),   # bottom-right
        }
        counts = {k: np.sum(v) for k, v in CORNERS.items()}
        best   = min(counts, key=lambda k: counts[k])

        placement = {
            "tl": (0.04, 0.96, "left",  "top"),
            "tr": (0.96, 0.96, "right", "top"),
            "bl": (0.04, 0.04, "left",  "bottom"),
            "br": (0.96, 0.04, "right", "bottom"),
        }
        return placement[best]
    except Exception:
        return (0.04, 0.96, "left", "top")   # safe fallback


# ---------------------------------------------------------------------------
# prism_scatterplot
# ---------------------------------------------------------------------------

def prism_scatterplot(
    excel_path: str,
    sheet=0,
    color=None,
    title: str = "",
    xlabel: str = "",
    ytitle: str = "",
    yscale: str = "linear",
    ylim=None,
    figsize=(5, 5),
    font_size: float = 12.0,
    marker_style: str = "auto",
    marker_size: float = 7.0,
    show_regression: bool = True,
    show_ci_band: bool = True,
    show_prediction_band: bool = False,
    correlation_type: str = "pearson",
    show_correlation: bool = True,
    show_regression_table: bool = False,
    gridlines: bool = False,
    grid_style: str = "none",
    ref_line=None,
    ref_line_label: str = "",
    # ── Priority-1 styling params ─────────────────────────────────────────
    axis_style: str = "open",
    tick_dir: str = "out",
    minor_ticks: bool = False,
    point_size: float = 6.0,
    point_alpha: float = 0.80,
    cap_size: float = 4.0,
    ytick_interval: float = 0.0,
    xtick_interval: float = 0.0,
    fig_bg: str = "white",
    spine_width: float = 0.8,
    legend_pos: str = "best",
    ref_vline=None,               # vertical reference line (x value)
    ref_vline_label: str = "",
):
    """
    Plot a GraphPad Prism-style XY scatter plot with optional regression and
    correlation annotation.

    Expected Excel layout — same as line graph:
      Row 1  : Col 1 = X-axis label (or blank), Cols 2+ = series names
               (repeat the series name across its replicate columns)
      Rows 2+: Col 1 = numeric X value, Cols 2+ = numeric Y values

    For a simple single-series scatter:
      X     | Y
      1.0   | 2.3
      2.0   | 4.1
      ...

    Statistics per series (annotated on plot):
      - Pearson r, r², p  (correlation_type="pearson")
      - Spearman r, p     (correlation_type="spearman")
      - Linear regression line with 95% CI band
      - Optional 95% prediction band
    """

    _ensure_imports()

    # ── Load data (same layout as line graph) ─────────────────────────────────
    df_raw    = pd.read_excel(excel_path, sheet_name=sheet, header=None)
    row1      = df_raw.iloc[0]
    data_rows = df_raw.iloc[1:].reset_index(drop=True)

    x_vals       = pd.to_numeric(data_rows.iloc[:, 0], errors="coerce").values
    x_axis_label = str(row1.iloc[0]) if pd.notna(row1.iloc[0]) else ""

    series_hdrs   = [str(h) if pd.notna(h) else "" for h in row1.iloc[1:]]
    unique_series = list(dict.fromkeys(h for h in series_hdrs if h))
    series_cols   = {}
    for col_i, h in enumerate(series_hdrs, start=1):
        if h: series_cols.setdefault(h, []).append(col_i)

    colors = _assign_colors(len(unique_series), color)

    fig, ax = plt.subplots(figsize=figsize, dpi=_DPI)

    annot_lines  = []  # collect correlation annotations
    _all_data_xs = []  # for smart annotation placement
    _all_data_ys = []

    for s_idx, s_name in enumerate(unique_series):
        col_idxs = series_cols[s_name]
        c        = colors[s_idx]
        this_marker = (MARKER_CYCLE[s_idx % len(MARKER_CYCLE)]
                       if marker_style == "auto" else marker_style)

        # Flatten all (x, y) pairs for this series
        xs_all, ys_all = [], []
        for row_i, xv in enumerate(x_vals):
            if np.isnan(xv): continue
            ys = pd.to_numeric(
                data_rows.iloc[row_i, col_idxs], errors="coerce").dropna().values
            for yv in ys:
                xs_all.append(xv); ys_all.append(yv)

        if not xs_all: continue
        xs_arr = np.array(xs_all); ys_arr = np.array(ys_all)
        _all_data_xs.extend(xs_all)
        _all_data_ys.extend(ys_all)

        # Scatter points
        ax.scatter(xs_arr, ys_arr,
                   color=c, marker=this_marker, s=marker_size**2,
                   edgecolors="white", linewidths=0.5,
                   alpha=0.85, zorder=4,
                   label=s_name if len(unique_series) > 1 else None)

        # ── Regression + bands ────────────────────────────────────────────────
        if show_regression and len(xs_arr) >= 3:
            slope, intercept, r_val, p_val, se = stats.linregress(xs_arr, ys_arr)
            n   = len(xs_arr)
            x_line = np.linspace(xs_arr.min(), xs_arr.max(), 200)
            y_line = slope * x_line + intercept

            ax.plot(x_line, y_line, color=c, linewidth=1.5, zorder=3)

            if show_ci_band or show_prediction_band:
                x_mean = xs_arr.mean()
                ss_xx  = np.sum((xs_arr - x_mean) ** 2)
                df_    = n - 2
                t_crit = stats.t.ppf(0.975, df=df_)
                y_hat  = slope * xs_arr + intercept
                mse    = np.sum((ys_arr - y_hat) ** 2) / df_

                se_line = np.sqrt(mse * (1/n + (x_line - x_mean)**2 / ss_xx))

                if show_ci_band:
                    ci = t_crit * se_line
                    ax.fill_between(x_line, y_line - ci, y_line + ci,
                                    color=c, alpha=_ALPHA_CI, zorder=2, label=None)

                if show_prediction_band:
                    pi = t_crit * np.sqrt(mse * (1 + 1/n + (x_line - x_mean)**2 / ss_xx))
                    ax.fill_between(x_line, y_line - pi, y_line + pi,
                                    color=c, alpha=0.07, zorder=1,
                                    linestyle="--", label=None)
                    ax.plot(x_line, y_line - pi, color=c,
                            linewidth=0.8, linestyle="--", alpha=0.4, zorder=2)
                    ax.plot(x_line, y_line + pi, color=c,
                            linewidth=0.8, linestyle="--", alpha=0.4, zorder=2)

        # ── Correlation annotation ─────────────────────────────────────────────
        if show_correlation and len(xs_arr) >= 3:
            if correlation_type == "spearman":
                r_corr, p_corr = stats.spearmanr(xs_arr, ys_arr)
                corr_label = "r\u209b"  # subscript s
            else:
                r_corr, p_corr = stats.pearsonr(xs_arr, ys_arr)
                corr_label = "r"

            r2    = r_corr ** 2
            p_str = "p<0.0001" if p_corr < 0.0001 else f"p={p_corr:.4f}"

            if len(unique_series) > 1:
                prefix = f"{s_name}: "
            else:
                prefix = ""

            annot_lines.append(
                f"{prefix}{corr_label}={r_corr:.3f}, R\u00b2={r2:.3f}, {p_str}"
            )

            if show_regression and len(xs_arr) >= 3:
                slope2, intercept2, _, _, _ = stats.linregress(xs_arr, ys_arr)
                sign   = "+" if intercept2 >= 0 else "-"
                annot_lines.append(
                    f"  y = {slope2:.3f}x {sign} {abs(intercept2):.3f}"
                )

    # Smart annotation placement: choose least-crowded corner
    if annot_lines:
        _ax_frac, _ay_frac, _ha, _va = _best_annotation_corner(
            ax, _all_data_xs, _all_data_ys)
        ax.text(_ax_frac, _ay_frac, "\n".join(annot_lines),
                transform=ax.transAxes,
                ha=_ha, va=_va,
                fontsize=font_size - 2,
                fontfamily=_get_font(),
                color=_COLOR_ANNOT,
                bbox=dict(boxstyle="round,pad=0.4", fc="white",
                          ec="lightgray", alpha=0.9))

    # Full regression table (Priority 2c) — single series only
    if show_regression_table and len(unique_series) == 1 and _all_data_xs:
        _draw_regression_table(ax, fig,
                               np.array(_all_data_xs), np.array(_all_data_ys),
                               font_size, colors[0])

    # Legend for multi-series
    if len(unique_series) > 1:
        _apply_legend(ax, legend_pos, font_size)

    # ── Axis styling ──────────────────────────────────────────────────────────
    _sk = _style_kwargs(locals())
    _apply_prism_style(ax, font_size, **_sk)
    fig.patch.set_facecolor(fig_bg)

    if yscale == "log":  ax.set_yscale("log")
    if ylim is not None: ax.set_ylim(ylim)

    effective_xlabel = xlabel if xlabel else x_axis_label
    _set_axis_labels(ax, effective_xlabel, ytitle, title, font_size)

    _apply_grid(ax, grid_style, gridlines)
    if ref_vline is not None: _draw_ref_vline(ax, ref_vline, font_size, label=ref_vline_label or None)
    _base_plot_finish(ax, fig, title, xlabel, ytitle, yscale, ylim,
                      font_size, ref_line, ref_line_label=ref_line_label, **_sk)
    return fig, ax
# ---------------------------------------------------------------------------

def prism_violin(
    excel_path: str,
    sheet=0,
    color=None,
    title: str = "",
    xlabel: str = "",
    ytitle: str = "",
    yscale: str = "linear",
    ylim=None,
    show_stats: bool = False,
    stats_test: str = "parametric",
    n_permutations: int = 9999,
    control=None,
    mc_correction: str = "Holm-Bonferroni",
    posthoc: str = "Tukey HSD",
    figsize=(5, 5),
    font_size: float = 12.0,
    jitter_amount: float = 0.15,
    show_points: bool = True,
    show_p_values: bool = False,
    show_effect_size: bool = False,
    show_n_labels: bool = False,
    show_test_name: bool = False,
    gridlines: bool = False,
    grid_style: str = "none",
    open_points: bool = False,
    ref_line=None,
    ref_line_label: str = "",
    # ── Priority-1 styling params ─────────────────────────────────────────
    axis_style: str = "open",
    tick_dir: str = "out",
    minor_ticks: bool = False,
    point_size: float = 6.0,
    point_alpha: float = 0.80,
    cap_size: float = 4.0,
    ytick_interval: float = 0.0,
    xtick_interval: float = 0.0,
    fig_bg: str = "white",
    spine_width: float = 0.8,
    bracket_style: str = "lines",
    xtick_labels: list = None,
):
    """
    Plot a GraphPad Prism-style violin plot.

    Same Excel layout as bar chart:
      Row 1  : group/category names
      Rows 2+: replicate values

    Each violin shows the full data distribution (kernel density estimate).
    A box-and-whisker overlay shows the median, IQR, and 1.5×IQR whiskers.
    Individual points are optionally overlaid.
    """

    group_order, groups, vln_colors, fig, ax = _base_plot_setup(
        excel_path, sheet, color, None, figsize)
    n_groups = len(group_order)

    norm_warn = normality_warning(groups, stats_test)

    plot_df = pd.DataFrame([
        {"group": g, "value": v}
        for g, vals in groups.items() for v in vals
    ])
    plot_df["group"] = pd.Categorical(
        plot_df["group"], categories=group_order, ordered=True)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FutureWarning)
        # Draw violins
        sns.violinplot(
            data=plot_df, x="group", y="value", order=group_order,
            palette=vln_colors, inner=None,
            linewidth=0.8, cut=0, density_norm="width",
            zorder=2, ax=ax)

        # Overlay thin boxplot for median/IQR
        sns.boxplot(
            data=plot_df, x="group", y="value", order=group_order,
            width=0.12, linewidth=1.0, fliersize=0,
            color="white",
            medianprops={"color": "black", "linewidth": 2.0},
            whiskerprops={"linewidth": 1.0, "color": _COLOR_BOX},
            capprops={"linewidth": 1.0, "color": _COLOR_BOX},
            boxprops={"edgecolor": _COLOR_BOX, "linewidth": 1.0},
            zorder=4, ax=ax)

    # Darken violin edges to match fill
    for i, patch in enumerate(ax.collections):
        if hasattr(patch, 'get_facecolor'):
            c = vln_colors[i % len(vln_colors)]
            patch.set_edgecolor(_darken_color(c, 0.7))
            patch.set_linewidth(0.8)

    if show_points:
        for g_idx, g in enumerate(group_order):
            _draw_jitter_points(ax, g_idx, groups[g], vln_colors[g_idx],
                                jitter_amount=jitter_amount, open_points=open_points,
                                point_size=point_size, point_alpha=point_alpha)

    _apply_prism_style(ax, font_size, **_style_kwargs(locals()))
    _apply_grid(ax, grid_style, gridlines)
    _set_categorical_xticks(ax, group_order, groups, font_size,
                            show_n_labels=show_n_labels)
    ax.set_xlabel("")

    if yscale != "log":
        ax.set_ylim(bottom=ax.get_ylim()[0])

    _apply_grid(ax, grid_style, gridlines)

    if show_stats:
        _apply_stats_brackets(ax, groups, group_order,
                              stats_test, n_permutations, control,
                              mc_correction, posthoc,
                              show_p_values, show_effect_size, show_test_name,
                              font_size, bracket_style=bracket_style)

    _draw_normality_warning(ax, norm_warn, font_size)

    _base_plot_finish(ax, fig, title, xlabel, ytitle, yscale, ylim,
                      font_size, ref_line, n_groups, ref_line_label=ref_line_label,
                      **_style_kwargs(locals()))
    return fig, ax


# ---------------------------------------------------------------------------
# Kaplan-Meier helpers
# ---------------------------------------------------------------------------

def _km_curve(times, events):
    """
    Compute Kaplan-Meier survival curve.
    Returns (unique_times, survival, lower_ci, upper_ci, n_at_risk, n_events)
    using Greenwood's formula for 95% CI (log-log transform).
    """
    times  = np.asarray(times,  dtype=float)
    events = np.asarray(events, dtype=float)
    order  = np.argsort(times)
    times, events = times[order], events[order]

    unique_times = np.unique(times[events == 1])
    n            = len(times)
    S            = 1.0
    survival     = [1.0]
    lower_ci     = [1.0]
    upper_ci     = [1.0]
    n_at_risk_   = [n]
    n_events_    = [0]
    greenwood    = 0.0
    t_out        = [0.0]

    n_remaining = n
    for t in unique_times:
        d_i = np.sum((times == t) & (events == 1))
        n_i = np.sum(times >= t)
        if n_i == 0: continue
        S          = S * (1.0 - d_i / n_i)
        if d_i < n_i:
            greenwood += d_i / (n_i * (n_i - d_i))
        # Greenwood log-log CI
        if S > 0 and S < 1:
            log_log_S   = np.log(-np.log(S))
            se_log_log  = np.sqrt(greenwood) / abs(np.log(S))
            z           = 1.96
            ll          = np.exp(-np.exp(log_log_S + z * se_log_log))
            ul          = np.exp(-np.exp(log_log_S - z * se_log_log))
        else:
            ll = ul = S

        t_out.append(t)
        survival.append(S)
        lower_ci.append(max(0.0, ll))
        upper_ci.append(min(1.0, ul))
        n_at_risk_.append(int(np.sum(times >= t)))
        n_events_.append(int(d_i))

    return (np.array(t_out), np.array(survival),
            np.array(lower_ci), np.array(upper_ci),
            np.array(n_at_risk_), np.array(n_events_))


def _logrank_test(groups_dict):
    """
    Pairwise log-rank tests between all groups.
    Returns list of (group_a, group_b, p_value, stars).
    """
    from itertools import combinations
    results = []
    keys = list(groups_dict.keys())
    for a, b in combinations(keys, 2):
        t1, e1 = groups_dict[a]
        t2, e2 = groups_dict[b]
        # Mantel-Cox log-rank
        all_times = np.unique(np.concatenate([t1[e1==1], t2[e2==1]]))
        O1 = O2 = E1 = E2 = 0.0
        var = 0.0
        for t in all_times:
            n1 = np.sum(t1 >= t); n2 = np.sum(t2 >= t)
            d1 = np.sum((t1 == t) & (e1 == 1))
            d2 = np.sum((t2 == t) & (e2 == 1))
            n  = n1 + n2; d = d1 + d2
            if n < 2: continue
            e1_exp = d * n1 / n
            O1 += d1; O2 += d2
            E1 += e1_exp; E2 += d - e1_exp
            var += (d * n1 * n2 * (n - d)) / (n**2 * (n - 1)) if n > 1 else 0
        if var > 0:
            chi2 = (O1 - E1)**2 / var
            p    = float(stats.chi2.sf(chi2, df=1))
        else:
            p = 1.0
        results.append((a, b, p, _p_to_stars(p)))
    return results


# ---------------------------------------------------------------------------
# prism_kaplan_meier
# ---------------------------------------------------------------------------

def prism_kaplan_meier(
    excel_path: str,
    sheet=0,
    color=None,
    title: str = "",
    xlabel: str = "Time",
    ytitle: str = "Survival Probability",
    ylim=None,
    figsize=(6, 5),
    font_size: float = 12.0,
    show_ci: bool = True,
    show_censors: bool = True,
    show_stats: bool = False,
    show_p_values: bool = False,
    show_at_risk: bool = False,
    ref_line=None,
    ref_line_label: str = "",
    # ── Priority-1 styling params ─────────────────────────────────────────
    axis_style: str = "open",
    tick_dir: str = "out",
    minor_ticks: bool = False,
    point_size: float = 6.0,
    point_alpha: float = 0.80,
    cap_size: float = 4.0,
    ytick_interval: float = 0.0,
    xtick_interval: float = 0.0,
    fig_bg: str = "white",
    spine_width: float = 0.8,
    legend_pos: str = "best",
):
    """
    Plot Kaplan-Meier survival curves.

    Expected Excel layout:
      Row 1  : group names — each group spans 2 columns
      Row 2  : 'Time' | 'Event'  (repeat per group; Event: 1=occurred, 0=censored)
      Rows 3+: numeric data

    Example (2 groups):
      Control | Control | Treatment | Treatment
      Time    | Event   | Time      | Event
      5       | 1       | 3         | 1
      10      | 0       | 8         | 1
      ...
    """
    _ensure_imports()

    # ── Load data ─────────────────────────────────────────────────────────────
    df_raw  = pd.read_excel(excel_path, sheet_name=sheet, header=None)
    row1    = [str(v).strip() if pd.notna(v) else "" for v in df_raw.iloc[0]]
    row2    = [str(v).strip().lower() if pd.notna(v) else "" for v in df_raw.iloc[1]]
    data    = df_raw.iloc[2:].reset_index(drop=True)

    # Pair columns by group name
    group_cols = {}
    i = 0
    while i < len(row1) - 1:
        gname = row1[i]
        if gname and row1[i+1] == gname:
            group_cols[gname] = (i, i+1)
            i += 2
        elif gname:
            group_cols[gname] = (i, i+1)
            i += 2
        else:
            i += 1

    if not group_cols:
        raise ValueError("Could not parse group columns. "
                         "Ensure row 1 has group names spanning two columns each.")

    groups_data = {}
    for gname, (tc, ec) in group_cols.items():
        t = pd.to_numeric(data.iloc[:, tc], errors="coerce").dropna().values
        e = pd.to_numeric(data.iloc[:, ec], errors="coerce").values[:len(t)]
        e = np.nan_to_num(e, nan=0).astype(float)
        if len(t) > 0:
            groups_data[gname] = (t, e)

    if not groups_data:
        raise ValueError("No valid time/event data found.")

    group_order = list(groups_data.keys())
    n_groups    = len(group_order)
    km_colors   = _assign_colors(n_groups, color)

    fig, ax = plt.subplots(figsize=figsize, dpi=_DPI)

    for g_idx, gname in enumerate(group_order):
        t_arr, e_arr = groups_data[gname]
        c = km_colors[g_idx]
        t_out, surv, lo, hi, n_risk, n_ev = _km_curve(t_arr, e_arr)

        # Step function
        ax.step(t_out, surv, where="post", color=c, linewidth=2.0,
                label=f"{gname} (n={len(t_arr)})", zorder=3)

        # 95% CI band
        if show_ci:
            # Build step versions of CI
            ax.fill_between(t_out, lo, hi, step="post",
                            color=c, alpha=0.15, zorder=2)

        # Censoring tick marks
        if show_censors:
            censor_t = t_arr[e_arr == 0]
            if len(censor_t) > 0:
                # Interpolate survival at censor times
                censor_s = np.interp(censor_t, t_out, surv)
                ax.scatter(censor_t, censor_s, marker="|", s=60,
                           color=c, linewidths=1.5, zorder=5)

    # ── Styling ───────────────────────────────────────────────────────────────
    _apply_prism_style(ax, font_size, **_style_kwargs(locals()))
    ax.set_ylim(-0.05, 1.05)
    if ylim is not None:
        ax.set_ylim(ylim)
    ax.set_xlim(left=0)
    ax.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda x, _: f"{x:.0%}"))

    _apply_legend(ax, legend_pos, font_size)

    # ── At-risk table ─────────────────────────────────────────────────────────
    if show_at_risk:
        time_pts = np.linspace(0, max(
            t_arr.max() for t_arr, _ in groups_data.values()), 6)
        table_rows = []
        for gname in group_order:
            t_arr, _ = groups_data[gname]
            row = [str(int(np.sum(t_arr >= tp))) for tp in time_pts]
            table_rows.append(row)
        tbl = ax.table(cellText=table_rows,
                       rowLabels=group_order,
                       colLabels=[f"{tp:.0f}" for tp in time_pts],
                       loc="bottom", cellLoc="center")
        tbl.auto_set_font_size(False)
        tbl.set_fontsize(font_size - 2)
        plt.subplots_adjust(bottom=0.25)
        ax.set_xlabel(xlabel or "Time", fontsize=font_size+2,
                      fontfamily=_get_font(), labelpad=30, fontweight="bold")
    else:
        ax.set_xlabel(xlabel or "Time", fontsize=font_size+2,
                      fontfamily=_get_font(), labelpad=_LABEL_PAD, fontweight="bold")

    _set_axis_labels(ax, xlabel, ytitle or "Survival Probability",
                     title, font_size, title_fs=font_size+6)

    # ── Log-rank statistics ───────────────────────────────────────────────────
    if show_stats and n_groups >= 2:
        lr_results = _logrank_test(groups_data)
        lines = []
        for a, b, p, stars in lr_results:
            p_str = f"p={p:.4f}" if show_p_values else stars
            lines.append(f"{a} vs {b}: {p_str}")
        ax.text(0.98, 0.98, "Log-rank test\n" + "\n".join(lines),
                transform=ax.transAxes, ha="right", va="top",
                fontsize=font_size - 2, fontfamily=_get_font(), color=_COLOR_ANNOT,
                bbox=dict(boxstyle="round,pad=0.4", fc="white",
                          ec="lightgray", alpha=0.9))

    if ref_line is not None:
        _draw_ref_line(ax, ref_line, font_size)
    fig.tight_layout(pad=_TIGHT_PAD)
    return fig, ax


# ---------------------------------------------------------------------------
# prism_heatmap
# ---------------------------------------------------------------------------

def prism_heatmap(
    excel_path: str,
    sheet=0,
    color=None,                   # colormap name e.g. "viridis", "RdBu_r", "mako"
    title: str = "",
    xlabel: str = "",
    ytitle: str = "",
    figsize=(7, 6),
    font_size: float = 11.0,
    annotate: bool = False,       # show numeric values in cells
    fmt: str = ".2f",             # number format when annotate=True
    cluster_rows: bool = False,   # hierarchical clustering on rows
    cluster_cols: bool = False,   # hierarchical clustering on columns
    vmin=None,                    # color scale min (None = data min)
    vmax=None,                    # color scale max (None = data max)
    center=None,                  # value to center diverging colormap on
    robust: bool = False,         # use 2nd/98th percentile for color limits
    ref_line=None,
    ref_line_label: str = "",
    # ── Priority-1 styling params ─────────────────────────────────────────
    axis_style: str = "open",
    tick_dir: str = "out",
    minor_ticks: bool = False,
    point_size: float = 6.0,
    point_alpha: float = 0.80,
    cap_size: float = 4.0,
    ytick_interval: float = 0.0,
    xtick_interval: float = 0.0,
    fig_bg: str = "white",
    spine_width: float = 0.8,
):
    """
    Plot a GraphPad Prism-style heat map.

    Expected Excel layout:
      Row 1    : Optional blank/label in A1, then column labels across B1, C1, ...
      Rows 2+  : Row label in column A, then numeric values across columns B, C, ...

    Example:
      Gene   | Sample1 | Sample2 | Sample3
      GeneA  |  2.1    |  -0.3   |  1.4
      GeneB  | -1.2    |   3.1   | -0.8
      ...
    """
    import matplotlib.colors as mcolors
    from scipy.cluster.hierarchy import linkage, dendrogram, leaves_list
    from scipy.spatial.distance import pdist

    _ensure_imports()

    # ── Load data ─────────────────────────────────────────────────────────────
    df_raw = pd.read_excel(excel_path, sheet_name=sheet, header=0, index_col=0)
    df_raw = df_raw.apply(pd.to_numeric, errors="coerce")
    df_raw = df_raw.dropna(how="all").dropna(axis=1, how="all")

    if df_raw.empty:
        raise ValueError("No numeric data found. Check your spreadsheet format.")

    row_labels = [str(i) for i in df_raw.index]
    col_labels = [str(c) for c in df_raw.columns]
    data       = df_raw.values.astype(float)
    n_rows, n_cols = data.shape

    # ── Optional hierarchical clustering ──────────────────────────────────────
    row_order = np.arange(n_rows)
    col_order = np.arange(n_cols)

    def _cluster(mat):
        """Return leaf order from average-linkage hierarchical clustering."""
        if mat.shape[0] < 2:
            return np.arange(mat.shape[0])
        dist = pdist(mat, metric="euclidean")
        Z    = linkage(dist, method="average")
        return leaves_list(Z)

    if cluster_rows:
        row_order = _cluster(data)
    if cluster_cols:
        col_order = _cluster(data.T)

    data_ordered      = data[np.ix_(row_order, col_order)]
    row_labels_ordered = [row_labels[i] for i in row_order]
    col_labels_ordered = [col_labels[i] for i in col_order]

    # ── Colour map ─────────────────────────────────────────────────────────────
    _CMAP_MAP = {
        "Default (Blue-Red)": "RdBu_r",
        "Viridis":            "viridis",
        "Mako":               "mako",
        "Plasma":             "plasma",
        "Coolwarm":           "coolwarm",
        "Spectral":           "Spectral_r",
        "YlOrRd":             "YlOrRd",
        "Blues":              "Blues",
        "Greens":             "Greens",
        "RdYlGn":             "RdYlGn",
    }
    cmap_name = _CMAP_MAP.get(color, color) if color else "RdBu_r"
    try:
        cmap = plt.get_cmap(cmap_name)
    except Exception:
        cmap = plt.get_cmap("RdBu_r")

    # ── Figure layout ──────────────────────────────────────────────────────────
    # Scale figure height to number of rows, width to number of cols
    cell_h  = max(0.35, min(0.7, 5.0 / n_rows))
    cell_w  = max(0.35, min(0.9, 7.0 / n_cols))
    fig_h   = figsize[1] if figsize else max(4, n_rows * cell_h + 1.5)
    fig_w   = figsize[0] if figsize else max(5, n_cols * cell_w + 2.5)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=_DPI)

    # ── Compute colour limits ──────────────────────────────────────────────────
    flat = data_ordered[~np.isnan(data_ordered)]
    if robust and len(flat):
        _vmin = float(np.percentile(flat, 2))
        _vmax = float(np.percentile(flat, 98))
    else:
        _vmin = float(np.nanmin(flat)) if len(flat) else 0
        _vmax = float(np.nanmax(flat)) if len(flat) else 1
    if vmin is not None: _vmin = vmin
    if vmax is not None: _vmax = vmax

    if center is not None:
        from matplotlib.colors import TwoSlopeNorm
        norm = TwoSlopeNorm(vmin=_vmin, vcenter=center, vmax=_vmax)
    else:
        norm = plt.Normalize(vmin=_vmin, vmax=_vmax)

    # ── Draw heatmap ──────────────────────────────────────────────────────────
    im = ax.imshow(data_ordered, aspect="auto", cmap=cmap, norm=norm,
                   interpolation="nearest")

    # Grid lines
    ax.set_xticks(np.arange(n_cols + 1) - 0.5, minor=True)
    ax.set_yticks(np.arange(n_rows + 1) - 0.5, minor=True)
    ax.grid(which="minor", color="white", linewidth=0.8)
    ax.tick_params(which="minor", bottom=False, left=False)

    # Tick labels
    ax.set_xticks(np.arange(n_cols))
    ax.set_yticks(np.arange(n_rows))
    ax.set_xticklabels(col_labels_ordered, fontsize=font_size,
                       fontfamily=_get_font(), rotation=45, ha="right")
    ax.set_yticklabels(row_labels_ordered, fontsize=font_size,
                       fontfamily=_get_font())
    ax.tick_params(axis="both", which="major", length=0)

    # ── Annotate cells with values ─────────────────────────────────────────────
    if annotate:
        thresh = (_vmin + _vmax) / 2
        for ri in range(n_rows):
            for ci in range(n_cols):
                val = data_ordered[ri, ci]
                if not np.isnan(val):
                    text_color = "white" if abs(val - thresh) > (_vmax - _vmin) * 0.3 else "black"
                    ax.text(ci, ri, format(val, fmt),
                            ha="center", va="center",
                            fontsize=max(6, font_size - 3),
                            fontfamily=_get_font(), color=text_color)

    # ── Color bar ────────────────────────────────────────────────────────────
    cbar = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cbar.ax.tick_params(labelsize=font_size - 1)
    cbar.outline.set_linewidth(0.5)

    # ── Spines and labels ─────────────────────────────────────────────────────
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_facecolor(fig_bg)
    fig.patch.set_facecolor(fig_bg)

    _set_axis_labels(ax, xlabel, ytitle, title, font_size, title_fs=font_size+6)

    if ref_line is not None:
        _draw_ref_line(ax, ref_line, font_size)

    fig.tight_layout(pad=_TIGHT_PAD)
    return fig, ax


# ---------------------------------------------------------------------------
# Two-way ANOVA helpers
# ---------------------------------------------------------------------------

def _twoway_anova(df, dv, factor_a, factor_b):
    """
    Compute two-way ANOVA (Type II SS) from a long-format DataFrame.
    Returns dict with keys: factor_a, factor_b, interaction, residual.
    Each value: {SS, df, MS, F, p, eta2}.
    Works for balanced and unbalanced designs.
    """
    from itertools import product as iproduct

    y      = df[dv].values.astype(float)
    a_vals = df[factor_a].values
    b_vals = df[factor_b].values
    N      = len(y)

    a_levels = sorted(set(a_vals))
    b_levels = sorted(set(b_vals))
    I, J     = len(a_levels), len(b_levels)

    a_idx = {v: i for i, v in enumerate(a_levels)}
    b_idx = {v: i for i, v in enumerate(b_levels)}

    # ── Build design matrix (intercept + A dummies + B dummies + AB dummies) ──
    def _make_X(include_a, include_b, include_ab):
        cols = [np.ones(N)]
        if include_a:
            for i in range(I - 1):
                cols.append((a_vals == a_levels[i]).astype(float))
        if include_b:
            for j in range(J - 1):
                cols.append((b_vals == b_levels[j]).astype(float))
        if include_ab:
            for i, j in iproduct(range(I - 1), range(J - 1)):
                cols.append(((a_vals == a_levels[i]) &
                              (b_vals == b_levels[j])).astype(float))
        return np.column_stack(cols)

    def _rss(X):
        """Residual sum of squares from OLS projection."""
        beta, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
        resid = y - X @ beta
        return float(np.dot(resid, resid))

    # Type II SS: each effect tested removing only that effect
    rss_full   = _rss(_make_X(True,  True,  True))
    rss_no_a   = _rss(_make_X(False, True,  True))
    rss_no_b   = _rss(_make_X(True,  False, True))
    rss_no_ab  = _rss(_make_X(True,  True,  False))
    ss_total   = float(np.sum((y - y.mean()) ** 2))

    SS_A   = rss_no_a  - rss_full
    SS_B   = rss_no_b  - rss_full
    SS_AB  = rss_no_ab - rss_full
    SS_err = rss_full

    df_A   = I - 1
    df_B   = J - 1
    df_AB  = (I - 1) * (J - 1)
    df_err = N - I * J

    if df_err <= 0:
        raise ValueError("Not enough observations for two-way ANOVA "
                         f"({N} obs, {I*J} cells). Need >1 replicate per cell.")

    MS_A   = SS_A   / df_A
    MS_B   = SS_B   / df_B
    MS_AB  = SS_AB  / df_AB
    MS_err = SS_err / df_err

    def _F_p(MS_effect, df_effect):
        if MS_err <= 0 or MS_effect < 0: return float("nan"), 1.0
        F = MS_effect / MS_err
        p = float(stats.f.sf(F, df_effect, df_err))
        return F, p

    F_A,  p_A  = _F_p(MS_A,  df_A)
    F_B,  p_B  = _F_p(MS_B,  df_B)
    F_AB, p_AB = _F_p(MS_AB, df_AB)

    return {
        factor_a:     {"SS": SS_A,  "df": df_A,  "MS": MS_A,  "F": F_A,  "p": p_A,
                        "eta2": SS_A  / ss_total},
        factor_b:     {"SS": SS_B,  "df": df_B,  "MS": MS_B,  "F": F_B,  "p": p_B,
                        "eta2": SS_B  / ss_total},
        "interaction": {"SS": SS_AB, "df": df_AB, "MS": MS_AB, "F": F_AB, "p": p_AB,
                        "eta2": SS_AB / ss_total},
        "residual":    {"SS": SS_err, "df": df_err, "MS": MS_err},
    }


def _twoway_posthoc(df, dv, factor_a, factor_b, correction="holm"):
    """
    Pairwise t-tests for each level of factor_A within each level of factor_B.
    Returns list of (label, group1, group2, p_raw, p_corr, stars).
    """
    from itertools import combinations

    results = []
    b_levels = sorted(df[factor_b].unique())
    a_levels = sorted(df[factor_a].unique())

    raw_ps = []
    pairs  = []

    for b_val in b_levels:
        sub = df[df[factor_b] == b_val]
        for a1, a2 in combinations(a_levels, 2):
            g1 = sub[sub[factor_a] == a1][dv].dropna().values
            g2 = sub[sub[factor_a] == a2][dv].dropna().values
            if len(g1) >= 2 and len(g2) >= 2:
                _, p = stats.ttest_ind(g1, g2)
                raw_ps.append(p)
                pairs.append((b_val, a1, a2))

    if not raw_ps:
        return []

    corr_ps = _apply_correction(raw_ps, "Holm-Bonferroni"
                                if correction == "holm" else correction)

    for (b_val, a1, a2), p_raw, p_corr in zip(pairs, raw_ps, corr_ps):
        results.append({
            "factor_b_level": b_val,
            "group1": a1, "group2": a2,
            "p_raw": p_raw, "p_corr": p_corr,
            "stars": _p_to_stars(p_corr),
        })

    return results


# ---------------------------------------------------------------------------
# prism_two_way_anova
# ---------------------------------------------------------------------------

def prism_two_way_anova(
    excel_path: str,
    sheet=0,
    color=None,
    title: str = "",
    xlabel: str = "",
    ytitle: str = "",
    yscale: str = "linear",
    ylim=None,
    figsize=(7, 5),
    font_size: float = 12.0,
    bar_width: float = 0.6,
    jitter_amount: float = 0.15,
    show_points: bool = True,
    error: str = "sem",
    show_stats: bool = False,
    show_posthoc: bool = False,
    show_p_values: bool = False,
    show_effect_size: bool = False,
    ref_line=None,
    ref_line_label: str = "",
    # ── Priority-1 styling params ─────────────────────────────────────────
    axis_style: str = "open",
    tick_dir: str = "out",
    minor_ticks: bool = False,
    point_size: float = 6.0,
    point_alpha: float = 0.80,
    cap_size: float = 4.0,
    ytick_interval: float = 0.0,
    xtick_interval: float = 0.0,
    fig_bg: str = "white",
    spine_width: float = 0.8,
):
    """
    Plot a grouped bar chart with two-way ANOVA statistics.

    Expected Excel layout (long format):
      Row 1  : Column headers — must include columns named:
               'Factor_A', 'Factor_B', 'Value'
               (exact names configurable; first two non-Value cols used as factors)
      Rows 2+: One observation per row

    Example:
      Factor_A | Factor_B | Value
      Drug     | Male     | 3.2
      Drug     | Female   | 4.1
      Control  | Male     | 1.8
      Control  | Male     | 2.1
      ...
    """
    import warnings

    _ensure_imports()

    # ── Load long-format data ─────────────────────────────────────────────────
    df = pd.read_excel(excel_path, sheet_name=sheet, header=0)
    df.columns = [str(c).strip() for c in df.columns]

    # Auto-detect columns: last numeric col = DV, first two = factors
    num_cols = [c for c in df.columns if pd.to_numeric(df[c], errors="coerce").notna().any()]
    cat_cols = [c for c in df.columns if c not in num_cols]

    if len(num_cols) < 1:
        raise ValueError("No numeric column found. Need at least one numeric 'Value' column.")
    if len(cat_cols) < 2:
        # Try to infer: last col = value, first two = factors
        if len(df.columns) >= 3:
            cat_cols  = list(df.columns[:2])
            num_cols  = [df.columns[2]]
        else:
            raise ValueError("Need at least 3 columns: Factor_A, Factor_B, Value.")

    factor_a = cat_cols[0]
    factor_b = cat_cols[1]
    dv       = num_cols[-1]

    df[dv] = pd.to_numeric(df[dv], errors="coerce")
    df     = df[[factor_a, factor_b, dv]].dropna()

    a_levels = sorted(df[factor_a].unique())
    b_levels = sorted(df[factor_b].unique())
    I, J     = len(a_levels), len(b_levels)
    n_colors = len(b_levels)
    colors   = _assign_colors(n_colors, color)

    # ── Build grouped bar layout ──────────────────────────────────────────────
    group_width = bar_width * J + 0.15
    x_positions = np.arange(I) * (group_width + 0.25)

    fig, ax = plt.subplots(figsize=figsize, dpi=_DPI)

    bar_tops    = {}   # (a_level, b_level) -> bar top for brackets
    b_x_centers = {b: [] for b in b_levels}

    for b_idx, b_val in enumerate(b_levels):
        offset  = (b_idx - (J - 1) / 2) * bar_width
        x_cents = x_positions + offset
        b_x_centers[b_val] = x_cents

        for xi, a_val in zip(x_cents, a_levels):
            cell_data = df[(df[factor_a] == a_val) &
                           (df[factor_b] == b_val)][dv].values
            if len(cell_data) == 0:
                bar_tops[(a_val, b_val)] = 0
                continue
            m, err = _calc_error(cell_data, error)
            c      = colors[b_idx]
            ax.bar(xi, m, width=bar_width * 0.9,
                   color=c, edgecolor=_darken_color(c),
                   linewidth=0.8, zorder=3)
            _draw_bar_errorbar(ax, xi, cell_data, error, yscale, cap_size=4.0)
            bar_tops[(a_val, b_val)] = m + err

            if show_points and len(cell_data) > 0:
                jx = np.full(len(cell_data), xi) + \
                     (np.random.rand(len(cell_data)) - 0.5) * jitter_amount
                ax.scatter(jx, cell_data, color=_darken_color(c),
                           s=16, alpha=0.75, zorder=5)

    # ── Axis styling ──────────────────────────────────────────────────────────
    _apply_prism_style(ax, font_size, **_style_kwargs(locals()))
    ax.set_xticks(x_positions)
    _rot, _ha = _smart_xrotation(a_levels)
    ax.set_xticklabels(a_levels, fontsize=font_size, fontfamily=_get_font(),
                       rotation=_rot, ha=_ha, fontweight="bold")
    ax.set_xlim(x_positions[0] - group_width, x_positions[-1] + group_width)
    if yscale != "log":
        ax.set_ylim(bottom=0)
    ax.set_xlabel(xlabel or factor_a, fontsize=font_size+2,
                  fontfamily=_get_font(), labelpad=_LABEL_PAD, fontweight="bold")
    _set_axis_labels(ax, xlabel, ytitle, title, font_size, title_fs=font_size+6)
    if ylim: ax.set_ylim(ylim)
    if yscale == "log": _apply_log_formatting(ax)

    # ── Legend ────────────────────────────────────────────────────────────────
    from matplotlib.patches import Patch
    legend_patches = [Patch(facecolor=colors[i],
                             edgecolor=_darken_color(colors[i]),
                             label=str(b)) for i, b in enumerate(b_levels)]
    # legend_pos wired below via _apply_legend after patches set
    ax.legend(handles=legend_patches, frameon=False,
              fontsize=font_size, title=factor_b,
              title_fontsize=font_size, loc="upper right")

    # ── Two-way ANOVA ─────────────────────────────────────────────────────────
    if show_stats:
        try:
            aov = _twoway_anova(df, dv, factor_a, factor_b)

            lines = ["Two-way ANOVA (Type II SS)"]
            for effect, label in [
                (factor_a,     f"  {factor_a}"),
                (factor_b,     f"  {factor_b}"),
                ("interaction", f"  {factor_a} × {factor_b}"),
            ]:
                r   = aov[effect]
                p   = r["p"]
                eta = r["eta2"]
                if show_p_values:
                    p_str = f"p={p:.4f}" if p >= 0.0001 else "p<0.0001"
                else:
                    p_str = _p_to_stars(p)
                eta_str = f", η²={eta:.3f}" if show_effect_size else ""
                lines.append(f"{label}: F({r['df']},{aov['residual']['df']})="
                              f"{r['F']:.2f}, {p_str}{eta_str}")

            ax.text(0.02, 0.98, "\n".join(lines),
                    transform=ax.transAxes, ha="left", va="top",
                    fontsize=font_size - 2, fontfamily=_get_font(),
                    color=_COLOR_ANNOT,
                    bbox=dict(boxstyle="round,pad=0.4", fc="white",
                              ec="lightgray", alpha=0.9))

            # Post-hoc brackets within each Factor A level
            if show_posthoc:
                ph = _twoway_posthoc(df, dv, factor_b, factor_a)
                y_top = ax.get_ylim()[1]
                bracket_step = (y_top - 0) * 0.08
                drawn = {}
                for res in ph:
                    if res["stars"] == "ns" and not __show_ns__:
                        continue
                    a_val = res["factor_b_level"]
                    b1, b2 = res["group1"], res["group2"]
                    b1_idx = b_levels.index(b1)
                    b2_idx = b_levels.index(b2)
                    a_xi   = x_positions[a_levels.index(a_val)]
                    x1 = a_xi + (b1_idx - (J-1)/2) * bar_width
                    x2 = a_xi + (b2_idx - (J-1)/2) * bar_width
                    key = (a_val, min(b1,b2), max(b1,b2))
                    level = drawn.get(a_val, 0)
                    y_br  = y_top * 0.92 + level * bracket_step
                    drawn[a_val] = level + 1
                    ax.plot([x1, x1, x2, x2],
                            [y_br*0.96, y_br, y_br, y_br*0.96],
                            color="black", linewidth=0.8)
                    lbl = res["p_corr"] if show_p_values else res["stars"]
                    ax.text((x1+x2)/2, y_br*1.005, str(lbl),
                            ha="center", va="bottom",
                            fontsize=font_size-3, fontfamily=_get_font())

        except Exception as e:
            ax.text(0.5, 0.5, f"ANOVA error:\n{e}",
                    transform=ax.transAxes, ha="center", va="center",
                    fontsize=font_size-2, color="red")

    if ref_line is not None: _draw_ref_line(ax, ref_line, font_size, label=ref_line_label or None)
    fig.tight_layout(pad=_TIGHT_PAD)
    return fig, ax


# ---------------------------------------------------------------------------
# prism_before_after  (↕ Before/After paired dot plot)
# ---------------------------------------------------------------------------

def prism_before_after(
    excel_path: str,
    sheet=0,
    color=None,
    title: str = "",
    xlabel: str = "",
    ytitle: str = "",
    yscale: str = "linear",
    ylim=None,
    figsize=(5, 5),
    font_size: float = 12.0,
    jitter_amount: float = 0.05,
    show_stats: bool = False,
    show_p_values: bool = False,
    show_n_labels: bool = False,
    gridlines: bool = False,
    grid_style: str = "none",
    ref_line=None,
    ref_line_label: str = "",
    # ── Priority-1 styling params ─────────────────────────────────────────
    axis_style: str = "open",
    tick_dir: str = "out",
    minor_ticks: bool = False,
    point_size: float = 6.0,
    point_alpha: float = 0.80,
    cap_size: float = 4.0,
    ytick_interval: float = 0.0,
    xtick_interval: float = 0.0,
    fig_bg: str = "white",
    spine_width: float = 0.8,
):
    """
    Paired dot plot with subject lines — the "Before/After" graph.

    Each subject is drawn as a dot in each column, connected by a thin grey line.
    A mean ± SD bar is overlaid per group.  A paired t-test bracket is drawn when
    show_stats=True (requires exactly 2 groups).

    Excel layout — same as bar chart:
      Row 1  : group names  (e.g. "Before", "After")
      Rows 2+: one row per subject (matched by row order)
    """
    group_order, groups, bar_colors, fig, ax = _base_plot_setup(
        excel_path, sheet, color, None, figsize)
    n_groups = len(group_order)

    # ── Subject connecting lines ──────────────────────────────────────────────
    # Align groups to the same row count (pad shorter columns with NaN)
    max_n = max(len(v) for v in groups.values())
    aligned = {}
    for g in group_order:
        v = groups[g]
        if len(v) < max_n:
            v = np.concatenate([v, np.full(max_n - len(v), np.nan)])
        aligned[g] = v

    x_pos = {g: i for i, g in enumerate(group_order)}
    _draw_subject_lines(ax, group_order, aligned, x_pos)

    # ── Individual dots ───────────────────────────────────────────────────────
    for g_idx, g in enumerate(group_order):
        vals = groups[g]
        jitter = (np.random.rand(len(vals)) - 0.5) * jitter_amount
        ax.scatter(g_idx + jitter, vals,
                   color=bar_colors[g_idx],
                   edgecolors=_darken_color(bar_colors[g_idx]),
                   linewidths=1.2, s=36, alpha=0.85, zorder=4)

    # ── Mean ± SD bar (thick line + cap) ─────────────────────────────────────
    for g_idx, g in enumerate(group_order):
        _draw_mean_errorbar(ax, g_idx, groups[g], bar_colors[g_idx], "sd", yscale)

    # ── Paired t-test bracket ─────────────────────────────────────────────────
    if show_stats and n_groups == 2:
        a, b = group_order[0], group_order[1]
        n  = min(len(groups[a]), len(groups[b]))
        _, p = stats.ttest_rel(groups[a][:n], groups[b][:n])
        stars = _p_to_stars(p)
        if stars != "ns" or __show_ns__:
            y_top  = ax.get_ylim()[1]
            y_range = ax.get_ylim()[1] - ax.get_ylim()[0]
            bk_y   = y_top + y_range * 0.07
            tip    = y_range * 0.025
            ax.plot([0, 0, 1, 1], [bk_y - tip, bk_y, bk_y, bk_y - tip],
                    color="black", linewidth=1.0)
            lbl = (f"p={p:.4f}" if show_p_values else stars)
            ax.text(0.5, bk_y + tip * 0.5, lbl,
                    ha="center", va="bottom",
                    fontsize=13 if stars != "ns" else 11,
                    fontfamily=_get_font(), fontweight="bold")
            ax.set_ylim(top=bk_y + y_range * 0.12)

    # ── Axis styling ──────────────────────────────────────────────────────────
    _apply_prism_style(ax, font_size, **_style_kwargs(locals()))
    ax.set_xticks(range(n_groups))
    _tick_labels = _n_labels(group_order, groups, font_size) if show_n_labels else group_order
    _rot, _ha = _smart_xrotation(group_order)
    ax.set_xticklabels(_tick_labels, fontsize=font_size, fontfamily=_get_font(),
                       rotation=_rot, ha=_ha, fontweight="bold")
    ax.set_xlim(-0.6, n_groups - 0.4)
    ax.set_xlabel(xlabel, fontsize=font_size + 2, fontfamily=_get_font(),
                  labelpad=_LABEL_PAD, fontweight="bold")

    _apply_grid(ax, grid_style, gridlines)
    _base_plot_finish(ax, fig, title, xlabel, ytitle, yscale, ylim, font_size, ref_line,
                      **_style_kwargs(locals()))
    return fig, ax


# ---------------------------------------------------------------------------
# prism_histogram  (📶 Histogram)
# ---------------------------------------------------------------------------

def prism_histogram(
    excel_path: str,
    sheet=0,
    color=None,
    title: str = "",
    xlabel: str = "",
    ytitle: str = "",
    ylim=None,
    figsize=(5, 5),
    font_size: float = 12.0,
    bins: int = 0,          # 0 = auto (Sturges)
    density: bool = False,  # True = probability density
    overlay_normal: bool = False,
    ref_line=None,
    ref_line_label: str = "",
    # ── Priority-1 styling params ─────────────────────────────────────────
    axis_style: str = "open",
    tick_dir: str = "out",
    minor_ticks: bool = False,
    point_size: float = 6.0,
    point_alpha: float = 0.80,
    cap_size: float = 4.0,
    ytick_interval: float = 0.0,
    xtick_interval: float = 0.0,
    fig_bg: str = "white",
    spine_width: float = 0.8,
    legend_pos: str = "best",
):
    """
    Histogram of raw values from one or more columns.

    Excel layout:
      Row 1  : series / group names
      Rows 2+: numeric values (columns may have different lengths; NaNs ignored)

    Parameters
    ----------
    bins          : number of bins (0 = automatic via Sturges' rule)
    density       : if True, normalise to probability density (area = 1)
    overlay_normal: draw a fitted normal curve on top of each series
    """
    group_order, groups, bar_colors, fig, ax = _base_plot_setup(
        excel_path, sheet, color, None, figsize)

    all_vals = np.concatenate(list(groups.values()))
    n_bins   = bins if bins > 0 else max(5, int(np.ceil(np.log2(len(all_vals)) + 1)))

    global_min = float(all_vals.min())
    global_max = float(all_vals.max())
    bin_edges  = np.linspace(global_min, global_max, n_bins + 1)

    alpha = 0.55 if len(group_order) > 1 else 0.75

    for g_idx, g in enumerate(group_order):
        vals = groups[g]
        c    = bar_colors[g_idx]
        ax.hist(vals, bins=bin_edges, density=density,
                color=c, edgecolor=_darken_color(c, 0.75),
                linewidth=0.6, alpha=alpha, label=g, zorder=3)

        if overlay_normal and len(vals) >= 5:
            mu, sigma = float(np.mean(vals)), float(np.std(vals, ddof=1))
            if sigma > 0:
                x_norm = np.linspace(global_min, global_max, 300)
                if density:
                    y_norm = stats.norm.pdf(x_norm, mu, sigma)
                else:
                    # Scale to match histogram counts
                    bin_w  = (global_max - global_min) / n_bins
                    y_norm = stats.norm.pdf(x_norm, mu, sigma) * len(vals) * bin_w
                ax.plot(x_norm, y_norm, color=_darken_color(c, 0.55),
                        linewidth=1.8, zorder=5)

    if len(group_order) > 1:
        _apply_legend(ax, legend_pos, font_size)

    _apply_prism_style(ax, font_size, **_style_kwargs(locals()))
    ax.set_xlabel(xlabel or group_order[0] if len(group_order) == 1 else xlabel,
                  fontsize=font_size + 2, fontfamily=_get_font(),
                  labelpad=6, fontweight="bold")
    y_lbl = ytitle or ("Density" if density else "Count")
    ax.set_ylabel(y_lbl, fontsize=font_size + 2, fontfamily=_get_font(),
                  labelpad=_LABEL_PAD, fontweight="bold")

    _base_plot_finish(ax, fig, title, xlabel, ytitle or y_lbl, "linear", ylim,
                      font_size, ref_line, **_style_kwargs(locals()))
    return fig, ax


# ---------------------------------------------------------------------------
# prism_subcolumn_scatter  (∷ Subcolumn Scatter)
# ---------------------------------------------------------------------------

def prism_subcolumn_scatter(
    excel_path: str,
    sheet=0,
    color=None,
    title: str = "",
    xlabel: str = "",
    ytitle: str = "",
    yscale: str = "linear",
    ylim=None,
    figsize=(5, 5),
    font_size: float = 12.0,
    jitter_amount: float = 0.15,
    error: str = "sem",
    show_stats: bool = False,
    show_p_values: bool = False,
    show_effect_size: bool = False,
    show_n_labels: bool = True,
    show_test_name: bool = False,
    stats_test: str = "parametric",
    n_permutations: int = 9999,
    control=None,
    mc_correction: str = "Holm-Bonferroni",
    posthoc: str = "Tukey HSD",
    gridlines: bool = False,
    grid_style: str = "none",
    open_points: bool = False,
    ref_line=None,
    ref_line_label: str = "",
    # ── Priority-1 styling params ─────────────────────────────────────────
    axis_style: str = "open",
    tick_dir: str = "out",
    minor_ticks: bool = False,
    point_size: float = 6.0,
    point_alpha: float = 0.80,
    cap_size: float = 4.0,
    ytick_interval: float = 0.0,
    xtick_interval: float = 0.0,
    fig_bg: str = "white",
    spine_width: float = 0.8,
    bracket_style: str = "lines",
    xtick_labels: list = None,
):
    """
    Subcolumn scatter: individual points + mean ± error bar, no box/bar fill.
    The "honest bar chart" used in top journals (Weissgerber et al. 2015).

    Excel layout — same as bar chart:
      Row 1  : group names
      Rows 2+: numeric values
    """
    group_order, groups, bar_colors, fig, ax = _base_plot_setup(
        excel_path, sheet, color, None, figsize)
    n_groups = len(group_order)

    bar_tops = {}

    for g_idx, g in enumerate(group_order):
        vals = groups[g]
        c    = bar_colors[g_idx]
        x    = g_idx

        # Jittered individual points
        jitter = (np.random.rand(len(vals)) - 0.5) * jitter_amount
        fc = "none" if open_points else c
        ax.scatter(x + jitter, vals,
                   color=fc, edgecolors=_darken_color(c, 0.75),
                   linewidths=1.2, s=28, alpha=0.85, zorder=4)

        # Mean ± error bar via shared helper
        m = _draw_mean_errorbar(ax, x, vals, c, error, yscale)
        bar_tops[g] = float(vals.max())

    # ── Significance brackets + normality warning ─────────────────────────────
    norm_warn = normality_warning(groups, stats_test)

    if show_stats:
        _apply_stats_brackets(ax, groups, group_order,
                              stats_test, n_permutations, control,
                              mc_correction, posthoc,
                              show_p_values, show_effect_size, show_test_name,
                              font_size, bar_tops=bar_tops,
                              bracket_style=bracket_style)

    _draw_normality_warning(ax, norm_warn, font_size)

    # ── Axis styling ──────────────────────────────────────────────────────────
    _apply_prism_style(ax, font_size, **_style_kwargs(locals()))
    _set_categorical_xticks(ax, group_order, groups, font_size,
                            show_n_labels=show_n_labels,
                            xtick_labels=xtick_labels)
    if yscale != "log":
        data_min = min(float(v.min()) for v in groups.values())
        pad      = abs(data_min) * 0.10 if data_min != 0 else 0.5
        ax.set_ylim(bottom=data_min - pad)

    _base_plot_finish(ax, fig, title, xlabel, ytitle, yscale, ylim, font_size, ref_line,
                      **_style_kwargs(locals()))
    return fig, ax

# ---------------------------------------------------------------------------
# Nonlinear curve fitting — prism_curve_fit
# ---------------------------------------------------------------------------

# ── Model library ────────────────────────────────────────────────────────────
# Each entry: name -> (callable, param_names, p0_hint_fn)
# p0_hint_fn receives (x_arr, y_arr) and returns a list of initial-guess values.
# Adding a new model = one entry here, nothing else.

def _p0_range(x, y):
    """Utility: return (x_min, x_max, y_min, y_max, y_range, x_mid)."""
    xmn, xmx = float(np.nanmin(x)), float(np.nanmax(x))
    ymn, ymx = float(np.nanmin(y)), float(np.nanmax(y))
    return xmn, xmx, ymn, ymx, ymx - ymn, (xmn + xmx) / 2


def _make_4pl():
    """Return the 4-parameter logistic (Hill equation) model specification."""
    def fn(x, Bottom, Top, EC50, HillSlope):
        return Bottom + (Top - Bottom) / (1.0 + (EC50 / np.where(x == 0, 1e-12, x)) ** HillSlope)
    def p0(x, y):
        xmn, xmx, ymn, ymx, yr, xm = _p0_range(x, y)
        return [ymn, ymx, xm, 1.0]
    return fn, ["Bottom", "Top", "EC50", "HillSlope"], p0

def _make_3pl():
    """Return the 3-parameter logistic model specification."""
    def fn(x, Top, EC50, HillSlope):
        return Top / (1.0 + (EC50 / np.where(x == 0, 1e-12, x)) ** HillSlope)
    def p0(x, y):
        xmn, xmx, ymn, ymx, yr, xm = _p0_range(x, y)
        return [ymx, xm, 1.0]
    return fn, ["Top", "EC50", "HillSlope"], p0

def _make_exp_decay1():
    """Return the single-component exponential decay model specification."""
    def fn(x, Y0, Plateau, K):
        return Plateau + (Y0 - Plateau) * np.exp(-K * x)
    def p0(x, y):
        xmn, xmx, ymn, ymx, yr, xm = _p0_range(x, y)
        return [ymx, ymn, 1.0 / max(xm, 1e-9)]
    return fn, ["Y0", "Plateau", "K"], p0

def _make_exp_growth1():
    """Return the single-component exponential growth model specification."""
    def fn(x, Y0, Plateau, K):
        return Plateau - (Plateau - Y0) * np.exp(-K * x)
    def p0(x, y):
        xmn, xmx, ymn, ymx, yr, xm = _p0_range(x, y)
        return [ymn, ymx, 1.0 / max(xm, 1e-9)]
    return fn, ["Y0", "Plateau", "K"], p0

def _make_exp_decay2():
    """Return the two-component exponential decay model specification."""
    def fn(x, Y0, Plateau, K_fast, K_slow, Fraction_fast):
        frac = max(0.0, min(1.0, Fraction_fast))
        return (Plateau
                + (Y0 - Plateau) * frac       * np.exp(-K_fast * x)
                + (Y0 - Plateau) * (1 - frac) * np.exp(-K_slow * x))
    def p0(x, y):
        xmn, xmx, ymn, ymx, yr, xm = _p0_range(x, y)
        k = 1.0 / max(xm, 1e-9)
        return [ymx, ymn, k * 3, k * 0.3, 0.5]
    return fn, ["Y0", "Plateau", "K_fast", "K_slow", "Fraction_fast"], p0

def _make_linear():
    """Return the linear (straight-line) model specification."""
    def fn(x, Slope, Intercept):
        return Slope * x + Intercept
    def p0(x, y):
        try:
            from scipy import stats as _st
            s, i, *_ = _st.linregress(x, y)
            return [s, i]
        except Exception:
            return [1.0, 0.0]
    return fn, ["Slope", "Intercept"], p0

def _make_poly2():
    """Return the second-degree polynomial model specification."""
    def fn(x, A, B, C):
        return A * x**2 + B * x + C
    def p0(x, y):
        return [0.0, 1.0, float(np.nanmean(y))]
    return fn, ["A (x²)", "B (x)", "C (const)"], p0

def _make_michaelis_menten():
    """Return the Michaelis-Menten enzyme kinetics model specification."""
    def fn(x, Vmax, Km):
        return Vmax * x / (Km + np.where(x == 0, 1e-12, x))
    def p0(x, y):
        xmn, xmx, ymn, ymx, yr, xm = _p0_range(x, y)
        return [ymx * 1.2, xm]
    return fn, ["Vmax", "Km"], p0

def _make_gaussian():
    """Return the Gaussian (normal distribution) model specification."""
    def fn(x, Amplitude, Mean, SD):
        return Amplitude * np.exp(-0.5 * ((x - Mean) / np.where(SD == 0, 1e-9, SD)) ** 2)
    def p0(x, y):
        xmn, xmx, ymn, ymx, yr, xm = _p0_range(x, y)
        return [ymx, xm, (xmx - xmn) / 4]
    return fn, ["Amplitude", "Mean", "SD"], p0

def _make_hill():
    """Return the Hill sigmoidal dose-response model specification."""
    def fn(x, Vmax, K_half, n):
        xn = np.power(np.where(x <= 0, 1e-12, x), n)
        return Vmax * xn / (K_half**n + xn)
    def p0(x, y):
        xmn, xmx, ymn, ymx, yr, xm = _p0_range(x, y)
        return [ymx, xm, 1.0]
    return fn, ["Vmax", "K_half", "n (Hill)"], p0

def _make_log_normal():
    """Return the log-normal cumulative distribution model specification."""
    def fn(x, Amplitude, mu, sigma):
        lx = np.log(np.where(x <= 0, 1e-12, x))
        return Amplitude * np.exp(-0.5 * ((lx - mu) / np.where(sigma == 0, 1e-9, sigma))**2)
    def p0(x, y):
        xmn, xmx, ymn, ymx, yr, xm = _p0_range(x, y)
        return [ymx, float(np.log(max(xm, 1e-9))), 1.0]
    return fn, ["Amplitude", "mu (log)", "sigma (log)"], p0

# Build the public model registry
CURVE_MODELS: dict = {}
for _name, _maker in [
    ("4PL Sigmoidal (EC50/IC50)",         _make_4pl),
    ("3PL Sigmoidal (no bottom)",          _make_3pl),
    ("One-phase exponential decay",        _make_exp_decay1),
    ("One-phase exponential growth",       _make_exp_growth1),
    ("Two-phase exponential decay",        _make_exp_decay2),
    ("Michaelis-Menten",                   _make_michaelis_menten),
    ("Hill equation",                      _make_hill),
    ("Gaussian (bell curve)",              _make_gaussian),
    ("Log-normal",                         _make_log_normal),
    ("Linear",                             _make_linear),
    ("Polynomial (2nd order)",             _make_poly2),
]:
    _fn, _params, _p0 = _maker()
    CURVE_MODELS[_name] = {"fn": _fn, "params": _params, "p0": _p0}


def _fit_model(x, y, model_name):
    """
    Fit a model to (x, y) data.
    Returns dict with keys: popt, pcov, perr, r2, residuals, model_name, param_names.
    Raises ValueError on failure.
    """
    from scipy.optimize import curve_fit

    model   = CURVE_MODELS[model_name]
    fn      = model["fn"]
    p_names = model["params"]
    p0_fn   = model["p0"]

    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    x, y = x[mask], y[mask]

    if len(x) < len(p_names) + 1:
        raise ValueError(f"Need at least {len(p_names)+1} points for {model_name} "
                         f"({len(x)} provided)")

    p0 = p0_fn(x, y)

    try:
        popt, pcov = curve_fit(fn, x, y, p0=p0, maxfev=10000,
                               full_output=False, check_finite=True)
    except Exception:
        # Try with tighter bounds / different initial guess
        popt, pcov = curve_fit(fn, x, y, p0=p0, maxfev=50000)

    perr     = np.sqrt(np.diag(pcov))
    y_pred   = fn(x, *popt)
    ss_res   = np.sum((y - y_pred) ** 2)
    ss_tot   = np.sum((y - np.mean(y)) ** 2)
    r2       = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    residuals = y - y_pred

    return {
        "popt": popt, "pcov": pcov, "perr": perr,
        "r2": r2, "residuals": residuals,
        "model_name": model_name, "param_names": p_names,
        "x": x, "y": y,
    }


def _curve_ci_band(x_line, x_data, y_data, popt, fn, alpha=0.05):
    """Return (lower_ci, upper_ci) for the fitted curve using delta method."""
    from scipy import stats as _st
    from scipy.optimize import curve_fit

    n  = len(x_data)
    p  = len(popt)
    df = max(n - p, 1)
    t  = _st.t.ppf(1 - alpha / 2, df)

    # Numerical Jacobian of the model at each x in x_line
    eps   = 1e-6 * (np.abs(popt) + 1e-8)
    y0    = fn(x_line, *popt)
    J     = np.zeros((len(x_line), p))
    for i in range(p):
        dp = np.zeros(p); dp[i] = eps[i]
        J[:, i] = (fn(x_line, *(popt + dp)) - y0) / eps[i]

    try:
        _, pcov = curve_fit(fn, x_data, y_data, p0=popt, maxfev=100)
    except Exception:
        pcov = np.eye(p) * 1e-6

    se_line = np.sqrt(np.einsum("ij,jk,ik->i", J, pcov, J))
    return y0 - t * se_line, y0 + t * se_line


# ---------------------------------------------------------------------------
# prism_curve_fit  (📈 Curve Fit)
# ---------------------------------------------------------------------------

def prism_curve_fit(
    excel_path: str,
    sheet=0,
    color=None,
    title: str = "",
    xlabel: str = "",
    ytitle: str = "",
    yscale: str = "linear",
    ylim=None,
    figsize=(6, 5),
    font_size: float = 12.0,
    marker_style: str = "auto",
    marker_size: float = 7.0,
    model_name: str = "4PL Sigmoidal (EC50/IC50)",
    show_ci_band: bool = True,
    show_residuals: bool = False,
    show_equation: bool = True,
    show_r2: bool = True,
    show_params: bool = True,
    gridlines: bool = False,
    grid_style: str = "none",
    ref_line=None,
    ref_line_label: str = "",
    # ── Priority-1 styling params ─────────────────────────────────────────
    axis_style: str = "open",
    tick_dir: str = "out",
    minor_ticks: bool = False,
    point_size: float = 6.0,
    point_alpha: float = 0.80,
    cap_size: float = 4.0,
    ytick_interval: float = 0.0,
    xtick_interval: float = 0.0,
    fig_bg: str = "white",
    spine_width: float = 0.8,
    ref_vline=None,               # optional vertical reference line (x value)
    ref_vline_label: str = "",
):
    """
    Nonlinear curve fitting with a library of built-in models.

    Excel layout — same as scatter/line graph:
      Row 1  : Col 1 = X-axis label (or blank), Cols 2+ = series names
      Rows 2+: Col 1 = numeric X value, Cols 2+ = Y replicates

    Each series is fitted independently. The fitted curve, optional 95% CI
    band, and parameter estimates are annotated on the plot.

    model_name must be one of the keys in CURVE_MODELS.
    """
    _ensure_imports()

    # ── Load data (same layout as scatter) ───────────────────────────────────
    df_raw    = pd.read_excel(excel_path, sheet_name=sheet, header=None)
    row1      = df_raw.iloc[0]
    data_rows = df_raw.iloc[1:].reset_index(drop=True)

    x_vals       = pd.to_numeric(data_rows.iloc[:, 0], errors="coerce").values
    x_axis_label = str(row1.iloc[0]) if pd.notna(row1.iloc[0]) else ""

    series_hdrs   = [str(h) if pd.notna(h) else "" for h in row1.iloc[1:]]
    unique_series = list(dict.fromkeys(h for h in series_hdrs if h))
    series_cols   = {}
    for col_i, h in enumerate(series_hdrs, start=1):
        if h: series_cols.setdefault(h, []).append(col_i)

    colors = _assign_colors(len(unique_series), color)

    if show_residuals:
        fig, (ax_main, ax_res) = plt.subplots(
            2, 1, figsize=(figsize[0], figsize[1] * 1.4),
            gridspec_kw={"height_ratios": [3, 1]}, sharex=True)
    else:
        fig, ax_main = plt.subplots(figsize=figsize, dpi=_DPI)
        ax_res = None

    ax = ax_main
    annot_lines  = []
    fit_failed   = []
    _all_data_xs = []   # for smart annotation placement
    _all_data_ys = []

    for s_idx, s_name in enumerate(unique_series):
        col_idxs = series_cols[s_name]
        c        = colors[s_idx]
        mk = (MARKER_CYCLE[s_idx % len(MARKER_CYCLE)]
              if marker_style == "auto" else marker_style)

        # Flatten all (x, y) pairs for this series
        xs_all, ys_all = [], []
        for row_i, xv in enumerate(x_vals):
            if np.isnan(xv): continue
            ys = pd.to_numeric(
                data_rows.iloc[row_i, col_idxs], errors="coerce").dropna().values
            for yv in ys:
                xs_all.append(xv); ys_all.append(yv)

        if not xs_all:
            continue

        xs_arr = np.array(xs_all, dtype=float)
        ys_arr = np.array(ys_all, dtype=float)

        # Scatter raw data
        _all_data_xs.extend(xs_arr.tolist())
        _all_data_ys.extend(ys_arr.tolist())
        ax.scatter(xs_arr, ys_arr,
                   color=c, marker=mk, s=marker_size**2,
                   edgecolors=_darken_color(c, 0.7), linewidths=0.8,
                   alpha=0.75, zorder=4,
                   label=s_name if len(unique_series) > 1 else None)

        # ── Fit ──────────────────────────────────────────────────────────────
        try:
            result = _fit_model(xs_arr, ys_arr, model_name)
        except Exception as e:
            fit_failed.append(f"{s_name}: {e}")
            continue

        popt    = result["popt"]
        p_names = result["param_names"]
        r2      = result["r2"]
        fn      = CURVE_MODELS[model_name]["fn"]

        # Smooth curve over data range (200 pts, log-spaced if x > 0)
        x_lo, x_hi = xs_arr.min(), xs_arr.max()
        if x_lo > 0 and x_hi / x_lo > 10:
            x_line = np.logspace(np.log10(x_lo), np.log10(x_hi), 300)
        else:
            x_line = np.linspace(x_lo, x_hi, 300)

        y_line = fn(x_line, *popt)
        ax.plot(x_line, y_line, color=c, linewidth=2.0, zorder=5)

        # CI band — skip if pcov is ill-conditioned (any inf/nan in diag)
        # An ill-conditioned covariance means parameter uncertainty is unbounded
        # and the CI band would span the entire axis, hiding the data.
        _pcov_ok = (result["perr"] is not None and
                    np.all(np.isfinite(result["perr"])) and
                    np.all(result["perr"] < 1e6 * (np.abs(result["popt"]) + 1.0)))
        if show_ci_band and len(xs_arr) > len(popt) + 1 and _pcov_ok:
            try:
                lo, hi = _curve_ci_band(x_line, xs_arr, ys_arr, popt, fn)
                # Final sanity check — band must be within 100× the data range
                y_range = float(np.ptp(ys_arr)) or 1.0
                if (np.all(np.isfinite(lo)) and np.all(np.isfinite(hi)) and
                        np.max(hi - lo) < 100 * y_range):
                    ax.fill_between(x_line, lo, hi, color=c, alpha=0.15, zorder=3)
            except Exception:
                pass

        # Residuals
        if ax_res is not None:
            ax_res.scatter(xs_arr, result["residuals"],
                           color=c, marker=mk, s=marker_size**2 * 0.6,
                           edgecolors=_darken_color(c, 0.7), linewidths=0.6,
                           alpha=0.75, zorder=4)
            ax_res.axhline(0, color="black", linewidth=0.8, linestyle="--", alpha=0.4)

        # ── Annotation ───────────────────────────────────────────────────────
        prefix = f"{s_name}:  " if len(unique_series) > 1 else ""

        if show_r2:
            annot_lines.append(f"{prefix}R² = {r2:.4f}")

        if show_params:
            for pname, pval, pe in zip(p_names, popt, result["perr"]):
                if not np.isfinite(pe) or pe > 1e6 * (abs(pval) + 1.0):
                    annot_lines.append(f"  {pname} = {pval:.4g}  (unconstrained)")
                else:
                    annot_lines.append(f"  {pname} = {pval:.4g} ± {pe:.4g}")

        if show_equation:
            # Lazy equation strings — only access popt[n] when len(popt) > n
            eq = None
            if model_name == "4PL Sigmoidal (EC50/IC50)" and len(popt) >= 4:
                eq = (f"Y = {popt[0]:.3g} + ({popt[1]:.3g}\u2212{popt[0]:.3g})"
                      f" / (1+(EC50/X)^{popt[3]:.3g})")
            elif model_name == "3PL Sigmoidal (no bottom)" and len(popt) >= 3:
                eq = f"Y = {popt[0]:.3g} / (1+(EC50/X)^{popt[2]:.3g})"
            elif model_name == "Michaelis-Menten" and len(popt) >= 2:
                eq = f"Y = {popt[0]:.3g}\u00b7X / ({popt[1]:.3g} + X)"
            elif model_name == "Hill equation" and len(popt) >= 3:
                eq = (f"Y = {popt[0]:.3g}\u00b7X^{popt[2]:.3g}"
                      f" / ({popt[1]:.3g}^{popt[2]:.3g} + X^{popt[2]:.3g})")
            elif model_name == "One-phase exponential decay" and len(popt) >= 3:
                eq = (f"Y = {popt[1]:.3g} + {popt[0]-popt[1]:.3g}"
                      f"\u00b7e^(\u2212{popt[2]:.3g}\u00b7X)")
            elif model_name == "One-phase exponential growth" and len(popt) >= 3:
                eq = (f"Y = {popt[0]:.3g} + ({popt[1]:.3g}\u2212{popt[0]:.3g})"
                      f"\u00b7(1\u2212e^(\u2212{popt[2]:.3g}\u00b7X))")
            elif model_name == "Gaussian (bell curve)" and len(popt) >= 3:
                eq = (f"Y = {popt[0]:.3g}\u00b7exp(\u2212(X\u2212{popt[1]:.3g})\u00b2"
                      f"/(2\u00b7{popt[2]:.3g}\u00b2))")
            elif model_name == "Linear" and len(popt) >= 2:
                sign = "+" if popt[1] >= 0 else "\u2212"
                eq = f"Y = {popt[0]:.4g}\u00b7X {sign} {abs(popt[1]):.4g}"
            elif model_name == "Polynomial (2nd order)" and len(popt) >= 3:
                eq = f"Y = {popt[0]:.3g}\u00b7X\u00b2 + {popt[1]:.3g}\u00b7X + {popt[2]:.3g}"
            if eq:
                annot_lines.append(f"  {eq}")

        annot_lines.append("")  # spacer between series

    # Remove trailing blank
    while annot_lines and annot_lines[-1] == "":
        annot_lines.pop()

    # Annotate fit failures
    for msg in fit_failed:
        annot_lines.append(f"⚠ Fit failed — {msg}")

    if annot_lines:
        _ax_frac, _ay_frac, _ha, _va = _best_annotation_corner(
            ax, _all_data_xs, _all_data_ys)
        ax.text(_ax_frac, _ay_frac, "\n".join(annot_lines),
                transform=ax.transAxes,
                ha=_ha, va=_va,
                fontsize=max(font_size - 3, 8),
                fontfamily=_get_font(), color=_COLOR_ANNOT,
                bbox=dict(boxstyle="round,pad=0.5", fc="white",
                          ec="lightgray", alpha=0.92))

    # ── Axis styling ─────────────────────────────────────────────────────────
    _apply_prism_style(ax, font_size, **_style_kwargs(locals()))
    if yscale == "log":
        ax.set_yscale("log")
        _apply_log_formatting(ax)
    if ylim is not None:
        ax.set_ylim(ylim)

    effective_xlabel = xlabel if xlabel else x_axis_label
    if effective_xlabel:
        ax.set_xlabel(effective_xlabel, fontsize=font_size+2,
                      fontfamily=_get_font(), labelpad=_LABEL_PAD, fontweight="bold")
    _set_axis_labels(ax, xlabel, ytitle, title, font_size)

    if len(unique_series) > 1:
        _apply_legend(ax, legend_pos, font_size)

    _apply_grid(ax, grid_style, gridlines)

    if ax_res is not None:
        _apply_prism_style(ax_res, font_size - 2, **_style_kwargs(locals()))
        ax_res.set_ylabel("Residuals", fontsize=font_size,
                          fontfamily=_get_font(), labelpad=6)
        ax_res.set_xlabel(effective_xlabel, fontsize=font_size+2,
                          fontfamily=_get_font(), labelpad=6, fontweight="bold")
        ax.set_xlabel("")

    if ref_line is not None:
        _draw_ref_line(ax, ref_line, font_size)
    if ref_vline is not None:
        _draw_ref_vline(ax, ref_vline, font_size, label=ref_vline_label or None)

    fig.tight_layout(pad=_TIGHT_PAD)
    return fig, ax

# ---------------------------------------------------------------------------
# prism_column_stats  (📋 Column Statistics)
# ---------------------------------------------------------------------------

def prism_column_stats(
    excel_path: str,
    sheet=0,
    color=None,
    title: str = "",
    font_size: float = 12.0,
    figsize=(7, 5),
    show_normality: bool = True,
    show_ci: bool = True,
    show_cv: bool = True,
    ref_line=None,
    ref_line_label: str = "",
    # ── Priority-1 styling params ─────────────────────────────────────────
    axis_style: str = "open",
    tick_dir: str = "out",
    minor_ticks: bool = False,
    point_size: float = 6.0,
    point_alpha: float = 0.80,
    cap_size: float = 4.0,
    ytick_interval: float = 0.0,
    xtick_interval: float = 0.0,
    fig_bg: str = "white",
    spine_width: float = 0.8,
):
    """
    Display a formatted statistics table for each group/column.

    Computes per-column: N, Mean, SD, SEM, 95% CI, Median, Min, Max, CV%,
    and optionally Shapiro-Wilk p-value.

    Same Excel layout as bar chart:
      Row 1  : group names
      Rows 2+: numeric values
    """
    _ensure_imports()

    group_order, groups, bar_colors, fig_tmp, ax_tmp = _base_plot_setup(
        excel_path, sheet, color, None, figsize)
    plt.close(fig_tmp)

    # ── Compute stats ─────────────────────────────────────────────────────────
    rows = []
    for g in group_order:
        v   = groups[g]
        n   = len(v)
        m   = float(np.mean(v))
        sd  = float(np.std(v, ddof=1)) if n > 1 else 0.0
        sem = sd / np.sqrt(n) if n > 0 else 0.0
        med = float(np.median(v))
        mn  = float(v.min())
        mx  = float(v.max())
        cv  = abs(sd / m * 100) if m != 0 else float("nan")

        if n >= 2:
            t_crit = stats.t.ppf(0.975, df=n-1)
            ci_lo  = m - t_crit * sem
            ci_hi  = m + t_crit * sem
        else:
            ci_lo = ci_hi = m

        row = {"Group": g, "N": n,
               "Mean": m, "SD": sd, "SEM": sem,
               "95% CI low": ci_lo, "95% CI high": ci_hi,
               "Median": med, "Min": mn, "Max": mx, "CV%": cv}

        if show_normality and n >= 3:
            sw_stat, sw_p = stats.shapiro(v)
            row["Shapiro-Wilk p"] = sw_p
            row["Normal?"] = "Yes" if sw_p > 0.05 else "No"

        rows.append(row)

    # ── Choose columns ────────────────────────────────────────────────────────
    base_cols  = ["Group", "N", "Mean", "SD", "SEM"]
    if show_ci:
        base_cols += ["95% CI low", "95% CI high"]
    base_cols += ["Median", "Min", "Max"]
    if show_cv:
        base_cols.append("CV%")
    if show_normality:
        base_cols += ["Shapiro-Wilk p", "Normal?"]

    col_data = {c: [r.get(c, "") for r in rows] for c in base_cols}

    # ── Format cell values ────────────────────────────────────────────────────
    def _fmt(val, col):
        if val == "" or (isinstance(val, float) and np.isnan(val)):
            return "—"
        if col in ("N",):
            return str(int(val))
        if col in ("Normal?", "Group"):
            return str(val)
        if col == "Shapiro-Wilk p":
            return f"{val:.4f}"
        if col == "CV%":
            return f"{val:.1f}%"
        return f"{val:.4f}" if abs(val) < 0.001 else f"{val:.4g}"

    cell_text   = [[_fmt(col_data[c][r], c) for c in base_cols]
                   for r in range(len(rows))]
    row_colours = [[bar_colors[ri % len(bar_colors)] + "33"   # light fill
                    for _ in base_cols]
                   for ri in range(len(rows))]

    # ── Draw ──────────────────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=figsize, dpi=_DPI)
    ax.axis("off")

    tbl = ax.table(
        cellText=cell_text,
        colLabels=base_cols,
        cellColours=row_colours,
        cellLoc="center",
        loc="center",
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(font_size - 1)
    tbl.auto_set_column_width(list(range(len(base_cols))))

    # Header row styling
    for ci in range(len(base_cols)):
        cell = tbl[(0, ci)]
        cell.set_facecolor(_COLOR_HDR)
        cell.set_text_props(color="white", fontweight="bold",
                            fontsize=font_size - 1)

    # Colour "No" normality cells orange
    if show_normality and "Normal?" in base_cols:
        norm_ci = base_cols.index("Normal?")
        for ri, row in enumerate(rows):
            if row.get("Normal?") == "No":
                tbl[(ri+1, norm_ci)].set_facecolor(_COLOR_WARN_FILL)

    _set_axis_labels(ax, "", "", title, font_size)
    ax.set_facecolor(fig_bg)
    fig.patch.set_facecolor(fig_bg)

    fig.tight_layout(pad=_TIGHT_PAD)
    return fig, ax


# ---------------------------------------------------------------------------
# prism_contingency  (🔲 Contingency)
# ---------------------------------------------------------------------------

def prism_contingency(
    excel_path: str,
    sheet=0,
    color=None,
    title: str = "",
    xlabel: str = "",
    ytitle: str = "",
    figsize=(7, 5),
    font_size: float = 12.0,
    show_percentages: bool = True,
    show_expected: bool = False,
    bar_width: float = 0.6,
    ref_line=None,
    ref_line_label: str = "",
    # ── Priority-1 styling params ─────────────────────────────────────────
    axis_style: str = "open",
    tick_dir: str = "out",
    minor_ticks: bool = False,
    point_size: float = 6.0,
    point_alpha: float = 0.80,
    cap_size: float = 4.0,
    ytick_interval: float = 0.0,
    xtick_interval: float = 0.0,
    fig_bg: str = "white",
    spine_width: float = 0.8,
):
    """
    Contingency table analysis: chi-square test (or Fisher's exact for 2×2).

    Excel layout:
      Row 1  : column labels (outcomes, e.g. "Survived", "Died")
      Col A  : row labels (groups, e.g. "Drug", "Control")  [from row 2]
      Cells  : counts (integers)

    Example:
      (blank)  | Survived | Died
      Drug     |    45    |  5
      Control  |    20    | 30
    """
    _ensure_imports()

    df_raw   = pd.read_excel(excel_path, sheet_name=sheet, header=None)
    col_lbls = [str(h) if pd.notna(h) else f"Col{i}"
                for i, h in enumerate(df_raw.iloc[0, 1:], 1)]
    row_lbls = [str(df_raw.iloc[r, 0]) if pd.notna(df_raw.iloc[r, 0])
                else f"Row{r}" for r in range(1, df_raw.shape[0])]
    obs = df_raw.iloc[1:, 1:].apply(pd.to_numeric, errors="coerce").fillna(0).values.astype(float)

    n_rows, n_cols = obs.shape
    row_totals = obs.sum(axis=1, keepdims=True)
    col_totals = obs.sum(axis=0, keepdims=True)
    grand_total = obs.sum()
    expected    = row_totals * col_totals / grand_total

    # ── Statistical tests ─────────────────────────────────────────────────────
    stat_lines = []
    if n_rows == 2 and n_cols == 2:
        from scipy.stats import fisher_exact, chi2_contingency
        fe_stat, fe_p = fisher_exact(obs)
        chi2, chi2_p, dof, _ = chi2_contingency(obs)
        try:
            from scipy.stats import odds_ratio as _or_fn
            or_res = _or_fn(obs.astype(int))
            or_val = or_res.statistic
            or_lo, or_hi = or_res.confidence_interval(0.95)
        except ImportError:
            a, b, c, d = obs[0,0], obs[0,1], obs[1,0], obs[1,1]
            denom = b * c
            or_val = (a * d / denom) if denom > 0 else float("nan")
            try:
                import math
                log_or = math.log(or_val)
                se = math.sqrt(1/a + 1/b + 1/c + 1/d)
                or_lo = math.exp(log_or - 1.96 * se)
                or_hi = math.exp(log_or + 1.96 * se)
            except Exception:
                or_lo = or_hi = float("nan")
        try:
            stat_lines.append(f"Odds Ratio = {or_val:.3f}  (95% CI {or_lo:.3f}\u2013{or_hi:.3f})")
        except Exception:
            pass
        stat_lines.append(f"Fisher's exact:  p = {fe_p:.4f}  {'*' if fe_p < 0.05 else 'ns'}")
        stat_lines.append(f"Chi-square = {chi2:.3f},  df = {dof},  p = {chi2_p:.4f}")
    else:
        from scipy.stats import chi2_contingency
        chi2, chi2_p, dof, _ = chi2_contingency(obs)
        stat_lines.append(f"Chi-square = {chi2:.3f},  df = {dof},  p = {chi2_p:.4f}  "
                          f"{'*' if chi2_p < 0.05 else 'ns'}")

    # ── Plot ──────────────────────────────────────────────────────────────────
    colors = _assign_colors(n_cols, color)
    x      = np.arange(n_rows)
    width  = bar_width / n_cols

    fig, ax = plt.subplots(figsize=figsize, dpi=_DPI)

    for ci in range(n_cols):
        offset   = (ci - (n_cols - 1) / 2) * width
        vals     = obs[:, ci]
        c        = colors[ci]
        bars     = ax.bar(x + offset, vals, width=width * 0.92,
                          color=c, edgecolor=_darken_color(c), linewidth=0.8,
                          label=col_lbls[ci], zorder=3)
        if show_percentages:
            for xi, v in zip(x + offset, vals):
                rt = row_totals[int(round(xi - offset))][0]
                pct = v / rt * 100 if rt > 0 else 0
                ax.text(xi, v + grand_total * 0.005,
                        f"{pct:.1f}%", ha="center", va="bottom",
                        fontsize=font_size - 3, color=_COLOR_ANNOT)
        if show_expected:
            for xi, ev in zip(x + offset, expected[:, ci]):
                ax.plot([xi - width*0.4, xi + width*0.4], [ev, ev],
                        color="black", linewidth=1.5, linestyle="--",
                        zorder=5)

    _apply_prism_style(ax, font_size, **_style_kwargs(locals()))
    _rot, _ha = _smart_xrotation(row_lbls)
    ax.set_xticks(x)
    ax.set_xticklabels(row_lbls, fontsize=font_size, fontfamily=_get_font(),
                       rotation=_rot, ha=_ha, fontweight="bold")
    ax.set_ylim(bottom=0)
    ax.set_xlim(-0.6, n_rows - 0.4)

    if xlabel: ax.set_xlabel(xlabel, fontsize=font_size+2, fontfamily=_get_font(),
                              labelpad=_LABEL_PAD, fontweight="bold")
    _set_axis_labels(ax, xlabel, ytitle or "Count", title, font_size)

    ax.legend(frameon=False, fontsize=font_size, loc="upper right")

    # Stats annotation
    ax.text(0.02, 0.98, "\n".join(stat_lines),
            transform=ax.transAxes, ha="left", va="top",
            fontsize=font_size - 2, fontfamily=_get_font(), color=_COLOR_ANNOT,
            bbox=dict(boxstyle="round,pad=0.4", fc="white",
                      ec="lightgray", alpha=0.92))

    if show_expected:
        ax.plot([], [], color="black", linewidth=1.5, linestyle="--",
                label="Expected")
        ax.legend(frameon=False, fontsize=font_size, loc="upper right")

    if ref_line is not None: _draw_ref_line(ax, ref_line, font_size, label=ref_line_label or None)
    fig.tight_layout(pad=_TIGHT_PAD)
    return fig, ax


# ---------------------------------------------------------------------------
# prism_repeated_measures  (🔁 Repeated Measures)
# ---------------------------------------------------------------------------

def prism_repeated_measures(
    excel_path: str,
    sheet=0,
    color=None,
    title: str = "",
    xlabel: str = "",
    ytitle: str = "",
    yscale: str = "linear",
    ylim=None,
    figsize=(6, 5),
    font_size: float = 12.0,
    jitter_amount: float = 0.05,
    error: str = "sem",
    show_subject_lines: bool = True,
    show_stats: bool = False,
    show_p_values: bool = False,
    test_type: str = "parametric",
    ref_line=None,
    ref_line_label: str = "",
    # ── Priority-1 styling params ─────────────────────────────────────────
    axis_style: str = "open",
    tick_dir: str = "out",
    minor_ticks: bool = False,
    point_size: float = 6.0,
    point_alpha: float = 0.80,
    cap_size: float = 4.0,
    ytick_interval: float = 0.0,
    xtick_interval: float = 0.0,
    fig_bg: str = "white",
    spine_width: float = 0.8,
    bracket_style: str = "lines",
    xtick_labels: list = None,
):
    """
    Repeated-measures plot with subject lines + mean±error bars.

    Parametric:    one-way repeated-measures ANOVA (pingouin if available,
                   fallback to pairwise paired t-tests with Holm correction)
    Nonparametric: Friedman test + Dunn's post-hoc

    Excel layout — same as bar chart:
      Row 1  : condition names (columns = time points / conditions)
      Rows 2+: one row per subject

    Example:
      Baseline | Week 2 | Week 4 | Week 8
         2.1   |  2.8   |  3.5   |  4.2     ← subject 1
         1.9   |  2.5   |  3.1   |  3.8     ← subject 2
    """
    _ensure_imports()

    group_order, groups, bar_colors, fig_tmp, _ = _base_plot_setup(
        excel_path, sheet, color, None, figsize)
    plt.close(fig_tmp)

    n_conditions = len(group_order)

    # Align subjects (same row order = same subject)
    max_n = max(len(v) for v in groups.values())
    aligned = {}
    for g in group_order:
        v = groups[g]
        if len(v) < max_n:
            v = np.concatenate([v, np.full(max_n - len(v), np.nan)])
        aligned[g] = v

    fig, ax = plt.subplots(figsize=figsize, dpi=_DPI)
    x_pos = {g: i for i, g in enumerate(group_order)}

    # ── Subject lines ─────────────────────────────────────────────────────────
    if show_subject_lines:
        _draw_subject_lines(ax, group_order, aligned, x_pos)

    # ── Individual dots ───────────────────────────────────────────────────────
    for g_idx, g in enumerate(group_order):
        vals   = groups[g]
        c      = bar_colors[g_idx]
        jitter = (np.random.rand(len(vals)) - 0.5) * jitter_amount
        ax.scatter(g_idx + jitter, vals,
                   color=c, edgecolors=_darken_color(c, 0.7),
                   linewidths=1.0, s=28, alpha=0.8, zorder=4)

        # Mean ± error bar via shared helper
        _draw_mean_errorbar(ax, g_idx, vals, c, error, yscale)

    # ── Statistics ────────────────────────────────────────────────────────────
    if show_stats and n_conditions >= 2:
        stat_header = ""
        sig_results = []

        if test_type == "parametric":
            try:
                import pingouin as pg
                # Build long-format dataframe
                records = []
                for subj_i in range(max_n):
                    for g in group_order:
                        y = aligned[g][subj_i]
                        if not np.isnan(y):
                            records.append({"subject": subj_i,
                                            "condition": g, "value": y})
                df_long = pd.DataFrame(records)
                aov = pg.rm_anova(data=df_long, dv="value",
                                  within="condition", subject="subject")
                F    = float(aov["F"].iloc[0])
                p    = float(aov["p-unc"].iloc[0])
                eps  = float(aov.get("eps", pd.Series([float("nan")])).iloc[0])
                stat_header = (f"RM-ANOVA: F = {F:.3f},  p = {p:.4f}"
                               f"{'  (Greenhouse-Geisser ε={:.3f})'.format(eps) if not np.isnan(eps) else ''}")
                if p < 0.05:
                    posthoc = pg.pairwise_tests(data=df_long, dv="value",
                                                within="condition",
                                                subject="subject",
                                                padjust="holm")
                    for _, row in posthoc.iterrows():
                        p_adj = float(row.get("p-corr", row.get("p-unc", 1.0)))
                        sig_results.append((str(row["A"]), str(row["B"]),
                                            p_adj, _p_to_stars(p_adj)))
            except ImportError:
                # Fallback: pairwise paired t-tests with Holm-Bonferroni
                pairs   = list(itertools.combinations(group_order, 2))
                raw_p   = []
                for a, b in pairs:
                    n = min(len(groups[a]), len(groups[b]))
                    _, p = stats.ttest_rel(groups[a][:n], groups[b][:n])
                    raw_p.append(p)
                corrected = _apply_correction(raw_p, "Holm-Bonferroni")
                for (a, b), cp in zip(pairs, corrected):
                    sig_results.append((a, b, cp, _p_to_stars(cp)))
                stat_header = "Pairwise paired t-tests (Holm-Bonferroni)"

        else:  # nonparametric — Friedman
            mat = np.column_stack([aligned[g] for g in group_order])
            # Remove rows with any NaN
            mat = mat[~np.isnan(mat).any(axis=1)]
            if mat.shape[0] >= 2:
                friedman_stat, friedman_p = stats.friedmanchisquare(*mat.T)
                stat_header = (f"Friedman: χ² = {friedman_stat:.3f},  "
                               f"p = {friedman_p:.4f}")
                if friedman_p < 0.05:
                    # Dunn's post-hoc (manual)
                    pairs   = list(itertools.combinations(group_order, 2))
                    k       = n_conditions
                    n_subj  = mat.shape[0]
                    all_vals = mat.flatten()
                    ranks    = stats.rankdata(all_vals).reshape(mat.shape)
                    col_ranks = ranks.mean(axis=0)
                    raw_p = []
                    for ai, bi in [(group_order.index(a), group_order.index(b))
                                   for a, b in pairs]:
                        z = abs(col_ranks[ai] - col_ranks[bi]) / np.sqrt(
                            k * (k+1) / (6 * n_subj))
                        raw_p.append(2 * (1 - stats.norm.cdf(z)))
                    corrected = _apply_correction(raw_p, "Holm-Bonferroni")
                    for (a, b), cp in zip(pairs, corrected):
                        sig_results.append((a, b, cp, _p_to_stars(cp)))

        if stat_header:
            ax.text(0.02, 0.02, stat_header,
                    transform=ax.transAxes, ha="left", va="bottom",
                    fontsize=font_size - 3, fontfamily=_get_font(), color=_COLOR_ANNOT,
                    bbox=dict(boxstyle="round,pad=0.3", fc="white",
                              ec="lightgray", alpha=0.88))

        sig_results = [r for r in sig_results
                       if r[3] != "ns" or __show_ns__]
        if sig_results:
            _draw_significance_brackets(
                ax, sig_results,
                {g: float(i) for i, g in enumerate(group_order)},
                {g: float(groups[g].max()) for g in group_order},
                show_p_values=show_p_values)

    # ── Axis styling ──────────────────────────────────────────────────────────
    _apply_prism_style(ax, font_size, **_style_kwargs(locals()))
    _set_categorical_xticks(ax, group_order, None, font_size,
                            show_n_labels=False,
                            xtick_labels=xtick_labels)
    ax.set_xlim(-0.6, n_conditions - 0.4)

    _set_axis_labels(ax, xlabel, ytitle, title, font_size)
    if yscale == "log":
        ax.set_yscale("log")
        _apply_log_formatting(ax)
    if ylim is not None: ax.set_ylim(ylim)

    if ref_line is not None: _draw_ref_line(ax, ref_line, font_size, label=ref_line_label or None)
    fig.tight_layout(pad=_TIGHT_PAD)
    return fig, ax


# ---------------------------------------------------------------------------
# Priority 2b — Chi-Square Goodness of Fit
# ---------------------------------------------------------------------------

def prism_chi_square_gof(
    excel_path: str,
    sheet=0,
    color=None,
    title: str = "",
    xlabel: str = "",
    ytitle: str = "",
    figsize=(6, 5),
    font_size: float = 12.0,
    expected_equal: bool = True,
    ref_line=None,
    ref_line_label: str = "",
    # ── Priority-1 styling params ─────────────────────────────────────────
    axis_style: str = "open",
    tick_dir: str = "out",
    minor_ticks: bool = False,
    point_size: float = 6.0,
    point_alpha: float = 0.80,
    cap_size: float = 4.0,
    ytick_interval: float = 0.0,
    xtick_interval: float = 0.0,
    fig_bg: str = "white",
    spine_width: float = 0.8,
):
    """Chi-Square Goodness of Fit test.

    Compares observed counts in each category to expected proportions.

    Excel layout — same as bar chart (Row 1 = category names, Row 2 = observed
    counts, optional Row 3 = expected proportions or counts).  If Row 3 is
    absent (or ``expected_equal=True``), equal expected proportions are assumed.

    Example::

        Category A | Category B | Category C
            30     |     50     |     20        ← observed
            0.333  |    0.333   |    0.333      ← expected proportions (optional)
    """
    _ensure_imports()

    df_raw = pd.read_excel(excel_path, sheet_name=sheet, header=None)
    categories = [str(h) if pd.notna(h) else f"Cat{i+1}"
                  for i, h in enumerate(df_raw.iloc[0])]
    observed = pd.to_numeric(df_raw.iloc[1], errors="coerce").values.astype(float)

    # Expected
    if expected_equal or df_raw.shape[0] < 3:
        expected = np.ones(len(observed)) / len(observed) * observed.sum()
    else:
        raw_exp = pd.to_numeric(df_raw.iloc[2], errors="coerce").values.astype(float)
        # Normalise if proportions (sum ≤ 1.01) else use as counts
        if raw_exp.sum() <= 1.01:
            expected = raw_exp / raw_exp.sum() * observed.sum()
        else:
            expected = raw_exp / raw_exp.sum() * observed.sum()

    from scipy.stats import chisquare
    chi2_stat, p_val = chisquare(observed, f_exp=expected)
    df_ = len(observed) - 1

    colors = _assign_colors(len(categories), color)
    x = np.arange(len(categories))

    fig, ax = plt.subplots(figsize=figsize, dpi=_DPI)

    for i, (cat, obs, exp, c) in enumerate(zip(categories, observed, expected, colors)):
        ax.bar(i, obs, color=c, edgecolor=_darken_color(c), linewidth=0.8,
               alpha=0.85, zorder=3, label=cat)
        ax.bar(i, exp, color="none", edgecolor="black", linewidth=1.5,
               linestyle="--", zorder=4)

    # Stat annotation
    p_str = "p<0.0001" if p_val < 0.0001 else f"p={p_val:.4f}"
    sig = _p_to_stars(p_val)
    annot = (f"χ²={chi2_stat:.3f},  df={df_},  {p_str}  {sig}\n"
             "Dashed bars = expected")
    ax.text(0.02, 0.98, annot, transform=ax.transAxes,
            ha="left", va="top", fontsize=font_size - 2,
            fontfamily=_get_font(), color=_COLOR_ANNOT,
            bbox=dict(boxstyle="round,pad=0.4", fc="white", ec="lightgray", alpha=0.92))

    _sk = _style_kwargs(locals())
    _apply_prism_style(ax, font_size, **_sk)
    ax.set_xticks(x)
    _rot, _ha = _smart_xrotation(categories)
    ax.set_xticklabels(categories, fontsize=font_size, fontfamily=_get_font(),
                       rotation=_rot, ha=_ha, fontweight="bold")
    ax.set_xlim(-0.6, len(categories) - 0.4)
    ax.set_ylim(bottom=0)
    _set_axis_labels(ax, xlabel, ytitle or "Count", title, font_size)

    _base_plot_finish(ax, fig, title, xlabel, ytitle or "Count", "linear", None,
                      font_size, ref_line, ref_line_label=ref_line_label, **_sk)
    return fig, ax


# ---------------------------------------------------------------------------
# Priority 2c — Full Linear Regression Table helper (used by prism_scatterplot)
# ---------------------------------------------------------------------------

def _draw_regression_table(ax, fig, xs_arr, ys_arr, font_size, color):
    """Draw a Prism-style full linear regression statistics table on the axes.

    Displayed metrics:
      • Slope ± SE, 95% CI of slope
      • Intercept ± SE
      • F-statistic, df, p-value
      • R, R², adjusted R²
      • Runs test for deviation from linearity (p-value)
    """
    from scipy import stats as _st

    n = len(xs_arr)
    if n < 3:
        return

    slope, intercept, r_val, p_val, se_slope = _st.linregress(xs_arr, ys_arr)
    df_ = n - 2
    t_crit = _st.t.ppf(0.975, df=df_)
    ci_slope_lo = slope - t_crit * se_slope
    ci_slope_hi = slope + t_crit * se_slope

    y_hat  = slope * xs_arr + intercept
    ss_res = np.sum((ys_arr - y_hat) ** 2)
    ss_tot = np.sum((ys_arr - ys_arr.mean()) ** 2)
    r2     = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    r2_adj = 1 - (1 - r2) * (n - 1) / df_ if df_ > 0 else float("nan")
    mse    = ss_res / df_ if df_ > 0 else float("nan")
    ss_reg = ss_tot - ss_res
    f_stat = (ss_reg / mse) if mse > 0 else float("nan")

    # SE of intercept
    x_mean   = xs_arr.mean()
    ss_xx    = np.sum((xs_arr - x_mean) ** 2)
    se_int   = np.sqrt(mse * (1/n + x_mean**2 / ss_xx)) if ss_xx > 0 else float("nan")

    # Runs test for linearity
    residuals = ys_arr - y_hat
    signs     = np.sign(residuals)
    runs = 1 + np.sum(signs[1:] != signs[:-1])
    n_pos = np.sum(signs > 0); n_neg = np.sum(signs < 0)
    if n_pos > 0 and n_neg > 0:
        mu_runs = 2 * n_pos * n_neg / n + 1
        var_runs = (mu_runs - 1) * (mu_runs - 2) / (n - 1)
        z_runs   = (runs - mu_runs) / np.sqrt(var_runs) if var_runs > 0 else 0
        p_runs   = float(2 * (1 - _st.norm.cdf(abs(z_runs))))
    else:
        p_runs = float("nan")

    def _fmt_p(p):
        return "p<0.0001" if p < 0.0001 else f"p={p:.4f}"

    lines = [
        f"Slope = {slope:.4g} ± {se_slope:.4g}",
        f"  95% CI: [{ci_slope_lo:.4g}, {ci_slope_hi:.4g}]",
        f"Intercept = {intercept:.4g} ± {se_int:.4g}",
        f"F({1}, {df_}) = {f_stat:.3f},  {_fmt_p(p_val)}",
        f"R = {r_val:.4f},  R² = {r2:.4f},  R²adj = {r2_adj:.4f}",
        f"Runs test: {_fmt_p(p_runs)}" if not np.isnan(p_runs) else "Runs test: n/a",
    ]

    xf, yf, ha, va = _best_annotation_corner(ax, xs_arr.tolist(), ys_arr.tolist())
    ax.text(xf, yf, "\n".join(lines),
            transform=ax.transAxes, ha=ha, va=va,
            fontsize=max(font_size - 3, 7),
            fontfamily=_get_font(),
            color=_COLOR_ANNOT,
            bbox=dict(boxstyle="round,pad=0.4", fc="white", ec="lightgray", alpha=0.92))


# ===========================================================================
# Priority 3a — Stacked Bar Chart
# ===========================================================================

def prism_stacked_bar(
    excel_path: str,
    sheet=0,
    color=None,
    title: str = "",
    xlabel: str = "",
    ytitle: str = "",
    yscale: str = "linear",
    ylim=None,
    figsize=(6, 5),
    font_size: float = 12.0,
    bar_width: float = 0.6,
    alpha: float = 0.85,
    mode: str = "absolute",
    show_n_labels: bool = False,
    gridlines: bool = False,
    grid_style: str = "none",
    ref_line=None,
    ref_line_label: str = "",
    axis_style: str = "open",
    tick_dir: str = "out",
    minor_ticks: bool = False,
    point_size: float = 6.0,
    point_alpha: float = 0.80,
    cap_size: float = 4.0,
    ytick_interval: float = 0.0,
    xtick_interval: float = 0.0,
    fig_bg: str = "white",
    spine_width: float = 0.8,
    legend_pos: str = "upper right",
    show_value_labels: bool = False,
    horizontal: bool = False,
    xtick_labels: list = None,
):
    """Stacked bar chart — Prism equivalent: Grouped Data → Stacked bar.

    Excel layout — same as grouped bar:
      Row 1 : category names (repeated across sub-group columns)
      Row 2 : sub-group / series names
      Rows 3+: replicate values

    ``mode="absolute"``  — bars show raw sums stacked.
    ``mode="percent"``   — each bar sums to 100% (normalised stacks).
    ``horizontal=True``  — draw horizontal stacked bars (P17).
    ``xtick_labels``     — override category labels (P18).
    """
    _ensure_imports()
    _sk = _style_kwargs(locals())

    df_raw = pd.read_excel(excel_path, sheet_name=sheet, header=None)
    row1 = [str(h) if pd.notna(h) else "" for h in df_raw.iloc[0]]
    row2 = [str(h) if pd.notna(h) else "" for h in df_raw.iloc[1]]
    data = df_raw.iloc[2:].reset_index(drop=True)

    categories = list(dict.fromkeys(c for c in row1 if c))
    subgroups  = list(dict.fromkeys(s for s in row2 if s))
    col_map = {}
    for ci in range(df_raw.shape[1]):
        cat, sub = row1[ci], row2[ci]
        if cat and sub:
            col_map.setdefault((cat, sub), []).append(ci)

    def _mean(cat, sub):
        idxs = col_map.get((cat, sub), [])
        if not idxs:
            return 0.0
        vals = pd.to_numeric(data.iloc[:, idxs].values.flatten(), errors="coerce")
        return float(np.nanmean(vals))

    # Build matrix: rows=categories, cols=subgroups
    matrix = np.array([[_mean(cat, sub) for sub in subgroups]
                        for cat in categories])  # shape (n_cats, n_subs)

    if mode == "percent":
        row_sums = matrix.sum(axis=1, keepdims=True)
        row_sums[row_sums == 0] = 1
        matrix = matrix / row_sums * 100

    colors = _assign_colors(len(subgroups), color)
    x = np.arange(len(categories))

    # Override category display labels if xtick_labels provided
    cat_display = (list(xtick_labels) if xtick_labels and len(xtick_labels) == len(categories)
                   else categories)

    fig, ax = plt.subplots(figsize=figsize, dpi=_DPI)

    bottoms = np.zeros(len(categories))
    for si, (sub, c) in enumerate(zip(subgroups, colors)):
        vals = matrix[:, si]
        if horizontal:
            ax.barh(x, vals, left=bottoms, height=bar_width,
                    color=c, edgecolor=_darken_color(c), linewidth=0.8,
                    alpha=alpha, label=sub, zorder=3)
            if show_value_labels:
                for xi, v, bot in zip(x, vals, bottoms):
                    if v <= 0:
                        continue
                    y_range = matrix.sum(axis=1).max() or 1
                    if v / y_range > 0.06:
                        ax.text(bot + v / 2, xi, _fmt_bar_label(float(v)),
                                ha="center", va="center",
                                fontsize=font_size * 0.78, fontfamily=_get_font(),
                                color="white", fontweight="bold", zorder=8)
        else:
            ax.bar(x, vals, bottom=bottoms, width=bar_width,
                   color=c, edgecolor=_darken_color(c), linewidth=0.8,
                   alpha=alpha, label=sub, zorder=3)
            # Value labels at the centre of each segment
            if show_value_labels:
                for xi, v, bot in zip(x, vals, bottoms):
                    if v <= 0:
                        continue
                    label_txt = _fmt_bar_label(float(v))
                    if label_txt:
                        mid_y = bot + v / 2
                        # Only draw if segment tall enough to fit text
                        y_range = matrix.sum(axis=1).max() or 1
                        if v / y_range > 0.06:
                            ax.text(xi, mid_y, label_txt,
                                    ha="center", va="center",
                                    fontsize=font_size * 0.78,
                                    fontfamily=_get_font(),
                                    color="white", fontweight="bold",
                                    zorder=8)
        bottoms += vals

    _apply_prism_style(ax, font_size, **_sk)

    if horizontal:
        ax.set_yticks(x)
        _rot, _ha = _smart_xrotation(cat_display)
        ax.set_yticklabels(cat_display, fontsize=font_size, fontfamily=_get_font(),
                           fontweight="bold")
        ax.set_ylim(-0.6, len(categories) - 0.4)
        ax.set_xlim(left=0)
        if ylim:
            ax.set_xlim(ylim)
        if mode == "percent":
            ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.0f}%"))
        default_ytitle = xlabel or ""
        default_xlabel = ytitle or ("Percentage (%)" if mode == "percent" else "")
        _set_axis_labels(ax, default_xlabel, default_ytitle, title, font_size)
    else:
        _rot, _ha = _smart_xrotation(cat_display)
        ax.set_xticks(x)
        ax.set_xticklabels(cat_display, fontsize=font_size, fontfamily=_get_font(),
                           rotation=_rot, ha=_ha, fontweight="bold")
        ax.set_xlim(-0.6, len(categories) - 0.4)
        ax.set_ylim(bottom=0)
        if ylim:
            ax.set_ylim(ylim)
        if mode == "percent":
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.0f}%"))
        default_ytitle = ytitle or ("Percentage (%)" if mode == "percent" else "")
        _set_axis_labels(ax, xlabel, default_ytitle, title, font_size)

    _apply_legend(ax, legend_pos, font_size)
    _apply_grid(ax, grid_style, gridlines)

    _base_plot_finish(ax, fig, title, xlabel,
                      ytitle or ("Percentage (%)" if mode == "percent" else ""),
                      yscale, ylim, font_size, ref_line,
                      ref_line_label=ref_line_label, **_sk)
    return fig, ax


# ===========================================================================
# Priority 3b — Bubble Chart
# ===========================================================================

def prism_bubble(
    excel_path: str,
    sheet=0,
    color=None,
    title: str = "",
    xlabel: str = "",
    ytitle: str = "",
    yscale: str = "linear",
    ylim=None,
    figsize=(6, 5),
    font_size: float = 12.0,
    bubble_scale: float = 1.0,
    show_labels: bool = False,
    gridlines: bool = False,
    grid_style: str = "none",
    ref_line=None,
    ref_line_label: str = "",
    axis_style: str = "open",
    tick_dir: str = "out",
    minor_ticks: bool = False,
    point_size: float = 6.0,
    point_alpha: float = 0.70,
    cap_size: float = 4.0,
    ytick_interval: float = 0.0,
    xtick_interval: float = 0.0,
    fig_bg: str = "white",
    spine_width: float = 0.8,
    legend_pos: str = "best",
):
    """Bubble chart — Prism equivalent: XY → Bubble plot.

    Excel layout:
      Row 1 : X-axis label | Series name(s)
      Rows 2+: X | Y | Size  (repeat X/Y/Size triple for each series)

    ``bubble_scale`` multiplies the area of every bubble (default 1.0).
    ``show_labels``  annotates each bubble with its size value.
    """
    _ensure_imports()
    _sk = _style_kwargs(locals())

    df_raw    = pd.read_excel(excel_path, sheet_name=sheet, header=None)
    row1      = df_raw.iloc[0]
    data_rows = df_raw.iloc[1:].reset_index(drop=True)

    x_axis_label = str(row1.iloc[0]) if pd.notna(row1.iloc[0]) else ""

    # Parse series: every 3 columns = (X, Y, Size) for one series
    n_cols = df_raw.shape[1]
    series_list = []
    ci = 1
    while ci + 1 < n_cols:
        s_name = str(row1.iloc[ci]) if pd.notna(row1.iloc[ci]) else f"Series {len(series_list)+1}"
        xs   = pd.to_numeric(data_rows.iloc[:, ci],   errors="coerce").dropna().values
        ys   = pd.to_numeric(data_rows.iloc[:, ci+1], errors="coerce").dropna().values
        szs  = (pd.to_numeric(data_rows.iloc[:, ci+2], errors="coerce").dropna().values
                if ci + 2 < n_cols else np.ones(len(xs)))
        n = min(len(xs), len(ys), len(szs))
        if n:
            series_list.append((s_name, xs[:n], ys[:n], szs[:n]))
        ci += 3

    # Fallback: if only X/Y columns (no size), treat as uniform size
    if not series_list and n_cols >= 2:
        xs  = pd.to_numeric(data_rows.iloc[:, 0], errors="coerce").dropna().values
        ys  = pd.to_numeric(data_rows.iloc[:, 1], errors="coerce").dropna().values
        n   = min(len(xs), len(ys))
        series_list = [("Data", xs[:n], ys[:n], np.ones(n))]

    colors = _assign_colors(len(series_list), color)
    fig, ax = plt.subplots(figsize=figsize, dpi=_DPI)

    for (s_name, xs, ys, szs), c in zip(series_list, colors):
        # Normalise sizes: median maps to 200 pt²; scale by bubble_scale
        median_s = np.median(szs) if len(szs) else 1
        s_norm   = szs / max(median_s, 1e-9) * 200 * bubble_scale
        ax.scatter(xs, ys, s=s_norm, color=c, edgecolors=_darken_color(c),
                   linewidths=0.8, alpha=point_alpha, zorder=4,
                   label=s_name if len(series_list) > 1 else None)
        if show_labels:
            for x_, y_, sz_ in zip(xs, ys, szs):
                ax.annotate(f"{sz_:g}", (x_, y_),
                            ha="center", va="center",
                            fontsize=max(font_size - 4, 7),
                            fontfamily=_get_font(), color="white", fontweight="bold")

    _apply_prism_style(ax, font_size, **_sk)
    if len(series_list) > 1:
        _apply_legend(ax, legend_pos, font_size)

    effective_xlabel = xlabel or x_axis_label
    _set_axis_labels(ax, effective_xlabel, ytitle, title, font_size)

    _apply_grid(ax, grid_style, gridlines)

    if yscale == "log": ax.set_yscale("log")
    if ylim: ax.set_ylim(ylim)

    _base_plot_finish(ax, fig, title, xlabel, ytitle, yscale, ylim,
                      font_size, ref_line, ref_line_label=ref_line_label, **_sk)
    return fig, ax


# ===========================================================================
# Priority 3c — Dot Plot (Strip / Cleveland)
# ===========================================================================

def prism_dot_plot(
    excel_path: str,
    sheet=0,
    color=None,
    title: str = "",
    xlabel: str = "",
    ytitle: str = "",
    yscale: str = "linear",
    ylim=None,
    figsize=(5, 5),
    font_size: float = 12.0,
    jitter_amount: float = 0.15,
    show_mean: bool = True,
    show_median: bool = False,
    show_n_labels: bool = True,
    open_points: bool = False,
    gridlines: bool = False,
    grid_style: str = "none",
    ref_line=None,
    ref_line_label: str = "",
    axis_style: str = "open",
    tick_dir: str = "out",
    minor_ticks: bool = False,
    point_size: float = 7.0,
    point_alpha: float = 0.80,
    cap_size: float = 4.0,
    ytick_interval: float = 0.0,
    xtick_interval: float = 0.0,
    fig_bg: str = "white",
    spine_width: float = 0.8,
    bracket_style: str = "lines",
    xtick_labels: list = None,
):
    """Dot plot (strip chart / Cleveland dot plot).

    Like subcolumn_scatter but no bar/box fill — just jittered points with an
    optional mean or median line overlay.  Prism equivalent: Column → Dot plot.

    Same Excel layout as bar chart:
      Row 1 : group names
      Rows 2+: numeric values
    """
    _ensure_imports()
    _sk = _style_kwargs(locals())

    group_order, groups, colors, fig, ax = _base_plot_setup(
        excel_path, sheet, color, None, figsize)

    for g_idx, g in enumerate(group_order):
        vals = groups[g]
        c    = colors[g_idx]

        jitter = (np.random.rand(len(vals)) - 0.5) * jitter_amount
        fc = "none" if open_points else c
        ax.scatter(g_idx + jitter, vals,
                   color=fc, edgecolors=_darken_color(c, 0.75),
                   linewidths=1.2, s=point_size**2, alpha=point_alpha, zorder=4)

        if show_mean:
            m = float(np.mean(vals))
            ax.plot([g_idx - 0.22, g_idx + 0.22], [m, m],
                    color=_darken_color(c, 0.55), linewidth=2.5, zorder=5)

        if show_median:
            med = float(np.median(vals))
            ax.plot([g_idx - 0.22, g_idx + 0.22], [med, med],
                    color=_darken_color(c, 0.4), linewidth=1.8,
                    linestyle="--", zorder=5)

    _apply_prism_style(ax, font_size, **_sk)
    _set_categorical_xticks(ax, group_order, groups, font_size,
                            show_n_labels=show_n_labels,
                            xtick_labels=xtick_labels)
    ax.set_xlabel("")
    ax.set_xlim(-0.6, len(group_order) - 0.4)

    if ylim:
        ax.set_ylim(ylim)
    elif yscale != "log":
        pass  # auto

    _apply_grid(ax, grid_style, gridlines)

    _base_plot_finish(ax, fig, title, xlabel, ytitle, yscale, ylim,
                      font_size, ref_line, ref_line_label=ref_line_label, **_sk)
    return fig, ax


# ===========================================================================
# Priority 3d — Bland-Altman Plot
# ===========================================================================

def prism_bland_altman(
    excel_path: str,
    sheet=0,
    color=None,
    title: str = "",
    xlabel: str = "",
    ytitle: str = "",
    figsize=(6, 5),
    font_size: float = 12.0,
    show_ci: bool = True,
    gridlines: bool = False,
    grid_style: str = "none",
    ref_line=None,
    ref_line_label: str = "",
    axis_style: str = "open",
    tick_dir: str = "out",
    minor_ticks: bool = False,
    point_size: float = 6.0,
    point_alpha: float = 0.80,
    cap_size: float = 4.0,
    ytick_interval: float = 0.0,
    xtick_interval: float = 0.0,
    fig_bg: str = "white",
    spine_width: float = 0.8,
):
    """Bland-Altman agreement plot.  Prism equivalent: Analyze → Agreement.

    X-axis : mean of two measurements
    Y-axis : difference (Method A − Method B)
    Lines  : mean difference ± 1.96 SD (limits of agreement)
    Optional 95% CI bands around the LoA (shown when ``show_ci=True``).

    Excel layout:
      Row 1  : method names (e.g. "Method A", "Method B")
      Rows 2+: paired values, one row per subject
    """
    _ensure_imports()
    _sk = _style_kwargs(locals())

    group_order, groups, colors, fig_tmp, _ = _base_plot_setup(
        excel_path, sheet, color, None, figsize)
    plt.close(fig_tmp)

    if len(group_order) < 2:
        raise ValueError("Bland-Altman requires exactly 2 columns (Method A, Method B).")

    a_vals = groups[group_order[0]]
    b_vals = groups[group_order[1]]
    n = min(len(a_vals), len(b_vals))
    a_vals, b_vals = a_vals[:n], b_vals[:n]

    means = (a_vals + b_vals) / 2
    diffs = a_vals - b_vals

    mean_diff = float(np.mean(diffs))
    sd_diff   = float(np.std(diffs, ddof=1))
    loa_lo    = mean_diff - 1.96 * sd_diff
    loa_hi    = mean_diff + 1.96 * sd_diff

    fig, ax = plt.subplots(figsize=figsize, dpi=_DPI)

    c = colors[0] if colors else PRISM_PALETTE[0]
    ax.scatter(means, diffs, color=c, edgecolors=_darken_color(c),
               linewidths=0.8, s=point_size**2, alpha=point_alpha, zorder=4)

    x_lo, x_hi = float(means.min()), float(means.max())
    x_pad = (x_hi - x_lo) * 0.06
    x_range = [x_lo - x_pad, x_hi + x_pad]

    # Mean difference line
    ax.axhline(mean_diff, color="#2274A5", linewidth=1.5, zorder=3)
    ax.text(x_range[1], mean_diff, f" Mean: {mean_diff:.3f}",
            va="center", ha="left", fontsize=font_size - 2,
            fontfamily=_get_font(), color="#2274A5")

    # Limits of agreement
    for loa, lbl in ((loa_lo, f"−1.96 SD: {loa_lo:.3f}"),
                     (loa_hi, f"+1.96 SD: {loa_hi:.3f}")):
        ax.axhline(loa, color="#E8453C", linewidth=1.2,
                   linestyle="--", zorder=3)
        ax.text(x_range[1], loa, f" {lbl}",
                va="center", ha="left", fontsize=font_size - 2,
                fontfamily=_get_font(), color="#E8453C")

    # 95% CI bands around mean diff and LoA
    if show_ci and n >= 3:
        se = sd_diff / np.sqrt(n)
        from scipy.stats import t as _t
        t_crit = _t.ppf(0.975, df=n - 1)
        se_loa = np.sqrt(3 * sd_diff**2 / n)
        for centre, se_ in ((mean_diff, se), (loa_lo, se_loa), (loa_hi, se_loa)):
            ax.axhspan(centre - t_crit * se_, centre + t_crit * se_,
                       color="#aaaaaa", alpha=0.12, zorder=2)

    ax.axhline(0, color="black", linewidth=0.6, linestyle=":", zorder=2)

    _apply_prism_style(ax, font_size, **_sk)
    ax.set_xlim(x_range)

    eff_xlabel = xlabel or f"Mean of {group_order[0]} & {group_order[1]}"
    eff_ytitle = ytitle or f"{group_order[0]} − {group_order[1]}"
    _set_axis_labels(ax, eff_xlabel, eff_ytitle, title, font_size)

    _apply_grid(ax, grid_style, gridlines)

    _base_plot_finish(ax, fig, title, eff_xlabel, eff_ytitle, "linear", None,
                      font_size, ref_line, ref_line_label=ref_line_label, **_sk)
    return fig, ax


# ===========================================================================
# Priority 3e — Forest Plot
# ===========================================================================

def prism_forest_plot(
    excel_path: str,
    sheet=0,
    color=None,
    title: str = "",
    xlabel: str = "",
    ytitle: str = "",
    figsize=(7, 5),
    font_size: float = 11.0,
    ref_value: float = 0.0,
    show_weights: bool = True,
    show_summary: bool = True,
    gridlines: bool = False,
    grid_style: str = "none",
    ref_line=None,
    ref_line_label: str = "",
    axis_style: str = "open",
    tick_dir: str = "out",
    minor_ticks: bool = False,
    point_size: float = 6.0,
    point_alpha: float = 0.90,
    cap_size: float = 4.0,
    ytick_interval: float = 0.0,
    xtick_interval: float = 0.0,
    fig_bg: str = "white",
    spine_width: float = 0.8,
):
    """Forest plot for meta-analysis or multi-study comparisons.

    Prism equivalent: File → New table → Forest.

    Excel layout:
      Row 1 : Study | Effect | CI_lo | CI_hi | Weight   (header row)
      Rows 2+: one row per study / subgroup

    Columns:
      • Study   — study label (text)
      • Effect  — point estimate (e.g. OR, RR, MD)
      • CI_lo   — lower bound of 95% CI
      • CI_hi   — upper bound of 95% CI
      • Weight  — optional relative weight (used for diamond size and summary)

    ``ref_value``    — vertical reference line (0 for MD, 1 for OR/RR).
    ``show_summary`` — draw pooled-effect diamond (inverse-variance weighted mean).
    """
    _ensure_imports()
    _sk = _style_kwargs(locals())

    df = pd.read_excel(excel_path, sheet_name=sheet, header=0)

    # Normalise column names case-insensitively
    col_map_ci = {c.lower().strip(): c for c in df.columns}

    def _col(name, fallback_idx=None):
        for candidate in (name, name.lower(), name.upper(), name.title()):
            if candidate in df.columns:
                return df[candidate]
        # try case-insensitive
        if name.lower() in col_map_ci:
            return df[col_map_ci[name.lower()]]
        if fallback_idx is not None and df.shape[1] > fallback_idx:
            return df.iloc[:, fallback_idx]
        return None

    labels  = _col("Study",  0)
    effects = pd.to_numeric(_col("Effect", 1), errors="coerce")
    ci_lo   = pd.to_numeric(_col("CI_lo",  2), errors="coerce")
    ci_hi   = pd.to_numeric(_col("CI_hi",  3), errors="coerce")
    weights_raw = _col("Weight", 4)
    weights = (pd.to_numeric(weights_raw, errors="coerce")
               if weights_raw is not None else None)

    # Drop rows with missing effect/CI
    mask = effects.notna() & ci_lo.notna() & ci_hi.notna()
    labels  = [str(l) for l in (labels[mask].values if labels is not None
                                 else [f"Study {i+1}" for i in range(mask.sum())])]
    effects = effects[mask].values
    ci_lo   = ci_lo[mask].values
    ci_hi   = ci_hi[mask].values
    weights_arr = (weights[mask].values if weights is not None else
                   np.ones(len(effects)))
    weights_arr = np.where(np.isnan(weights_arr), 1.0, weights_arr)

    n = len(effects)
    if n == 0:
        raise ValueError("No valid rows found (need Effect, CI_lo, CI_hi columns).")

    # Inverse-variance summary (weights as 1/SE² approximation)
    w_norm = weights_arr / weights_arr.sum()
    summary_effect = float(np.sum(w_norm * effects))
    # Weighted SE for summary
    ses = (ci_hi - ci_lo) / (2 * 1.96)
    var_pool = 1.0 / np.sum(1.0 / np.maximum(ses**2, 1e-12))
    summary_se = float(np.sqrt(var_pool))
    summary_lo = summary_effect - 1.96 * summary_se
    summary_hi = summary_effect + 1.96 * summary_se

    colors_list = _assign_colors(n, color)
    fig, ax = plt.subplots(figsize=figsize, dpi=_DPI)

    # Y positions: studies top→bottom, summary below a gap
    y_positions = list(range(n - 1, -1, -1))   # n-1 down to 0

    # Marker size proportional to weight (capped)
    ms_arr = 20 + 180 * (weights_arr / weights_arr.max())

    for i, (y, eff, lo, hi, lbl, ms, c) in enumerate(
            zip(y_positions, effects, ci_lo, ci_hi, labels, ms_arr, colors_list)):
        # CI line
        ax.plot([lo, hi], [y, y], color=c, linewidth=1.5, zorder=3)
        # Cap ticks
        ax.plot([lo, lo], [y - 0.15, y + 0.15], color=c, linewidth=1.5, zorder=4)
        ax.plot([hi, hi], [y - 0.15, y + 0.15], color=c, linewidth=1.5, zorder=4)
        # Effect point
        ax.scatter([eff], [y], s=ms,
                   color=c, edgecolors=_darken_color(c),
                   linewidths=0.8, alpha=point_alpha, zorder=5)
        # Study label (left)
        ax.text(-0.02, y, lbl, transform=ax.get_yaxis_transform(),
                ha="right", va="center",
                fontsize=font_size - 1, fontfamily=_get_font())
        # Weight label (right)
        if show_weights:
            ax.text(1.02, y, f"{weights_arr[i]:.1f}",
                    transform=ax.get_yaxis_transform(),
                    ha="left", va="center",
                    fontsize=font_size - 2, fontfamily=_get_font(),
                    color=_COLOR_ANNO_SUBTLE)

    # Summary diamond
    if show_summary:
        y_sum = -1.8
        diamond_x = [summary_lo, summary_effect, summary_hi, summary_effect]
        diamond_y = [y_sum, y_sum + 0.35, y_sum, y_sum - 0.35]
        ax.fill(diamond_x, diamond_y, color="#2274A5", zorder=5, alpha=0.85)
        ax.text(-0.02, y_sum, "Summary", transform=ax.get_yaxis_transform(),
                ha="right", va="center",
                fontsize=font_size - 1, fontfamily=_get_font(), fontweight="bold")
        ax.text(summary_effect, y_sum - 0.6,
                f"{summary_effect:.3f} [{summary_lo:.3f}, {summary_hi:.3f}]",
                ha="center", va="top",
                fontsize=font_size - 2, fontfamily=_get_font(), color="#2274A5")

    # Reference line
    ax.axvline(ref_value, color="black", linewidth=0.8, linestyle="--", zorder=2)

    # Y-axis: no ticks, no labels (labels drawn as text)
    ax.set_yticks([])
    y_bottom = (-2.5 if show_summary else -0.8)
    ax.set_ylim(y_bottom, n - 0.5)

    _apply_prism_style(ax, font_size, **_sk)
    ax.spines["left"].set_visible(False)

    eff_xlabel = xlabel or "Effect size"
    _set_axis_labels(ax, eff_xlabel, "", title, font_size)

    _apply_grid(ax, grid_style, gridlines)

    fig.tight_layout(pad=_TIGHT_PAD)
    return fig, ax


# ===========================================================================
# P20 — Export all chart types as a multi-page PDF showcase
# ===========================================================================


# ===========================================================================
# NEW CHART TYPES  (Session 14 — Prism-parity expansion)
# ===========================================================================

# ---------------------------------------------------------------------------
# prism_area_chart  — Area fill under line chart
# ---------------------------------------------------------------------------

def prism_area_chart(
    excel_path: str,
    sheet=0,
    error: str = "sem",
    color=None,
    title: str = "",
    xlabel: str = "",
    ytitle: str = "",
    yscale: str = "linear",
    ylim=None,
    figsize=(5, 5),
    font_size: float = 12.0,
    line_width: float = 1.5,
    marker_style: str = "o",
    marker_size: float = 7.0,
    alpha: float = 0.30,
    fill_alpha: float = 0.25,
    stacked: bool = False,
    gridlines: bool = False,
    grid_style: str = "none",
    show_points: bool = True,
    ref_line=None,
    ref_line_label: str = "",
    legend_pos: str = "best",
    axis_style: str = "open",
    tick_dir: str = "out",
    minor_ticks: bool = False,
    point_size: float = 6.0,
    point_alpha: float = 0.80,
    cap_size: float = 4.0,
    ytick_interval: float = 0.0,
    xtick_interval: float = 0.0,
    fig_bg: str = "white",
    spine_width: float = 0.8,
):
    """Area chart — filled region under line series, matching Prism's XY area style.

    Expected Excel layout (same as Line Graph):
      Row 1  : Col 1 = X-axis label, Cols 2+ = series names
      Rows 2+: Col 1 = X value, Cols 2+ = Y replicates

    Parameters
    ----------
    alpha      : line + marker opacity
    fill_alpha : area fill opacity (0 = no fill, 1 = fully opaque)
    stacked    : if True, stack series (each series adds on top of the previous)
    """
    _ensure_imports()
    _sk = _style_kwargs(locals())
    df_raw   = pd.read_excel(excel_path, sheet_name=sheet, header=None)
    row1     = df_raw.iloc[0]
    x_label  = str(row1.iloc[0]) if pd.notna(row1.iloc[0]) else "X"
    headers  = [str(h) for h in row1.iloc[1:] if pd.notna(h) and str(h).strip()]
    unique_s = list(dict.fromkeys(headers))
    colors   = _assign_colors(len(unique_s), color)

    data_rows = df_raw.iloc[1:].reset_index(drop=True)
    x_vals    = pd.to_numeric(data_rows.iloc[:, 0], errors="coerce").values

    series_data = {}
    for s_name in unique_s:
        col_idxs = [j for j, h in enumerate(headers) if h == s_name]
        means, xs = [], []
        for row_i, xv in enumerate(x_vals):
            if np.isnan(xv): continue
            vals = pd.to_numeric(data_rows.iloc[row_i, [c + 1 for c in col_idxs]],
                                  errors="coerce").dropna().values
            if len(vals) == 0: continue
            means.append(float(np.mean(vals))); xs.append(xv)
        series_data[s_name] = (np.array(xs), np.array(means))

    fig, ax = plt.subplots(figsize=figsize, dpi=_DPI)

    baseline = np.zeros_like(list(series_data.values())[0][1]) if unique_s else np.array([])
    for s_idx, (s_name, (xs, means)) in enumerate(series_data.items()):
        c = colors[s_idx % len(colors)]
        if stacked:
            if len(baseline) != len(means):
                baseline = np.zeros(len(means))
            top = baseline + means
        else:
            top = means
        ax.fill_between(xs, baseline if stacked else 0, top,
                        alpha=fill_alpha, color=c, zorder=2)
        ax.plot(xs, top, color=c, linewidth=line_width, alpha=alpha,
                zorder=3, label=s_name, solid_capstyle="round")
        if show_points:
            mk = MARKER_CYCLE[s_idx % len(MARKER_CYCLE)] if marker_style == "auto" else marker_style
            ax.scatter(xs, top, color=c, s=point_size**2,
                       marker=mk, zorder=4, alpha=point_alpha,
                       edgecolors=_darken_color(c, 0.7), linewidths=0.8)
        if stacked:
            baseline = top.copy()

    _apply_prism_style(ax, font_size, **_sk)
    _apply_grid(ax, grid_style, gridlines)
    if ylim is not None: ax.set_ylim(ylim)
    elif not stacked: ax.set_ylim(bottom=0)
    if yscale == "log": ax.set_yscale("log")
    _set_axis_labels(ax, xlabel or x_label, ytitle, title, font_size)
    _apply_legend(ax, legend_pos, font_size)
    _base_plot_finish(ax, fig, title, xlabel or x_label, ytitle, yscale, ylim,
                      font_size, ref_line, len(unique_s), ref_line_label=ref_line_label, **_sk)
    return fig, ax


# ---------------------------------------------------------------------------
# prism_raincloud  — Half-violin + jitter strip + mean/SD bar (raincloud plot)
# ---------------------------------------------------------------------------

def prism_raincloud(
    excel_path: str,
    sheet=0,
    color=None,
    title: str = "",
    xlabel: str = "",
    ytitle: str = "",
    yscale: str = "linear",
    ylim=None,
    figsize=(5, 5),
    font_size: float = 12.0,
    show_points: bool = True,
    point_size: float = 5.0,
    point_alpha: float = 0.65,
    jitter_amount: float = 0.08,
    show_box: bool = True,
    show_stats: bool = False,
    stats_test: str = "parametric",
    n_permutations: int = 9999,
    control=None,
    mc_correction: str = "Holm-Bonferroni",
    posthoc: str = "Tukey HSD",
    show_p_values: bool = False,
    show_effect_size: bool = False,
    show_test_name: bool = False,
    ref_line=None,
    ref_line_label: str = "",
    axis_style: str = "open",
    tick_dir: str = "out",
    minor_ticks: bool = False,
    cap_size: float = 4.0,
    ytick_interval: float = 0.0,
    xtick_interval: float = 0.0,
    fig_bg: str = "white",
    spine_width: float = 0.8,
    bracket_style: str = "lines",
    gridlines: bool = False,
    grid_style: str = "none",
    show_n_labels: bool = True,
):
    """Raincloud plot: half-violin (left) + jitter strip (right) + optional thin box.

    A modern alternative to violin/box plots popular in psychological and clinical
    research.  The half-violin shows the full distribution; the strip plot shows
    individual data points; the box shows median and IQR.

    Same Excel layout as Bar Chart (row 0 = group names, rows 1+ = values).
    """
    _ensure_imports()
    from matplotlib.patches import Polygon

    group_order, groups, bar_colors, fig, ax = _base_plot_setup(
        excel_path, sheet, color, None, figsize)
    n_groups = len(group_order)
    _sk = _style_kwargs(locals())
    norm_warn = normality_warning(groups, stats_test)

    rng = np.random.default_rng(seed=42)

    for g_idx, g in enumerate(group_order):
        vals  = groups[g]
        c     = bar_colors[g_idx]
        cx    = g_idx

        # ── Half-violin (left side only) ─────────────────────────────────
        try:
            from scipy.stats import gaussian_kde
            kde      = gaussian_kde(vals, bw_method="scott")
            kd_range = np.linspace(vals.min() - 0.5, vals.max() + 0.5, 200)
            kd_dens  = kde(kd_range)
            max_w    = 0.38
            kd_dens  = kd_dens / kd_dens.max() * max_w
            # Left half polygon
            xs_left  = cx - kd_dens   # extends left of centre
            xs_poly  = np.concatenate([[cx], xs_left, [cx]])
            ys_poly  = np.concatenate([[kd_range[0]], kd_range, [kd_range[-1]]])
            poly = Polygon(list(zip(xs_poly, ys_poly)),
                           facecolor=c, edgecolor=_darken_color(c, 0.7),
                           linewidth=0.8, alpha=0.80, zorder=3)
            ax.add_patch(poly)
        except Exception:
            pass

        # ── Jitter strip (right side) ────────────────────────────────────
        if show_points:
            jitter_x = cx + 0.06 + rng.uniform(0, jitter_amount * 2, len(vals))
            fc = "none" if False else c
            ax.scatter(jitter_x, vals, color=fc, edgecolors=_darken_color(c, 0.7),
                       linewidths=0.8, s=point_size**2, alpha=point_alpha, zorder=5)

        # ── Thin box overlay ──────────────────────────────────────────────
        if show_box and len(vals) >= 3:
            q1, med, q3 = np.percentile(vals, [25, 50, 75])
            iqr = q3 - q1
            lo_w = max(vals[vals >= q1 - 1.5 * iqr].min(), vals.min())
            hi_w = min(vals[vals <= q3 + 1.5 * iqr].max(), vals.max())
            bx = cx + 0.02
            bw = 0.06
            ax.add_patch(__import__("matplotlib").patches.FancyBboxPatch(
                (bx - bw/2, q1), bw, q3 - q1,
                boxstyle="square,pad=0", linewidth=1.0,
                edgecolor=_darken_color(c, 0.7), facecolor="white", zorder=6))
            ax.plot([bx - bw/2, bx + bw/2], [med, med],
                    color=_darken_color(c, 0.5), linewidth=2, zorder=7)
            ax.plot([bx, bx], [lo_w, q1], color=_darken_color(c, 0.6), linewidth=0.8, zorder=6)
            ax.plot([bx, bx], [q3, hi_w], color=_darken_color(c, 0.6), linewidth=0.8, zorder=6)

    _set_categorical_xticks(ax, group_order, groups, font_size,
                            show_n_labels=show_n_labels)
    ax.set_xlim(-0.6, n_groups - 0.4)
    ax.set_xlabel("")
    _apply_prism_style(ax, font_size, **_sk)
    _apply_grid(ax, grid_style, gridlines)
    if ylim is not None: ax.set_ylim(ylim)

    if show_stats:
        _apply_stats_brackets(ax, groups, group_order,
                              stats_test, n_permutations, control,
                              mc_correction, posthoc,
                              show_p_values, show_effect_size, show_test_name,
                              font_size, bracket_style=bracket_style)

    _draw_normality_warning(ax, norm_warn, font_size)
    _base_plot_finish(ax, fig, title, xlabel, ytitle, yscale, ylim,
                      font_size, ref_line, n_groups, ref_line_label=ref_line_label, **_sk)
    return fig, ax


# ---------------------------------------------------------------------------
# prism_qq_plot  — Quantile-quantile normality plot
# ---------------------------------------------------------------------------

def prism_qq_plot(
    excel_path: str,
    sheet=0,
    color=None,
    title: str = "",
    xlabel: str = "Theoretical Quantiles",
    ytitle: str = "Sample Quantiles",
    figsize=(5, 5),
    font_size: float = 12.0,
    point_size: float = 5.0,
    point_alpha: float = 0.75,
    show_ci_band: bool = True,
    ci_alpha: float = 0.15,
    ref_line=None,
    ref_line_label: str = "",
    axis_style: str = "open",
    tick_dir: str = "out",
    minor_ticks: bool = False,
    ytick_interval: float = 0.0,
    xtick_interval: float = 0.0,
    fig_bg: str = "white",
    spine_width: float = 0.8,
    legend_pos: str = "best",
    gridlines: bool = False,
    grid_style: str = "none",
):
    """Normal Q-Q plot for one or more groups, matching Prism's Q-Q normality check.

    Points lying along the diagonal indicate normality.  A 95% confidence band
    is drawn around the line when show_ci_band=True.

    Same Excel layout as Bar Chart (row 0 = group names, rows 1+ = values).
    """
    _ensure_imports()
    from scipy import stats as _sst

    group_order, groups, bar_colors, fig, ax = _base_plot_setup(
        excel_path, sheet, color, None, figsize)
    _sk = _style_kwargs(locals())

    for g_idx, g in enumerate(group_order):
        vals = np.sort(groups[g])
        n    = len(vals)
        if n < 3:
            continue
        c = bar_colors[g_idx]

        # Theoretical quantiles
        probs = (np.arange(1, n + 1) - 0.375) / (n + 0.25)   # Blom plotting positions
        theo  = _sst.norm.ppf(probs)
        ax.scatter(theo, vals, color=c, edgecolors=_darken_color(c, 0.7),
                   s=point_size**2, linewidths=0.7, alpha=point_alpha,
                   zorder=4, label=g)

        # Reference line: through 1st and 3rd quartile
        q1, q3  = np.percentile(vals, [25, 75])
        th1, th3 = _sst.norm.ppf([0.25, 0.75])
        slope    = (q3 - q1) / (th3 - th1)
        intercept= q1 - slope * th1
        t_ext    = np.array([theo.min() - 0.3, theo.max() + 0.3])
        ax.plot(t_ext, slope * t_ext + intercept,
                color=_darken_color(c, 0.7), linewidth=1.0, linestyle="--",
                alpha=0.8, zorder=3)

        # Confidence band (simulation-based)
        if show_ci_band and n >= 5:
            n_sim  = 1000
            rng    = np.random.default_rng(42)
            sims   = np.sort(rng.standard_normal((n_sim, n)), axis=1)
            # Scale to match reference line
            sims   = sims * slope + intercept
            lo_ci  = np.percentile(sims, 2.5,  axis=0)
            hi_ci  = np.percentile(sims, 97.5, axis=0)
            ax.fill_between(theo, lo_ci, hi_ci, alpha=ci_alpha,
                            color=c, zorder=2)

    _apply_prism_style(ax, font_size, **_sk)
    _apply_grid(ax, grid_style, gridlines)
    _apply_legend(ax, legend_pos, font_size)
    ax.set_xlabel(xlabel, fontsize=font_size + 2, fontfamily=_get_font(),
                  labelpad=_LABEL_PAD, fontweight="bold")
    ax.set_ylabel(ytitle, fontsize=font_size + 2, fontfamily=_get_font(),
                  labelpad=_LABEL_PAD, fontweight="bold")
    if title:
        ax.set_title(title, fontsize=font_size + 4, fontfamily=_get_font(),
                     pad=_TITLE_PAD, fontweight="bold")
    fig.tight_layout(pad=_TIGHT_PAD)
    return fig, ax


# ---------------------------------------------------------------------------
# prism_lollipop  — Lollipop / Cleveland dot chart
# ---------------------------------------------------------------------------

def prism_lollipop(
    excel_path: str,
    sheet=0,
    error: str = "sem",
    color=None,
    title: str = "",
    xlabel: str = "",
    ytitle: str = "",
    yscale: str = "linear",
    ylim=None,
    figsize=(5, 5),
    font_size: float = 12.0,
    marker_size: float = 10.0,
    stem_width: float = 1.5,
    horizontal: bool = False,
    show_value_labels: bool = False,
    show_n_labels: bool = True,
    ref_line=None,
    ref_line_label: str = "",
    axis_style: str = "open",
    tick_dir: str = "out",
    minor_ticks: bool = False,
    point_size: float = 6.0,
    point_alpha: float = 0.90,
    cap_size: float = 4.0,
    ytick_interval: float = 0.0,
    xtick_interval: float = 0.0,
    fig_bg: str = "white",
    spine_width: float = 0.8,
    gridlines: bool = False,
    grid_style: str = "none",
    show_stats: bool = False,
    stats_test: str = "parametric",
    n_permutations: int = 9999,
    control=None,
    mc_correction: str = "Holm-Bonferroni",
    posthoc: str = "Tukey HSD",
    show_p_values: bool = False,
    show_effect_size: bool = False,
    show_test_name: bool = False,
    bracket_style: str = "lines",
    xtick_labels: list = None,
):
    """Lollipop (Cleveland dot) chart — dot + thin stem, a clean Prism alternative to bars.

    Conveys the same information as a bar chart with less visual weight.
    Same Excel layout as Bar Chart (row 0 = group names, rows 1+ = values).
    """
    _ensure_imports()
    group_order, groups, bar_colors, _, _ = _base_plot_setup(
        excel_path, sheet, color, None, figsize)
    n_groups = len(group_order)
    fig, ax  = plt.subplots(figsize=figsize, dpi=_DPI)
    _sk      = _style_kwargs(locals())
    norm_warn = normality_warning(groups, stats_test)

    for g_idx, g in enumerate(group_order):
        vals = groups[g]
        m, err = _calc_error(vals, error)
        c = bar_colors[g_idx]
        dark_c = _darken_color(c, 0.7)

        if horizontal:
            ax.hlines(g_idx, 0, m, colors=dark_c, linewidths=stem_width, zorder=2)
            ax.errorbar(m, g_idx, xerr=err, fmt="none", ecolor=dark_c,
                        elinewidth=1.0, capsize=cap_size, capthick=1.0, zorder=3)
            ax.scatter([m], [g_idx], color=c, edgecolors=dark_c,
                       linewidths=1.0, s=marker_size**2, zorder=4, alpha=point_alpha)
            if show_value_labels:
                ax.text(m + err + 0.02, g_idx, _fmt_bar_label(m),
                        va="center", fontsize=font_size * 0.82,
                        fontfamily=_get_font(), color=_COLOR_ANNOT)
        else:
            ax.vlines(g_idx, 0, m, colors=dark_c, linewidths=stem_width, zorder=2)
            ax.errorbar(g_idx, m, yerr=err, fmt="none", ecolor=dark_c,
                        elinewidth=1.0, capsize=cap_size, capthick=1.0, zorder=3)
            ax.scatter([g_idx], [m], color=c, edgecolors=dark_c,
                       linewidths=1.0, s=marker_size**2, zorder=4, alpha=point_alpha)
            if show_value_labels:
                ax.text(g_idx, m + err + 0.02 * ax.get_ylim()[1] if ax.get_ylim()[1] else 0.02,
                        _fmt_bar_label(m), ha="center",
                        fontsize=font_size * 0.82, fontfamily=_get_font(), color=_COLOR_ANNOT)

    if horizontal:
        ax.set_yticks(range(n_groups))
        h_lbls = (_n_labels(group_order, groups, font_size)
                  if show_n_labels else (xtick_labels or group_order))
        ax.set_yticklabels(h_lbls, fontsize=font_size, fontfamily=_get_font(), fontweight="bold")
        ax.set_xlim(left=0)
        _apply_prism_style(ax, font_size, **_sk)
        if ytitle:
            ax.set_xlabel(ytitle, fontsize=font_size + 2, fontfamily=_get_font(),
                          labelpad=_LABEL_PAD, fontweight="bold")
    else:
        _set_categorical_xticks(ax, group_order, groups, font_size,
                                show_n_labels=show_n_labels,
                                xtick_labels=xtick_labels)
        ax.set_xlim(-0.6, n_groups - 0.4)
        ax.set_ylim(bottom=0)
        ax.set_xlabel("")
        _apply_prism_style(ax, font_size, **_sk)
        if show_stats:
            _apply_stats_brackets(ax, groups, group_order,
                                  stats_test, n_permutations, control,
                                  mc_correction, posthoc,
                                  show_p_values, show_effect_size, show_test_name,
                                  font_size, bracket_style=bracket_style)

    _apply_grid(ax, grid_style, gridlines)
    _draw_normality_warning(ax, norm_warn, font_size)
    _base_plot_finish(ax, fig, title, xlabel, ytitle, yscale, ylim,
                      font_size, ref_line, n_groups,
                      ref_line_label=ref_line_label, **_sk)
    return fig, ax


# ---------------------------------------------------------------------------
# prism_waterfall  — Waterfall / bridge chart
# ---------------------------------------------------------------------------

def prism_waterfall(
    excel_path: str,
    sheet=0,
    color=None,
    title: str = "",
    xlabel: str = "",
    ytitle: str = "",
    figsize=(6, 5),
    font_size: float = 12.0,
    show_value_labels: bool = True,
    show_connector_lines: bool = True,
    positive_color: str = "#2274A5",
    negative_color: str = "#E8453C",
    total_color: str = "#32936F",
    bar_width: float = 0.7,
    alpha: float = 0.85,
    show_total: bool = True,
    ref_line=None,
    ref_line_label: str = "",
    axis_style: str = "open",
    tick_dir: str = "out",
    minor_ticks: bool = False,
    ytick_interval: float = 0.0,
    xtick_interval: float = 0.0,
    fig_bg: str = "white",
    spine_width: float = 0.8,
    gridlines: bool = False,
    grid_style: str = "none",
):
    """Waterfall (bridge/McKinsey) chart — cumulative running totals.

    Excel layout (same as flat-header bar chart):
      Row 1  : Category names
      Row 2  : Numeric values (positive = increase, negative = decrease)

    A "Total" bar is added automatically at the right when show_total=True.
    Positive changes are drawn in positive_color, negative in negative_color,
    the total in total_color.
    """
    _ensure_imports()
    group_order, groups, _, _, _ = _base_plot_setup(
        excel_path, sheet, color, None, figsize)
    fig, ax = plt.subplots(figsize=figsize, dpi=_DPI)
    _sk     = _style_kwargs(locals())

    # Use first value per group as the step delta
    deltas = {}
    for g in group_order:
        vals = groups[g]
        deltas[g] = float(np.mean(vals)) if len(vals) > 0 else 0.0

    running = 0.0
    bar_bottoms = []
    bar_heights = []
    bar_colors_list = []
    bar_labels = list(group_order)

    for g in group_order:
        d = deltas[g]
        bottom = running if d >= 0 else running + d
        bar_bottoms.append(bottom)
        bar_heights.append(abs(d))
        bar_colors_list.append(positive_color if d >= 0 else negative_color)
        running += d

    if show_total:
        bar_bottoms.append(0.0 if running >= 0 else running)
        bar_heights.append(abs(running))
        bar_colors_list.append(total_color)
        bar_labels.append("Total")

    n = len(bar_labels)
    x_pos = range(n)

    for i, (bot, hgt, c) in enumerate(zip(bar_bottoms, bar_heights, bar_colors_list)):
        dark_c = _darken_color(c, 0.65)
        ax.bar(i, hgt, bottom=bot, width=bar_width, color=c,
               edgecolor=dark_c, linewidth=0.8, alpha=alpha, zorder=3)
        if show_value_labels and hgt > 0:
            # Value label above or below bar
            top    = bot + hgt
            val    = deltas.get(bar_labels[i], running if bar_labels[i] == "Total" else 0)
            label  = f"+{val:.3g}" if val > 0 else f"{val:.3g}"
            if bar_labels[i] == "Total":
                label = f"{running:.3g}"
            y_pos  = top + abs(ax.get_ylim()[1] - ax.get_ylim()[0]) * 0.01 if top >= 0 else bot - abs(ax.get_ylim()[1] - ax.get_ylim()[0]) * 0.02
            ax.text(i, top + 0.02, label, ha="center", va="bottom",
                    fontsize=font_size * 0.82, fontfamily=_get_font(),
                    color=_COLOR_ANNOT, zorder=6)

    # Connector lines between bars
    if show_connector_lines:
        for i in range(n - 1):
            top_i = bar_bottoms[i] + bar_heights[i]
            ax.plot([i + bar_width/2, i + 1 - bar_width/2],
                    [top_i, top_i],
                    color="#999999", linewidth=0.8, linestyle="--", zorder=2)

    # Zero line
    ax.axhline(0, color="#333333", linewidth=0.8, zorder=1)

    ax.set_xticks(range(n))
    ax.set_xticklabels(bar_labels, fontsize=font_size, fontfamily=_get_font(),
                       fontweight="bold", rotation=45 if n > 5 else 0,
                       ha="right" if n > 5 else "center")
    ax.set_xlim(-0.6, n - 0.4)
    _apply_prism_style(ax, font_size, **_sk)
    _apply_grid(ax, grid_style, gridlines)
    _base_plot_finish(ax, fig, title, xlabel, ytitle, "linear", None,
                      font_size, ref_line, n,
                      ref_line_label=ref_line_label, **_sk)
    return fig, ax


# ---------------------------------------------------------------------------
# prism_pyramid  — Population pyramid / mirrored bar chart
# ---------------------------------------------------------------------------

def prism_pyramid(
    excel_path: str,
    sheet=0,
    color=None,
    title: str = "",
    xlabel: str = "",
    ytitle: str = "Category",
    figsize=(6, 5),
    font_size: float = 12.0,
    bar_width: float = 0.7,
    alpha: float = 0.85,
    show_value_labels: bool = True,
    ref_line=None,
    ref_line_label: str = "",
    axis_style: str = "open",
    tick_dir: str = "out",
    minor_ticks: bool = False,
    ytick_interval: float = 0.0,
    xtick_interval: float = 0.0,
    fig_bg: str = "white",
    spine_width: float = 0.8,
    legend_pos: str = "upper right",
    gridlines: bool = False,
    grid_style: str = "none",
):
    """Population pyramid (mirrored/diverging bar chart).

    Excel layout (3 columns, no header row):
      Col 1 : Category labels (e.g. age groups "0-9", "10-19", …)
      Col 2 : Left-side values (e.g. Male counts) — plotted to the left (negative X)
      Col 3 : Right-side values (e.g. Female counts) — plotted to the right (positive X)

    The column headers in Row 1 are used as legend labels.
    """
    _ensure_imports()
    df     = pd.read_excel(excel_path, sheet_name=sheet, header=0)
    cols   = df.columns.tolist()
    if len(cols) < 3:
        raise ValueError("Pyramid chart needs exactly 3 columns: Category, Left series, Right series.")

    cat_col, left_col, right_col = cols[0], cols[1], cols[2]
    categories  = df[cat_col].astype(str).tolist()
    left_vals   = pd.to_numeric(df[left_col],  errors="coerce").fillna(0).abs().tolist()
    right_vals  = pd.to_numeric(df[right_col], errors="coerce").fillna(0).abs().tolist()

    colors = _assign_colors(2, color)
    lc, rc = colors[0], colors[1]
    n      = len(categories)
    y_pos  = np.arange(n)

    fig, ax = plt.subplots(figsize=figsize, dpi=_DPI)
    _sk = _style_kwargs(locals())

    lbars = ax.barh(y_pos, [-v for v in left_vals], height=bar_width,
                    color=lc, edgecolor=_darken_color(lc, 0.65),
                    linewidth=0.8, alpha=alpha, label=left_col, zorder=3)
    rbars = ax.barh(y_pos, right_vals, height=bar_width,
                    color=rc, edgecolor=_darken_color(rc, 0.65),
                    linewidth=0.8, alpha=alpha, label=right_col, zorder=3)

    if show_value_labels:
        for i, (lv, rv) in enumerate(zip(left_vals, right_vals)):
            ax.text(-lv - 0.01, i, f"{lv:,.0f}", ha="right", va="center",
                    fontsize=font_size * 0.78, fontfamily=_get_font(), color=_COLOR_ANNOT)
            ax.text(rv  + 0.01, i, f"{rv:,.0f}",  ha="left",  va="center",
                    fontsize=font_size * 0.78, fontfamily=_get_font(), color=_COLOR_ANNOT)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(categories, fontsize=font_size, fontfamily=_get_font())
    ax.axvline(0, color="#333333", linewidth=0.8, zorder=1)

    # Symmetric x-axis
    max_val = max(max(left_vals), max(right_vals)) * 1.15
    ax.set_xlim(-max_val, max_val)

    # Positive tick labels on both sides
    ticks     = ax.get_xticks()
    ax.set_xticklabels([f"{abs(t):,.0f}" for t in ticks],
                       fontsize=font_size * 0.85, fontfamily=_get_font())

    _apply_prism_style(ax, font_size, **_sk)
    _apply_grid(ax, grid_style, gridlines)
    _apply_legend(ax, legend_pos, font_size)
    if title: ax.set_title(title, fontsize=font_size + 4, fontfamily=_get_font(),
                           pad=_TITLE_PAD, fontweight="bold")
    if xlabel: ax.set_xlabel(xlabel, fontsize=font_size + 2, fontfamily=_get_font(),
                              labelpad=_LABEL_PAD, fontweight="bold")
    if ytitle: ax.set_ylabel(ytitle, fontsize=font_size + 2, fontfamily=_get_font(),
                              labelpad=_LABEL_PAD, fontweight="bold")
    fig.tight_layout(pad=_TIGHT_PAD)
    return fig, ax


# ---------------------------------------------------------------------------
# prism_ecdf  — Empirical cumulative distribution function plot
# ---------------------------------------------------------------------------

def prism_ecdf(
    excel_path: str,
    sheet=0,
    color=None,
    title: str = "",
    xlabel: str = "",
    ytitle: str = "Cumulative Probability",
    figsize=(5, 5),
    font_size: float = 12.0,
    line_width: float = 1.8,
    show_points: bool = False,
    point_size: float = 4.0,
    point_alpha: float = 0.6,
    complementary: bool = False,
    ref_line=None,
    ref_line_label: str = "",
    axis_style: str = "open",
    tick_dir: str = "out",
    minor_ticks: bool = False,
    ytick_interval: float = 0.0,
    xtick_interval: float = 0.0,
    fig_bg: str = "white",
    spine_width: float = 0.8,
    legend_pos: str = "best",
    gridlines: bool = False,
    grid_style: str = "none",
):
    """Empirical CDF (ECDF) plot — step function showing the cumulative distribution.

    Prism calls this a "Cumulative frequency distribution" plot.
    Set complementary=True for a survival-function style (1 - ECDF).

    Same Excel layout as Bar Chart (row 0 = group names, rows 1+ = values).
    """
    _ensure_imports()
    group_order, groups, bar_colors, fig, ax = _base_plot_setup(
        excel_path, sheet, color, None, figsize)
    _sk = _style_kwargs(locals())

    for g_idx, g in enumerate(group_order):
        vals  = np.sort(groups[g])
        n     = len(vals)
        probs = np.arange(1, n + 1) / n
        if complementary:
            probs = 1.0 - probs

        c = bar_colors[g_idx]
        # Step function
        xs = np.concatenate([[vals[0] - (vals[-1] - vals[0]) * 0.02],
                              np.repeat(vals, 2)[:-1]])
        ys = np.concatenate([[0.0 if not complementary else 1.0],
                              np.repeat(probs, 2)[:-1]])
        ax.plot(xs, ys, color=c, linewidth=line_width,
                zorder=3, label=g, solid_capstyle="round")
        # Extend to right edge
        ax.plot([vals[-1], vals[-1] + (vals[-1] - vals[0]) * 0.02],
                [probs[-1], probs[-1]], color=c, linewidth=line_width, zorder=3)

        if show_points:
            ax.scatter(vals, probs, color=c, edgecolors=_darken_color(c, 0.7),
                       s=point_size**2, linewidths=0.7, alpha=point_alpha, zorder=4)

    ax.set_ylim(0, 1.05)
    _apply_prism_style(ax, font_size, **_sk)
    _apply_grid(ax, grid_style, gridlines)
    _apply_legend(ax, legend_pos, font_size)
    ax.set_xlabel(xlabel or "Value", fontsize=font_size + 2, fontfamily=_get_font(),
                  labelpad=_LABEL_PAD, fontweight="bold")
    ax.set_ylabel(ytitle, fontsize=font_size + 2, fontfamily=_get_font(),
                  labelpad=_LABEL_PAD, fontweight="bold")
    if title: ax.set_title(title, fontsize=font_size + 4, fontfamily=_get_font(),
                           pad=_TITLE_PAD, fontweight="bold")
    if ref_line is not None:
        _draw_ref_line(ax, ref_line, font_size, label=ref_line_label or None)
    fig.tight_layout(pad=_TIGHT_PAD)
    return fig, ax

def export_all_charts_pdf(output_path: str, excel_path: str,
                           sheet=0, figsize=(6, 5), font_size: float = 11.0,
                           color=None) -> str:
    """Generate a multi-page PDF with one page per chart type (P20).

    Each page shows the chart type rendered with the supplied Excel data.
    Charts that cannot render the data (wrong layout, too few columns, etc.)
    show a graceful error page instead of crashing.

    Parameters
    ----------
    output_path : Destination .pdf file path.
    excel_path  : Excel file used as data source for every chart.
    sheet       : Sheet index or name (default 0).
    figsize     : (width, height) inches for each chart page.
    font_size   : Base font size.
    color       : Color palette name or None for default.

    Returns
    -------
    output_path : the path that was written.
    """
    _ensure_imports()
    from matplotlib.backends.backend_pdf import PdfPages

    CHART_FNS = [
        ("Bar",                prism_barplot),
        ("Line",               prism_linegraph),
        ("Grouped Bar",        prism_grouped_barplot),
        ("Box Plot",           prism_boxplot),
        ("Scatter",            prism_scatterplot),
        ("Violin",             prism_violin),
        ("Before / After",     prism_before_after),
        ("Histogram",          prism_histogram),
        ("Subcolumn Scatter",  prism_subcolumn_scatter),
        ("Dot Plot",           prism_dot_plot),
        ("Repeated Measures",  prism_repeated_measures),
        ("Stacked Bar",        prism_stacked_bar),
        ("Kaplan-Meier",       prism_kaplan_meier),
        ("Heatmap",            prism_heatmap),
        ("Two-Way ANOVA",      prism_two_way_anova),
        ("Curve Fit",          prism_curve_fit),
        ("Column Statistics",  prism_column_stats),
        ("Contingency",        prism_contingency),
        ("Chi-Square GoF",     prism_chi_square_gof),
        ("Bubble",             prism_bubble),
        ("Bland-Altman",       prism_bland_altman),
        ("Forest Plot",        prism_forest_plot),
    ]

    _common = dict(excel_path=excel_path, sheet=sheet,
                   figsize=figsize, font_size=font_size, color=color)

    with PdfPages(output_path) as pdf:
        # Cover page
        fig_cover, ax_cover = plt.subplots(figsize=figsize, dpi=_DPI)
        ax_cover.axis("off")
        ax_cover.text(0.5, 0.60, "Claude Prism", transform=ax_cover.transAxes,
                      ha="center", va="center", fontsize=28, fontweight="bold",
                      fontfamily=_get_font(), color="#2274A5")
        ax_cover.text(0.5, 0.48, "Chart Type Showcase", transform=ax_cover.transAxes,
                      ha="center", va="center", fontsize=16,
                      fontfamily=_get_font(), color="#555555")
        ax_cover.text(0.5, 0.38, f"Data: {excel_path}", transform=ax_cover.transAxes,
                      ha="center", va="center", fontsize=9,
                      fontfamily=_get_font(), color="#888888")
        import datetime
        ax_cover.text(0.5, 0.30,
                      datetime.datetime.now().strftime("%B %d, %Y"),
                      transform=ax_cover.transAxes,
                      ha="center", va="center", fontsize=9,
                      fontfamily=_get_font(), color="#888888")
        ax_cover.text(0.5, 0.06,
                      "Designed and implemented by Claude (Anthropic)\n"
                      "MIT License — Ashwin Pasupathy",
                      transform=ax_cover.transAxes,
                      ha="center", va="center", fontsize=8,
                      fontfamily=_get_font(), color="#aaaaaa")
        pdf.savefig(fig_cover, bbox_inches="tight")
        plt.close(fig_cover)

        for page_num, (chart_name, fn) in enumerate(CHART_FNS, 1):
            try:
                import inspect as _insp
                sig = _insp.signature(fn)
                kw = {k: v for k, v in _common.items() if k in sig.parameters}
                fig, ax = fn(**kw)
                # Add chart name as super-title if not already set
                if not ax.get_title():
                    ax.set_title(chart_name, fontsize=font_size + 2,
                                 fontfamily=_get_font(), pad=8, fontweight="bold")
                # Footer
                fig.text(0.5, 0.01, f"Page {page_num} of {len(CHART_FNS)}  ·  {chart_name}",
                         ha="center", fontsize=7, color="#aaaaaa", fontfamily=_get_font())
                pdf.savefig(fig, bbox_inches="tight")
                plt.close(fig)
            except Exception as exc:
                # Error page — never crash the whole export
                fig_err, ax_err = plt.subplots(figsize=figsize, dpi=_DPI)
                ax_err.axis("off")
                ax_err.text(0.5, 0.6, chart_name, transform=ax_err.transAxes,
                            ha="center", va="center", fontsize=16, fontweight="bold",
                            fontfamily=_get_font(), color="#555555")
                ax_err.text(0.5, 0.45,
                            "Could not render with the supplied data.\n"
                            f"Reason: {str(exc)[:120]}",
                            transform=ax_err.transAxes,
                            ha="center", va="center", fontsize=9,
                            fontfamily=_get_font(), color="#cc6600",
                            wrap=True)
                fig_err.text(0.5, 0.01, f"Page {page_num} of {len(CHART_FNS)}  ·  {chart_name}",
                             ha="center", fontsize=7, color="#aaaaaa", fontfamily=_get_font())
                pdf.savefig(fig_err, bbox_inches="tight")
                plt.close(fig_err)

        # PDF metadata
        d = pdf.infodict()
        d["Title"] = "Claude Prism — Chart Showcase"
        d["Author"] = "Claude (Anthropic) / Ashwin Pasupathy"
        d["Subject"] = "GraphPad Prism-style charts"

    return output_path
