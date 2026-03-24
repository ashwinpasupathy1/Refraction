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
