"""
test_validators.py
==================
Tests for every validator in refraction.core.validators.

For each validator:
1. Valid data -> 0 errors
2. Each specific error condition -> verify error message text
3. Boundary cases (minimum valid data)

No UI, no API, no Tk, no Plotly required.
"""

import pandas as pd
import pytest

from refraction.core.validators import (
    validate_bar,
    validate_bland_altman,
    validate_chi_square_gof,
    validate_contingency,
    validate_flat_header,
    validate_forest_plot,
    validate_grouped_bar,
    validate_heatmap,
    validate_kaplan_meier,
    validate_line,
    validate_pyramid,
    validate_two_way_anova,
)


# ============================================================================
# validate_flat_header / validate_bar
# ============================================================================

class TestValidateFlatHeader:
    """Tests for validate_flat_header (and its alias validate_bar)."""

    def test_valid_data_zero_errors(self):
        """Standard valid layout: 2+ groups, 3+ data rows."""
        df = pd.DataFrame([
            ["Control", "Drug"],
            [1.0, 4.0],
            [2.0, 5.0],
            [3.0, 6.0],
        ])
        errors, warnings = validate_flat_header(df)
        assert errors == []

    def test_single_row_errors_with_message(self):
        """Only header row (< 2 rows total) -> error mentioning 'fewer than 2 rows'."""
        df = pd.DataFrame([["A", "B"]])
        errors, warnings = validate_flat_header(df)
        assert len(errors) == 1
        assert "fewer than 2 rows" in errors[0].lower()

    def test_all_headers_empty_errors_with_message(self):
        """All headers NaN -> error mentioning 'entirely empty'."""
        df = pd.DataFrame([
            [None, None],
            [1.0, 2.0],
            [3.0, 4.0],
        ])
        errors, warnings = validate_flat_header(df)
        assert any("entirely empty" in e.lower() for e in errors)

    def test_non_numeric_data_errors_with_message(self):
        """Non-numeric values in data rows -> error mentioning 'non-numeric'."""
        df = pd.DataFrame([
            ["A", "B"],
            [1.0, "abc"],
            [2.0, 3.0],
        ])
        errors, warnings = validate_flat_header(df)
        assert any("non-numeric" in e.lower() for e in errors)

    def test_minimum_valid_data_two_rows(self):
        """Exactly 2 rows (1 header + 1 data) -> 0 errors, but may warn about few rows."""
        df = pd.DataFrame([
            ["A", "B"],
            [1.0, 2.0],
        ])
        errors, warnings = validate_flat_header(df)
        assert errors == []  # valid, though warnings about too few rows are ok

    def test_single_column_warns(self):
        """Single column -> warning about min_groups."""
        df = pd.DataFrame([
            ["A"],
            [1.0],
            [2.0],
            [3.0],
        ])
        errors, warnings = validate_flat_header(df)
        assert errors == []
        assert any("1 group" in w.lower() or "1 column" in w.lower() for w in warnings)

    def test_identical_values_warns(self):
        """All identical values -> warning about zero standard deviation."""
        df = pd.DataFrame([
            ["A", "B"],
            [5.0, 1.0],
            [5.0, 2.0],
            [5.0, 3.0],
        ])
        errors, warnings = validate_flat_header(df)
        assert errors == []
        assert any("identical" in w.lower() or "zero" in w.lower() for w in warnings)

    def test_validate_bar_is_alias(self):
        """validate_bar delegates to validate_flat_header with same results."""
        df = pd.DataFrame([
            ["Control", "Drug"],
            [1.0, 4.0],
            [2.0, 5.0],
            [3.0, 6.0],
        ])
        errors_bar, warnings_bar = validate_bar(df)
        errors_flat, warnings_flat = validate_flat_header(df)
        assert errors_bar == errors_flat


# ============================================================================
# validate_line
# ============================================================================

