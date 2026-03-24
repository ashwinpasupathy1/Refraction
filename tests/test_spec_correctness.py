"""
test_spec_correctness.py
========================
Spec builder correctness tests — verifies that each spec builder produces
numerically correct output for known input data.

Tests 10 chart types with specific numerical assertions on output values.

Run:
  python3 tests/test_spec_correctness.py  (or via run_all.py)
"""

import sys, os, json, math
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import plotter_test_harness as _h
from plotter_test_harness import (
    ok, fail, run, section, summarise,
    bar_excel, simple_xy_excel, grouped_excel,
    km_excel, heatmap_excel, forest_excel,
    with_excel,
)

# ═══════════════════════════════════════════════════════════════════════════
# 1. Bar chart spec correctness
# ═══════════════════════════════════════════════════════════════════════════
section("Spec correctness — Bar chart")


def test_bar_means_three_groups():
    """3 groups with known values: verify each trace y[0] equals group mean."""
    with with_excel(lambda p: bar_excel(
            {"A": np.array([10.0, 20.0, 30.0]),
             "B": np.array([1.0, 2.0, 3.0]),
             "C": np.array([100.0, 200.0, 300.0])}, path=p)) as xl:
        from refraction.specs.bar import build_bar_spec
        spec = json.loads(build_bar_spec({"excel_path": xl}))
        assert "data" in spec, "Missing 'data' key"
        assert len(spec["data"]) == 3, f"Expected 3 traces, got {len(spec['data'])}"
        # Group A mean = 20.0
        assert abs(spec["data"][0]["y"][0] - 20.0) < 0.01, \
            f"Group A mean: expected 20.0, got {spec['data'][0]['y'][0]}"
        # Group B mean = 2.0
        assert abs(spec["data"][1]["y"][0] - 2.0) < 0.01, \
            f"Group B mean: expected 2.0, got {spec['data'][1]['y'][0]}"
        # Group C mean = 200.0
        assert abs(spec["data"][2]["y"][0] - 200.0) < 0.01, \
            f"Group C mean: expected 200.0, got {spec['data'][2]['y'][0]}"

run("bar: 3 groups produce correct means", test_bar_means_three_groups)


def test_bar_sem_calculation():
    """Verify SEM calculation for known data."""
    # Data: [10, 20, 30], mean=20, population_std=8.165, SEM=8.165/sqrt(3)=4.714
    # Note: bar.py uses population std (divides by n, not n-1)
    with with_excel(lambda p: bar_excel(
            {"A": np.array([10.0, 20.0, 30.0])}, path=p)) as xl:
        from refraction.specs.bar import build_bar_spec
        spec = json.loads(build_bar_spec({"excel_path": xl}))
        sem_value = spec["data"][0]["error_y"]["array"][0]
        # Population std = sqrt(((10-20)^2 + (20-20)^2 + (30-20)^2) / 3) = sqrt(200/3)
        # SEM = pop_std / sqrt(3) = sqrt(200/3) / sqrt(3) = sqrt(200/9) = sqrt(22.222) = 4.714
        expected_sem = (200.0 / 3.0) ** 0.5 / (3.0 ** 0.5)
        assert abs(sem_value - expected_sem) < 0.01, \
            f"SEM: expected {expected_sem:.4f}, got {sem_value:.4f}"

run("bar: SEM value is correct for known data", test_bar_sem_calculation)


def test_bar_trace_names():
    """Verify trace names match group headers."""
    with with_excel(lambda p: bar_excel(
            {"Control": np.array([1.0, 2.0]),
             "Treatment": np.array([3.0, 4.0])}, path=p)) as xl:
        from refraction.specs.bar import build_bar_spec
        spec = json.loads(build_bar_spec({"excel_path": xl}))
        names = [t["name"] for t in spec["data"]]
        assert names == ["Control", "Treatment"], f"Expected ['Control', 'Treatment'], got {names}"

run("bar: trace names match group headers", test_bar_trace_names)


def test_bar_title_in_layout():
    """Verify title is passed through to layout."""
    with with_excel(lambda p: bar_excel(
            {"A": np.array([1.0])}, path=p)) as xl:
        from refraction.specs.bar import build_bar_spec
        spec = json.loads(build_bar_spec({"excel_path": xl, "title": "My Title"}))
        assert spec["layout"]["title"]["text"] == "My Title"

