"""
test_api.py
===========
FastAPI endpoint tests for all endpoints in plotter_server.py.

Covers: /health, /chart-types, /render (bar, grouped_bar, line, scatter),
        /render-png (violin, box, histogram — spot checks), /upload.

Uses TestClient from starlette.testclient. Minimum 15 tests.

Run:
  python3 -m pytest tests/test_api.py  (or via run_all.py)
"""

import sys, os, json, tempfile
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import plotter_test_harness as _h
from plotter_test_harness import (
    ok, fail, run, section, summarise,
    bar_excel, simple_xy_excel, grouped_excel,
    km_excel, heatmap_excel, contingency_excel,
    bland_altman_excel, forest_excel, chi_gof_excel,
    with_excel,
)

# ── Import FastAPI app and test client ──────────────────────────────────────
from plotter_server import _make_app

try:
    from starlette.testclient import TestClient
except ImportError:
    from fastapi.testclient import TestClient

app = _make_app()
client = TestClient(app, raise_server_exceptions=False)

# ═══════════════════════════════════════════════════════════════════════════
# 1. Health endpoint
# ═══════════════════════════════════════════════════════════════════════════
section("API — /health endpoint")

def test_health_returns_ok():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"

run("/health: returns 200 and status=ok", test_health_returns_ok)


# ═══════════════════════════════════════════════════════════════════════════
# 2. Chart-types endpoint
# ═══════════════════════════════════════════════════════════════════════════
section("API — /chart-types endpoint")

def test_chart_types_returns_list():
    resp = client.get("/chart-types")
    assert resp.status_code == 200
    data = resp.json()
    assert "all" in data
    assert "priority" in data

run("/chart-types: returns 200 with all + priority", test_chart_types_returns_list)

def test_chart_types_has_29_entries():
    resp = client.get("/chart-types")
    data = resp.json()
    assert len(data["all"]) == 29, f"Expected 29, got {len(data['all'])}"

run("/chart-types: 29 chart types listed", test_chart_types_has_29_entries)

def test_chart_types_priority_subset():
    resp = client.get("/chart-types")
    data = resp.json()
    for ct in data["priority"]:
        assert ct in data["all"], f"Priority type {ct} not in 'all' list"

run("/chart-types: priority types are subset of all", test_chart_types_priority_subset)


# ═══════════════════════════════════════════════════════════════════════════
# 3. /render — bar chart
# ═══════════════════════════════════════════════════════════════════════════
section("API — /render bar chart")

