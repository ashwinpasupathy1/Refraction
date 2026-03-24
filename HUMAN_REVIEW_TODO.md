# Human Review TODO — AI-Generated Code Audit

Findings from an audit of AI/vibe-coded logic. These need a human
with domain knowledge to verify correctness or decide on fixes.

---

## CRITICAL — May produce wrong results for users

### 1. Double multiple-comparisons correction on Tukey HSD
- **File:** `refraction/core/chart_helpers.py` ~line 288
- **Issue:** Tukey HSD already controls family-wise error rate via the
  studentized range distribution. The code then applies an *additional*
  Bonferroni or FDR correction on top when `mc_correction` is set.
- **Effect:** P-values become overly conservative. Users may miss real
  effects.
- **Human call:** Is this intentional (extra-conservative by design)?
  If not, Tukey results should bypass `_apply_correction()` entirely.

### 2. Chi-square warning checks observed counts, labels it "expected"
- **File:** `refraction/core/validators.py` ~line 438
- **Issue:** Code checks `obs_row < 5` but the warning message says
  "Some expected counts < 5". The chi-square validity rule is about
  *expected* counts, not observed.
- **Human call:** Change the check to expected counts, or fix the message.

### 3. Prism .pzfx OneWay import scrambles group data
- **File:** `refraction/io/import_pzfx.py` ~line 165
- **Issue:** Uses the value-within-subcolumn index `i` to look up the
  group name in `headers[]`. If groups have different lengths, data
  gets transposed across groups silently.
- **Human call:** Load a real .pzfx file with unequal group sizes and
  verify the imported DataFrame matches Prism's display.

### 4. Prism .pzfx survival import — group index never incremented
- **File:** `refraction/io/import_pzfx.py` ~line 217
- **Issue:** `gi` starts at 0 but is never incremented in the loop, so
  all survival groups get the first group's name.
- **Human call:** Import a multi-group Kaplan-Meier .pzfx and check
  that group names are distinct.

---

## HIGH — Subtle bugs, incorrect logging, lost state

### 5. `log_error()` captures wrong traceback
- **File:** `refraction/core/errors.py` ~line 42
- **Issue:** `traceback.format_exc()` returns the *current* exception
  context, not the `exc` argument. In nested exception handlers, the
  logged traceback may belong to a different exception.
- **Fix:** `traceback.format_exception(type(exc), exc, exc.__traceback__)`

### 6. Redo stack cleared on empty compound command
- **File:** `refraction/core/undo.py` ~line 76
- **Issue:** `end_compound()` clears `_redo` even when no commands were
  recorded during the compound block. User loses redo history for no reason.
- **Fix:** Only clear `_redo` inside the `if self._compound_acc:` branch.

---

## HIGH — Test suite gives false confidence

The test suite has 120+ tests and 0 failures, but many tests verify
*structure* (keys exist, lists are non-empty) rather than *correctness*
(values match ground truth). A function returning `p=0.5` for everything
would pass most statistical tests.

### 7. No scipy ground-truth comparison for most stat functions
- **Where:** `tests/test_stats.py`, `tests/test_api.py`
- **What's missing:** For each stat test (_run_stats with parametric,
  nonparametric, paired, etc.), compute the expected p-value independently
  using scipy and assert they match within documented tolerance.
- **Currently:** Welch t-test and Mann-Whitney have scipy comparisons.
  ANOVA posthoc, paired t-test, Kruskal-Wallis, permutation test,
  one-sample t-test, chi-square, log-rank, and two-way ANOVA do NOT.

### 8. API tests verify response shape, not numerical values
- **Where:** `tests/test_api.py`
- **What's missing:** After `POST /analyze`, tests check `data["ok"]`
  and `len(data["groups"])` but never verify that means, SEMs, error
  bars, or p-values are correct.
- **Ground truth approach:** Create a fixture with known data (e.g.,
  `[10, 20, 30]`), compute expected mean/sem/sd/ci95 with numpy/scipy,
  then assert the API response matches.

