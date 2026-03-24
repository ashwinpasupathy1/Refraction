"""
test_api.py -- pytest tests for FastAPI endpoints.

Covers: /health, /chart-types, /analyze, /upload.
"""

import os
import tempfile

import numpy as np
import pytest

from tests.conftest import (
    _bar_excel, _simple_xy_excel, _grouped_excel,
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

    def test_has_29_chart_types(self, client):
        resp = client.get("/chart-types")
        data = resp.json()
        assert len(data["all"]) == 29, (
            f"Expected 29 chart types, got {len(data['all'])}: {data['all']}"
        )

    def test_priority_subset(self, client):
        resp = client.get("/chart-types")
        data = resp.json()
        for ct in data["priority"]:
            assert ct in data["all"], f"Priority type {ct} not in 'all' list"


# =========================================================================
# /analyze -- bar chart
# =========================================================================

class TestAnalyzeBar:
    def test_basic(self, client):
        with _with_excel(lambda p: _bar_excel(
                {"Control": np.array([1, 2, 3]), "Drug": np.array([4, 5, 6])}, path=p)) as xl:
            resp = client.post("/analyze", json={
                "chart_type": "bar",
                "excel_path": xl,
            })
            assert resp.status_code == 200
            data = resp.json()
            assert data["ok"] is True
            assert "groups" in data
            assert len(data["groups"]) == 2

    def test_with_title(self, client):
        with _with_excel(lambda p: _bar_excel(
                {"A": np.array([10, 20, 30])}, path=p)) as xl:
            resp = client.post("/analyze", json={
                "chart_type": "bar",
                "excel_path": xl,
                "config": {"title": "Test Title"},
            })
            data = resp.json()
            assert data["ok"] is True
            assert data["title"] == "Test Title"

    def test_group_count(self, client):
        with _with_excel(lambda p: _bar_excel(
                {"A": np.array([1, 2]), "B": np.array([3, 4]), "C": np.array([5, 6])},
                path=p)) as xl:
            resp = client.post("/analyze", json={
                "chart_type": "bar",
                "excel_path": xl,
            })
            data = resp.json()
            assert len(data["groups"]) == 3, f"Expected 3 groups, got {len(data['groups'])}"

    def test_mean_correct(self, client):
        with _with_excel(lambda p: _bar_excel(
                {"A": np.array([10, 20, 30])}, path=p)) as xl:
            resp = client.post("/analyze", json={
                "chart_type": "bar",
                "excel_path": xl,
            })
            data = resp.json()
            assert abs(data["groups"][0]["mean"] - 20.0) < 0.01


# =========================================================================
# /analyze -- with statistics
# =========================================================================

class TestAnalyzeWithStats:
    def test_bar_with_stats(self, client):
        with _with_excel(lambda p: _bar_excel(
                {"Control": np.array([1, 2, 3, 4, 5]),
                 "Drug": np.array([6, 7, 8, 9, 10])}, path=p)) as xl:
            resp = client.post("/analyze", json={
                "chart_type": "bar",
                "excel_path": xl,
                "config": {"stats_test": "parametric"},
            })
            data = resp.json()
            assert data["ok"] is True
            assert len(data["comparisons"]) >= 1
            assert "p_value" in data["comparisons"][0]
            assert "stars" in data["comparisons"][0]


# =========================================================================
# /analyze -- other chart types
# =========================================================================

class TestAnalyzeOther:
    def test_box(self, client):
        with _with_excel(lambda p: _bar_excel(
                {"G1": np.array([1, 2, 3, 4, 5]),
                 "G2": np.array([6, 7, 8, 9, 10])}, path=p)) as xl:
            resp = client.post("/analyze", json={
                "chart_type": "box",
                "excel_path": xl,
            })
            data = resp.json()
            assert data["ok"] is True

    def test_violin(self, client):
        with _with_excel(lambda p: _bar_excel(
                {"G1": np.random.default_rng(0).normal(5, 1, 20),
                 "G2": np.random.default_rng(0).normal(8, 1, 20)}, path=p)) as xl:
            resp = client.post("/analyze", json={
                "chart_type": "violin",
                "excel_path": xl,
            })
            data = resp.json()
            assert data["ok"] is True

    def test_histogram(self, client):
        with _with_excel(lambda p: _bar_excel(
                {"Data": np.random.default_rng(1).normal(0, 1, 50)}, path=p)) as xl:
            resp = client.post("/analyze", json={
                "chart_type": "histogram",
                "excel_path": xl,
            })
            data = resp.json()
            assert data["ok"] is True


# =========================================================================
# /analyze -- error handling
# =========================================================================

class TestAnalyzeErrors:
    def test_missing_file(self, client):
        resp = client.post("/analyze", json={
            "chart_type": "bar",
            "excel_path": "/nonexistent/file.xlsx",
        })
        data = resp.json()
        assert data["ok"] is False
        assert "error" in data


# =========================================================================
# /analyze -- SEM accuracy
# =========================================================================

class TestAnalyzeSEM:
    def test_sem_matches_scipy(self, client):
        from scipy import stats as scipy_stats
        vals_a = np.array([2.0, 4.0, 6.0, 8.0, 10.0])
        vals_b = np.array([1.0, 3.0, 5.0, 7.0, 9.0])
        expected_sem_a = scipy_stats.sem(vals_a)
        expected_sem_b = scipy_stats.sem(vals_b)

        with _with_excel(lambda p: _bar_excel({"A": vals_a, "B": vals_b}, path=p)) as xl:
            resp = client.post("/analyze", json={
                "chart_type": "bar",
                "excel_path": xl,
                "config": {"error_type": "sem"},
            })
            data = resp.json()
            actual_sem_a = data["groups"][0]["sem"]
            actual_sem_b = data["groups"][1]["sem"]
            assert abs(actual_sem_a - expected_sem_a) < 1e-10, \
                f"SEM mismatch: got {actual_sem_a}, expected {expected_sem_a}"
            assert abs(actual_sem_b - expected_sem_b) < 1e-10, \
                f"SEM mismatch: got {actual_sem_b}, expected {expected_sem_b}"


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
            assert "unsupported" in d.get("error", "").lower() or \
                   "Unsupported" in d.get("error", "")
        finally:
            os.unlink(tmp.name)
