# Statistics Test Plan

Hand-write these tests against known reference values from R or GraphPad Prism.
Each test should use a **fixed dataset** and assert **exact p-values** (to 4-6
decimal places), not just structural properties like bracket count.

## Files to create

- `tests/test_stats_core.py` — tests for `refraction/core/stats.py`
- `tests/test_stats_annotator.py` — tests for the annotator wrapper

---

## 1. Descriptive Statistics (`core/stats.py`)

Use a known dataset (e.g. [2, 4, 4, 4, 5, 5, 7, 9]):
- [ ] `calc_mean` → 5.0
- [ ] `calc_sd(ddof=1)` → 2.0
- [ ] `calc_sem` → SD/√n
- [ ] `calc_error("sem")`, `calc_error("sd")`, `calc_error("ci95")`
- [ ] `_calc_error_asymmetric` — verify lower/upper bars on log scale

## 2. Two-group parametric tests

Dataset: Group A = [1,2,3,4,5], Group B = [6,7,8,9,10].
Run in R: `t.test(A, B, var.equal=TRUE)` and `t.test(A, B, var.equal=FALSE)`.

- [ ] Unpaired t-test (`_run_stats` with `equal_var=True` path) — assert exact p
- [ ] Welch's t-test (`_run_stats` parametric, 2 groups) — assert exact p
- [ ] Verify t-test and Welch produce **different** p-values

## 3. ANOVA + Post-hoc (3+ groups)

Dataset: A=[1,2,3,4,5], B=[6,7,8,9,10], C=[3,4,5,6,7].
Run in R: `TukeyHSD(aov(val ~ group, data=df))`.

- [ ] One-way ANOVA omnibus F and p match `summary(aov(...))`
- [ ] Tukey HSD pairwise p-values match R's `TukeyHSD()` output
- [ ] Tukey p-values are **different** from plain pairwise t-test p-values
- [ ] Bonferroni post-hoc: p-values = raw_p × n_comparisons (capped at 1)
- [ ] Sidak post-hoc: p = 1 − (1 − raw_p)^m
- [ ] Fisher LSD: uncorrected pairwise Welch t-tests

## 4. Dunnett's test (vs control)

Dataset: Control=[5,6,7,8,9], Trt1=[10,11,12,13,14], Trt2=[6,7,8,9,10].
Run in R: `library(DescTools); DunnettTest(val ~ group, data=df, control="Control")`.

- [ ] p-values match R output (note: scipy uses Monte Carlo, so allow ±tolerance)
- [ ] Only control-vs-treatment pairs appear (not treatment-vs-treatment)

## 5. Non-parametric tests

Dataset: A=[1,3,5,7,9], B=[2,4,6,8,10].
Run in R: `wilcox.test(A, B)`.

- [ ] Mann-Whitney U p-value matches R
- [ ] Kruskal-Wallis omnibus p matches `kruskal.test()`
- [ ] Dunn's post-hoc p-values match R's `dunn.test()` with Holm correction

## 6. Paired tests

Dataset: Before=[120,130,125,140,135], After=[110,115,120,125,118].
Run in R: `t.test(Before, After, paired=TRUE)`.

- [ ] Paired t-test p matches R
- [ ] Unequal-length groups: verify warning and truncation behavior

## 7. Multiple comparison corrections

Use raw p-values: [0.001, 0.01, 0.03, 0.05, 0.20].
Compute by hand or in R: `p.adjust(p, method="holm")` etc.

- [ ] Holm-Bonferroni corrected values match R
- [ ] Bonferroni corrected values match R
- [ ] Benjamini-Hochberg (FDR) corrected values match R
- [ ] Correction preserves ordering

## 8. P-value → stars mapping

- [ ] p=0.0001 → "****"
- [ ] p=0.001 → "***"
- [ ] p=0.01 → "**"
- [ ] p=0.05 → "*"
- [ ] p=0.06 → "ns"
- [ ] Custom threshold (e.g. 0.01): p=0.03 → "ns"

## 9. Effect sizes

Dataset: A=[1,2,3,4,5], B=[6,7,8,9,10].
Compute by hand: Cohen's d = (mean_diff) / pooled_SD.

- [ ] `_cohens_d` matches hand calculation
- [ ] `_hedges_g` matches hand calculation (d × correction factor)
- [ ] `_rank_biserial_r` matches hand calculation
- [ ] `_effect_label` thresholds: <0.2=negligible, 0.2-0.5=small, 0.5-0.8=medium, ≥0.8=large

## 10. Normality testing

- [ ] `check_normality` on normal data (Shapiro p > 0.05)
- [ ] `check_normality` on skewed data (Shapiro p < 0.05)
- [ ] n < 3 returns (True, 1.0) — not enough data to test

## 11. Survival analysis

- [ ] `_km_curve` survival probabilities match R's `survfit()`
- [ ] `_logrank_test` p-value matches R's `survdiff()`
- [ ] Confidence intervals match Greenwood formula

## 12. Two-way ANOVA

Balanced 2×2 factorial design. Run in R: `summary(aov(Y ~ A * B, data=df))`.

- [ ] Main effect A: F and p match R
- [ ] Main effect B: F and p match R
- [ ] Interaction A×B: F and p match R
- [ ] Eta-squared values match R

## 13. The annotator wrapper (`stats_annotator.py`)

These test that the thin wrapper correctly routes to `_run_stats`:

- [ ] `build_stats_brackets("t-test", ...)` returns brackets with p from Welch path
- [ ] `build_stats_brackets("anova", "tukey", ...)` returns Tukey HSD p-values
- [ ] `build_stats_brackets("mann-whitney", ...)` returns Mann-Whitney p-values
- [ ] `build_stats_brackets("", ...)` returns empty list
- [ ] `build_stats_brackets("none", ...)` returns empty list
- [ ] Single group → empty list
- [ ] Bracket `stacking_order` values are sequential integers

## 14. Cross-test differentiation

The original bug: different tests returning identical results.

- [ ] t-test p ≠ Tukey HSD p (for same 3-group data)
- [ ] Mann-Whitney p ≠ t-test p (for same 2-group data)
- [ ] Paired t-test p ≠ unpaired t-test p (for same data)
- [ ] Holm-corrected p ≠ uncorrected p (for multiple comparisons)

---

## Reference datasets

Keep a `tests/reference_data/` folder with:
- CSV files of test datasets
- Expected results from R (copy-paste from R console)
- R scripts that reproduce the expected values

This way anyone can re-derive the expected values independently.