### 9. Validator tests check error counts, not error content
- **Where:** `tests/test_validators.py`
- **What's missing:** Tests assert `len(errors) == 0` or `> 0` but
  never check *which* error was raised or what the message says.
  A validator that rejects everything passes half the negative tests.
- **Fix:** Assert on error message substrings or error codes.

### 10. No end-to-end validator-to-analyzer round-trip tests
- **What's missing:** Nothing verifies that data passing validation
  actually produces correct analysis output. Validators and analyzers
  are tested in isolation.

### 11. `run_all.py` can't distinguish 0 failures from 0 tests found
- **Issue:** pytest exit code 5 (no tests collected) vs 0 (all passed)
  are not distinguished. If a test file fails to import, you get
  "0 failures" which looks like success.

---

## MEDIUM — Error handling gaps

### 12. Uncaught `os.remove()` in presets and session
- **Files:** `refraction/core/presets.py` ~line 164,
  `refraction/core/session.py` ~line 82
- **Issue:** `os.remove()` without try-except. Permission errors raise
  `OSError` instead of returning False / handling gracefully.

### 13. Orphaned default sheet in .cplot extraction
- **File:** `refraction/io/project.py` ~line 167
- **Issue:** If all sheet CSVs are missing from a .cplot file, the
  workbook ends up with an empty unnamed "Sheet" instead of a
  meaningful error.

### 14. Module-level logging init can crash on import
- **File:** `refraction/core/errors.py` ~line 18
- **Issue:** If both `RotatingFileHandler` and fallback `FileHandler`
  fail, import of `errors.py` crashes. Low probability but no fallback.

---

## CRITICAL — SwiftUI / UI-side issues

### 15. Race condition in PythonServer.stop()
- **File:** `RefractionApp/Refraction/Services/PythonServer.swift` ~line 167
- **Issue:** `stop()` sets `state = .idle` and `process = nil` on the main
  thread before the async dispatch queue actually kills the process. If
  `stop()` is called twice rapidly, the guard on `process` can pass in
  both calls.
- **Human call:** Test rapid window close / reopen cycles. Check for
  crashes or zombie Python processes.

### 16. .pzfx missing from DataTabView file picker
- **File:** `RefractionApp/Refraction/Views/Config/DataTabView.swift` ~line 148
- **Issue:** `allowedContentTypes` includes xlsx/xls/csv but NOT pzfx.
  WelcomeView advertises pzfx support. Users can load pzfx from welcome
  but not from the main config panel.
- **Human call:** Add `UTType(filenameExtension: "pzfx")!` to the
  allowed types, or remove pzfx from welcome screen advertising.

### 17. hasAutoRestarted flag never resets
- **File:** `RefractionApp/Refraction/Services/PythonServer.swift` ~line 35
- **Issue:** Once set to `true` after first crash recovery, auto-restart
  is permanently disabled for the session. Manual restart via alert
  doesn't reset the flag.
- **Human call:** Should the flag reset after a successful manual restart?

---

## HIGH — SwiftUI functional bugs

### 18. Y-range invalid when all values identical
- **File:** `RefractionApp/Refraction/Views/Chart/ChartCanvasView.swift` ~line 126
- **Issue:** `computeYRange()` returns `(min(lo, 0), hi + padding)`. When
  all values are the same, padding=0. If all values are negative and
  identical (e.g., all -5), range becomes `(-5, -5)` — zero-height chart.
- **Human call:** Test with uniform-value datasets and negative data.

### 19. Reference lines silently hidden outside data range
- **File:** `RefractionApp/Refraction/Views/Chart/ChartCanvasView.swift` ~line 92
- **Issue:** If a reference line's Y value is outside `computeYRange()`,
  the guard returns without drawing. The user's configuration is silently
  ignored with no feedback.
- **Human call:** Should the Y range expand to include reference lines?

