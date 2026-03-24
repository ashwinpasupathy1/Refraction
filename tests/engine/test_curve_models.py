"""Tests for refraction.analysis.curve_models and curve_fit.

Verifies that every model can be evaluated, fitted to known data,
and produces valid FitResult objects.
"""

import os
import sys
import math

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from refraction.analysis.curve_models import CURVE_MODELS, list_models_by_category, model_count, get_model
from refraction.analysis.curve_fit import fit_curve, compare_models, FitResult


class TestModelRegistry:
    def test_model_count_at_least_100(self):
        assert model_count() >= 100, f"Expected 100+ models, got {model_count()}"

    def test_all_models_have_required_keys(self):
        for key, model in CURVE_MODELS.items():
            assert "fn" in model, f"Model '{key}' missing 'fn'"
            assert "params" in model, f"Model '{key}' missing 'params'"
            assert "category" in model, f"Model '{key}' missing 'category'"
            assert "doc" in model, f"Model '{key}' missing 'doc'"
            assert callable(model["fn"]), f"Model '{key}' fn is not callable"
            assert isinstance(model["params"], list), f"Model '{key}' params not a list"
            assert len(model["params"]) >= 1, f"Model '{key}' has no params"

    def test_list_models_by_category(self):
        cats = list_models_by_category()
        assert isinstance(cats, dict)
        assert len(cats) >= 5  # At least 5 categories
        total = sum(len(models) for models in cats.values())
        assert total == model_count()

    def test_get_model_existing(self):
        m = get_model("linear")
        assert m is not None
        assert "fn" in m

    def test_get_model_nonexistent(self):
        assert get_model("nonexistent_model_xyz") is None

    def test_all_categories_present(self):
        cats = list_models_by_category()
        expected = {"Dose-response", "Enzyme kinetics", "Growth", "Decay",
                    "Binding", "Polynomial", "Sigmoidal", "Gaussian"}
        for cat in expected:
            assert cat in cats, f"Missing category: {cat}"


class TestModelFunctions:
    """Test that each model function can be called with sample data."""

    def test_linear(self):
        x = np.array([1, 2, 3, 4, 5], dtype=float)
        y = CURVE_MODELS["linear"]["fn"](x, 2.0, 1.0)
        np.testing.assert_allclose(y, [3, 5, 7, 9, 11])

    def test_quadratic(self):
        x = np.array([0, 1, 2], dtype=float)
        y = CURVE_MODELS["quadratic"]["fn"](x, 1.0, 0.0, 0.0)
        np.testing.assert_allclose(y, [0, 1, 4])

    def test_michaelis_menten(self):
        x = np.array([1, 5, 10, 50, 100], dtype=float)
        y = CURVE_MODELS["michaelis_menten"]["fn"](x, 100.0, 10.0)
        assert y[0] < y[-1]  # Saturating curve
        assert y[-1] < 100.0  # Below Vmax

    def test_exponential_growth(self):
        x = np.array([0, 1, 2], dtype=float)
        y = CURVE_MODELS["exponential_growth"]["fn"](x, 1.0, 1.0)
        np.testing.assert_allclose(y, [1.0, np.e, np.e ** 2], rtol=1e-10)

    def test_gaussian(self):
        x = np.array([0], dtype=float)
        y = CURVE_MODELS["gaussian"]["fn"](x, 1.0, 0.0, 1.0)
        np.testing.assert_allclose(y, [1.0])

    def test_one_phase_decay(self):
        x = np.array([0, 100], dtype=float)
        y = CURVE_MODELS["one_phase_decay"]["fn"](x, 100.0, 0.1, 10.0)
        assert y[0] > y[1]  # Decaying

    def test_dose_response_4pl(self):
        x = np.array([0.01, 0.1, 1, 10, 100], dtype=float)
        y = CURVE_MODELS["dose_response_4pl"]["fn"](x, 100.0, 0.0, 1.0, 1.0)
        assert y[0] < y[-1]  # Increasing

    def test_boltzmann(self):
        x = np.array([-10, 0, 10], dtype=float)
        y = CURVE_MODELS["boltzmann"]["fn"](x, 100.0, 0.0, 0.0, 2.0)
        assert y[0] < y[1] < y[2]  # Sigmoidal increasing

    def test_hill_equation(self):
        x = np.array([0.1, 1, 10], dtype=float)
        y = CURVE_MODELS["hill_equation"]["fn"](x, 100.0, 1.0, 2.0)
        assert y[0] < y[1] < y[2]

    def test_logistic_growth(self):
        x = np.array([-10, 0, 10], dtype=float)
        y = CURVE_MODELS["logistic_growth"]["fn"](x, 100.0, 0.5, 0.0)
        assert y[1] == pytest.approx(50.0, abs=0.1)


