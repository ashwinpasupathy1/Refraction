# Testing Guide

## Running tests

```bash
# Run the full test suite (4 suites)
python3 run_all.py

# Run a single suite
python3 run_all.py stats              # statistical verification + control logic
python3 run_all.py validators         # spreadsheet validators
python3 run_all.py specs              # Plotly spec builders + server (needs plotly)
python3 run_all.py api                # FastAPI endpoint tests

# Run multiple suites
python3 run_all.py stats validators
```

---

## Test suites

| Suite | Module | Tests | What it covers |
|---|---|---|---|
| stats | test_stats | 57 | Statistical verification + control-group logic |
| validators | test_validators | 35 | All spreadsheet validators |
| specs | test_phase3_plotly | 11+ | Plotly spec builders + FastAPI server |
| api | test_api | 18 | FastAPI endpoint tests (TestClient) |

Additional test files (not in run_all.py):
- `tests/test_png_render.py` -- 29 tests, one per chart type (matplotlib render)
- `tests/visual_test.py` -- manual visual regression tests

---

## Test harness patterns

```python
# All test files follow this pattern:
import plotter_test_harness as _h
from plotter_test_harness import pf, plt, ok, fail, run, section, summarise, bar_excel, with_excel

# Write a test:
def test_my_feature():
    with bar_excel({"Control": [1,2,3], "Drug": [4,5,6]}) as path:
        fig, ax = pf.plotter_barplot(path)
        assert ax.get_xlim()[0] < 0
        plt.close(fig)
run("plotter_barplot: x axis extends left of first bar", test_my_feature)

# Run standalone:
summarise()
sys.exit(0 if _h.FAIL == 0 else 1)
```

---

## Available test fixtures

| Fixture | What it creates |
|---|---|
| `bar_excel(data_dict)` | Simple group data: `{"Group1": [vals], "Group2": [vals]}` |
| `line_excel(data_dict)` | Line/scatter data with X column |
| `grouped_excel(data)` | Two-row-header grouped bar data |
| `km_excel(data)` | Kaplan-Meier survival data |
| `heatmap_excel(data)` | Heatmap matrix data |
| `two_way_excel(data)` | Two-way ANOVA long-format data |
| `contingency_excel(data)` | Contingency table data |
| `bland_altman_excel(data)` | Bland-Altman paired measurements |
| `forest_excel(data)` | Forest plot study data |
| `bubble_excel(data)` | Bubble chart data |
| `chi_gof_excel(data)` | Chi-square goodness-of-fit data |
| `with_excel(df)` | Generic: writes any DataFrame to a temp Excel file |

All fixtures are context managers that yield a temporary file path and clean up
after the `with` block exits.

---

## Writing new tests

1. Add a test function to the appropriate test module
2. Use the `run(label, fn)` helper to register and execute it
3. Use `ok(label)` / `fail(label, msg)` for pass/fail reporting
4. Always close matplotlib figures with `plt.close(fig)` to avoid memory leaks
5. Run `python3 run_all.py` to confirm 0 failures before committing

---

## CI notes

- Headless / CI environments need `xvfb-run python3 run_all.py` if any Tk
  modules are tested. The current test suites avoid Tk imports.
- The GitHub Actions CI workflow runs `python3 run_all.py` on every push and PR.