### 20. hasFileLoaded true even after upload failure
- **File:** `RefractionApp/Refraction/App/AppState.swift` ~line 26
- **Issue:** `hasFileLoaded` checks `!excelPath.isEmpty`. If upload fails
  midway, excelPath may point to an invalid/partial path. Subsequent
  analyze calls fail with confusing errors.
- **Human call:** Track upload success separately from path existence.

### 21. Inverted Y-limits sent to backend without validation
- **File:** `RefractionApp/Refraction/Models/ChartConfig.swift` ~line 208
- **Issue:** User can enter yMin=10, yMax=5. The inverted range is sent
  to Python as `"ylim": [10, 5]` without validation. No UI feedback.
- **Human call:** Add `min < max` validation or swap automatically.

---

## MEDIUM — SwiftUI layout and UX issues

### 22. Fixed NavigationSplitView widths — minimum total 840px
- **File:** `RefractionApp/Refraction/Views/ContentView.swift` ~line 15
- **Issue:** Hardcoded min widths (180+400+260=840). May break on
  smaller external monitors or split-screen usage.

### 23. Hardcoded chart canvas insets
- **File:** `RefractionApp/Refraction/Views/Chart/ChartCanvasView.swift` ~line 12
- **Issue:** `plotInsets = EdgeInsets(top: 40, leading: 60, bottom: 50, trailing: 20)`
  assumes specific axis label widths. Long titles/labels get clipped.

### 24. Bracket stacking can overflow canvas top
- **File:** `RefractionApp/Refraction/Renderers/BracketRenderer.swift` ~line 45
- **Issue:** Many significance brackets (stacking_order > 3) move above
  the plot area with no clipping or overflow handling.

### 25. Hex color parsing silently returns black on invalid input
- **File:** `RefractionApp/Refraction/Renderers/AxisRenderer.swift` ~line 182
- **Issue:** `Color(hex:)` uses `Scanner.scanHexInt64` which returns 0
  on invalid strings like "#GGGGGG". Color silently becomes black.

### 26. stderr handler not cleared on process launch failure
- **File:** `RefractionApp/Refraction/Services/PythonServer.swift` ~line 113
- **Issue:** If `proc.run()` throws, the readability handler on the
  stderr pipe is never cleaned up.

### 27. Plotly JSON fallback uses first Y value as mean
- **File:** `RefractionApp/Refraction/Models/ChartSpec.swift` ~line 63
- **Issue:** Fallback path sets `mean = trace.y?.first` instead of
  computing the actual mean. If this path is ever hit, results are wrong.
- **Human call:** Is this fallback path reachable? If so, compute mean
  properly. If not, remove the dead code.

---

## Statistical Engine Deep Dive

Line-by-line audit of every statistical computation in
`refraction/core/chart_helpers.py`. Functions are listed with their
correctness status and specific items needing human verification.

### Verified correct (no action needed)

These implementations match standard formulas and scipy references:

| Function | Lines | Notes |
|---|---|---|
| `_cohens_d()` | 527-539 | Pooled SD formula, Bessel correction, edge cases all correct |
| `_hedges_g()` | 544-561 | J correction factor formula correct |
| `_rank_biserial_r()` | 566-585 | U1/U2 vectorized comparison correct |
| `_apply_correction()` Bonferroni | 161-162 | p × m capped at 1.0 |
| `_apply_correction()` Holm-Bonferroni | 164-172 | Step-down with running max, correct |
| `_apply_correction()` BH FDR | 174-183 | Step-up with running min, correct |
| `_km_curve()` Kaplan-Meier | 604-653 | Product-limit, Greenwood variance, log-log CI all correct |
| `_logrank_test()` | 657-688 | Mantel-Cox chi-square, hypergeometric E and Var correct |
| `_twoway_anova()` Type III SS | 696-794 | OLS residual approach, correct df and F-tests |
| `_run_stats()` Welch t-test | 247-253 | `ttest_ind(equal_var=False)` correct |
| `_run_stats()` Mann-Whitney | 318-322 | `mannwhitneyu(alternative="two-sided")` correct |
| `_run_stats()` Paired t-test | 226-244 | `ttest_rel()` with length truncation correct |
| `_run_stats()` Dunnett | 255-268 | `scipy.stats.dunnett()` correct, no extra correction |
| `_run_stats()` Permutation | 351-366 | `permutation_test()` correct |
| `_run_stats()` Kruskal-Wallis posthoc | 323-348 | Tie correction, pairwise z-test correct |
| `_twoway_posthoc()` | 798-838 | Stratified pairwise Welch t-tests correct |

