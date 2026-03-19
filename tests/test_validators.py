"""
test_validators.py
==================
Tests for every validator in plotter_validators.py.

Covers: validate_flat_header, validate_line, validate_grouped_bar,
        validate_kaplan_meier, validate_heatmap, validate_two_way_anova,
        validate_contingency, validate_chi_square_gof, validate_bland_altman,
        validate_forest_plot, validate_pyramid.

Each validator is tested with both valid data (expect 0 errors) and
invalid data (expect errors). Minimum 24 tests.

Run:
  python3 tests/test_validators.py  (or via run_all.py)
"""

import sys, os
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import plotter_test_harness as _h
from plotter_test_harness import ok, fail, run, section, summarise

from plotter_validators import (
    validate_flat_header,
    validate_bar,
    validate_line,
    validate_grouped_bar,
    validate_kaplan_meier,
    validate_heatmap,
    validate_two_way_anova,
    validate_contingency,
    validate_chi_square_gof,
    validate_bland_altman,
    validate_forest_plot,
    validate_pyramid,
)


# ═══════════════════════════════════════════════════════════════════════════
# 1. validate_flat_header / validate_bar
# ═══════════════════════════════════════════════════════════════════════════
section("validate_flat_header / validate_bar")

def test_flat_header_valid():
    """Valid bar data: headers + numeric values → 0 errors."""
    df = pd.DataFrame([["Control", "Drug"],
                        [1.0, 4.0],
                        [2.0, 5.0],
                        [3.0, 6.0]])
    errors, warnings = validate_flat_header(df)
    assert len(errors) == 0, f"Expected 0 errors, got: {errors}"

run("validate_flat_header: valid data → 0 errors", test_flat_header_valid)

def test_flat_header_too_few_rows():
    """Only 1 row (header) → error."""
    df = pd.DataFrame([["A", "B"]])
    errors, warnings = validate_flat_header(df)
    assert len(errors) > 0, "Expected error for <2 rows"

run("validate_flat_header: 1 row → error", test_flat_header_too_few_rows)

def test_flat_header_empty_headers():
    """All headers empty → error."""
    df = pd.DataFrame([[None, None],
                        [1.0, 2.0],
                        [3.0, 4.0]])
    errors, warnings = validate_flat_header(df)
    assert len(errors) > 0, "Expected error for empty headers"

run("validate_flat_header: all headers empty → error", test_flat_header_empty_headers)

def test_flat_header_non_numeric_data():
    """Non-numeric values in data rows → error."""
    df = pd.DataFrame([["A", "B"],
                        [1.0, "abc"],
                        [2.0, 3.0]])
    errors, warnings = validate_flat_header(df)
    assert len(errors) > 0, "Expected error for non-numeric data"

run("validate_flat_header: non-numeric data → error", test_flat_header_non_numeric_data)

def test_validate_bar_alias():
    """validate_bar is a thin wrapper around validate_flat_header."""
    df = pd.DataFrame([["Control", "Drug"],
                        [1.0, 4.0],
                        [2.0, 5.0],
                        [3.0, 6.0]])
    errors, warnings = validate_bar(df)
    assert len(errors) == 0

run("validate_bar: valid data → 0 errors", test_validate_bar_alias)


# ═══════════════════════════════════════════════════════════════════════════
# 2. validate_line
# ═══════════════════════════════════════════════════════════════════════════
section("validate_line")

def test_line_valid():
    """Valid line data: X-label + series name row, numeric X and Y values."""
    df = pd.DataFrame([["X", "Series1"],
                        [1.0, 10.0],
                        [2.0, 20.0],
                        [3.0, 30.0]])
    errors, warnings = validate_line(df)
    assert len(errors) == 0, f"Expected 0 errors, got: {errors}"

run("validate_line: valid data → 0 errors", test_line_valid)

def test_line_too_few_columns():
    """Only 1 column → error (need X + at least 1 Y)."""
    df = pd.DataFrame([["X"], [1.0], [2.0]])
    errors, warnings = validate_line(df)
    assert len(errors) > 0, "Expected error for <2 columns"

run("validate_line: 1 column → error", test_line_too_few_columns)

def test_line_non_numeric_x():
    """Non-numeric X column → error."""
    df = pd.DataFrame([["X", "Y"],
                        ["a", 10.0],
                        ["b", 20.0]])
    errors, warnings = validate_line(df)
    assert len(errors) > 0, "Expected error for non-numeric X"

run("validate_line: non-numeric X → error", test_line_non_numeric_x)