class TestValidateLine:
    """Tests for validate_line (XY data: col 0 = X, cols 1+ = Y series)."""

    def test_valid_data_zero_errors(self):
        """Standard valid layout: X + Y columns, numeric data."""
        df = pd.DataFrame([
            ["X", "Series1"],
            [1.0, 10.0],
            [2.0, 20.0],
            [3.0, 30.0],
        ])
        errors, warnings = validate_line(df)
        assert errors == []

    def test_single_column_errors_with_message(self):
        """Only 1 column -> error mentioning 'at least 2 columns'."""
        df = pd.DataFrame([["X"], [1.0], [2.0]])
        errors, warnings = validate_line(df)
        assert len(errors) >= 1
        assert any("2 columns" in e for e in errors)

    def test_non_numeric_x_errors_with_message(self):
        """Non-numeric X column -> error mentioning 'numeric X'."""
        df = pd.DataFrame([
            ["X", "Y"],
            ["a", 10.0],
            ["b", 20.0],
        ])
        errors, warnings = validate_line(df)
        assert any("numeric x" in e.lower() or "column 1" in e.lower() for e in errors)

    def test_all_series_names_empty_errors(self):
        """All series name cells empty -> error mentioning 'series names'."""
        df = pd.DataFrame([
            ["X", None],
            [1.0, 10.0],
            [2.0, 20.0],
        ])
        errors, warnings = validate_line(df)
        assert any("series name" in e.lower() for e in errors)

    def test_minimum_valid_two_rows(self):
        """Exactly 2 rows (header + 1 data point) -> valid but may warn about few data."""
        df = pd.DataFrame([
            ["X", "Y"],
            [1.0, 10.0],
        ])
        errors, warnings = validate_line(df)
        assert errors == []


# ============================================================================
# validate_grouped_bar
# ============================================================================

class TestValidateGroupedBar:
    """Tests for validate_grouped_bar (row 0 = categories, row 1 = subgroups)."""

    def test_valid_data_zero_errors(self):
        """Standard valid grouped layout."""
        df = pd.DataFrame([
            ["CatA", "CatA", "CatB", "CatB"],
            ["Sub1", "Sub2", "Sub1", "Sub2"],
            [1.0, 2.0, 3.0, 4.0],
            [5.0, 6.0, 7.0, 8.0],
        ])
        errors, warnings = validate_grouped_bar(df)
        assert errors == []

    def test_too_few_rows_errors_with_message(self):
        """Only 2 rows -> error mentioning 'at least 3 rows'."""
        df = pd.DataFrame([
            ["CatA", "CatB"],
            ["Sub1", "Sub2"],
        ])
        errors, warnings = validate_grouped_bar(df)
        assert len(errors) >= 1
        assert any("3 rows" in e for e in errors)

    def test_non_numeric_data_errors(self):
        """Non-numeric data in rows 3+ -> error mentioning 'non-numeric'."""
        df = pd.DataFrame([
            ["CatA", "CatA"],
            ["Sub1", "Sub2"],
            ["abc", 2.0],
        ])
        errors, warnings = validate_grouped_bar(df)
        assert any("non-numeric" in e.lower() for e in errors)

    def test_minimum_valid_three_rows(self):
        """Exactly 3 rows (2 headers + 1 data) -> valid."""
        df = pd.DataFrame([
            ["CatA", "CatA"],
            ["Sub1", "Sub2"],
            [1.0, 2.0],
        ])
        errors, warnings = validate_grouped_bar(df)
        assert errors == []

    def test_single_column_errors(self):
        """Only 1 column -> error mentioning columns."""
        df = pd.DataFrame([["Cat"], ["Sub"], [1.0]])
        errors, warnings = validate_grouped_bar(df)
        assert len(errors) >= 1


# ============================================================================
# validate_kaplan_meier
# ============================================================================

class TestValidateKaplanMeier:
    """Tests for validate_kaplan_meier."""

    def test_valid_data_zero_errors(self):
        """Standard valid KM layout."""
        df = pd.DataFrame([
            ["GroupA", "GroupA", "GroupB", "GroupB"],
            ["Time", "Event", "Time", "Event"],
            [1.0, 1.0, 2.0, 0.0],
            [3.0, 0.0, 4.0, 1.0],
            [5.0, 1.0, 6.0, 1.0],
        ])
        errors, warnings = validate_kaplan_meier(df)
        assert errors == []

    def test_too_few_rows_errors(self):
        """Only 2 rows -> error mentioning 'at least 3 rows'."""
        df = pd.DataFrame([
            ["A", "A"],
            ["Time", "Event"],
        ])
        errors, warnings = validate_kaplan_meier(df)
        assert len(errors) >= 1
        assert any("3 rows" in e for e in errors)

    def test_non_numeric_time_event_errors(self):
        """Non-numeric time/event values -> error mentioning 'non-numeric'."""
        df = pd.DataFrame([
            ["A", "A"],
            ["Time", "Event"],
            ["abc", 1.0],
        ])
        errors, warnings = validate_kaplan_meier(df)
        assert any("non-numeric" in e.lower() for e in errors)

    def test_odd_columns_warns(self):
        """Odd number of columns -> warning about column pairing."""
        df = pd.DataFrame([
            ["A", "A", "B"],
            ["Time", "Event", "Time"],
            [1.0, 1.0, 2.0],
            [3.0, 0.0, 4.0],
        ])
        errors, warnings = validate_kaplan_meier(df)
        assert any("odd" in w.lower() or "pairing" in w.lower() for w in warnings)