run("bar: title appears in layout", test_bar_title_in_layout)


# ═══════════════════════════════════════════════════════════════════════════
# 2. Box plot spec correctness
# ═══════════════════════════════════════════════════════════════════════════
section("Spec correctness — Box plot")


def test_box_data_passthrough():
    """Known data [1,2,3,4,5] — verify raw y values are passed to Plotly."""
    with with_excel(lambda p: bar_excel(
            {"G1": np.array([1.0, 2.0, 3.0, 4.0, 5.0])}, path=p)) as xl:
        from refraction.specs.box import build_box_spec
        spec = json.loads(build_box_spec({"excel_path": xl}))
        assert len(spec["data"]) == 1, f"Expected 1 trace, got {len(spec['data'])}"
        y_vals = sorted(spec["data"][0]["y"])
        assert y_vals == [1.0, 2.0, 3.0, 4.0, 5.0], \
            f"Expected [1,2,3,4,5], got {y_vals}"

run("box: raw y values match input data", test_box_data_passthrough)


def test_box_trace_type():
    """Box trace should be of type 'box'."""
    with with_excel(lambda p: bar_excel(
            {"G1": np.array([1.0, 2.0, 3.0])}, path=p)) as xl:
        from refraction.specs.box import build_box_spec
        spec = json.loads(build_box_spec({"excel_path": xl}))
        assert spec["data"][0]["type"] == "box", \
            f"Expected type 'box', got {spec['data'][0]['type']}"

run("box: trace type is 'box'", test_box_trace_type)


def test_box_two_groups():
    """Two groups produce two traces."""
    with with_excel(lambda p: bar_excel(
            {"G1": np.array([1.0, 2.0, 3.0]),
             "G2": np.array([4.0, 5.0, 6.0])}, path=p)) as xl:
        from refraction.specs.box import build_box_spec
        spec = json.loads(build_box_spec({"excel_path": xl}))
        assert len(spec["data"]) == 2
        assert spec["data"][0]["name"] == "G1"
        assert spec["data"][1]["name"] == "G2"

run("box: two groups produce two correctly named traces", test_box_two_groups)


# ═══════════════════════════════════════════════════════════════════════════
# 3. Line chart spec correctness
# ═══════════════════════════════════════════════════════════════════════════
section("Spec correctness — Line chart")


def test_line_xy_values():
    """Known XY data — verify x and y arrays match input."""
    with with_excel(lambda p: simple_xy_excel(
            np.array([1.0, 2.0, 3.0, 4.0]),
            np.array([10.0, 20.0, 30.0, 40.0]), path=p)) as xl:
        from refraction.specs.line import build_line_spec
        spec = json.loads(build_line_spec({"excel_path": xl}))
        trace = spec["data"][0]
        assert trace["x"] == [1.0, 2.0, 3.0, 4.0], \
            f"X values: expected [1,2,3,4], got {trace['x']}"
        assert trace["y"] == [10.0, 20.0, 30.0, 40.0], \
            f"Y values: expected [10,20,30,40], got {trace['y']}"

run("line: x and y arrays match input", test_line_xy_values)


def test_line_mode():
    """Line trace mode should be lines+markers."""
    with with_excel(lambda p: simple_xy_excel(
            np.array([1.0, 2.0]), np.array([3.0, 4.0]), path=p)) as xl:
        from refraction.specs.line import build_line_spec
        spec = json.loads(build_line_spec({"excel_path": xl}))
        assert spec["data"][0]["mode"] == "lines+markers"

run("line: mode is lines+markers", test_line_mode)


def test_line_series_name():
    """Line trace name matches column header."""
    with with_excel(lambda p: simple_xy_excel(
            np.array([1.0]), np.array([2.0]),
            x_label="Time", y_label="Growth", path=p)) as xl:
        from refraction.specs.line import build_line_spec
        spec = json.loads(build_line_spec({"excel_path": xl}))
        assert spec["data"][0]["name"] == "Growth", \
            f"Expected name 'Growth', got {spec['data'][0]['name']}"

run("line: trace name matches y-column header", test_line_series_name)


# ═══════════════════════════════════════════════════════════════════════════
# 4. Scatter plot spec correctness
# ═══════════════════════════════════════════════════════════════════════════
section("Spec correctness — Scatter plot")


