---
name: review-pr
description: Review a pull request against Claude Prism's conventions and quality bar
---

You are reviewing a pull request for Claude Prism. Use `gh pr view` and `gh pr diff` to read it, then evaluate it against the project's standards.

## How to read the PR

```bash
gh pr view <number>          # title, description, author
gh pr diff <number>          # full diff
gh pr checks <number>        # CI status if available
```

If no PR number is provided, use `gh pr list` to show open PRs and ask the user which to review.

## What to check

### Tests
- [ ] `python3 run_all.py` passes with 0 failures (count must be ≥ 571 or higher than before the PR)
- [ ] New chart types have tests in `test_comprehensive.py`: render test, visual property test, validator tests
- [ ] No tests were deleted or weakened to make the suite pass

### New chart types (if applicable)
- [ ] All 5 steps of the checklist are complete (function → registry → UI → validator → tests)
- [ ] `_ensure_imports()` is first in the chart function
- [ ] `_style_kwargs(locals())` is called immediately after `_base_plot_setup()`
- [ ] `**_sk` is passed to both `_apply_prism_style` and `_base_plot_finish`
- [ ] Function returns `fig, ax`
- [ ] `PlotTypeConfig` entry has correct `tab_mode` and `stats_tab`

### Code quality
- [ ] No module-level matplotlib/seaborn imports
- [ ] No new globals or mutable module-level state
- [ ] Shared style params are not reimplemented — they use `_style_kwargs` / `PLOT_PARAM_DEFAULTS`
- [ ] No backwards-compatibility shims for removed code

### Commit messages
- [ ] Follow the format: `type: short description` (feat / fix / test / refactor / docs)
- [ ] No "wip" or "temp" commits in the final branch

## Output

Give a concise verdict: **Approve**, **Request changes**, or **Needs discussion**. List specific line references for any issues found. Keep feedback actionable.
