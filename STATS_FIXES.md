# Stats Engine — Known Issues & Fix Plan

## Status: Needs hand-rewrite by Ashwin

The statistics layer has two files:
- `refraction/core/stats.py` — the actual math (`_run_stats()`)
- `refraction/analysis/stats_annotator.py` — thin wrapper that maps UI test names to `_run_stats()` args

The wrapper is fine. The math in `_run_stats()` has real problems.

---

## Issue 1: Welch's t-test vs Student's t-test — no distinction

**File**: `refraction/core/stats.py:329-335`

When `test_type == "parametric"` and there are 2 groups, the code always runs
`ttest_ind(..., equal_var=False)` (Welch's). There is no path for the classical
Student's t-test (`equal_var=True`). The UI offers both "Unpaired t-test" and
"Welch's t-test" but they produce identical results.

**Fix**: The `stats_annotator._resolve_test_type()` maps both to `"parametric"`.
Either add a separate test_type for Student's, or pass an `equal_var` flag through.

---

## Issue 2: No omnibus ANOVA test before post-hoc

**File**: `refraction/core/stats.py:317-375`

When there are 3+ groups with `test_type == "parametric"`, the code jumps directly
to post-hoc pairwise comparisons (Tukey HSD, Bonferroni, etc.) without first
running the omnibus F-test (`scipy.stats.f_oneway`). Prism runs the omnibus first
and only reports post-hoc if the omnibus is significant (or always, depending on
settings). The omnibus p-value and F-statistic are never reported.

**Fix**: Run `f_oneway()` first, include `omnibus_p` and `f_statistic` in results.
Optionally gate post-hoc on omnibus significance.

---

## Issue 3: No Welch's ANOVA

**File**: `refraction/core/stats.py` — missing entirely

The UI offers "Welch's ANOVA" but `_resolve_test_type()` maps it to `"parametric"`,
which runs regular Tukey HSD. Welch's ANOVA uses `scipy.stats.alexandergovern()`
(or the Welch F-test) and should use Games-Howell for post-hoc, not Tukey.

**Fix**: Add a `"welch_anova"` test_type path that calls `alexandergovern()` and
implements Games-Howell post-hoc.

---

## Issue 4: Games-Howell not implemented

**File**: `refraction/analysis/stats_annotator.py:98`

Games-Howell is mapped to `"Tukey HSD"` with a comment saying it's the "closest
approximation". It's not — Tukey HSD assumes equal variances, Games-Howell doesn't.
They can give very different p-values with heterogeneous variances.

**Fix**: Implement Games-Howell in `core/stats.py`. The algorithm:
1. Pairwise mean differences
2. SE = sqrt(var_i/n_i + var_j/n_j)  (uses per-group variances)
3. q = |mean_diff| / SE
4. Welch-Satterthwaite df for each pair
5. p from studentized range distribution with those df

---

## Issue 5: Tukey HSD implementation may be wrong

**File**: `refraction/core/stats.py:352-375`

The hand-rolled Tukey HSD uses pooled MS_within and `studentized_range.cdf()`.
Issues:
- SE formula: `sqrt((ms_within/2) * (1/n_a + 1/n_b))` — the `/2` is correct for
  equal n but this formula handles unequal n via the harmonic mean approximation.
  Need to verify against R's `TukeyHSD()` with unequal group sizes.
- MC correction logic: Tukey HSD already controls family-wise error rate, so
  applying Holm-Bonferroni on top is double-correction. The code skips correction
  for Holm and None but applies it for Bonferroni — inconsistent.

**Fix**: Validate against `R TukeyHSD()` output for:
- Equal n (3 groups × 10 obs)
- Unequal n (groups of 5, 10, 20)
- Groups with very different variances

---

## Issue 6: Dunn's test implementation — unverified

**File**: `refraction/core/stats.py:396-426`

The nonparametric path for 3+ groups runs Kruskal-Wallis then a hand-rolled
Dunn's test using rank differences and a z-approximation with tie correction.
This has never been validated against R's `dunn.test()` or `PMCMRplus::kwAllPairsDunnTest()`.

Specific concerns:
- Tie correction formula: `tc = 1 - sum(counts^3 - counts) / (N^3 - N)` — need
  to verify this is the right adjustment
- Z-statistic SE formula — multiple variants exist in the literature
- The Kruskal-Wallis omnibus p-value is computed but discarded (never returned)

**Fix**: Compare against R `dunn.test(method="holm")` for a known dataset.

---

## Issue 7: Dunnett's test — now uses scipy but untested

**File**: `refraction/core/stats.py:337-350`

This was recently fixed to use `scipy.stats.dunnett()` instead of faked pairwise
t-tests. However:
- Never validated against R `DescTools::DunnettTest()` or SAS output
- The control group defaults to `labels[0]` if not specified — Prism lets the user
  pick which group is control
- No omnibus test reported

**Fix**: Validate against R reference values. Ensure the control group selection
flows correctly from the UI.

---

## Issue 8: Permutation test — no seed, not reproducible

**File**: `refraction/core/stats.py:429-444`

The permutation test uses `scipy.stats.permutation_test()` with `n_resamples=9999`
but no random seed. Results will differ between runs for the same data.

**Fix**: Either set a seed for reproducibility or document that results are
approximate. Prism doesn't offer permutation tests so there's no reference to
validate against, but the scipy implementation is trustworthy — this is low priority.

---

## Issue 9: One-sample t-test applies MC correction unnecessarily

**File**: `refraction/core/stats.py:232-241`

When running one-sample t-tests across multiple groups, the code applies MC
correction to the p-values. This is correct if you're testing multiple groups
against the same μ₀, but the UI doesn't make it clear that correction is being
applied. Prism reports uncorrected p-values for one-sample tests.

**Fix**: Low priority. Consider making correction optional for one-sample.

---

## Issue 10: Missing effect sizes

The engine never computes:
- Eta-squared (η²) for ANOVA
- Partial eta-squared for multi-factor designs
- Cohen's d is available via `_cohens_d()` but never included in bracket output
- Rank-biserial correlation for Mann-Whitney
- W (Kendall's W) for Friedman test

Prism reports these alongside p-values. Low priority but would make the results
view much more useful.

---

## What's NOT broken

- **`_calc_error()`** — SEM, SD, CI95 calculations are standard and correct
- **`_apply_correction()`** — Holm-Bonferroni, Bonferroni, FDR corrections look
  correct (they use `statsmodels.stats.multitest.multipletests`)
- **`_p_to_stars()`** — Simple threshold mapping, works fine
- **`check_normality()`** — Shapiro-Wilk via scipy, correct
- **`_km_curve()`** — Kaplan-Meier uses lifelines, well-tested
- **`_twoway_anova()`** — Uses statsmodels OLS, standard approach
- **Mann-Whitney U** (2-group nonparametric) — Direct scipy call, correct
- **Paired t-test** (2-group) — Direct scipy call, correct
- **stats_annotator.py** — Pure name mapping, no math, works correctly

---

## Validation approach

For each test, create a small dataset, compute expected values in R, and
assert exact match (to 4 decimal places). See `STATS_TEST_PLAN.md` for the
full test matrix.

Priority order:
1. Unpaired t-test (Student's vs Welch's distinction)
2. One-way ANOVA + Tukey HSD (most common use case)
3. Welch's ANOVA + Games-Howell
4. Kruskal-Wallis + Dunn's
5. Dunnett's
6. Everything else
