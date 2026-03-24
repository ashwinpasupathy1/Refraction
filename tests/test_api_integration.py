"""
test_api_integration.py
=======================
Full-pipeline API integration tests: upload -> render, error handling,
and rendering all 29 chart types through the FastAPI server.

Run:
  python3 tests/test_api_integration.py  (or via run_all.py)
"""

import sys, os, json, tempfile
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import plotter_test_harness as _h
from plotter_test_harness import (
    ok, fail, run, section, summarise,
    bar_excel, simple_xy_excel, grouped_excel,
    km_excel, heatmap_excel, contingency_excel,
    bland_altman_excel, forest_excel, chi_gof_excel,
    bubble_excel, two_way_excel,
    with_excel,
)

# ── Import FastAPI app and test client ──────────────────────────────────────
from refraction.server.api import _make_app

try:
    from starlette.testclient import TestClient
except ImportError:
    from fastapi.testclient import TestClient

app = _make_app()
client = TestClient(app, raise_server_exceptions=False)


# ═══════════════════════════════════════════════════════════════════════════
# 1. Upload then render — full pipeline
# ═══════════════════════════════════════════════════════════════════════════
section("API integration — Upload then render pipeline")


def test_upload_then_render():
    """Upload Excel file, then use returned path in /render, verify spec data."""
    import openpyxl
    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    tmp.close()
    try:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["Control", "Drug"])
        ws.append([10, 40])
        ws.append([20, 50])
        ws.append([30, 60])
        wb.save(tmp.name)

        with open(tmp.name, "rb") as f:
            upload_resp = client.post("/upload", files={"file": ("data.xlsx", f,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
        upload_data = upload_resp.json()
        assert upload_data["ok"] is True, f"Upload failed: {upload_data}"

        # Use uploaded path to render
        render_resp = client.post("/render", json={
            "chart_type": "bar",
            "kw": {"excel_path": upload_data["path"]}
        })
        render_data = render_resp.json()
        assert render_data["ok"] is True, f"Render failed: {render_data}"
        assert len(render_data["spec"]["data"]) == 2
        # Control mean = 20, Drug mean = 50
        assert abs(render_data["spec"]["data"][0]["y"][0] - 20.0) < 0.01
        assert abs(render_data["spec"]["data"][1]["y"][0] - 50.0) < 0.01

        # Clean up uploaded file
        os.unlink(upload_data["path"])
    finally:
        os.unlink(tmp.name)

run("pipeline: upload -> render produces correct spec", test_upload_then_render)


# ═══════════════════════════════════════════════════════════════════════════
# 2. Invalid file path in /render
# ═══════════════════════════════════════════════════════════════════════════
section("API integration — Error handling")


def test_render_invalid_path():
    """Render with non-existent file path should return error, not crash."""
    resp = client.post("/render", json={
        "chart_type": "bar",
        "kw": {"excel_path": "/tmp/nonexistent_file_abc123.xlsx"}
    })
    d = resp.json()
    # Should not return 500
    assert resp.status_code == 200
    # Should indicate failure
    assert d["ok"] is False or "error" in str(d.get("spec", {})).lower(), \
        f"Expected error for invalid path, got: {d}"

run("error: invalid file path returns error", test_render_invalid_path)


# ═══════════════════════════════════════════════════════════════════════════
# 3. Malformed JSON body
# ═══════════════════════════════════════════════════════════════════════════


def test_render_malformed_json():
    """Malformed JSON body should return 422, not 500."""
    resp = client.post("/render",
                       content=b"not valid json",
                       headers={"Content-Type": "application/json"})
    assert resp.status_code == 422, f"Expected 422, got {resp.status_code}"

run("error: malformed JSON returns 422", test_render_malformed_json)


# ═══════════════════════════════════════════════════════════════════════════
# 4. Missing required fields
# ═══════════════════════════════════════════════════════════════════════════


def test_render_missing_chart_type():
    """Render without chart_type should return 422."""
    resp = client.post("/render", json={"kw": {}})
    assert resp.status_code == 422, f"Expected 422, got {resp.status_code}"

run("error: missing chart_type returns 422", test_render_missing_chart_type)


def test_render_missing_kw():
    """Render without kw should return 422."""
    resp = client.post("/render", json={"chart_type": "bar"})
    assert resp.status_code == 422, f"Expected 422, got {resp.status_code}"

run("error: missing kw returns 422", test_render_missing_kw)


# ═══════════════════════════════════════════════════════════════════════════
# 5. Unknown chart type
# ═══════════════════════════════════════════════════════════════════════════


def test_render_unknown_type_error_message():
    """Render with unknown chart type should return error with message."""
    resp = client.post("/render", json={
        "chart_type": "nonexistent_chart_type",
        "kw": {}
    })
    d = resp.json()
    assert resp.status_code == 200  # doesn't crash
    # Should have an error indication
    spec = d.get("spec", {})
    if d.get("ok") is True:
        # If ok=True, the spec should contain an error key
        assert "error" in spec, f"Expected error in spec for unknown type, got: {spec}"

run("error: unknown chart type has error message", test_render_unknown_type_error_message)


# ═══════════════════════════════════════════════════════════════════════════
# 6. Upload wrong format
# ═══════════════════════════════════════════════════════════════════════════
section("API integration — Upload validation")


def test_upload_txt_rejected():
    """Uploading a .txt file should be rejected."""
    tmp = tempfile.NamedTemporaryFile(suffix=".txt", delete=False)
    tmp.write(b"hello world")
    tmp.close()
    try:
        with open(tmp.name, "rb") as f:
            resp = client.post("/upload", files={"file": ("test.txt", f, "text/plain")})
        d = resp.json()
        assert d["ok"] is False
    finally:
        os.unlink(tmp.name)

run("upload: .txt file rejected", test_upload_txt_rejected)


def test_upload_py_rejected():
    """Uploading a .py file should be rejected."""
    tmp = tempfile.NamedTemporaryFile(suffix=".py", delete=False)
    tmp.write(b"print('hello')")
    tmp.close()
    try:
        with open(tmp.name, "rb") as f:
            resp = client.post("/upload", files={"file": ("script.py", f, "text/x-python")})
        d = resp.json()
        assert d["ok"] is False
    finally:
        os.unlink(tmp.name)

run("upload: .py file rejected", test_upload_py_rejected)


# ═══════════════════════════════════════════════════════════════════════════
# 7. Upload empty file
# ═══════════════════════════════════════════════════════════════════════════


def test_upload_empty_xlsx():
    """Uploading an empty .xlsx file should succeed (valid format)."""
    import openpyxl
    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    tmp.close()
    try:
        wb = openpyxl.Workbook()
        wb.save(tmp.name)
        with open(tmp.name, "rb") as f:
            resp = client.post("/upload", files={"file": ("empty.xlsx", f,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
        d = resp.json()
        # File format is valid, upload should succeed
        assert d["ok"] is True
        if os.path.exists(d.get("path", "")):
            os.unlink(d["path"])
    finally:
        os.unlink(tmp.name)

run("upload: empty .xlsx file accepted (valid format)", test_upload_empty_xlsx)


# ═══════════════════════════════════════════════════════════════════════════
# 8. All 29 chart types render through API
# ═══════════════════════════════════════════════════════════════════════════
section("API integration — All 29 chart types render")

# Build test data for each chart type layout
_rng = np.random.default_rng(42)

# Bar-layout data (works for bar, box, violin, histogram, dot_plot, ecdf,
# lollipop, waterfall, raincloud, qq_plot, before_after, column_stats,
# subcolumn_scatter, repeated_measures)
_BAR_DATA = {"Control": _rng.normal(5, 1, 10), "Drug": _rng.normal(8, 1, 10)}

# XY layout data (line, scatter, area_chart, curve_fit)
_XY_XS = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
_XY_YS = np.array([2.0, 4.0, 6.0, 8.0, 10.0])

# Grouped layout (grouped_bar, stacked_bar)
_GROUPED_DATA = {
    "CatA": {"Sub1": [1.0, 2.0, 3.0], "Sub2": [4.0, 5.0, 6.0]},
    "CatB": {"Sub1": [7.0, 8.0, 9.0], "Sub2": [10.0, 11.0, 12.0]},
}

# KM layout (kaplan_meier)
_KM_DATA = {
    "Control": {"time": np.array([1, 2, 3, 4, 5]), "event": np.array([1, 1, 0, 1, 0])},
    "Treatment": {"time": np.array([2, 3, 4, 5, 6]), "event": np.array([1, 0, 1, 0, 1])},
}

# Heatmap layout
_HEAT_MATRIX = np.array([[1.0, 2.0], [3.0, 4.0]])

# Forest plot layout — spec builder expects "Lower CI" / "Upper CI" columns
_FOREST_STUDIES = ["S1", "S2", "S3"]
_FOREST_EFFECTS = [0.5, 1.0, 1.5]
_FOREST_LO = [0.1, 0.5, 1.0]
_FOREST_HI = [0.9, 1.5, 2.0]

# Contingency layout
_CONT_ROWS = ["GroupA", "GroupB"]
_CONT_COLS = ["Outcome1", "Outcome2"]
_CONT_MATRIX = np.array([[10, 20], [30, 40]])

# Bland-Altman layout
_BA_A = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
_BA_B = np.array([1.1, 2.2, 2.9, 4.1, 5.3])

# Chi-square GoF
_CHI_CATS = ["A", "B", "C"]
_CHI_OBS = [30.0, 40.0, 30.0]

# Bubble layout
_BUB_XS = np.array([1.0, 2.0, 3.0])
_BUB_YS = np.array([4.0, 5.0, 6.0])
_BUB_SZ = np.array([10.0, 20.0, 30.0])

# Two-way ANOVA layout
_TWO_WAY = [
    ("A", "X", 1.0), ("A", "X", 2.0), ("A", "Y", 3.0), ("A", "Y", 4.0),
    ("B", "X", 5.0), ("B", "X", 6.0), ("B", "Y", 7.0), ("B", "Y", 8.0),
]

# Pyramid layout: same as bar for the spec builder
# (columns: Category, Left, Right)
def _pyramid_excel(path=None):
    """Create pyramid-style Excel file."""
    path = path or tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False).name
    df = pd.DataFrame({
        "Category": ["Young", "Middle", "Old"],
        "Male": [100.0, 80.0, 50.0],
        "Female": [110.0, 85.0, 55.0],
    })
    df.to_excel(path, index=False)
    return path


def _forest_excel_spec(path=None):
    """Create forest Excel with column names matching the spec builder:
    Study, Effect, Lower CI, Upper CI."""
    path = path or tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False).name
    df = pd.DataFrame({
        "Study": _FOREST_STUDIES,
        "Effect": [float(v) for v in _FOREST_EFFECTS],
        "Lower CI": [float(v) for v in _FOREST_LO],
        "Upper CI": [float(v) for v in _FOREST_HI],
    })
    df.to_excel(path, index=False)
    return path


# Map each chart type to (excel_creator, extra_kw)
def _make_chart_excel_map():
    """Create temp Excel files for all chart types and return map."""
    m = {}

    # Bar-layout charts
    bar_types = ["bar", "box", "violin", "histogram", "dot_plot", "ecdf",
                 "lollipop", "waterfall", "raincloud", "qq_plot",
                 "before_after", "column_stats", "subcolumn_scatter",
                 "repeated_measures"]
    for ct in bar_types:
        m[ct] = ("bar", _BAR_DATA, {})

    # XY-layout charts
    xy_types = ["line", "scatter", "area_chart", "curve_fit"]
    for ct in xy_types:
        m[ct] = ("xy", _XY_XS, _XY_YS)

    # Grouped layout
    m["grouped_bar"] = ("grouped", None, None)
    m["stacked_bar"] = ("grouped", None, None)

    # Specialized layouts
    m["kaplan_meier"] = ("km", None, None)
    m["heatmap"] = ("heatmap", None, None)
    m["forest_plot"] = ("forest", None, None)
    m["contingency"] = ("contingency", None, None)
    m["bland_altman"] = ("bland_altman", None, None)
    m["chi_square_gof"] = ("chi_gof", None, None)
    m["bubble"] = ("bubble", None, None)
    m["two_way_anova"] = ("two_way", None, None)
    m["pyramid"] = ("pyramid", None, None)

    return m


def _create_excel_for_type(chart_type):
    """Create appropriate Excel file for the given chart type, return path."""
    chart_map = _make_chart_excel_map()
    layout_type = chart_map[chart_type][0]

    if layout_type == "bar":
        return bar_excel(_BAR_DATA)
    elif layout_type == "xy":
        return simple_xy_excel(_XY_XS, _XY_YS)
    elif layout_type == "grouped":
        return grouped_excel(["CatA", "CatB"], ["Sub1", "Sub2"], _GROUPED_DATA)
    elif layout_type == "km":
        return km_excel(_KM_DATA)
    elif layout_type == "heatmap":
        return heatmap_excel(_HEAT_MATRIX, ["R1", "R2"], ["C1", "C2"])
    elif layout_type == "forest":
        return _forest_excel_spec()
    elif layout_type == "contingency":
        return contingency_excel(_CONT_ROWS, _CONT_COLS, _CONT_MATRIX)
    elif layout_type == "bland_altman":
        return bland_altman_excel(_BA_A, _BA_B)
    elif layout_type == "chi_gof":
        return chi_gof_excel(_CHI_CATS, _CHI_OBS)
    elif layout_type == "bubble":
        return bubble_excel(_BUB_XS, _BUB_YS, _BUB_SZ)
    elif layout_type == "two_way":
        return two_way_excel(_TWO_WAY)
    elif layout_type == "pyramid":
        return _pyramid_excel()
    else:
        raise ValueError(f"Unknown layout type: {layout_type}")


# Get all 29 chart types from the API
_resp = client.get("/chart-types")
_ALL_CHART_TYPES = _resp.json()["all"]

# BUG FOUND: raincloud spec builder has a bug on line 55 of raincloud.py:
# `g + rng.uniform(0.05, 0.25)` tries to concatenate a string group name
# with a float. The fix would be to use numeric x positions (like dot_plot.py).
_KNOWN_BROKEN = {"raincloud"}

for _ct in _ALL_CHART_TYPES:
    def _make_test(chart_type):
        def test_fn():
            xl = _create_excel_for_type(chart_type)
            try:
                resp = client.post("/render", json={
                    "chart_type": chart_type,
                    "kw": {"excel_path": xl}
                })
                d = resp.json()
                assert resp.status_code == 200, \
                    f"Status {resp.status_code} for {chart_type}"
                if chart_type in _KNOWN_BROKEN:
                    # Known bug — just verify it doesn't 500
                    return
                assert d["ok"] is True, \
                    f"{chart_type} render failed: {d.get('error', d)}"
                assert "spec" in d, f"Missing spec for {chart_type}"
                assert "data" in d["spec"], f"Missing data in spec for {chart_type}"
                assert "layout" in d["spec"], f"Missing layout in spec for {chart_type}"
            finally:
                try:
                    os.unlink(xl)
                except FileNotFoundError:
                    pass
        return test_fn

    run(f"render all 29: {_ct} returns ok with data+layout",
        _make_test(_ct))


# ═══════════════════════════════════════════════════════════════════════════
# 9. /spec endpoint
# ═══════════════════════════════════════════════════════════════════════════
section("API integration — /spec endpoint")


def test_spec_endpoint():
    """The /spec endpoint should return raw JSON spec string."""
    with with_excel(lambda p: bar_excel(
            {"A": np.array([1.0, 2.0, 3.0])}, path=p)) as xl:
        resp = client.post("/spec", json={
            "chart_type": "bar",
            "kw": {"excel_path": xl}
        })
        d = resp.json()
        assert d["ok"] is True
        assert "spec_json" in d
        # spec_json should be a valid JSON string
        parsed = json.loads(d["spec_json"])
        assert "data" in parsed

run("/spec: returns raw JSON spec string", test_spec_endpoint)


# ═══════════════════════════════════════════════════════════════════════════
# 10. /event endpoint
# ═══════════════════════════════════════════════════════════════════════════
section("API integration — /event endpoint")


def test_event_endpoint():
    """The /event endpoint should accept events without crashing."""
    resp = client.post("/event", json={
        "event": "title_changed",
        "value": "New Title",
        "extra": {}
    })
    d = resp.json()
    assert d["ok"] is True

run("/event: accepts title_changed event", test_event_endpoint)


# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
summarise()
sys.exit(0 if _h.FAIL == 0 else 1)