# ============================================================================
# validate_heatmap
# ============================================================================

class TestValidateHeatmap:
    """Tests for validate_heatmap."""

    def test_valid_data_zero_errors(self):
        """Standard valid heatmap layout."""
        df = pd.DataFrame([
            ["", "C1", "C2"],
            ["R1", 1.0, 2.0],
            ["R2", 3.0, 4.0],
        ])
        errors, warnings = validate_heatmap(df)
        assert errors == []

    def test_non_numeric_data_region_errors(self):
        """Non-numeric in data region -> error mentioning 'non-numeric'."""
        df = pd.DataFrame([
            ["", "C1", "C2"],
            ["R1", "abc", 2.0],
            ["R2", 3.0, 4.0],
        ])
        errors, warnings = validate_heatmap(df)
        assert any("non-numeric" in e.lower() for e in errors)

    def test_minimum_valid_two_by_two(self):
        """Minimum valid: 2 rows, 2 cols."""
        df = pd.DataFrame([
            ["", "C1"],
            ["R1", 1.0],
        ])
        errors, warnings = validate_heatmap(df)
        assert errors == []

    def test_single_row_errors(self):
        """Only 1 row -> error."""
        df = pd.DataFrame([["", "C1", "C2"]])
        errors, warnings = validate_heatmap(df)
        assert len(errors) >= 1


# ============================================================================
# validate_two_way_anova
# ============================================================================

class TestValidateTwoWayAnova:
    """Tests for validate_two_way_anova (long-format: Factor_A, Factor_B, Value)."""

    def test_valid_data_zero_errors(self):
        """Standard valid 2x2 design with 2 reps per cell."""
        df = pd.DataFrame({
            "Factor_A": ["a1", "a1", "a2", "a2", "a1", "a1", "a2", "a2"],
            "Factor_B": ["b1", "b2", "b1", "b2", "b1", "b2", "b1", "b2"],
            "Value": [1.0, 2.0, 3.0, 4.0, 1.5, 2.5, 3.5, 4.5],
        })
        errors, warnings = validate_two_way_anova(df)
        assert errors == []

    def test_too_few_columns_errors(self):
        """Only 2 columns -> error mentioning '3 columns'."""
        df = pd.DataFrame({"A": ["a1", "a2"], "B": [1.0, 2.0]})
        errors, warnings = validate_two_way_anova(df)
        assert any("3 columns" in e for e in errors)

    def test_single_level_errors(self):
        """One factor with only 1 level -> error mentioning 'at least 2'."""
        df = pd.DataFrame({
            "Factor_A": ["a1", "a1", "a1", "a1"],
            "Factor_B": ["b1", "b2", "b1", "b2"],
            "Value": [1.0, 2.0, 3.0, 4.0],
        })
        errors, warnings = validate_two_way_anova(df)
        assert any("1 level" in e for e in errors)

    def test_missing_cell_errors(self):
        """Missing factor combination -> error mentioning 'missing cell'.
        Need >= 4 observations to pass the early size check, so we add
        enough data but leave one cell (a2/b2) empty."""
        df = pd.DataFrame({
            "Factor_A": ["a1", "a1", "a2", "a2", "a1"],
            "Factor_B": ["b1", "b2", "b1", "b1", "b2"],
            "Value": [1.0, 2.0, 3.0, 3.5, 2.5],
        })
        errors, warnings = validate_two_way_anova(df)
        # Should error about missing cell a2/b2
        assert any("missing" in e.lower() for e in errors)


# ============================================================================
# validate_contingency
# ============================================================================

class TestValidateContingency:
    """Tests for validate_contingency."""

    def test_valid_data_zero_errors(self):
        """Standard valid contingency table."""
        df = pd.DataFrame([
            ["", "Outcome1", "Outcome2"],
            ["GroupA", 10, 20],
            ["GroupB", 30, 40],
        ])
        errors, warnings = validate_contingency(df)
        assert errors == []

    def test_non_numeric_counts_errors(self):
        """Non-numeric count -> error mentioning 'numeric counts'."""
        df = pd.DataFrame([
            ["", "O1", "O2"],
            ["G1", "abc", 20],
            ["G2", 30, 40],
        ])
        errors, warnings = validate_contingency(df)
        assert any("numeric" in e.lower() for e in errors)

    def test_too_few_rows_errors(self):
        """Only 2 rows (header + 1 group) -> error."""
        df = pd.DataFrame([
            ["", "O1", "O2"],
            ["G1", 10, 20],
        ])
        errors, warnings = validate_contingency(df)
        assert len(errors) >= 1

    def test_too_few_columns_errors(self):
        """Only 2 columns (label + 1 outcome) -> error mentioning 'outcome columns'."""
        df = pd.DataFrame([
            ["", "O1"],
            ["G1", 10],
            ["G2", 30],
        ])
        errors, warnings = validate_contingency(df)
        assert any("outcome" in e.lower() for e in errors)

    def test_negative_counts_warns(self):
        """Negative counts -> warning."""
        df = pd.DataFrame([
            ["", "O1", "O2"],
            ["G1", -5, 20],
            ["G2", 30, 40],
        ])
        errors, warnings = validate_contingency(df)
        assert any("negative" in w.lower() for w in warnings)


