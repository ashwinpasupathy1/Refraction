"""
visual_test.py
==============
Renders every chart type (and key stat/display variants) to PNG files,
then composites them into a single browsable grid.

Run:
    python3 visual_test.py
Output:
    visual_output/  – individual PNGs (one per test case)
    visual_grid.png – full grid for at-a-glance inspection
"""

import sys, os, tempfile, warnings, traceback
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "claude_prism_src"))
os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from PIL import Image

import prism_functions as pf
pf._ensure_imports()

OUT_DIR = os.path.join(os.path.dirname(__file__), "visual_output")
os.makedirs(OUT_DIR, exist_ok=True)

rng = np.random.default_rng(2025)

# ─────────────────────────────────────────────────────────────────────────────
# Data fixtures
# ─────────────────────────────────────────────────────────────────────────────

CTRL  = rng.normal(10.0, 1.5, 10)
DRUG  = rng.normal(14.5, 1.8, 10)
DRUGB = rng.normal(17.0, 2.0, 10)

BEFORE = rng.normal(10.0, 1.5, 10)
AFTER  = BEFORE + rng.normal(3.0, 0.8, 10)

T0 = rng.normal(10.0, 1.5, 8)
T1 = T0 + rng.normal(1.5, 0.5, 8)
T2 = T1 + rng.normal(1.5, 0.5, 8)
T3 = T2 + rng.normal(1.5, 0.5, 8)

X_VALS = np.array([0, 1, 2, 4, 8, 16, 24], dtype=float)
CF_X   = np.logspace(-2, 2, 12)
CF_Y   = 100 / (1 + (10 / CF_X) ** 1.5) + rng.normal(0, 3, 12)


def write_bar(path, groups):
    names = list(groups.keys())
    n = max(len(v) for v in groups.values())
    rows = [names] + [[groups[k][i] if i < len(groups[k]) else None for k in names]
                      for i in range(n)]
    pd.DataFrame(rows).to_excel(path, index=False, header=False)


def write_line(path, x_vals, series):
    reps  = len(next(iter(series.values()))[0])
    hdr   = ["X"] + [n for n in series for _ in range(reps)]
    rows  = [hdr] + [[x] + [series[n][i][j] for n in series
                             for j in range(reps)]
                     for i, x in enumerate(x_vals)]
    pd.DataFrame(rows).to_excel(path, index=False, header=False)


def write_grouped(path, cats, subs, data):
    max_n = max(len(v) for c in cats for s in subs
                for v in [data[c].get(s, [])] if v)
    rows  = [[c for c in cats for _ in subs],
             [s for _ in cats for s in subs]]
    for i in range(max_n):
        rows.append([data[c].get(s, [None] * max_n)[i]
                     if i < len(data[c].get(s, [])) else None
                     for c in cats for s in subs])
    pd.DataFrame(rows).to_excel(path, index=False, header=False)


def write_km(path, groups):
    row1 = [n for n in groups for _ in range(2)]
    row2 = ["Time", "Event"] * len(groups)
    max_n = max(len(g["time"]) for g in groups.values())
    rows  = [row1, row2]
    for i in range(max_n):
        row = []
        for g in groups.values():
            row += [g["time"][i] if i < len(g["time"]) else None,
                    g["event"][i] if i < len(g["event"]) else None]
        rows.append(row)
    pd.DataFrame(rows).to_excel(path, index=False, header=False)


def write_heatmap(path, matrix, rlbls, clbls):
    rows = [[""] + clbls] + [[rl] + list(r) for rl, r in zip(rlbls, matrix)]
    pd.DataFrame(rows).to_excel(path, index=False, header=False)


def write_two_way(path, records):
    pd.DataFrame(records, columns=["Factor_A", "Factor_B", "Value"]).to_excel(path, index=False)


def write_contingency(path, rlbls, clbls, matrix):
    rows = [[""] + clbls] + [[rl] + list(r) for rl, r in zip(rlbls, matrix)]
    pd.DataFrame(rows).to_excel(path, index=False, header=False)


# ─────────────────────────────────────────────────────────────────────────────
# Test runner
# ─────────────────────────────────────────────────────────────────────────────