### Needs human verification

#### 28. `_calc_error()` CI95 with n=1 resolves to 0 but by accident
- **File:** `chart_helpers.py` ~line 95-101
- **Issue:** When n=1, `s = 0.0` (ddof=1 makes std undefined, code
  returns 0). Then CI95 = `t.ppf(0.975, df=1) * 0.0 / 1.0 = 0.0`.
  The answer is accidentally correct (CI is meaningless for n=1) but
  the logic path is: undefined SD → 0 → 0 CI. A comment or explicit
  early return would make intent clear.
- **Human call:** Should n=1 return `(mean, NaN)` to signal "undefined"
  instead of `(mean, 0.0)` which looks like "zero uncertainty"?

#### 29. `_p_to_stars()` returns "*" for NaN p-values
- **File:** `chart_helpers.py` ~line 144
- **Issue:** `np.nan > 0.05` is `False`, so NaN falls through all
  thresholds and returns `"*"`. Should return `"NA"` or `"ns"`.
- **Human call:** Decide desired behavior. Add `if np.isnan(p): return "ns"`.

#### 30. `_run_stats()` one-sample t-test crashes on n<2
- **File:** `chart_helpers.py` ~line 214
- **Issue:** `stats.ttest_1samp()` requires n≥2. If a group has 1 value,
  scipy raises `ValueError`. Not caught by any try-except.
- **Human call:** Add `if len(groups[g]) < 2: continue` guard,
  or catch ValueError and append (group, "μ₀", 1.0, "ns").

#### 31. "Bonferroni" posthoc + mc_correction creates double-correction ambiguity
- **File:** `chart_helpers.py` ~line 312
- **Issue:** When `posthoc="Bonferroni"` and `mc_correction="Bonferroni"`,
  the code applies Bonferroni once (correct). But if
  `mc_correction="Holm-Bonferroni"`, it applies Holm-Bonferroni instead
  of classical Bonferroni. The posthoc name is misleading.
- **Human call:** Should posthoc="Bonferroni" always use Bonferroni
  regardless of mc_correction? Or should the UI prevent this combination?

#### 32. ANOVA gate (p≥0.05 → empty results) is a design choice, not a bug
- **File:** `chart_helpers.py` ~lines 272, 325
- **Issue:** Both Tukey HSD and Kruskal-Wallis posthoc return `[]` if the
  omnibus test is not significant at α=0.05. This matches GraphPad Prism
  behavior but is not universally standard — some statisticians argue
  posthoc tests should be run regardless.
- **Human call:** Is this the intended behavior? Should it be configurable?
  The hardcoded 0.05 threshold is not exposed to users.

#### 33. NaN propagation in `_calc_error()` — no filtering
- **File:** `chart_helpers.py` ~line 91
- **Issue:** If `vals` contains NaN, `np.mean()` and `np.std()` propagate
  NaN silently. The function returns `(NaN, NaN)` without warning.
- **Human call:** Should NaN values be filtered with `vals = vals[~np.isnan(vals)]`
  before computation (like `check_normality()` does), or should the caller
  be responsible?

#### 34. `_calc_error_asymmetric()` silent exception fallback
- **File:** `chart_helpers.py` ~line 128
- **Issue:** Any math error in the log-transform path (e.g., log10 of
  negative after floating-point drift) silently falls back to symmetric
  error bars. No logging or warning.
- **Human call:** Add logging so users know when asymmetric bars were
  requested but symmetric were returned.