def test_render_bar_basic():
    with with_excel(lambda p: bar_excel(
            {"Control": np.array([1, 2, 3]), "Drug": np.array([4, 5, 6])}, path=p)) as xl:
        resp = client.post("/render", json={
            "chart_type": "bar",
            "kw": {"excel_path": xl}
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert "spec" in data
        assert "data" in data["spec"]
        assert "layout" in data["spec"]

run("/render bar: returns valid Plotly spec", test_render_bar_basic)

def test_render_bar_with_title():
    with with_excel(lambda p: bar_excel(
            {"A": np.array([10, 20, 30])}, path=p)) as xl:
        resp = client.post("/render", json={
            "chart_type": "bar",
            "kw": {"excel_path": xl, "title": "Test Title"}
        })
        data = resp.json()
        assert data["ok"] is True
        spec = data["spec"]
        assert spec["layout"].get("title", {}).get("text", "") == "Test Title"

run("/render bar: title passed through to layout", test_render_bar_with_title)

def test_render_bar_trace_count():
    with with_excel(lambda p: bar_excel(
            {"A": np.array([1, 2]), "B": np.array([3, 4]), "C": np.array([5, 6])},
            path=p)) as xl:
        resp = client.post("/render", json={
            "chart_type": "bar",
            "kw": {"excel_path": xl}
        })
        data = resp.json()
        assert len(data["spec"]["data"]) == 3, \
            f"Expected 3 traces, got {len(data['spec']['data'])}"

run("/render bar: 3 groups produce 3 traces", test_render_bar_trace_count)


# ═══════════════════════════════════════════════════════════════════════════
# 4. /render — grouped_bar
# ═══════════════════════════════════════════════════════════════════════════
section("API — /render grouped_bar chart")

def test_render_grouped_bar():
    data_dict = {
        "CatA": {"Sub1": [1, 2, 3], "Sub2": [4, 5, 6]},
        "CatB": {"Sub1": [7, 8, 9], "Sub2": [10, 11, 12]},
    }
    with with_excel(lambda p: grouped_excel(
            ["CatA", "CatB"], ["Sub1", "Sub2"], data_dict, path=p)) as xl:
        resp = client.post("/render", json={
            "chart_type": "grouped_bar",
            "kw": {"excel_path": xl}
        })
        d = resp.json()
        assert d["ok"] is True
        assert len(d["spec"]["data"]) >= 2

run("/render grouped_bar: returns valid spec with traces", test_render_grouped_bar)


# ═══════════════════════════════════════════════════════════════════════════
# 5. /render — line chart
# ═══════════════════════════════════════════════════════════════════════════
section("API — /render line chart")

def test_render_line():
    with with_excel(lambda p: simple_xy_excel(
            np.array([1, 2, 3, 4, 5]),
            np.array([10, 20, 30, 40, 50]), path=p)) as xl:
        resp = client.post("/render", json={
            "chart_type": "line",
            "kw": {"excel_path": xl}
        })
        d = resp.json()
        assert d["ok"] is True
        assert d["spec"]["data"][0]["mode"] == "lines+markers"

run("/render line: returns spec with lines+markers mode", test_render_line)


# ═══════════════════════════════════════════════════════════════════════════
# 6. /render — scatter chart
# ═══════════════════════════════════════════════════════════════════════════
section("API — /render scatter chart")

def test_render_scatter():
    with with_excel(lambda p: simple_xy_excel(
            np.array([1, 2, 3, 4]), np.array([2, 4, 6, 8]), path=p)) as xl:
        resp = client.post("/render", json={
            "chart_type": "scatter",
            "kw": {"excel_path": xl}
        })
        d = resp.json()
        assert d["ok"] is True
        assert d["spec"]["data"][0]["mode"] == "markers"

run("/render scatter: returns spec with markers mode", test_render_scatter)


# ═══════════════════════════════════════════════════════════════════════════
# 7. /render — violin, box, histogram (spot checks)
# ═══════════════════════════════════════════════════════════════════════════
section("API — /render distribution charts")

def test_render_violin():
    with with_excel(lambda p: bar_excel(
            {"G1": np.random.default_rng(0).normal(5, 1, 20),
             "G2": np.random.default_rng(0).normal(8, 1, 20)}, path=p)) as xl:
        resp = client.post("/render", json={
            "chart_type": "violin",
            "kw": {"excel_path": xl}
        })
        d = resp.json()
        assert d["ok"] is True, f"violin render failed: {d}"

run("/render violin: returns ok", test_render_violin)

def test_render_box():
    with with_excel(lambda p: bar_excel(
            {"G1": np.array([1, 2, 3, 4, 5]),
             "G2": np.array([6, 7, 8, 9, 10])}, path=p)) as xl:
        resp = client.post("/render", json={
            "chart_type": "box",
            "kw": {"excel_path": xl}
        })
        d = resp.json()
        assert d["ok"] is True, f"box render failed: {d}"

run("/render box: returns ok", test_render_box)

def test_render_histogram():
    with with_excel(lambda p: bar_excel(
            {"Data": np.random.default_rng(1).normal(0, 1, 50)}, path=p)) as xl:
        resp = client.post("/render", json={
            "chart_type": "histogram",
            "kw": {"excel_path": xl}
        })
        d = resp.json()
        assert d["ok"] is True, f"histogram render failed: {d}"

run("/render histogram: returns ok", test_render_histogram)


# ═══════════════════════════════════════════════════════════════════════════
# 8. /render — unknown chart type
# ═══════════════════════════════════════════════════════════════════════════
section("API — /render error handling")

def test_render_unknown_chart_type():
    resp = client.post("/render", json={
        "chart_type": "nonexistent_chart",
        "kw": {}
    })
    d = resp.json()
    # Should not crash the server
    assert resp.status_code == 200
    # Might return ok=False or an error in the spec
    # Just verify it doesn't 500

run("/render unknown type: doesn't crash server", test_render_unknown_chart_type)


# ═══════════════════════════════════════════════════════════════════════════
# 9. /upload endpoint
# ═══════════════════════════════════════════════════════════════════════════
section("API — /upload endpoint")

def test_upload_xlsx():
    import openpyxl
    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    tmp.close()
    try:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["A", "B"])
        ws.append([1, 4])
        ws.append([2, 5])
        wb.save(tmp.name)

        with open(tmp.name, "rb") as f:
            resp = client.post("/upload", files={"file": ("test.xlsx", f,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
        d = resp.json()
        assert d["ok"] is True, f"Upload failed: {d}"
        assert "path" in d
        assert os.path.exists(d["path"])
        # Clean up uploaded file
        os.unlink(d["path"])
    finally:
        os.unlink(tmp.name)

run("/upload: .xlsx file accepted and stored", test_upload_xlsx)

def test_upload_unsupported_type():
    tmp = tempfile.NamedTemporaryFile(suffix=".txt", delete=False)
    tmp.write(b"hello")
    tmp.close()
    try:
        with open(tmp.name, "rb") as f:
            resp = client.post("/upload", files={"file": ("test.txt", f, "text/plain")})
        d = resp.json()
        assert d["ok"] is False
        assert "unsupported" in d.get("error", "").lower() or "Unsupported" in d.get("error", "")
    finally:
        os.unlink(tmp.name)

run("/upload: .txt file rejected", test_upload_unsupported_type)


# ═══════════════════════════════════════════════════════════════════════════
# 10. Additional /render chart types
# ═══════════════════════════════════════════════════════════════════════════
section("API — /render additional chart types")

def test_render_heatmap():
    matrix = np.array([[1.0, 2.0], [3.0, 4.0]])
    with with_excel(lambda p: heatmap_excel(
            matrix, ["R1", "R2"], ["C1", "C2"], path=p)) as xl:
        resp = client.post("/render", json={
            "chart_type": "heatmap",
            "kw": {"excel_path": xl}
        })
        d = resp.json()
        assert d["ok"] is True, f"heatmap render failed: {d}"

run("/render heatmap: returns ok", test_render_heatmap)

def test_render_kaplan_meier():
    km_data = {
        "Control": {"time": np.array([1, 2, 3, 4, 5]),
                     "event": np.array([1, 1, 0, 1, 0])},
        "Treatment": {"time": np.array([2, 3, 4, 5, 6]),
                       "event": np.array([1, 0, 1, 0, 1])},
    }
    with with_excel(lambda p: km_excel(km_data, path=p)) as xl:
        resp = client.post("/render", json={
            "chart_type": "kaplan_meier",
            "kw": {"excel_path": xl}
        })
        d = resp.json()
        assert d["ok"] is True, f"kaplan_meier render failed: {d}"

run("/render kaplan_meier: returns ok", test_render_kaplan_meier)


# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
summarise()
sys.exit(0 if _h.FAIL == 0 else 1)