results = []   # (label, path_or_None, error_or_None)

def run_case(label, fn, *args, **kwargs):
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            fig, ax = fn(*args, **kwargs)
        out = os.path.join(OUT_DIR, f"{label.replace(' ', '_').replace('/', '-')}.png")
        fig.savefig(out, dpi=120, bbox_inches="tight")
        plt.close(fig)
        results.append((label, out, None))
        print(f"  ✓  {label}")
    except Exception as e:
        tb = traceback.format_exc().strip().splitlines()[-1]
        results.append((label, None, f"{type(e).__name__}: {e}\n    {tb}"))
        print(f"  ✗  {label}\n     {tb}")


# ─────────────────────────────────────────────────────────────────────────────
# 1 ── Bar Chart
# ─────────────────────────────────────────────────────────────────────────────
print("\n── Bar Chart ──")
with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f: p = f.name
write_bar(p, {"Control": CTRL, "Drug A": DRUG, "Drug B": DRUGB})

run_case("Bar default",         pf.prism_barplot, p, title="Bar – default")
run_case("Bar + stats Tukey",   pf.prism_barplot, p, title="Bar + Tukey HSD",
         show_stats=True, stats_test="parametric", posthoc="Tukey HSD",
         show_p_values=True, show_effect_size=True)
run_case("Bar + Dunnett",       pf.prism_barplot, p, title="Bar + Dunnett",
         show_stats=True, posthoc="Dunnett (vs control)", control="Control")
run_case("Bar nonparametric",   pf.prism_barplot, p, title="Bar – KW + Dunn's",
         show_stats=True, stats_test="nonparametric")
run_case("Bar horizontal",      pf.prism_barplot, p, title="Bar – horizontal",
         horizontal=True)
run_case("Bar log scale",       pf.prism_barplot, p, title="Bar – log Y",
         yscale="log")
run_case("Bar error=SD",        pf.prism_barplot, p, error="sd",
         title="Bar – SD error bars")
run_case("Bar open pts median", pf.prism_barplot, p, open_points=True,
         show_median=True, title="Bar – open pts + median")
os.unlink(p)

# 2-group paired
with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f: p = f.name
write_bar(p, {"Before": BEFORE, "After": AFTER})
run_case("Bar paired t-test",   pf.prism_barplot, p, title="Bar – paired",
         show_stats=True, stats_test="paired")
os.unlink(p)

# ─────────────────────────────────────────────────────────────────────────────
# 2 ── Line Graph
# ─────────────────────────────────────────────────────────────────────────────
print("\n── Line Graph ──")
line_series = {
    "Control": np.column_stack([X_VALS * 0.5 + rng.normal(0, 0.5, 7) for _ in range(3)]),
    "Drug A":  np.column_stack([X_VALS * 1.1 + rng.normal(0, 0.6, 7) for _ in range(3)]),
}
with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f: p = f.name
write_line(p, X_VALS, line_series)
run_case("Line default",        pf.prism_linegraph, p, title="Line – default",
         xlabel="Time (h)", ytitle="Response")
run_case("Line log Y",          pf.prism_linegraph, p, title="Line – log Y",
         yscale="log")
run_case("Line SD error",       pf.prism_linegraph, p, error="sd",
         title="Line – SD error bars")
run_case("Line gridlines",      pf.prism_linegraph, p, gridlines=True,
         title="Line – gridlines")
os.unlink(p)

# ─────────────────────────────────────────────────────────────────────────────
# 3 ── Grouped Bar
# ─────────────────────────────────────────────────────────────────────────────
print("\n── Grouped Bar ──")
cats = ["CatA", "CatB", "CatC"]
subs = ["Male", "Female"]
gb_data = {c: {s: rng.normal(5 + i * 3 + j * 2, 1.0, 8).tolist()
               for j, s in enumerate(subs)}
           for i, c in enumerate(cats)}
with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f: p = f.name
write_grouped(p, cats, subs, gb_data)
run_case("Grouped Bar default", pf.prism_grouped_barplot, p,
         title="Grouped Bar – default")
run_case("Grouped + stats",     pf.prism_grouped_barplot, p,
         title="Grouped Bar + pairwise stats",
         show_stats=True, show_p_values=True)