# ============================================================================
# validate_chi_square_gof
# ============================================================================

class TestValidateChiSquareGof:
    """Tests for validate_chi_square_gof."""

    def test_valid_data_zero_errors(self):
        """Row 0 = categories, Row 1 = observed counts."""
        df = pd.DataFrame([
            ["Cat1", "Cat2", "Cat3"],
            [20, 30, 50],
        ])
        errors, warnings = validate_chi_square_gof(df)
        assert errors == []

    def test_non_numeric_observed_errors(self):
        """Non-numeric observed counts -> error mentioning 'numeric'."""
        df = pd.DataFrame([
            ["Cat1", "Cat2"],
            ["abc", 30],
        ])
        errors, warnings = validate_chi_square_gof(df)
        assert any("numeric" in e.lower() for e in errors)

    def test_negative_observed_errors(self):
        """Negative observed counts -> error mentioning 'non-negative'."""
        df = pd.DataFrame([
            ["Cat1", "Cat2"],
            [-5, 30],
        ])
        errors, warnings = validate_chi_square_gof(df)
        assert any("non-negative" in e.lower() for e in errors)

    def test_with_expected_row_valid(self):
        """Row 2 = expected counts is optional and valid."""
        df = pd.DataFrame([
            ["Cat1", "Cat2", "Cat3"],
            [20, 30, 50],
            [33.3, 33.3, 33.4],
        ])
        errors, warnings = validate_chi_square_gof(df)
        assert errors == []

    def test_expected_row_non_numeric_errors(self):
        """Non-numeric expected row -> error."""
        df = pd.DataFrame([
            ["Cat1", "Cat2"],
            [20, 30],
            ["abc", 33],
        ])
        errors, warnings = validate_chi_square_gof(df)
        assert any("numeric" in e.lower() for e in errors)

    def test_expected_row_zero_errors(self):
        """Zero expected value -> error mentioning 'positive'."""
        df = pd.DataFrame([
            ["Cat1", "Cat2"],
            [20, 30],
            [0, 33],
        ])
        errors, warnings = validate_chi_square_gof(df)
        assert any("positive" in e.lower() for e in errors)

    def test_too_few_rows_errors(self):
        """Only 1 row -> error."""
        df = pd.DataFrame([["Cat1", "Cat2"]])
        errors, warnings = validate_chi_square_gof(df)
        assert len(errors) >= 1

    def test_low_expected_counts_warns(self):
        """Observed counts < 5 -> warning about chi-square approximation."""
        df = pd.DataFrame([
            ["Cat1", "Cat2"],
            [3, 30],
        ])
        errors, warnings = validate_chi_square_gof(df)
        assert any("< 5" in w or "unreliable" in w.lower() for w in warnings)


# ============================================================================
# validate_bland_altman
# ============================================================================

class TestValidateBlandAltman:
    """Tests for validate_bland_altman."""

    def test_valid_data_zero_errors(self):
        """Standard valid: 2 columns, 3+ data rows."""
        df = pd.DataFrame([
            ["Method A", "Method B"],
            [1.0, 1.1],
            [2.0, 2.3],
            [3.0, 2.9],
            [4.0, 4.2],
        ])
        errors, warnings = validate_bland_altman(df)
        assert errors == []

    def test_too_few_rows_errors(self):
        """Only header + 1 data row -> error (need >= 3 pairs)."""
        df = pd.DataFrame([
            ["A", "B"],
            [1.0, 2.0],
        ])
        errors, warnings = validate_bland_altman(df)
        assert len(errors) >= 1

    def test_single_column_errors(self):
        """Only 1 column -> error mentioning '2 columns'."""
        df = pd.DataFrame([["A"], [1.0], [2.0], [3.0]])
        errors, warnings = validate_bland_altman(df)
        assert any("2 columns" in e for e in errors)

    def test_three_columns_warns(self):
        """More than 2 columns -> warning about using first 2 only."""
        df = pd.DataFrame([
            ["A", "B", "C"],
            [1.0, 1.1, 99],
            [2.0, 2.3, 99],
            [3.0, 2.9, 99],
        ])
        errors, warnings = validate_bland_altman(df)
        assert errors == []
        assert any("first 2" in w.lower() or "only" in w.lower() for w in warnings)


