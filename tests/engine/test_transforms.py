"""Tests for refraction.analysis.transforms — column transformations."""

import os
import sys
import math

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from refraction.analysis.transforms import (
    transform_column, list_transforms, transform_count
)


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "values": [1.0, 2.0, 4.0, 8.0, 16.0],
        "negative": [-2.0, -1.0, 0.0, 1.0, 2.0],
        "text_col": ["a", "b", "c", "d", "e"],
    })


class TestTransformRegistry:
    def test_at_least_30_transforms(self):
        assert transform_count() >= 30

    def test_list_transforms_has_categories(self):
        cats = list_transforms()
        assert isinstance(cats, dict)
        assert len(cats) >= 5
        expected = {"Logarithmic", "Normalization", "Arithmetic", "Statistical", "Baseline"}
        for cat in expected:
            assert cat in cats, f"Missing category: {cat}"

    def test_each_transform_has_metadata(self):
        cats = list_transforms()
        for cat, transforms in cats.items():
            for t in transforms:
                assert "key" in t
                assert "doc" in t
                assert "params" in t


class TestLogTransforms:
    def test_log10(self, sample_df):
        result = transform_column(sample_df, "values", "log10")
        np.testing.assert_allclose(result.values, np.log10([1, 2, 4, 8, 16]), rtol=1e-10)

    def test_ln(self, sample_df):
        result = transform_column(sample_df, "values", "ln")
        np.testing.assert_allclose(result.values, np.log([1, 2, 4, 8, 16]), rtol=1e-10)

    def test_log2(self, sample_df):
        result = transform_column(sample_df, "values", "log2")
        np.testing.assert_allclose(result.values, [0, 1, 2, 3, 4], rtol=1e-10)

    def test_exp(self, sample_df):
        result = transform_column(sample_df, "negative", "exp")
        np.testing.assert_allclose(result.values, np.exp([-2, -1, 0, 1, 2]), rtol=1e-10)

    def test_exp10(self, sample_df):
        df = pd.DataFrame({"x": [0.0, 1.0, 2.0]})
        result = transform_column(df, "x", "exp10")
        np.testing.assert_allclose(result.values, [1, 10, 100], rtol=1e-10)


class TestNormalization:
    def test_normalize_percent(self, sample_df):
        result = transform_column(sample_df, "values", "normalize_percent")
        assert result.iloc[-1] == pytest.approx(100.0)
        assert result.iloc[0] == pytest.approx(100 / 16)

    def test_normalize_zscore(self, sample_df):
        result = transform_column(sample_df, "values", "normalize_zscore")
        assert result.mean() == pytest.approx(0.0, abs=1e-10)
        assert result.std() == pytest.approx(1.0, abs=0.01)

    def test_normalize_minmax(self, sample_df):
        result = transform_column(sample_df, "values", "normalize_minmax")
        assert result.min() == pytest.approx(0.0)
        assert result.max() == pytest.approx(1.0)

    def test_normalize_robust(self, sample_df):
        result = transform_column(sample_df, "values", "normalize_robust")
        assert result.median() == pytest.approx(0.0, abs=1e-10)

    def test_normalize_fraction(self, sample_df):
        result = transform_column(sample_df, "values", "normalize_fraction")
        assert result.sum() == pytest.approx(1.0)


class TestArithmetic:
    def test_reciprocal(self, sample_df):
        result = transform_column(sample_df, "values", "reciprocal")
        np.testing.assert_allclose(result.values, [1, 0.5, 0.25, 0.125, 0.0625], rtol=1e-10)

    def test_square_root(self, sample_df):
        result = transform_column(sample_df, "values", "square_root")
        np.testing.assert_allclose(result.values, np.sqrt([1, 2, 4, 8, 16]), rtol=1e-10)

    def test_square(self, sample_df):
        result = transform_column(sample_df, "values", "square")
        np.testing.assert_allclose(result.values, [1, 4, 16, 64, 256], rtol=1e-10)

    def test_abs(self, sample_df):
        result = transform_column(sample_df, "negative", "abs")
        np.testing.assert_allclose(result.values, [2, 1, 0, 1, 2])

    def test_negate(self, sample_df):
        result = transform_column(sample_df, "values", "negate")
        np.testing.assert_allclose(result.values, [-1, -2, -4, -8, -16])

    def test_add_constant(self, sample_df):
        result = transform_column(sample_df, "values", "add_constant", value=10)
        np.testing.assert_allclose(result.values, [11, 12, 14, 18, 26])

    def test_multiply_constant(self, sample_df):
        result = transform_column(sample_df, "values", "multiply_constant", value=3)
        np.testing.assert_allclose(result.values, [3, 6, 12, 24, 48])

    def test_power(self, sample_df):
        df = pd.DataFrame({"x": [2.0, 3.0, 4.0]})
        result = transform_column(df, "x", "power", exponent=3)
        np.testing.assert_allclose(result.values, [8, 27, 64])

    def test_cube_root(self, sample_df):
        result = transform_column(sample_df, "values", "cube_root")
        np.testing.assert_allclose(result.values, np.cbrt([1, 2, 4, 8, 16]), rtol=1e-10)


