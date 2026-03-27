# Ashwin's Manual TODO

## Statistics Engine — Full Rewrite Needed

The stats layer (`refraction/analysis/stats_annotator.py` and `refraction/core/stats.py`)
needs hand-written, hand-validated statistical implementations. Claude wrote the plumbing
but the actual math needs to be verified against known reference values (R, GraphPad, etc.).

### What needs validation / rewriting:

- [ ] Unpaired t-test (Student's, equal variance)
- [ ] Welch's t-test (unequal variance)
- [ ] One-way ANOVA + Tukey HSD post-hoc
- [ ] Welch's ANOVA + Games-Howell post-hoc
- [ ] Paired t-test
- [ ] Mann-Whitney U
- [ ] Kruskal-Wallis + Dunn's post-hoc
- [ ] Dunnett's test (vs control) — currently uses scipy Monte Carlo, results are stochastic
- [ ] Multiple comparison corrections (Holm, Bonferroni, FDR)
- [ ] Two-way ANOVA
- [ ] Repeated measures ANOVA
- [ ] Chi-square goodness of fit
- [ ] Fisher's exact test (contingency)

### Why:

1. `stats_annotator.py` had ANOVA doing plain pairwise t-tests instead of Tukey HSD
2. Welch's ANOVA was missing entirely
3. Post-hoc method selection was ignored (all paths did the same thing)
4. Dunnett used `ttest_ind` instead of proper multivariate t
5. Test suite only checked bracket count/ordering, not p-value correctness
6. Two parallel stats implementations exist (`core/stats.py` vs `stats_annotator.py`)
   — the tested one was correct, the one actually called by analyzers was broken

### Reference for validation:

Compare against GraphPad Prism or R output with identical sample data.
