"""
test_api.py — pytest tests for FastAPI endpoints in plotter_server.py.

Covers: /health, /chart-types, /render, /upload.
"""

import os
import tempfile

import numpy as np
import pytest

from tests.conftest import (
    _bar_excel, _simple_xy_excel, _grouped_excel,
    _km_excel, _heatmap_excel, _contingency_excel,
    _bland_altman_excel, _forest_excel, _chi_gof_excel,
    _with_excel,
)

from refraction.server.api import _make_app

try:
    from starlette.testclient import TestClient
except ImportError:
    from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    app = _make_app()
    return TestClient(app, raise_server_exceptions=False)


# =========================================================================
# /health endpoint
# =========================================================================

class TestHealth:
    def test_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"


# =========================================================================
# /chart-types endpoint
# =========================================================================

class TestChartTypes:
    def test_returns_list(self, client):
        resp = client.get("/chart-types")
        assert resp.status_code == 200
        data = resp.json()
        assert "all" in data
        assert "priority" in data

    def test_has_29_entries(self, client):
        resp = client.get("/chart-types")
        data = resp.json()
        assert len(data["all"]) == 29, f"Expected 29, got {len(data['all'])}"

    def test_priority_subset(self, client):
        resp = client.get("/chart-types")
        data = resp.json()
        for ct in data["priority"]:
            assert ct in data["all"], f"Priority type {ct} not in 'all' list"


# =========================================================================
# /render — bar chart
# =========================================================================

class TestRenderBar:
    def test_basic(self, client):
        with _with_excel(lambda p: _bar_excel(
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

    def test_with_title(self, client):
        with _with_excel(lambda p: _bar_excel(
                {"A": np.array([10, 20, 30])}, path=p)) as xl:
            resp = client.post("/render", json={
                "chart_type": "bar",
                "kw": {"excel_path": xl, "title": "Test Title"}
            })
            data = resp.json()
            assert data["ok"] is True
            spec = data["spec"]
            assert spec["layout"].get("title", {}).get("text", "") == "Test Title"

    def test_trace_count(self, client):
        with _with_excel(lambda p: _bar_excel(
                {"A": np.array([1, 2]), "B": np.array([3, 4]), "C": np.array([5, 6])},
                path=p)) as xl:
            resp = client.post("/render", json={
                "chart_type": "bar",
                "kw": {"excel_path": xl}
            })
            data = resp.json()
            assert len(data["spec"]["data"]) == 3, \
                f"Expected 3 traces, got {len(data['spec']['data'])}"


# =========================================================================
# /render — grouped_bar
# =========================================================================

class TestRenderGroupedBar:
    def test_basic(self, client):
        data_dict = {
            "CatA": {"Sub1": [1, 2, 3], "Sub2": [4, 5, 6]},
            "CatB": {"Sub1": [7, 8, 9], "Sub2": [10, 11, 12]},
        }
        with _with_excel(lambda p: _grouped_excel(
                ["CatA", "CatB"], ["Sub1", "Sub2"], data_dict, path=p)) as xl:
            resp = client.post("/render", json={
                "chart_type": "grouped_bar",
                "kw": {"excel_path": xl}
            })
            d = resp.json()
            assert d["ok"] is True
            assert len(d["spec"]["data"]) >= 2


# =========================================================================
# /render — line chart
# =========================================================================

class TestRenderLine:
    def test_basic(self, client):
        with _with_excel(lambda p: _simple_xy_excel(
                np.array([1, 2, 3, 4, 5]),
                np.array([10, 20, 30, 40, 50]), path=p)) as xl:
            resp = client.post("/render", json={
                "chart_type": "line",
                "kw": {"excel_path": xl}
            })
            d = resp.json()
            assert d["ok"] is True
            assert d["spec"]["data"][0]["mode"] == "lines+markers"


# =========================================================================
# /render — scatter chart
# =========================================================================

class TestRenderScatter:
    def test_basic(self, client):
        with _with_excel(lambda p: _simple_xy_excel(
                np.array([1, 2, 3, 4]), np.array([2, 4, 6, 8]), path=p)) as xl:
            resp = client.post("/render", json={
                "chart_type": "scatter",
                "kw": {"excel_path": xl}
            })
            d = resp.json()
            assert d["ok"] is True
            assert d["spec"]["data"][0]["mode"] == "markers"


# =========================================================================
# /render — distribution charts (violin, box, histogram)
# =========================================================================

class TestRenderDistributions:
    def test_violin(self, client):
        with _with_excel(lambda p: _bar_excel(
                {"G1": np.random.default_rng(0).normal(5, 1, 20),
                 "G2": np.random.default_rng(0).normal(8, 1, 20)}, path=p)) as xl:
            resp = client.post("/render", json={
                "chart_type": "violin",
                "kw": {"excel_path": xl}
            })
            d = resp.json()
            assert d["ok"] is True, f"violin render failed: {d}"

    def test_box(self, client):
        with _with_excel(lambda p: _bar_excel(
                {"G1": np.array([1, 2, 3, 4, 5]),
                 "G2": np.array([6, 7, 8, 9, 10])}, path=p)) as xl:
            resp = client.post("/render", json={
                "chart_type": "box",
                "kw": {"excel_path": xl}
            })
            d = resp.json()
            assert d["ok"] is True, f"box render failed: {d}"

    def test_histogram(self, client):
        with _with_excel(lambda p: _bar_excel(
                {"Data": np.random.default_rng(1).normal(0, 1, 50)}, path=p)) as xl:
            resp = client.post("/render", json={
                "chart_type": "histogram",
                "kw": {"excel_path": xl}
            })
            d = resp.json()
            assert d["ok"] is True, f"histogram render failed: {d}"


# =========================================================================
# /render — error handling
# =========================================================================

class TestRenderErrors:
    def test_unknown_chart_type(self, client):
        resp = client.post("/render", json={
            "chart_type": "nonexistent_chart",
            "kw": {}
        })
        # Should not crash the server
        assert resp.status_code == 200


# =========================================================================
# /upload endpoint
# =========================================================================

class TestUpload:
    def test_xlsx(self, client):
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
            os.unlink(d["path"])
        finally:
            os.unlink(tmp.name)

    def test_unsupported_type(self, client):
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


# =========================================================================
# /render — additional chart types
# =========================================================================

class TestRenderAdditional:
    def test_heatmap(self, client):
        matrix = np.array([[1.0, 2.0], [3.0, 4.0]])
        with _with_excel(lambda p: _heatmap_excel(
                matrix, ["R1", "R2"], ["C1", "C2"], path=p)) as xl:
            resp = client.post("/render", json={
                "chart_type": "heatmap",
                "kw": {"excel_path": xl}
            })
            d = resp.json()
            assert d["ok"] is True, f"heatmap render failed: {d}"

    def test_kaplan_meier(self, client):
        km_data = {
            "Control": {"time": np.array([1, 2, 3, 4, 5]),
                         "event": np.array([1, 1, 0, 1, 0])},
            "Treatment": {"time": np.array([2, 3, 4, 5, 6]),
                           "event": np.array([1, 0, 1, 0, 1])},
        }
        with _with_excel(lambda p: _km_excel(km_data, path=p)) as xl:
            resp = client.post("/render", json={
                "chart_type": "kaplan_meier",
                "kw": {"excel_path": xl}
            })
            d = resp.json()
            assert d["ok"] is True, f"kaplan_meier render failed: {d}"