def test_line_empty_series_names():
    """All series name cells empty → error."""
    df = pd.DataFrame([["X", None],
                        [1.0, 10.0],
                        [2.0, 20.0]])
    errors, warnings = validate_line(df)
    assert len(errors) > 0, "Expected error for empty series names"

run("validate_line: empty series names → error", test_line_empty_series_names)


# ═══════════════════════════════════════════════════════════════════════════
# 3. validate_grouped_bar
# ═══════════════════════════════════════════════════════════════════════════
section("validate_grouped_bar")

def test_grouped_bar_valid():
    """Valid grouped bar: row 0 = categories, row 1 = subgroups, row 2+ = data."""
    df = pd.DataFrame([["CatA", "CatA", "CatB", "CatB"],
                        ["Sub1", "Sub2", "Sub1", "Sub2"],
                        [1.0, 2.0, 3.0, 4.0],
                        [5.0, 6.0, 7.0, 8.0]])
    errors, warnings = validate_grouped_bar(df)
    assert len(errors) == 0, f"Expected 0 errors, got: {errors}"

run("validate_grouped_bar: valid data → 0 errors", test_grouped_bar_valid)

def test_grouped_bar_too_few_rows():
    """Only 2 rows → error (need 3: categories + subgroups + data)."""
    df = pd.DataFrame([["CatA", "CatB"],
                        ["Sub1", "Sub2"]])
    errors, warnings = validate_grouped_bar(df)
    assert len(errors) > 0, "Expected error for <3 rows"

run("validate_grouped_bar: 2 rows → error", test_grouped_bar_too_few_rows)

def test_grouped_bar_non_numeric_data():
    """Non-numeric values in data rows → error."""
    df = pd.DataFrame([["CatA", "CatA"],
                        ["Sub1", "Sub2"],
                        ["abc", 2.0]])
    errors, warnings = validate_grouped_bar(df)
    assert len(errors) > 0, "Expected error for non-numeric data"

run("validate_grouped_bar: non-numeric data → error", test_grouped_bar_non_numeric_data)


# ═══════════════════════════════════════════════════════════════════════════
# 4. validate_kaplan_meier
# ═══════════════════════════════════════════════════════════════════════════
section("validate_kaplan_meier")

def test_km_valid():
    """Valid KM: row 0 = groups, row 1 = Time/Event headers, row 2+ = data."""
    df = pd.DataFrame([["GroupA", "GroupA", "GroupB", "GroupB"],
                        ["Time", "Event", "Time", "Event"],
                        [1.0, 1.0, 2.0, 0.0],
                        [3.0, 0.0, 4.0, 1.0],
                        [5.0, 1.0, 6.0, 1.0]])
    errors, warnings = validate_kaplan_meier(df)
    assert len(errors) == 0, f"Expected 0 errors, got: {errors}"

run("validate_kaplan_meier: valid data → 0 errors", test_km_valid)

def test_km_too_few_rows():
    """Only 2 rows → error."""
    df = pd.DataFrame([["A", "A"], ["Time", "Event"]])
    errors, warnings = validate_kaplan_meier(df)
    assert len(errors) > 0, "Expected error for <3 rows"

run("validate_kaplan_meier: 2 rows → error", test_km_too_few_rows)

def test_km_non_numeric():
    """Non-numeric time/event values → error."""
    df = pd.DataFrame([["A", "A"],
                        ["Time", "Event"],
                        ["abc", 1.0]])
    errors, warnings = validate_kaplan_meier(df)
    assert len(errors) > 0, "Expected error for non-numeric data"

run("validate_kaplan_meier: non-numeric → error", test_km_non_numeric)


# ═══════════════════════════════════════════════════════════════════════════
# 5. validate_heatmap
# ═══════════════════════════════════════════════════════════════════════════
section("validate_heatmap")

def test_heatmap_valid():
    """Valid heatmap: top-left blank, row 0 = col labels, col 0 = row labels."""
    df = pd.DataFrame([["", "C1", "C2"],
                        ["R1", 1.0, 2.0],
                        ["R2", 3.0, 4.0]])
    errors, warnings = validate_heatmap(df)
    assert len(errors) == 0, f"Expected 0 errors, got: {errors}"

run("validate_heatmap: valid data → 0 errors", test_heatmap_valid)

def test_heatmap_non_numeric():
    """Non-numeric in data region → error."""
    df = pd.DataFrame([["", "C1", "C2"],
                        ["R1", "abc", 2.0],
                        ["R2", 3.0, 4.0]])
    errors, warnings = validate_heatmap(df)
    assert len(errors) > 0, "Expected error for non-numeric data"

run("validate_heatmap: non-numeric data → error", test_heatmap_non_numeric)