def test_scatter_positions():
    """Known XY data — verify marker positions match input."""
    with with_excel(lambda p: simple_xy_excel(
            np.array([2.0, 4.0, 6.0]),
            np.array([1.0, 3.0, 5.0]), path=p)) as xl:
        from refraction.specs.scatter import build_scatter_spec
        spec = json.loads(build_scatter_spec({"excel_path": xl}))
        trace = spec["data"][0]
        assert trace["x"] == [2.0, 4.0, 6.0], f"X: {trace['x']}"
        assert trace["y"] == [1.0, 3.0, 5.0], f"Y: {trace['y']}"

run("scatter: marker positions match input XY", test_scatter_positions)


def test_scatter_mode():
    """Scatter mode is markers only."""
    with with_excel(lambda p: simple_xy_excel(
            np.array([1.0]), np.array([1.0]), path=p)) as xl:
        from refraction.specs.scatter import build_scatter_spec
        spec = json.loads(build_scatter_spec({"excel_path": xl}))
        assert spec["data"][0]["mode"] == "markers"

run("scatter: mode is markers", test_scatter_mode)


# ═══════════════════════════════════════════════════════════════════════════
# 5. Violin plot spec correctness
# ═══════════════════════════════════════════════════════════════════════════
section("Spec correctness — Violin plot")


def test_violin_trace_count():
    """Trace count matches group count."""
    with with_excel(lambda p: bar_excel(
            {"G1": np.array([1.0, 2.0, 3.0]),
             "G2": np.array([4.0, 5.0, 6.0]),
             "G3": np.array([7.0, 8.0, 9.0])}, path=p)) as xl:
        from refraction.specs.violin import build_violin_spec
        spec = json.loads(build_violin_spec({"excel_path": xl}))
        assert len(spec["data"]) == 3, \
            f"Expected 3 traces for 3 groups, got {len(spec['data'])}"

run("violin: trace count matches group count", test_violin_trace_count)


def test_violin_trace_type():
    """Each trace should be of type 'violin'."""
    with with_excel(lambda p: bar_excel(
            {"G1": np.array([1.0, 2.0, 3.0])}, path=p)) as xl:
        from refraction.specs.violin import build_violin_spec
        spec = json.loads(build_violin_spec({"excel_path": xl}))
        assert spec["data"][0]["type"] == "violin"

run("violin: trace type is 'violin'", test_violin_trace_type)


def test_violin_data_values():
    """Raw y values should be passed through."""
    with with_excel(lambda p: bar_excel(
            {"G1": np.array([10.0, 20.0, 30.0])}, path=p)) as xl:
        from refraction.specs.violin import build_violin_spec
        spec = json.loads(build_violin_spec({"excel_path": xl}))
        assert sorted(spec["data"][0]["y"]) == [10.0, 20.0, 30.0]

run("violin: y values match input data", test_violin_data_values)


# ═══════════════════════════════════════════════════════════════════════════
# 6. Histogram spec correctness
# ═══════════════════════════════════════════════════════════════════════════
section("Spec correctness — Histogram")


def test_histogram_x_values():
    """Histogram x values should contain the raw input data."""
    data = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
    with with_excel(lambda p: bar_excel({"Data": data}, path=p)) as xl:
        from refraction.specs.histogram import build_histogram_spec
        spec = json.loads(build_histogram_spec({"excel_path": xl}))
        assert len(spec["data"]) == 1
        assert spec["data"][0]["type"] == "histogram"
        x_vals = spec["data"][0]["x"]
        assert len(x_vals) == 10, f"Expected 10 values, got {len(x_vals)}"
        assert sorted(x_vals) == sorted(data.tolist())

run("histogram: x values contain raw input data", test_histogram_x_values)


def test_histogram_trace_count_multi_group():
    """Multiple groups produce multiple histogram traces."""
    with with_excel(lambda p: bar_excel(
            {"A": np.array([1.0, 2.0, 3.0, 4.0, 5.0]),
             "B": np.array([6.0, 7.0, 8.0, 9.0, 10.0])}, path=p)) as xl:
        from refraction.specs.histogram import build_histogram_spec
        spec = json.loads(build_histogram_spec({"excel_path": xl}))
        assert len(spec["data"]) == 2

