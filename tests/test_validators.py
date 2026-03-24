"""
test_validators.py — pytest tests for spreadsheet validators.

Covers: validate_flat_header, validate_line, validate_grouped_bar,
        validate_kaplan_meier, validate_heatmap, validate_two_way_anova,
        validate_contingency, validate_chi_square_gof, validate_bland_altman,
        validate_forest_plot, validate_pyramid.
"""

import pandas as pd

from refraction.core.validators import (
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


# =========================================================================
# 1. validate_flat_header / validate_bar
# =========================================================================

class TestFlatHeader:
    def test_valid_data(self):
        df = pd.DataFrame([["Control", "Drug"],
                            [1.0, 4.0],
                            [2.0, 5.0],
                            [3.0, 6.0]])
        errors, warnings = validate_flat_header(df)
        assert len(errors) == 0, f"Expected 0 errors, got: {errors}"

    def test_too_few_rows(self):
        df = pd.DataFrame([["A", "B"]])
        errors, warnings = validate_flat_header(df)
        assert len(errors) > 0, "Expected error for <2 rows"

    def test_empty_headers(self):
        df = pd.DataFrame([[None, None],
                            [1.0, 2.0],
                            [3.0, 4.0]])
        errors, warnings = validate_flat_header(df)
        assert len(errors) > 0, "Expected error for empty headers"

    def test_non_numeric_data(self):
        df = pd.DataFrame([["A", "B"],
                            [1.0, "abc"],
                            [2.0, 3.0]])
        errors, warnings = validate_flat_header(df)
        assert len(errors) > 0, "Expected error for non-numeric data"

    def test_validate_bar_alias(self):
        df = pd.DataFrame([["Control", "Drug"],
                            [1.0, 4.0],
                            [2.0, 5.0],
                            [3.0, 6.0]])
        errors, warnings = validate_bar(df)
        assert len(errors) == 0


# =========================================================================
# 2. validate_line
# =========================================================================

class TestLine:
    def test_valid_data(self):
        df = pd.DataFrame([["X", "Series1"],
                            [1.0, 10.0],
                            [2.0, 20.0],
                            [3.0, 30.0]])
        errors, warnings = validate_line(df)
        assert len(errors) == 0, f"Expected 0 errors, got: {errors}"

    def test_too_few_columns(self):
        df = pd.DataFrame([["X"], [1.0], [2.0]])
        errors, warnings = validate_line(df)
        assert len(errors) > 0, "Expected error for <2 columns"

    def test_non_numeric_x(self):
        df = pd.DataFrame([["X", "Y"],
                            ["a", 10.0],
                            ["b", 20.0]])
        errors, warnings = validate_line(df)
        assert len(errors) > 0, "Expected error for non-numeric X"

    def test_empty_series_names(self):
        df = pd.DataFrame([["X", None],
                            [1.0, 10.0],
                            [2.0, 20.0]])
        errors, warnings = validate_line(df)
        assert len(errors) > 0, "Expected error for empty series names"


# =========================================================================
# 3. validate_grouped_bar
# =========================================================================

class TestGroupedBar:
    def test_valid_data(self):
        df = pd.DataFrame([["CatA", "CatA", "CatB", "CatB"],
                            ["Sub1", "Sub2", "Sub1", "Sub2"],
                            [1.0, 2.0, 3.0, 4.0],
                            [5.0, 6.0, 7.0, 8.0]])
        errors, warnings = validate_grouped_bar(df)
        assert len(errors) == 0, f"Expected 0 errors, got: {errors}"

    def test_too_few_rows(self):
        df = pd.DataFrame([["CatA", "CatB"],
                            ["Sub1", "Sub2"]])
        errors, warnings = validate_grouped_bar(df)
        assert len(errors) > 0, "Expected error for <3 rows"

    def test_non_numeric_data(self):
        df = pd.DataFrame([["CatA", "CatA"],
                            ["Sub1", "Sub2"],
                            ["abc", 2.0]])
        errors, warnings = validate_grouped_bar(df)
        assert len(errors) > 0, "Expected error for non-numeric data"


# =========================================================================
# 4. validate_kaplan_meier
# =========================================================================

class TestKaplanMeier:
    def test_valid_data(self):
        df = pd.DataFrame([["GroupA", "GroupA", "GroupB", "GroupB"],
                            ["Time", "Event", "Time", "Event"],
                            [1.0, 1.0, 2.0, 0.0],
                            [3.0, 0.0, 4.0, 1.0],
                            [5.0, 1.0, 6.0, 1.0]])
        errors, warnings = validate_kaplan_meier(df)
        assert len(errors) == 0, f"Expected 0 errors, got: {errors}"

    def test_too_few_rows(self):
        df = pd.DataFrame([["A", "A"], ["Time", "Event"]])
        errors, warnings = validate_kaplan_meier(df)
        assert len(errors) > 0, "Expected error for <3 rows"

    def test_non_numeric(self):
        df = pd.DataFrame([["A", "A"],
                            ["Time", "Event"],
                            ["abc", 1.0]])
        errors, warnings = validate_kaplan_meier(df)
        assert len(errors) > 0, "Expected error for non-numeric data"


# =========================================================================
# 5. validate_heatmap
# =========================================================================

class TestHeatmap:
    def test_valid_data(self):
        df = pd.DataFrame([["", "C1", "C2"],
                            ["R1", 1.0, 2.0],
                            ["R2", 3.0, 4.0]])
        errors, warnings = validate_heatmap(df)
        assert len(errors) == 0, f"Expected 0 errors, got: {errors}"

    def test_non_numeric(self):
        df = pd.DataFrame([["", "C1", "C2"],
                            ["R1", "abc", 2.0],
                            ["R2", 3.0, 4.0]])
        errors, warnings = validate_heatmap(df)
        assert len(errors) > 0, "Expected error for non-numeric data"


# =========================================================================
# 6. validate_two_way_anova
# =========================================================================

class TestTwoWayAnova:
    def test_valid_data(self):
        df = pd.DataFrame({
            "Factor_A": ["a1", "a1", "a2", "a2", "a1", "a1", "a2", "a2"],
            "Factor_B": ["b1", "b2", "b1", "b2", "b1", "b2", "b1", "b2"],
            "Value":    [1.0, 2.0, 3.0, 4.0, 1.5, 2.5, 3.5, 4.5],
        })
        errors, warnings = validate_two_way_anova(df)
        assert len(errors) == 0, f"Expected 0 errors, got: {errors}"

    def test_too_few_columns(self):
        df = pd.DataFrame({"A": ["a1", "a2"], "B": [1.0, 2.0]})
        errors, warnings = validate_two_way_anova(df)
        assert len(errors) > 0, "Expected error for <3 columns"


# =========================================================================
# 7. validate_contingency
# =========================================================================

class TestContingency:
    def test_valid_data(self):
        df = pd.DataFrame([["", "Outcome1", "Outcome2"],
                            ["GroupA", 10, 20],
                            ["GroupB", 30, 40]])
        errors, warnings = validate_contingency(df)
        assert len(errors) == 0, f"Expected 0 errors, got: {errors}"

    def test_non_numeric(self):
        df = pd.DataFrame([["", "O1", "O2"],
                            ["G1", "abc", 20],
                            ["G2", 30, 40]])
        errors, warnings = validate_contingency(df)
        assert len(errors) > 0, "Expected error for non-numeric counts"

    def test_too_few_rows(self):
        df = pd.DataFrame([["", "O1", "O2"],
                            ["G1", 10, 20]])
        errors, warnings = validate_contingency(df)
        assert len(errors) > 0, "Expected error for <3 rows"


# =========================================================================
# 8. validate_chi_square_gof
# =========================================================================

class TestChiSquareGoF:
    def test_valid_data(self):
        df = pd.DataFrame([["Cat1", "Cat2", "Cat3"],
                            [20, 30, 50]])
        errors, warnings = validate_chi_square_gof(df)
        assert len(errors) == 0, f"Expected 0 errors, got: {errors}"

    def test_non_numeric_observed(self):
        df = pd.DataFrame([["Cat1", "Cat2"],
                            ["abc", 30]])
        errors, warnings = validate_chi_square_gof(df)
        assert len(errors) > 0, "Expected error for non-numeric observed"

    def test_negative_observed(self):
        df = pd.DataFrame([["Cat1", "Cat2"],
                            [-5, 30]])
        errors, warnings = validate_chi_square_gof(df)
        assert len(errors) > 0, "Expected error for negative observed counts"

    def test_with_expected(self):
        df = pd.DataFrame([["Cat1", "Cat2", "Cat3"],
                            [20, 30, 50],
                            [33.3, 33.3, 33.4]])
        errors, warnings = validate_chi_square_gof(df)
        assert len(errors) == 0, f"Expected 0 errors, got: {errors}"


# =========================================================================
# 9. validate_bland_altman
# =========================================================================

class TestBlandAltman:
    def test_valid_data(self):
        df = pd.DataFrame([["Method A", "Method B"],
                            [1.0, 1.1],
                            [2.0, 2.3],
                            [3.0, 2.9],
                            [4.0, 4.2]])
        errors, warnings = validate_bland_altman(df)
        assert len(errors) == 0, f"Expected 0 errors, got: {errors}"

    def test_too_few_rows(self):
        df = pd.DataFrame([["A", "B"],
                            [1.0, 2.0]])
        errors, warnings = validate_bland_altman(df)
        assert len(errors) > 0, "Expected error for too few data rows"

    def test_too_few_cols(self):
        df = pd.DataFrame([["A"], [1.0], [2.0], [3.0]])
        errors, warnings = validate_bland_altman(df)
        assert len(errors) > 0, "Expected error for <2 columns"


# =========================================================================
# 10. validate_forest_plot
# =========================================================================

class TestForestPlot:
    def test_valid_data(self):
        df = pd.DataFrame([["Study", "Effect", "CI_lo", "CI_hi"],
                            ["Study A", 0.5, 0.2, 0.8],
                            ["Study B", 1.0, 0.6, 1.4],
                            ["Study C", 0.8, 0.3, 1.3]])
        errors, warnings = validate_forest_plot(df)
        assert len(errors) == 0, f"Expected 0 errors, got: {errors}"

    def test_too_few_rows(self):
        df = pd.DataFrame([["Study", "Effect", "CI_lo", "CI_hi"],
                            ["A", 0.5, 0.2, 0.8]])
        errors, warnings = validate_forest_plot(df)
        assert len(errors) > 0, "Expected error for <3 rows"

    def test_too_few_cols(self):
        df = pd.DataFrame([["Study", "Effect", "CI_lo"],
                            ["A", 0.5, 0.2],
                            ["B", 1.0, 0.6]])
        errors, warnings = validate_forest_plot(df)
        assert len(errors) > 0, "Expected error for <4 columns"


# =========================================================================
# 11. validate_pyramid
# =========================================================================

class TestPyramid:
    def test_valid_data(self):
        df = pd.DataFrame([["Age", "Male", "Female"],
                            ["0-9", 100, 95],
                            ["10-19", 120, 115],
                            ["20-29", 130, 125]])
        errors, warnings = validate_pyramid(df)
        assert len(errors) == 0, f"Expected 0 errors, got: {errors}"

    def test_too_few_cols(self):
        df = pd.DataFrame([["Age", "Male"],
                            ["0-9", 100],
                            ["10-19", 120]])
        errors, warnings = validate_pyramid(df)
        assert len(errors) > 0, "Expected error for <3 columns"

    def test_non_numeric(self):
        df = pd.DataFrame([["Age", "Male", "Female"],
                            ["0-9", "abc", "def"],
                            ["10-19", "ghi", "jkl"]])
        errors, warnings = validate_pyramid(df)
        assert len(errors) > 0, "Expected error for non-numeric data"