# ═══════════════════════════════════════════════════════════════════════════
# 6. validate_two_way_anova
# ═══════════════════════════════════════════════════════════════════════════
section("validate_two_way_anova")

def test_two_way_valid():
    """Valid two-way ANOVA: 3 cols (Factor_A, Factor_B, Value), >=2 levels each."""
    df = pd.DataFrame({
        "Factor_A": ["a1", "a1", "a2", "a2", "a1", "a1", "a2", "a2"],
        "Factor_B": ["b1", "b2", "b1", "b2", "b1", "b2", "b1", "b2"],
        "Value":    [1.0, 2.0, 3.0, 4.0, 1.5, 2.5, 3.5, 4.5],
    })
    errors, warnings = validate_two_way_anova(df)
    assert len(errors) == 0, f"Expected 0 errors, got: {errors}"

run("validate_two_way_anova: valid data → 0 errors", test_two_way_valid)

def test_two_way_too_few_columns():
    """Only 2 columns → error."""
    df = pd.DataFrame({"A": ["a1", "a2"], "B": [1.0, 2.0]})
    errors, warnings = validate_two_way_anova(df)
    assert len(errors) > 0, "Expected error for <3 columns"

run("validate_two_way_anova: 2 columns → error", test_two_way_too_few_columns)


# ═══════════════════════════════════════════════════════════════════════════
# 7. validate_contingency
# ═══════════════════════════════════════════════════════════════════════════
section("validate_contingency")

def test_contingency_valid():
    """Valid contingency: row 0 = outcomes, col 0 = groups, rest = counts."""
    df = pd.DataFrame([["", "Outcome1", "Outcome2"],
                        ["GroupA", 10, 20],
                        ["GroupB", 30, 40]])
    errors, warnings = validate_contingency(df)
    assert len(errors) == 0, f"Expected 0 errors, got: {errors}"

run("validate_contingency: valid data → 0 errors", test_contingency_valid)

def test_contingency_non_numeric():
    """Non-numeric count → error."""
    df = pd.DataFrame([["", "O1", "O2"],
                        ["G1", "abc", 20],
                        ["G2", 30, 40]])
    errors, warnings = validate_contingency(df)
    assert len(errors) > 0, "Expected error for non-numeric counts"

run("validate_contingency: non-numeric → error", test_contingency_non_numeric)

def test_contingency_too_few_rows():
    """Only 2 rows (header + 1 group) → error (need >=3)."""
    df = pd.DataFrame([["", "O1", "O2"],
                        ["G1", 10, 20]])
    errors, warnings = validate_contingency(df)
    assert len(errors) > 0, "Expected error for <3 rows"

run("validate_contingency: 2 rows → error", test_contingency_too_few_rows)


# ═══════════════════════════════════════════════════════════════════════════
# 8. validate_chi_square_gof
# ═══════════════════════════════════════════════════════════════════════════
section("validate_chi_square_gof")

def test_chi_gof_valid():
    """Valid chi-square GoF: row 0 = cats, row 1 = observed counts."""
    df = pd.DataFrame([["Cat1", "Cat2", "Cat3"],
                        [20, 30, 50]])
    errors, warnings = validate_chi_square_gof(df)
    assert len(errors) == 0, f"Expected 0 errors, got: {errors}"

run("validate_chi_square_gof: valid data → 0 errors", test_chi_gof_valid)

def test_chi_gof_non_numeric_observed():
    """Non-numeric observed counts → error."""
    df = pd.DataFrame([["Cat1", "Cat2"],
                        ["abc", 30]])
    errors, warnings = validate_chi_square_gof(df)
    assert len(errors) > 0, "Expected error for non-numeric observed"

run("validate_chi_square_gof: non-numeric observed → error", test_chi_gof_non_numeric_observed)

def test_chi_gof_negative_observed():
    """Negative observed counts → error."""
    df = pd.DataFrame([["Cat1", "Cat2"],
                        [-5, 30]])
    errors, warnings = validate_chi_square_gof(df)
    assert len(errors) > 0, "Expected error for negative observed counts"

run("validate_chi_square_gof: negative observed → error", test_chi_gof_negative_observed)

def test_chi_gof_with_expected():
    """Valid with expected row (row 2)."""
    df = pd.DataFrame([["Cat1", "Cat2", "Cat3"],
                        [20, 30, 50],
                        [33.3, 33.3, 33.4]])
    errors, warnings = validate_chi_square_gof(df)
    assert len(errors) == 0, f"Expected 0 errors, got: {errors}"

run("validate_chi_square_gof: valid with expected row → 0 errors", test_chi_gof_with_expected)


# ═══════════════════════════════════════════════════════════════════════════
# 9. validate_bland_altman
# ═══════════════════════════════════════════════════════════════════════════
section("validate_bland_altman")

