"""
test_invariants.py
==================
Property-based invariant tests — mathematical properties that must always
hold regardless of input data.

Tests: p-values in [0,1], effect sizes finite, means within data range,
error bars non-negative, KM survival monotonically decreasing, trace count
matches group count, spec JSON validity.

Run:
  python3 tests/test_invariants.py  (or via run_all.py)
"""

import sys, os, json, math, warnings
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import plotter_test_harness as _h
from plotter_test_harness import (
    pf, ok, fail, run, section, summarise,
    bar_excel, simple_xy_excel, km_excel,
    with_excel,
)


# ═══════════════════════════════════════════════════════════════════════════
# 1. p-values in [0, 1]
# ═══════════════════════════════════════════════════════════════════════════
section("Invariants — p-values in [0, 1]")

_rng = np.random.default_rng(12345)

# Access internal stats helpers
_run_stats = pf._run_stats
_cohens_d = pf._cohens_d
_hedges_g = pf._hedges_g

from scipy import stats as _scipy_stats


def test_pvalues_welch_t():
    """50 random datasets: Welch's t-test p-values all in [0, 1]."""
    for i in range(50):
        a = _rng.normal(0, _rng.uniform(0.5, 5), size=_rng.integers(5, 30))
        b = _rng.normal(_rng.uniform(-3, 3), _rng.uniform(0.5, 5), size=_rng.integers(5, 30))
        _, p = _scipy_stats.ttest_ind(a, b, equal_var=False)
        assert 0 <= p <= 1, f"Trial {i}: p={p} out of [0,1]"

run("p-values: 50 random Welch t-tests all in [0,1]", test_pvalues_welch_t)


def test_pvalues_mann_whitney():
    """50 random datasets: Mann-Whitney p-values all in [0, 1]."""
    for i in range(50):
        a = _rng.normal(0, 1, size=_rng.integers(5, 30))
        b = _rng.normal(_rng.uniform(-2, 2), 1, size=_rng.integers(5, 30))
        _, p = _scipy_stats.mannwhitneyu(a, b, alternative="two-sided")
        assert 0 <= p <= 1, f"Trial {i}: p={p} out of [0,1]"

run("p-values: 50 random Mann-Whitney tests all in [0,1]", test_pvalues_mann_whitney)


def test_pvalues_kruskal():
    """50 random 3-group datasets: Kruskal-Wallis p-values in [0, 1]."""
    for i in range(50):
        groups = [_rng.normal(_rng.uniform(-3, 3), 1, size=_rng.integers(5, 20))
                  for _ in range(3)]
        _, p = _scipy_stats.kruskal(*groups)
        assert 0 <= p <= 1, f"Trial {i}: p={p} out of [0,1]"

run("p-values: 50 random Kruskal-Wallis tests all in [0,1]", test_pvalues_kruskal)


def test_pvalues_one_way_anova():
    """50 random 3-group datasets: one-way ANOVA p-values in [0, 1]."""
    for i in range(50):
        groups = [_rng.normal(_rng.uniform(-3, 3), _rng.uniform(0.5, 3),
                              size=_rng.integers(5, 20))
                  for _ in range(3)]
        _, p = _scipy_stats.f_oneway(*groups)
        assert 0 <= p <= 1, f"Trial {i}: p={p} out of [0,1]"

run("p-values: 50 random ANOVA F-tests all in [0,1]", test_pvalues_one_way_anova)


def test_pvalues_paired_t():
    """50 random paired datasets: paired t-test p-values in [0, 1]."""
    for i in range(50):
        n = _rng.integers(5, 30)
        a = _rng.normal(0, 1, size=n)
        b = a + _rng.normal(_rng.uniform(-2, 2), 0.5, size=n)
        _, p = _scipy_stats.ttest_rel(a, b)
        assert 0 <= p <= 1, f"Trial {i}: p={p} out of [0,1]"

run("p-values: 50 random paired t-tests all in [0,1]", test_pvalues_paired_t)