class TestAllModelsEvaluate:
    """Verify that every registered model can be called with positive x and dummy params."""

    @pytest.mark.parametrize("model_name", list(CURVE_MODELS.keys()))
    def test_model_evaluates(self, model_name):
        model = CURVE_MODELS[model_name]
        fn = model["fn"]
        n_params = len(model["params"])
        x = np.array([0.1, 0.5, 1.0, 2.0, 5.0, 10.0], dtype=float)

        # Use guess function if available, else use 1.0 for each param
        if model.get("guess"):
            try:
                p0 = model["guess"](x, x)  # dummy y = x
            except Exception:
                p0 = [1.0] * n_params
        else:
            p0 = [1.0] * n_params

        try:
            y = fn(x, *p0)
            assert len(y) == len(x), f"Output length mismatch for {model_name}"
        except Exception as e:
            pytest.fail(f"Model '{model_name}' failed to evaluate: {e}")


class TestCurveFit:
    def test_fit_linear(self):
        x = np.linspace(0, 10, 20)
        y = 2.5 * x + 3.0 + np.random.RandomState(42).normal(0, 0.1, 20)
        result = fit_curve(x, y, "linear")
        assert isinstance(result, FitResult)
        assert result.converged
        assert result.r_squared > 0.99
        assert abs(result.params["Slope"] - 2.5) < 0.2
        assert abs(result.params["Intercept"] - 3.0) < 0.5

    def test_fit_michaelis_menten(self):
        x = np.array([1, 2, 5, 10, 20, 50, 100, 200], dtype=float)
        true_vmax, true_km = 100.0, 10.0
        y = true_vmax * x / (true_km + x) + np.random.RandomState(0).normal(0, 1, len(x))
        result = fit_curve(x, y, "michaelis_menten")
        assert result.converged
        assert result.r_squared > 0.95
        assert abs(result.params["Vmax"] - true_vmax) < 15

    def test_fit_gaussian(self):
        x = np.linspace(-5, 5, 50)
        y = 10.0 * np.exp(-0.5 * (x / 1.5) ** 2)
        result = fit_curve(x, y, "gaussian")
        assert result.converged
        assert result.r_squared > 0.99
        assert abs(result.params["Amplitude"] - 10.0) < 1

    def test_fit_exponential_decay(self):
        x = np.linspace(0, 5, 30)
        y = 50 * np.exp(-0.5 * x) + np.random.RandomState(1).normal(0, 0.5, 30)
        result = fit_curve(x, y, "exponential_decay")
        assert result.converged
        assert result.r_squared > 0.95

    def test_fit_result_has_all_fields(self):
        x = np.linspace(0, 10, 20)
        y = 2.0 * x + 1.0
        result = fit_curve(x, y, "linear")
        assert "Slope" in result.params
        assert "Slope" in result.param_errors
        assert "Slope" in result.param_ci_lower
        assert "Slope" in result.param_ci_upper
        assert len(result.residuals) == len(x)
        assert len(result.x_fit) == 200
        assert len(result.y_fit) == 200
        assert result.n_data == 20
        assert result.n_params == 2

    def test_fit_result_to_dict(self):
        x = np.linspace(0, 10, 20)
        y = x ** 2
        result = fit_curve(x, y, "quadratic")
        d = result.to_dict()
        assert isinstance(d, dict)
        assert "params" in d
        assert "r_squared" in d

    def test_fit_unknown_model_raises(self):
        with pytest.raises(ValueError, match="Unknown model"):
            fit_curve(np.array([1, 2]), np.array([1, 2]), "nonexistent_xyz")

    def test_fit_insufficient_data_raises(self):
        with pytest.raises(ValueError, match="data points"):
            fit_curve(np.array([1.0]), np.array([1.0]), "quadratic")

    def test_aic_bic_computed(self):
        x = np.linspace(0, 10, 50)
        y = 3.0 * x + 2.0 + np.random.RandomState(42).normal(0, 0.5, 50)
        result = fit_curve(x, y, "linear")
        assert math.isfinite(result.aic)
        assert math.isfinite(result.bic)

    def test_confidence_intervals(self):
        x = np.linspace(0, 10, 50)
        y = 3.0 * x + 2.0 + np.random.RandomState(42).normal(0, 0.5, 50)
        result = fit_curve(x, y, "linear")
        for param in result.params:
            assert result.param_ci_lower[param] < result.params[param]
            assert result.param_ci_upper[param] > result.params[param]


class TestCompareModels:
    def test_compare_returns_sorted_by_aic(self):
        x = np.linspace(0, 10, 30)
        y = 2.0 * x + 1.0 + np.random.RandomState(42).normal(0, 0.5, 30)
        results = compare_models(x, y, ["linear", "quadratic", "cubic"])
        assert len(results) >= 1
        # First result should have lowest AIC
        aics = [r.aic for r in results if math.isfinite(r.aic)]
        assert aics == sorted(aics)

    def test_compare_skips_bad_models(self):
        x = np.linspace(1, 10, 20)
        y = x * 2
        results = compare_models(x, y, ["linear", "nonexistent_model"])
        assert len(results) == 1
        assert results[0].model_name == "linear"