run_case("Grouped ANOVA/grp",   pf.prism_grouped_barplot, p,
         title="Grouped Bar + ANOVA per group",
         show_anova_per_group=True)
run_case("Grouped log scale",   pf.prism_grouped_barplot, p,
         title="Grouped Bar – log Y", yscale="log")
os.unlink(p)

# ─────────────────────────────────────────────────────────────────────────────
# 4 ── Box Plot
# ─────────────────────────────────────────────────────────────────────────────
print("\n── Box Plot ──")
with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f: p = f.name
write_bar(p, {"Control": CTRL, "Drug A": DRUG, "Drug B": DRUGB})
run_case("Box default",         pf.prism_boxplot, p, title="Box – default")
run_case("Box + Tukey",         pf.prism_boxplot, p, title="Box + Tukey HSD",
         show_stats=True, posthoc="Tukey HSD", show_p_values=True)
run_case("Box nonparametric",   pf.prism_boxplot, p, title="Box – KW + Dunn's",
         show_stats=True, stats_test="nonparametric")
run_case("Box notch",           pf.prism_boxplot, p, title="Box – notched",
         notch=True)
run_case("Box log Y",           pf.prism_boxplot, p, title="Box – log Y",
         yscale="log")
os.unlink(p)

# ─────────────────────────────────────────────────────────────────────────────
# 5 ── Scatter Plot
# ─────────────────────────────────────────────────────────────────────────────
print("\n── Scatter ──")
scatter_series = {
    "Series 1": np.column_stack([X_VALS * 1.5 + rng.normal(0, 1, 7)]),
    "Series 2": np.column_stack([X_VALS * 2.5 + rng.normal(0, 1.5, 7)]),
}
with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f: p = f.name
write_line(p, X_VALS, scatter_series)
run_case("Scatter regression",  pf.prism_scatterplot, p,
         title="Scatter – regression + CI")
run_case("Scatter Spearman",    pf.prism_scatterplot, p,
         title="Scatter – Spearman ρ",
         correlation_type="spearman", show_regression=False)
run_case("Scatter pred band",   pf.prism_scatterplot, p,
         title="Scatter – prediction band",
         show_prediction_band=True)
os.unlink(p)

# ─────────────────────────────────────────────────────────────────────────────
# 6 ── Violin
# ─────────────────────────────────────────────────────────────────────────────
print("\n── Violin ──")
with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f: p = f.name
write_bar(p, {"Control": CTRL, "Drug A": DRUG, "Drug B": DRUGB})
run_case("Violin default",      pf.prism_violin, p, title="Violin – default")
run_case("Violin + Tukey",      pf.prism_violin, p, title="Violin + Tukey HSD",
         show_stats=True, posthoc="Tukey HSD", show_p_values=True)
run_case("Violin open points",  pf.prism_violin, p, title="Violin – open pts",
         open_points=True)
os.unlink(p)

# ─────────────────────────────────────────────────────────────────────────────
# 7 ── Kaplan-Meier
# ─────────────────────────────────────────────────────────────────────────────
print("\n── Kaplan-Meier ──")
km_data = {
    "Control":   {"time": [5,10,15,20,25,30,35,40,45,50],
                  "event":[1, 1, 0, 1, 1, 0, 1, 0, 1, 0]},
    "Treatment": {"time": [3, 8,12,18,22,28,32,38,42,48],
                  "event":[1, 1, 1, 0, 1, 1, 0, 1, 0, 1]},
}
with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f: p = f.name
write_km(p, km_data)
run_case("KM default",          pf.prism_kaplan_meier, p,
         title="Kaplan-Meier – default")
run_case("KM + log-rank",       pf.prism_kaplan_meier, p,
         title="KM – log-rank p-value",
         show_stats=True, show_p_values=True)
run_case("KM at-risk table",    pf.prism_kaplan_meier, p,
         title="KM – at-risk table",
         show_at_risk=True)
os.unlink(p)