# ═══════════════════════════════════════════════════════════════════════════
# 2. Effect sizes finite
# ═══════════════════════════════════════════════════════════════════════════
section("Invariants — Effect sizes finite")


def test_cohens_d_finite():
    """50 random datasets: Cohen's d should be finite (not inf)."""
    for i in range(50):
        a = _rng.normal(0, _rng.uniform(0.5, 5), size=_rng.integers(5, 30))
        b = _rng.normal(_rng.uniform(-3, 3), _rng.uniform(0.5, 5), size=_rng.integers(5, 30))
        d = _cohens_d(a, b)
        assert math.isfinite(d), f"Trial {i}: Cohen's d = {d} (not finite)"

run("effect size: Cohen's d finite for 50 random datasets", test_cohens_d_finite)


def test_hedges_g_finite():
    """50 random datasets: Hedges' g should be finite (not inf)."""
    for i in range(50):
        a = _rng.normal(0, _rng.uniform(0.5, 5), size=_rng.integers(5, 30))
        b = _rng.normal(_rng.uniform(-3, 3), _rng.uniform(0.5, 5), size=_rng.integers(5, 30))
        g = _hedges_g(a, b)
        assert math.isfinite(g), f"Trial {i}: Hedges' g = {g} (not finite)"

run("effect size: Hedges' g finite for 50 random datasets", test_hedges_g_finite)


def test_cohens_d_zero_variance():
    """Cohen's d with zero-variance data should be NaN, not inf."""
    a = np.array([5.0, 5.0, 5.0, 5.0])
    b = np.array([5.0, 5.0, 5.0, 5.0])
    d = _cohens_d(a, b)
    # Both groups identical => d should be 0 or NaN, never inf
    assert not math.isinf(d), f"Cohen's d = {d} (inf for zero-variance data)"

run("effect size: Cohen's d not inf for zero-variance data", test_cohens_d_zero_variance)


# ═══════════════════════════════════════════════════════════════════════════
# 3. Mean is within data range
# ═══════════════════════════════════════════════════════════════════════════
section("Invariants — Mean within data range")


def test_bar_mean_in_range():
    """For 50 random bar chart specs, each trace y-value is within data range."""
    from refraction.specs.bar import build_bar_spec
    for i in range(50):
        n = _rng.integers(3, 20)
        data = _rng.normal(_rng.uniform(-10, 10), _rng.uniform(0.5, 5), size=n)
        data_min = float(data.min())
        data_max = float(data.max())
        with with_excel(lambda p, d=data: bar_excel({"G": d}, path=p)) as xl:
            spec = json.loads(build_bar_spec({"excel_path": xl}))
            if "data" not in spec:
                continue
            mean_val = spec["data"][0]["y"][0]
            assert data_min - 0.01 <= mean_val <= data_max + 0.01, \
                f"Trial {i}: mean {mean_val} outside [{data_min}, {data_max}]"

run("mean in range: 50 random bar specs have mean within data range", test_bar_mean_in_range)


# ═══════════════════════════════════════════════════════════════════════════
# 4. Error bars non-negative
# ═══════════════════════════════════════════════════════════════════════════
section("Invariants — Error bars non-negative")


def test_bar_error_bars_non_negative():
    """For 50 random bar specs, SEM error bars are always >= 0."""
    from refraction.specs.bar import build_bar_spec
    for i in range(50):
        n = _rng.integers(2, 20)
        data = _rng.normal(0, _rng.uniform(0.1, 10), size=n)
        with with_excel(lambda p, d=data: bar_excel({"G": d}, path=p)) as xl:
            spec = json.loads(build_bar_spec({"excel_path": xl}))
            if "data" not in spec:
                continue
            sem = spec["data"][0]["error_y"]["array"][0]
            assert sem >= 0, f"Trial {i}: SEM = {sem} (negative!)"

run("error bars: SEM non-negative for 50 random datasets", test_bar_error_bars_non_negative)