run("histogram: 2 groups produce 2 traces", test_histogram_trace_count_multi_group)


# ═══════════════════════════════════════════════════════════════════════════
# 7. Kaplan-Meier spec correctness
# ═══════════════════════════════════════════════════════════════════════════
section("Spec correctness — Kaplan-Meier")


def test_km_survival_monotonic_decrease():
    """KM survival probabilities should decrease monotonically."""
    km_data = {
        "Group": {"time": np.array([1.0, 2.0, 3.0, 4.0, 5.0]),
                   "event": np.array([1, 1, 1, 1, 1])},
    }
    with with_excel(lambda p: km_excel(km_data, path=p)) as xl:
        from refraction.specs.kaplan_meier import build_kaplan_meier_spec
        spec = json.loads(build_kaplan_meier_spec({"excel_path": xl}))
        # First trace is the survival curve (mode=lines)
        surv_trace = spec["data"][0]
        y_vals = surv_trace["y"]
        # Should start at 1.0 and decrease
        assert y_vals[0] == 1.0, f"Expected start at 1.0, got {y_vals[0]}"
        for i in range(1, len(y_vals)):
            assert y_vals[i] <= y_vals[i - 1], \
                f"Survival increased from {y_vals[i-1]} to {y_vals[i]} at index {i}"

run("KM: survival probabilities decrease monotonically", test_km_survival_monotonic_decrease)


def test_km_analytical_values():
    """5 events at times 1-5, all events: verify analytical KM values.
    n=5, all events:
      t=1: S = (5-1)/5 = 4/5 = 0.8
      t=2: S = 0.8 * (4-1)/4 = 0.8 * 3/4 = 0.6
      t=3: S = 0.6 * (3-1)/3 = 0.6 * 2/3 = 0.4
      t=4: S = 0.4 * (2-1)/2 = 0.4 * 1/2 = 0.2
      t=5: S = 0.2 * (1-1)/1 = 0.0
    """
    km_data = {
        "Group": {"time": np.array([1.0, 2.0, 3.0, 4.0, 5.0]),
                   "event": np.array([1, 1, 1, 1, 1])},
    }
    with with_excel(lambda p: km_excel(km_data, path=p)) as xl:
        from refraction.specs.kaplan_meier import build_kaplan_meier_spec
        spec = json.loads(build_kaplan_meier_spec({"excel_path": xl}))
        surv_trace = spec["data"][0]
        y_vals = surv_trace["y"]
        x_vals = surv_trace["x"]
        expected = [1.0, 0.8, 0.6, 0.4, 0.2, 0.0]
        assert len(y_vals) == len(expected), \
            f"Expected {len(expected)} points, got {len(y_vals)}: {y_vals}"
        for i, (got, exp) in enumerate(zip(y_vals, expected)):
            assert abs(got - exp) < 0.01, \
                f"At index {i}: expected {exp}, got {got}"

run("KM: analytical survival values match (all events, n=5)", test_km_analytical_values)


def test_km_censoring():
    """KM with censored observations: final survival should be > 0 when last obs is censored."""
    # Only 2 events out of 5 subjects; last observation is censored
    km_data = {
        "Group": {"time": np.array([1.0, 2.0, 3.0, 4.0, 5.0]),
                   "event": np.array([1, 0, 1, 0, 0])},  # 0 = censored
    }
    with with_excel(lambda p: km_excel(km_data, path=p)) as xl:
        from refraction.specs.kaplan_meier import build_kaplan_meier_spec
        spec = json.loads(build_kaplan_meier_spec({"excel_path": xl}))
        surv_trace = spec["data"][0]
        y_vals = surv_trace["y"]
        # With 2 events and 3 censorings, final survival should be > 0
        assert y_vals[-1] > 0, \
            f"Expected final survival > 0 with censoring, got {y_vals[-1]}"

run("KM: censored observations yield higher survival", test_km_censoring)