# ─────────────────────────────────────────────────────────────────────────────
# 8 ── Heatmap
# ─────────────────────────────────────────────────────────────────────────────
print("\n── Heatmap ──")
hm_mat = rng.normal(0, 1, (8, 5))
with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f: p = f.name
write_heatmap(p, hm_mat, [f"Gene{i}" for i in range(8)],
              [f"S{i}" for i in range(5)])
run_case("Heatmap default",     pf.prism_heatmap, p, title="Heatmap – default")
run_case("Heatmap annotated",   pf.prism_heatmap, p, title="Heatmap – annotated",
         annotate=True)
run_case("Heatmap clustered",   pf.prism_heatmap, p,
         title="Heatmap – row+col cluster",
         cluster_rows=True, cluster_cols=True)
run_case("Heatmap RdBu_r",      pf.prism_heatmap, p, title="Heatmap – RdBu_r",
         color="RdBu_r", center=0)
os.unlink(p)

# ─────────────────────────────────────────────────────────────────────────────
# 9 ── Two-Way ANOVA
# ─────────────────────────────────────────────────────────────────────────────
print("\n── Two-Way ANOVA ──")
twa_recs = [(f, g, v)
            for f in ["Drug", "Control"]
            for g in ["Male", "Female"]
            for v in rng.normal(
                {"Drug_Male": 6, "Drug_Female": 7,
                 "Control_Male": 3, "Control_Female": 4}[f+"_"+g], 0.8, 8)]
with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f: p = f.name
write_two_way(p, twa_recs)
run_case("TwoWay default",      pf.prism_two_way_anova, p,
         title="Two-Way ANOVA – default")
run_case("TwoWay + stats",      pf.prism_two_way_anova, p,
         title="Two-Way ANOVA + posthoc",
         show_stats=True, show_posthoc=True, show_p_values=True)
run_case("TwoWay effect size",  pf.prism_two_way_anova, p,
         title="Two-Way ANOVA + η²",
         show_stats=True, show_effect_size=True)
os.unlink(p)

# ─────────────────────────────────────────────────────────────────────────────
# 10 ── Before / After
# ─────────────────────────────────────────────────────────────────────────────
print("\n── Before/After ──")
with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f: p = f.name
write_bar(p, {"Before": BEFORE, "After": AFTER})
run_case("Before/After default",   pf.prism_before_after, p,
         title="Before/After – default")
run_case("Before/After + stats",   pf.prism_before_after, p,
         title="Before/After – paired t-test",
         show_stats=True, show_p_values=True)
os.unlink(p)

# 3-condition repeated measures style
with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f: p = f.name
write_bar(p, {"Baseline": BEFORE, "Week 2": AFTER,
              "Week 4": AFTER + rng.normal(1, 0.5, 10)})
run_case("Before/After 3-cond",    pf.prism_before_after, p,
         title="Before/After – 3 conditions")
os.unlink(p)

# ─────────────────────────────────────────────────────────────────────────────
# 11 ── Histogram
# ─────────────────────────────────────────────────────────────────────────────
print("\n── Histogram ──")
with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f: p = f.name
write_bar(p, {"Control": rng.normal(10, 2, 50),
              "Drug A":  rng.normal(14, 2.5, 50)})
run_case("Histogram auto bins",    pf.prism_histogram, p,
         title="Histogram – auto bins")
run_case("Histogram density+norm", pf.prism_histogram, p,
         title="Histogram – density + normal curve",
         density=True, overlay_normal=True)
run_case("Histogram 20 bins",      pf.prism_histogram, p,
         title="Histogram – 20 bins", bins=20)
os.unlink(p)

# ─────────────────────────────────────────────────────────────────────────────
# 12 ── Subcolumn Scatter
# ─────────────────────────────────────────────────────────────────────────────
print("\n── Subcolumn ──")
with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f: p = f.name
write_bar(p, {"Control": CTRL, "Drug A": DRUG, "Drug B": DRUGB})
run_case("Subcolumn default",      pf.prism_subcolumn_scatter, p,
         title="Subcolumn – default")
run_case("Subcolumn + Tukey",      pf.prism_subcolumn_scatter, p,
         title="Subcolumn + Tukey HSD",
         show_stats=True, posthoc="Tukey HSD", show_p_values=True)
run_case("Subcolumn error=SD",     pf.prism_subcolumn_scatter, p,
         title="Subcolumn – SD error bars", error="sd")