def test_bar_sem_zero_for_identical():
    """SEM should be 0 when all values are identical."""
    with with_excel(lambda p: bar_excel({"G": np.array([5.0, 5.0, 5.0, 5.0])}, path=p)) as xl:
        from refraction.specs.bar import build_bar_spec
        spec = json.loads(build_bar_spec({"excel_path": xl}))
        sem = spec["data"][0]["error_y"]["array"][0]
        assert abs(sem) < 1e-10, f"Expected SEM ~0 for identical data, got {sem}"

run("error bars: SEM is 0 for identical values", test_bar_sem_zero_for_identical)


# ═══════════════════════════════════════════════════════════════════════════
# 5. KM survival monotonically decreasing
# ═══════════════════════════════════════════════════════════════════════════
section("Invariants — KM survival monotonically decreasing")


def test_km_monotonic_random():
    """20 random KM datasets: survival should never increase."""
    from refraction.specs.kaplan_meier import build_kaplan_meier_spec
    for i in range(20):
        n = _rng.integers(5, 30)
        times = np.sort(_rng.uniform(0.1, 100, size=n))
        events = _rng.choice([0, 1], size=n, p=[0.3, 0.7])
        km_data = {"Group": {"time": times, "event": events}}
        with with_excel(lambda p, d=km_data: km_excel(d, path=p)) as xl:
            spec = json.loads(build_kaplan_meier_spec({"excel_path": xl}))
            if "data" not in spec:
                continue
            # Find the survival curve trace (mode=lines)
            for trace in spec["data"]:
                if trace.get("mode") == "lines":
                    y = trace["y"]
                    for j in range(1, len(y)):
                        assert y[j] <= y[j-1] + 1e-10, \
                            f"Trial {i}: survival increased from {y[j-1]} to {y[j]}"
                    break

run("KM monotonic: 20 random datasets never increase", test_km_monotonic_random)


def test_km_starts_at_one():
    """KM curves should always start at survival = 1.0."""
    from refraction.specs.kaplan_meier import build_kaplan_meier_spec
    km_data = {
        "Group": {"time": np.array([1.0, 3.0, 5.0, 7.0, 9.0]),
                   "event": np.array([1, 0, 1, 1, 0])},
    }
    with with_excel(lambda p: km_excel(km_data, path=p)) as xl:
        spec = json.loads(build_kaplan_meier_spec({"excel_path": xl}))
        surv_trace = spec["data"][0]
        assert surv_trace["y"][0] == 1.0, \
            f"KM should start at 1.0, got {surv_trace['y'][0]}"

run("KM monotonic: curve starts at 1.0", test_km_starts_at_one)


# ═══════════════════════════════════════════════════════════════════════════
# 6. Color count matches group count
# ═══════════════════════════════════════════════════════════════════════════
section("Invariants — Trace count matches group count")


def test_bar_trace_count_matches_groups():
    """Number of bar traces should equal number of groups."""
    from refraction.specs.bar import build_bar_spec
    for n_groups in [1, 2, 3, 5, 8]:
        groups = {f"G{i}": _rng.normal(0, 1, size=5) for i in range(n_groups)}
        with with_excel(lambda p, g=groups: bar_excel(g, path=p)) as xl:
            spec = json.loads(build_bar_spec({"excel_path": xl}))
            assert len(spec["data"]) == n_groups, \
                f"n_groups={n_groups}: expected {n_groups} traces, got {len(spec['data'])}"

run("trace count: bar traces == group count for 1,2,3,5,8 groups", test_bar_trace_count_matches_groups)


def test_violin_trace_count_matches_groups():
    """Number of violin traces should equal number of groups."""
    from refraction.specs.violin import build_violin_spec
    for n_groups in [1, 3, 7]:
        groups = {f"G{i}": _rng.normal(0, 1, size=10) for i in range(n_groups)}
        with with_excel(lambda p, g=groups: bar_excel(g, path=p)) as xl:
            spec = json.loads(build_violin_spec({"excel_path": xl}))
            assert len(spec["data"]) == n_groups, \
                f"n_groups={n_groups}: expected {n_groups} traces, got {len(spec['data'])}"