class TestStatistical:
    def test_rank(self, sample_df):
        result = transform_column(sample_df, "values", "rank")
        np.testing.assert_allclose(result.values, [1, 2, 3, 4, 5])

    def test_cumsum(self, sample_df):
        result = transform_column(sample_df, "values", "cumsum")
        np.testing.assert_allclose(result.values, [1, 3, 7, 15, 31])

    def test_diff(self, sample_df):
        result = transform_column(sample_df, "values", "diff")
        assert np.isnan(result.iloc[0])
        np.testing.assert_allclose(result.values[1:], [1, 2, 4, 8])

    def test_pct_change(self, sample_df):
        result = transform_column(sample_df, "values", "pct_change")
        assert result.iloc[1] == pytest.approx(100.0)  # 1->2 = 100%

    def test_rolling_mean(self, sample_df):
        result = transform_column(sample_df, "values", "rolling_mean", window=3)
        assert len(result) == 5
        # Third value should be mean of first 3
        assert result.iloc[2] == pytest.approx((1 + 2 + 4) / 3)

    def test_percentile_rank(self, sample_df):
        result = transform_column(sample_df, "values", "percentile_rank")
        assert result.min() > 0
        assert result.max() == pytest.approx(100.0)


class TestBaseline:
    def test_subtract_baseline(self, sample_df):
        result = transform_column(sample_df, "values", "subtract_baseline")
        assert result.iloc[0] == pytest.approx(0.0)
        assert result.iloc[1] == pytest.approx(1.0)

    def test_fold_change(self, sample_df):
        result = transform_column(sample_df, "values", "fold_change")
        assert result.iloc[0] == pytest.approx(1.0)
        assert result.iloc[-1] == pytest.approx(16.0)

    def test_fold_change_with_reference(self, sample_df):
        result = transform_column(sample_df, "values", "fold_change", reference=2.0)
        np.testing.assert_allclose(result.values, [0.5, 1.0, 2.0, 4.0, 8.0])

    def test_subtract_mean(self, sample_df):
        result = transform_column(sample_df, "values", "subtract_mean")
        assert result.mean() == pytest.approx(0.0, abs=1e-10)

    def test_subtract_median(self, sample_df):
        result = transform_column(sample_df, "values", "subtract_median")
        assert result.median() == pytest.approx(0.0, abs=1e-10)

    def test_log2_fold_change(self, sample_df):
        result = transform_column(sample_df, "values", "log2_fold_change")
        assert result.iloc[0] == pytest.approx(0.0)
        assert result.iloc[-1] == pytest.approx(4.0)  # log2(16/1) = 4


class TestOutlierHandling:
    def test_winsorize(self):
        df = pd.DataFrame({"x": [1, 2, 3, 4, 5, 6, 7, 8, 9, 100]})
        result = transform_column(df, "x", "winsorize", percentile=10)
        assert result.max() < 100

    def test_clip(self, sample_df):
        result = transform_column(sample_df, "values", "clip", lower=2, upper=10)
        assert result.min() >= 2
        assert result.max() <= 10

    def test_replace_outliers_nan(self):
        # Need enough data points so 100 is clearly >3 SD from mean
        df = pd.DataFrame({"x": [1, 2, 3, 2, 1, 2, 3, 1, 2, 3, 2, 1, 2, 3, 100]})
        result = transform_column(df, "x", "replace_outliers_nan")
        assert np.isnan(result.iloc[-1])


class TestEdgeCases:
    def test_unknown_transform_raises(self, sample_df):
        with pytest.raises(ValueError, match="Unknown transform"):
            transform_column(sample_df, "values", "nonexistent_op")

    def test_bad_column_raises(self, sample_df):
        with pytest.raises(ValueError, match="not found"):
            transform_column(sample_df, "nonexistent_col", "log10")

    def test_column_by_index(self, sample_df):
        result = transform_column(sample_df, 0, "log10")
        assert len(result) == 5

    def test_column_index_out_of_range(self, sample_df):
        with pytest.raises(ValueError, match="out of range"):
            transform_column(sample_df, 99, "log10")