os.unlink(p)

# ─────────────────────────────────────────────────────────────────────────────
# 13 ── Curve Fit  (all 11 models)
# ─────────────────────────────────────────────────────────────────────────────
print("\n── Curve Fit ──")
cf_series = {"Data": np.column_stack([CF_Y])}

def write_cf(path, x, y):
    rows = [["X", "Data"]] + [[xi, yi] for xi, yi in zip(x, y)]
    pd.DataFrame(rows).to_excel(path, index=False, header=False)

model_data = {
    "4PL Sigmoidal (EC50/IC50)":    (CF_X, CF_Y),
    "3PL Sigmoidal (no bottom)":    (CF_X, np.abs(CF_Y)),
    "One-phase exponential decay":   (np.linspace(0, 10, 12),
                                      50 * np.exp(-0.3 * np.linspace(0,10,12))
                                      + rng.normal(0, 2, 12)),
    "One-phase exponential growth":  (np.linspace(0, 8, 12),
                                      2 + (20 - 2) * (1 - np.exp(-0.4 * np.linspace(0,8,12)))
                                      + rng.normal(0, 0.8, 12)),
    "Two-phase exponential decay":   (np.linspace(0, 10, 12),
                                      50 * np.exp(-0.3 * np.linspace(0,10,12))
                                      + rng.normal(0, 2, 12)),
    "Michaelis-Menten":              (np.linspace(0.1, 20, 12),
                                      100 * np.linspace(0.1,20,12)
                                      / (5 + np.linspace(0.1,20,12))
                                      + rng.normal(0, 2, 12)),
    "Hill equation":                 (np.logspace(-1, 2, 12),
                                      80 * np.logspace(-1,2,12)**1.5
                                      / (10**1.5 + np.logspace(-1,2,12)**1.5)
                                      + rng.normal(0, 2, 12)),
    "Gaussian (bell curve)":         (np.linspace(-5, 5, 15),
                                      50 * np.exp(-0.5 * np.linspace(-5,5,15)**2)
                                      + rng.normal(0, 1, 15)),
    "Log-normal":                    (np.logspace(-1, 2, 12),
                                      30 * np.exp(-0.5*(np.log(np.logspace(-1,2,12))-1)**2)
                                      + rng.normal(0, 1, 12)),
    "Linear":                        (np.linspace(0, 10, 12),
                                      2.5 * np.linspace(0,10,12) + 3
                                      + rng.normal(0, 0.5, 12)),
    "Polynomial (2nd order)":        (np.linspace(-3, 3, 12),
                                      2 * np.linspace(-3,3,12)**2
                                      - 1.5 * np.linspace(-3,3,12) + 5
                                      + rng.normal(0, 0.5, 12)),
}

for model_name, (x_d, y_d) in model_data.items():
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f: p = f.name
    write_cf(p, x_d, y_d)
    # Use enough of the model name to avoid filename collisions
    short = model_name.replace("(", "").replace(")", "").replace(" ", "_")[:28]
    run_case(f"CurveFit {short}", pf.prism_curve_fit, p,
             model_name=model_name, title=f"Curve Fit – {short}",
             show_ci_band=True)
    os.unlink(p)

# Residuals panel
with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f: p = f.name
write_cf(p, CF_X, CF_Y)
run_case("CurveFit residuals",  pf.prism_curve_fit, p,
         model_name="4PL Sigmoidal (EC50/IC50)",
         show_residuals=True, title="4PL – residuals panel")
os.unlink(p)

# ─────────────────────────────────────────────────────────────────────────────
# 14 ── Column Statistics
# ─────────────────────────────────────────────────────────────────────────────
print("\n── Column Stats ──")
with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f: p = f.name
write_bar(p, {"Control": CTRL, "Drug A": DRUG, "Drug B": DRUGB})
run_case("ColStats all on",     pf.prism_column_stats, p,
         title="Column Stats – all flags on")
run_case("ColStats minimal",    pf.prism_column_stats, p,
         title="Column Stats – minimal",
         show_normality=False, show_ci=False, show_cv=False)
os.unlink(p)