def test_bland_altman_valid():
    """Valid Bland-Altman: 2 columns of paired numeric values."""
    df = pd.DataFrame([["Method A", "Method B"],
                        [1.0, 1.1],
                        [2.0, 2.3],
                        [3.0, 2.9],
                        [4.0, 4.2]])
    errors, warnings = validate_bland_altman(df)
    assert len(errors) == 0, f"Expected 0 errors, got: {errors}"

run("validate_bland_altman: valid data → 0 errors", test_bland_altman_valid)

def test_bland_altman_too_few_rows():
    """Only 2 rows (header + 1 data) → error (need ≥3 pairs)."""
    df = pd.DataFrame([["A", "B"],
                        [1.0, 2.0]])
    errors, warnings = validate_bland_altman(df)
    assert len(errors) > 0, "Expected error for too few data rows"

run("validate_bland_altman: 1 data row → error", test_bland_altman_too_few_rows)

def test_bland_altman_too_few_cols():
    """Only 1 column → error."""
    df = pd.DataFrame([["A"], [1.0], [2.0], [3.0]])
    errors, warnings = validate_bland_altman(df)
    assert len(errors) > 0, "Expected error for <2 columns"

run("validate_bland_altman: 1 column → error", test_bland_altman_too_few_cols)


# ═══════════════════════════════════════════════════════════════════════════
# 10. validate_forest_plot
# ═══════════════════════════════════════════════════════════════════════════
section("validate_forest_plot")

def test_forest_plot_valid():
    """Valid forest plot: header + ≥2 study rows, 4+ columns."""
    df = pd.DataFrame([["Study", "Effect", "CI_lo", "CI_hi"],
                        ["Study A", 0.5, 0.2, 0.8],
                        ["Study B", 1.0, 0.6, 1.4],
                        ["Study C", 0.8, 0.3, 1.3]])
    errors, warnings = validate_forest_plot(df)
    assert len(errors) == 0, f"Expected 0 errors, got: {errors}"

run("validate_forest_plot: valid data → 0 errors", test_forest_plot_valid)

def test_forest_plot_too_few_rows():
    """Only 2 rows (header + 1 study) → error."""
    df = pd.DataFrame([["Study", "Effect", "CI_lo", "CI_hi"],
                        ["A", 0.5, 0.2, 0.8]])
    errors, warnings = validate_forest_plot(df)
    assert len(errors) > 0, "Expected error for <3 rows"

run("validate_forest_plot: 2 rows → error", test_forest_plot_too_few_rows)

def test_forest_plot_too_few_cols():
    """Only 3 columns → error (need 4: Study, Effect, CI_lo, CI_hi)."""
    df = pd.DataFrame([["Study", "Effect", "CI_lo"],
                        ["A", 0.5, 0.2],
                        ["B", 1.0, 0.6]])
    errors, warnings = validate_forest_plot(df)
    assert len(errors) > 0, "Expected error for <4 columns"

run("validate_forest_plot: 3 columns → error", test_forest_plot_too_few_cols)


# ═══════════════════════════════════════════════════════════════════════════
# 11. validate_pyramid
# ═══════════════════════════════════════════════════════════════════════════
section("validate_pyramid")

def test_pyramid_valid():
    """Valid pyramid: 3 columns (Category, Left, Right)."""
    df = pd.DataFrame([["Age", "Male", "Female"],
                        ["0-9", 100, 95],
                        ["10-19", 120, 115],
                        ["20-29", 130, 125]])
    errors, warnings = validate_pyramid(df)
    assert len(errors) == 0, f"Expected 0 errors, got: {errors}"

run("validate_pyramid: valid data → 0 errors", test_pyramid_valid)

def test_pyramid_too_few_cols():
    """Only 2 columns → error."""
    df = pd.DataFrame([["Age", "Male"],
                        ["0-9", 100],
                        ["10-19", 120]])
    errors, warnings = validate_pyramid(df)
    assert len(errors) > 0, "Expected error for <3 columns"

run("validate_pyramid: 2 columns → error", test_pyramid_too_few_cols)

def test_pyramid_non_numeric():
    """All non-numeric in left/right series → error."""
    df = pd.DataFrame([["Age", "Male", "Female"],
                        ["0-9", "abc", "def"],
                        ["10-19", "ghi", "jkl"]])
    errors, warnings = validate_pyramid(df)
    assert len(errors) > 0, "Expected error for non-numeric data"

run("validate_pyramid: non-numeric data → error", test_pyramid_non_numeric)


# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
summarise()
sys.exit(0 if _h.FAIL == 0 else 1)