def test_km_two_groups():
    """Two groups produce at least 2 traces (survival curves)."""
    km_data = {
        "Control": {"time": np.array([1.0, 2.0, 3.0]),
                      "event": np.array([1, 1, 1])},
        "Treatment": {"time": np.array([2.0, 4.0, 6.0]),
                        "event": np.array([1, 1, 1])},
    }
    with with_excel(lambda p: km_excel(km_data, path=p)) as xl:
        from refraction.specs.kaplan_meier import build_kaplan_meier_spec
        spec = json.loads(build_kaplan_meier_spec({"excel_path": xl}))
        # At least 2 traces (one per group, possibly more for censor marks)
        assert len(spec["data"]) >= 2, \
            f"Expected at least 2 traces, got {len(spec['data'])}"

run("KM: two groups produce at least 2 traces", test_km_two_groups)


# ═══════════════════════════════════════════════════════════════════════════
# 8. Forest plot spec correctness
# ═══════════════════════════════════════════════════════════════════════════
section("Spec correctness — Forest plot")


def _forest_excel_spec(studies, effects, ci_lo, ci_hi, path=None):
    """Create forest Excel with column names matching the spec builder expectations:
    Study, Effect, Lower CI, Upper CI."""
    import pandas as pd
    import tempfile
    path = path or tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False).name
    df = pd.DataFrame({
        "Study": studies,
        "Effect": [float(v) for v in effects],
        "Lower CI": [float(v) for v in ci_lo],
        "Upper CI": [float(v) for v in ci_hi],
    })
    df.to_excel(path, index=False)
    return path


def test_forest_effect_values():
    """Known effects [0.5, 1.0, 1.5] — verify trace x-values match."""
    with with_excel(lambda p: _forest_excel_spec(
            studies=["Study A", "Study B", "Study C"],
            effects=[0.5, 1.0, 1.5],
            ci_lo=[0.1, 0.5, 1.0],
            ci_hi=[0.9, 1.5, 2.0],
            path=p)) as xl:
        from refraction.specs.forest_plot import build_forest_plot_spec
        spec = json.loads(build_forest_plot_spec({"excel_path": xl}))
        trace = spec["data"][0]
        assert trace["x"] == [0.5, 1.0, 1.5], \
            f"Expected effects [0.5, 1.0, 1.5], got {trace['x']}"

run("forest: effect sizes match input", test_forest_effect_values)


def test_forest_ci_error_bars():
    """Verify CI error bars are correct (asymmetric)."""
    with with_excel(lambda p: _forest_excel_spec(
            studies=["S1"],
            effects=[1.0],
            ci_lo=[0.3],
            ci_hi=[1.8],
            path=p)) as xl:
        from refraction.specs.forest_plot import build_forest_plot_spec
        spec = json.loads(build_forest_plot_spec({"excel_path": xl}))
        trace = spec["data"][0]
        # error_x_plus = ci_hi - effect = 1.8 - 1.0 = 0.8
        # error_x_minus = effect - ci_lo = 1.0 - 0.3 = 0.7
        assert abs(trace["error_x"]["array"][0] - 0.8) < 0.01, \
            f"CI upper: expected 0.8, got {trace['error_x']['array'][0]}"
        assert abs(trace["error_x"]["arrayminus"][0] - 0.7) < 0.01, \
            f"CI lower: expected 0.7, got {trace['error_x']['arrayminus'][0]}"

run("forest: CI error bars match input", test_forest_ci_error_bars)


def test_forest_study_count():
    """Number of points should match number of studies."""
    with with_excel(lambda p: _forest_excel_spec(
            studies=["A", "B", "C", "D"],
            effects=[0.1, 0.2, 0.3, 0.4],
            ci_lo=[0.0, 0.1, 0.2, 0.3],
            ci_hi=[0.2, 0.3, 0.4, 0.5],
            path=p)) as xl:
        from refraction.specs.forest_plot import build_forest_plot_spec
        spec = json.loads(build_forest_plot_spec({"excel_path": xl}))
        assert len(spec["data"][0]["x"]) == 4

run("forest: point count matches study count", test_forest_study_count)


# ═══════════════════════════════════════════════════════════════════════════
# 9. Heatmap spec correctness
# ═══════════════════════════════════════════════════════════════════════════
section("Spec correctness — Heatmap")


def test_heatmap_z_values():
    """Known matrix — verify z values match input."""
    matrix = np.array([[1.0, 2.0, 3.0],
                       [4.0, 5.0, 6.0]])
    with with_excel(lambda p: heatmap_excel(
            matrix, ["R1", "R2"], ["C1", "C2", "C3"], path=p)) as xl:
        from refraction.specs.heatmap import build_heatmap_spec
        spec = json.loads(build_heatmap_spec({"excel_path": xl}))
        z = spec["data"][0]["z"]
        assert z == [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]], \
            f"Z values: expected [[1,2,3],[4,5,6]], got {z}"