# ─────────────────────────────────────────────────────────────────────────────
# 15 ── Contingency
# ─────────────────────────────────────────────────────────────────────────────
print("\n── Contingency ──")
with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f: p = f.name
write_contingency(p, ["Drug", "Control"], ["Survived", "Died"], [[45, 5], [20, 30]])
run_case("Contingency 2×2",     pf.prism_contingency, p,
         title="Contingency – 2×2 Fisher exact")
run_case("Contingency %+expect",pf.prism_contingency, p,
         title="Contingency – % + expected",
         show_percentages=True, show_expected=True)
os.unlink(p)

with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f: p = f.name
write_contingency(p, ["Young", "Middle", "Old"],
                  ["Recovered", "Not Recovered"],
                  [[45, 15], [30, 20], [20, 30]])
run_case("Contingency 3×2",     pf.prism_contingency, p,
         title="Contingency – 3×2 chi-square")
os.unlink(p)

# ─────────────────────────────────────────────────────────────────────────────
# 16 ── Repeated Measures
# ─────────────────────────────────────────────────────────────────────────────
print("\n── Repeated Measures ──")
with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f: p = f.name
write_bar(p, {"T0": T0, "T1": T1, "T2": T2, "T3": T3})
run_case("RM default",          pf.prism_repeated_measures, p,
         title="Repeated Measures – default")
run_case("RM parametric stats", pf.prism_repeated_measures, p,
         title="RM – RM-ANOVA / paired t-tests",
         show_stats=True, test_type="parametric", show_p_values=True)
run_case("RM nonparametric",    pf.prism_repeated_measures, p,
         title="RM – Friedman + Dunn's",
         show_stats=True, test_type="nonparametric")
run_case("RM no subject lines", pf.prism_repeated_measures, p,
         title="RM – no subject lines",
         show_subject_lines=False)
os.unlink(p)

# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
passed = [r for r in results if r[1] is not None]
failed = [r for r in results if r[1] is None]
print(f"\n{'─'*60}")
print(f"  Rendered: {len(passed)}   Failed: {len(failed)}   Total: {len(results)}")
if failed:
    print("\n  FAILURES:")
    for label, _, err in failed:
        print(f"    ✗  {label}\n       {err}")

# ─────────────────────────────────────────────────────────────────────────────
# Composite grid
# ─────────────────────────────────────────────────────────────────────────────
print("\nBuilding composite grid…")
COLS      = 5
THUMB_W   = 480
THUMB_H   = 480
PAD       = 12
LABEL_H   = 28
FONT_SIZE = 15

images = []
for label, path, err in results:
    if path:
        img = Image.open(path).convert("RGB")
        img = img.resize((THUMB_W, THUMB_H), Image.LANCZOS)
        images.append((label, img, True))
    else:
        # Red error placeholder
        img = Image.new("RGB", (THUMB_W, THUMB_H), (240, 220, 220))
        images.append((label, img, False))

ROWS       = (len(images) + COLS - 1) // COLS
grid_w     = COLS * (THUMB_W + PAD) + PAD
grid_h     = ROWS * (THUMB_H + LABEL_H + PAD) + PAD
grid       = Image.new("RGB", (grid_w, grid_h), (245, 245, 245))

try:
    from PIL import ImageDraw, ImageFont
    draw = ImageDraw.Draw(grid)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", FONT_SIZE)
    except Exception:
        font = ImageFont.load_default()
except Exception:
    draw = None; font = None

for idx, (label, img, ok) in enumerate(images):
    col = idx % COLS
    row = idx // COLS
    x   = PAD + col * (THUMB_W + PAD)
    y   = PAD + row * (THUMB_H + LABEL_H + PAD)
    grid.paste(img, (x, y))
    if draw:
        color = (30, 120, 30) if ok else (180, 30, 30)
        draw.text((x + 4, y + THUMB_H + 3), label[:38], fill=color, font=font)

grid_path = os.path.join(os.path.dirname(__file__), "visual_grid.png")
grid.save(grid_path, dpi=(150, 150))
print(f"  → {grid_path}  ({grid_w}×{grid_h} px)")
print(f"  → individual PNGs in {OUT_DIR}/")