run("trace count: violin traces == group count for 1,3,7 groups", test_violin_trace_count_matches_groups)


def test_box_trace_count_matches_groups():
    """Number of box traces should equal number of groups."""
    from refraction.specs.box import build_box_spec
    for n_groups in [1, 4, 10]:
        groups = {f"G{i}": _rng.normal(0, 1, size=8) for i in range(n_groups)}
        with with_excel(lambda p, g=groups: bar_excel(g, path=p)) as xl:
            spec = json.loads(build_box_spec({"excel_path": xl}))
            assert len(spec["data"]) == n_groups

run("trace count: box traces == group count for 1,4,10 groups", test_box_trace_count_matches_groups)


# ═══════════════════════════════════════════════════════════════════════════
# 7. Spec JSON is valid
# ═══════════════════════════════════════════════════════════════════════════
section("Invariants — Spec JSON validity")


def test_all_bar_layout_specs_valid():
    """All bar-layout spec builders produce valid JSON with data+layout."""
    import importlib
    builders = [
        ("refraction.specs.bar", "build_bar_spec"),
        ("refraction.specs.box", "build_box_spec"),
        ("refraction.specs.violin", "build_violin_spec"),
        ("refraction.specs.histogram", "build_histogram_spec"),
        ("refraction.specs.dot_plot", "build_dot_plot_spec"),
        ("refraction.specs.ecdf", "build_ecdf_spec"),
        ("refraction.specs.lollipop", "build_lollipop_spec"),
        ("refraction.specs.waterfall", "build_waterfall_spec"),
    ]
    data = {"A": np.array([1.0, 2.0, 3.0, 4.0, 5.0]),
            "B": np.array([6.0, 7.0, 8.0, 9.0, 10.0])}
    with with_excel(lambda p: bar_excel(data, path=p)) as xl:
        for mod_name, fn_name in builders:
            mod = importlib.import_module(mod_name)
            builder = getattr(mod, fn_name)
            result = builder({"excel_path": xl})
            spec = json.loads(result)
            assert "data" in spec, f"{fn_name}: missing 'data' key"
            assert "layout" in spec, f"{fn_name}: missing 'layout' key"

run("JSON validity: all bar-layout specs have data+layout", test_all_bar_layout_specs_valid)


def test_xy_layout_specs_valid():
    """All XY-layout spec builders produce valid JSON with data+layout."""
    import importlib
    builders = [
        ("refraction.specs.line", "build_line_spec"),
        ("refraction.specs.scatter", "build_scatter_spec"),
        ("refraction.specs.area", "build_area_spec"),
    ]
    with with_excel(lambda p: simple_xy_excel(
            np.array([1.0, 2.0, 3.0]),
            np.array([4.0, 5.0, 6.0]), path=p)) as xl:
        for mod_name, fn_name in builders:
            mod = importlib.import_module(mod_name)
            builder = getattr(mod, fn_name)
            result = builder({"excel_path": xl})
            spec = json.loads(result)
            assert "data" in spec, f"{fn_name}: missing 'data' key"
            assert "layout" in spec, f"{fn_name}: missing 'layout' key"

run("JSON validity: all XY-layout specs have data+layout", test_xy_layout_specs_valid)


def test_spec_json_roundtrip():
    """Spec JSON should survive a JSON parse/serialize roundtrip."""
    from refraction.specs.bar import build_bar_spec
    with with_excel(lambda p: bar_excel(
            {"A": np.array([1.0, 2.0, 3.0])}, path=p)) as xl:
        original = build_bar_spec({"excel_path": xl})
        parsed = json.loads(original)
        re_serialized = json.dumps(parsed)
        re_parsed = json.loads(re_serialized)
        assert parsed == re_parsed, "JSON roundtrip changed the spec"

run("JSON validity: spec survives parse/serialize roundtrip", test_spec_json_roundtrip)


# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
summarise()
sys.exit(0 if _h.FAIL == 0 else 1)