run("heatmap: z values match input matrix", test_heatmap_z_values)


def test_heatmap_labels():
    """Verify row and column labels are passed through."""
    matrix = np.array([[1.0, 2.0], [3.0, 4.0]])
    with with_excel(lambda p: heatmap_excel(
            matrix, ["Row1", "Row2"], ["Col1", "Col2"], path=p)) as xl:
        from refraction.specs.heatmap import build_heatmap_spec
        spec = json.loads(build_heatmap_spec({"excel_path": xl}))
        assert spec["data"][0]["x"] == ["Col1", "Col2"], \
            f"X labels: {spec['data'][0]['x']}"
        assert spec["data"][0]["y"] == ["Row1", "Row2"], \
            f"Y labels: {spec['data'][0]['y']}"

run("heatmap: row and column labels match input", test_heatmap_labels)


def test_heatmap_type():
    """Trace type should be 'heatmap'."""
    matrix = np.array([[1.0]])
    with with_excel(lambda p: heatmap_excel(
            matrix, ["R"], ["C"], path=p)) as xl:
        from refraction.specs.heatmap import build_heatmap_spec
        spec = json.loads(build_heatmap_spec({"excel_path": xl}))
        assert spec["data"][0]["type"] == "heatmap"

run("heatmap: trace type is 'heatmap'", test_heatmap_type)


# ═══════════════════════════════════════════════════════════════════════════
# 10. Grouped bar spec correctness
# ═══════════════════════════════════════════════════════════════════════════
section("Spec correctness — Grouped bar")


def test_grouped_bar_traces():
    """2 categories x 2 subgroups: verify 2 traces with correct means."""
    data_dict = {
        "CatA": {"Sub1": [10.0, 20.0, 30.0], "Sub2": [40.0, 50.0, 60.0]},
        "CatB": {"Sub1": [1.0, 2.0, 3.0], "Sub2": [4.0, 5.0, 6.0]},
    }
    with with_excel(lambda p: grouped_excel(
            ["CatA", "CatB"], ["Sub1", "Sub2"], data_dict, path=p)) as xl:
        from refraction.specs.grouped_bar import build_grouped_bar_spec
        spec = json.loads(build_grouped_bar_spec({"excel_path": xl}))
        assert len(spec["data"]) == 2, f"Expected 2 traces, got {len(spec['data'])}"
        # Sub1 trace: means = [20.0, 2.0] for CatA, CatB
        sub1_trace = spec["data"][0]
        assert sub1_trace["name"] == "Sub1", f"Expected 'Sub1', got {sub1_trace['name']}"
        assert abs(sub1_trace["y"][0] - 20.0) < 0.01, \
            f"CatA/Sub1 mean: expected 20.0, got {sub1_trace['y'][0]}"
        assert abs(sub1_trace["y"][1] - 2.0) < 0.01, \
            f"CatB/Sub1 mean: expected 2.0, got {sub1_trace['y'][1]}"
        # Sub2 trace: means = [50.0, 5.0]
        sub2_trace = spec["data"][1]
        assert sub2_trace["name"] == "Sub2"
        assert abs(sub2_trace["y"][0] - 50.0) < 0.01
        assert abs(sub2_trace["y"][1] - 5.0) < 0.01

run("grouped bar: 2x2 layout produces correct means", test_grouped_bar_traces)


def test_grouped_bar_barmode():
    """Grouped bar layout barmode should be 'group'."""
    data_dict = {
        "Cat": {"S1": [1.0], "S2": [2.0]},
    }
    with with_excel(lambda p: grouped_excel(
            ["Cat"], ["S1", "S2"], data_dict, path=p)) as xl:
        from refraction.specs.grouped_bar import build_grouped_bar_spec
        spec = json.loads(build_grouped_bar_spec({"excel_path": xl}))
        assert spec["layout"]["barmode"] == "group"

run("grouped bar: barmode is 'group'", test_grouped_bar_barmode)


# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
summarise()
sys.exit(0 if _h.FAIL == 0 else 1)