### Test gaps for the statistical engine

These functions have NO oracle-level (tier 1) tests comparing against
an independent implementation:

| Function | What to test against |
|---|---|
| Tukey HSD p-values | `statsmodels.stats.multicomp.pairwise_tukeyhsd` |
| Paired t-test | `scipy.stats.ttest_rel` (exists for k=2, missing for k>2 with correction) |
| One-sample t-test | `scipy.stats.ttest_1samp` |
| Kruskal-Wallis posthoc z-test | Manual rank computation + scipy normal CDF |
| Permutation test | Known-seed deterministic comparison |
| Chi-square GoF | `scipy.stats.chisquare` |
| Log-rank test | `lifelines.statistics.logrank_test` |
| Two-way ANOVA | `statsmodels.formula.api.ols` + `statsmodels.stats.anova.anova_lm(type=3)` |
| Kaplan-Meier curve | `lifelines.KaplanMeierFitter` |
| `_calc_error` SEM | `scipy.stats.sem` |
| `_calc_error` CI95 | `scipy.stats.t.interval` |

---

## Recommended Ground-Truth Test Structure

For each statistical function, add tests in this pattern:

```python
class TestTukeyGroundTruth:
    """Compare our Tukey HSD against scipy's pairwise_tukeyhsd."""

    # Tier 1: Oracle — compute independently with scipy
    def test_three_groups_vs_scipy(self):
        from scipy.stats import f_oneway
        from statsmodels.stats.multicomp import pairwise_tukeyhsd
        data = {"A": G_A, "B": G_B, "C": G_C}
        ours = _run_stats(data, "parametric", posthoc="Tukey HSD",
                          mc_correction="None (uncorrected)")
        # Build statsmodels comparison
        all_vals = np.concatenate([G_A, G_B, G_C])
        labels = (["A"]*len(G_A) + ["B"]*len(G_B) + ["C"]*len(G_C))
        ref = pairwise_tukeyhsd(all_vals, labels, alpha=0.05)
        for (a, b, p_ours, _) in ours:
            p_ref = _lookup_pair(ref, a, b)  # helper to find pair
            assert abs(p_ours - p_ref) < 1e-6, (
                f"Tukey {a}-{b}: ours={p_ours}, statsmodels={p_ref}"
            )

    # Tier 2: Known-answer from textbook
    def test_textbook_example(self):
        """Montgomery (2012) Example 3-1, Table 3-2."""
        # Data and expected p-values from published source
        ...

    # Tier 3: Invariants (already covered by existing tests)
    def test_pvalues_in_valid_range(self):
        ...
    def test_symmetric_pairs(self):
        ...
```

Apply this 3-tier pattern to:
- [ ] Welch t-test (tier 1 exists, add tier 2)
- [ ] Mann-Whitney U (tier 1 exists, add tier 2)
- [ ] ANOVA + Tukey HSD (needs all 3 tiers)
- [ ] Paired t-test (needs all 3 tiers)
- [ ] Kruskal-Wallis (needs all 3 tiers)
- [ ] Permutation test (needs tier 1 + invariants)
- [ ] One-sample t-test (needs tier 1)
- [ ] Chi-square test (needs tier 1 + tier 2)
- [ ] Log-rank test (needs tier 1 + tier 2)
- [ ] Two-way ANOVA (needs tier 1 + tier 2)
- [ ] `_calc_error` SEM/SD/CI95 (needs tier 1)
- [ ] `_apply_correction` Bonferroni/Holm/FDR (needs tier 1 + tier 2)

For the API layer, add:
- [ ] Known-data endpoint test: fixed input -> verify all output values
- [ ] Error bar correctness: SEM = scipy.stats.sem(), SD = np.std(ddof=1)
- [ ] Comparison p-values match the unit-tested stat functions

For validators, add:
- [ ] Assert on error message content, not just count
- [ ] Round-trip: valid data -> validate -> analyze -> check output
- [ ] Round-trip: invalid data -> validate -> confirm rejection reason