# ============================================================================
# validate_forest_plot
# ============================================================================

class TestValidateForestPlot:
    """Tests for validate_forest_plot."""

    def test_valid_data_zero_errors(self):
        """Standard valid: header + 2+ study rows, 4 columns."""
        df = pd.DataFrame([
            ["Study", "Effect", "CI_lo", "CI_hi"],
            ["Study A", 0.5, 0.2, 0.8],
            ["Study B", 1.0, 0.6, 1.4],
            ["Study C", 0.8, 0.3, 1.3],
        ])
        errors, warnings = validate_forest_plot(df)
        assert errors == []

    def test_too_few_rows_errors(self):
        """Only header + 1 study row -> error."""
        df = pd.DataFrame([
            ["Study", "Effect", "CI_lo", "CI_hi"],
            ["A", 0.5, 0.2, 0.8],
        ])
        errors, warnings = validate_forest_plot(df)
        assert any("2 study" in e.lower() or "at least" in e.lower() for e in errors)

    def test_too_few_columns_errors(self):
        """Only 3 columns -> error mentioning '4 columns'."""
        df = pd.DataFrame([
            ["Study", "Effect", "CI_lo"],
            ["A", 0.5, 0.2],
            ["B", 1.0, 0.6],
        ])
        errors, warnings = validate_forest_plot(df)
        assert any("4 columns" in e for e in errors)

    def test_non_numeric_effect_errors(self):
        """Non-numeric Effect column -> error mentioning 'numeric'."""
        df = pd.DataFrame([
            ["Study", "Effect", "CI_lo", "CI_hi"],
            ["A", "abc", 0.2, 0.8],
            ["B", "def", 0.6, 1.4],
        ])
        errors, warnings = validate_forest_plot(df)
        assert any("numeric" in e.lower() for e in errors)

    def test_inverted_ci_warns(self):
        """CI_lo > Effect -> warning about inverted bounds."""
        df = pd.DataFrame([
            ["Study", "Effect", "CI_lo", "CI_hi"],
            ["A", 0.5, 0.8, 1.0],  # CI_lo (0.8) > Effect (0.5)
            ["B", 1.0, 0.6, 1.4],
        ])
        errors, warnings = validate_forest_plot(df)
        assert any("inverted" in w.lower() for w in warnings)


# ============================================================================
# validate_pyramid
# ============================================================================

class TestValidatePyramid:
    """Tests for validate_pyramid (3 columns: Category, Left, Right)."""

    def test_valid_data_zero_errors(self):
        """Standard valid pyramid layout."""
        df = pd.DataFrame([
            ["Age", "Male", "Female"],
            ["0-9", 100, 95],
            ["10-19", 120, 115],
            ["20-29", 130, 125],
        ])
        errors, warnings = validate_pyramid(df)
        assert errors == []

    def test_too_few_columns_errors(self):
        """Only 2 columns -> error mentioning '3 columns'."""
        df = pd.DataFrame([
            ["Age", "Male"],
            ["0-9", 100],
            ["10-19", 120],
        ])
        errors, warnings = validate_pyramid(df)
        assert any("3 columns" in e for e in errors)

    def test_all_non_numeric_errors(self):
        """All non-numeric in left/right -> error mentioning 'numeric'."""
        df = pd.DataFrame([
            ["Age", "Male", "Female"],
            ["0-9", "abc", "def"],
            ["10-19", "ghi", "jkl"],
        ])
        errors, warnings = validate_pyramid(df)
        assert any("numeric" in e.lower() for e in errors)

    def test_minimum_valid_header_plus_one(self):
        """Header + 1 data row is minimum valid."""
        df = pd.DataFrame([
            ["Age", "Male", "Female"],
            ["0-9", 100, 95],
        ])
        errors, warnings = validate_pyramid(df)
        assert errors == []

    def test_unequal_lengths_warns(self):
        """Unequal left/right row counts -> warning."""
        df = pd.DataFrame([
            ["Age", "Male", "Female"],
            ["0-9", 100, 95],
            ["10-19", 120, None],
        ])
        errors, warnings = validate_pyramid(df)
        assert any("unequal" in w.lower() or "length" in w.lower() for w in warnings)
