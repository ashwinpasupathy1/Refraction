"""
test_api.py
===========
FastAPI endpoint integration tests for refraction.server.api.

Uses starlette TestClient -- no live server required.
Tests verify specific response structure and values for /analyze endpoint.
"""

import os

import numpy as np
import openpyxl
import pandas as pd
import pytest

from refraction.server.api import _make_app

try:
    from starlette.testclient import TestClient
except ImportError:
    from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    """Create a TestClient for the FastAPI app."""
    app = _make_app()
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def bar_xlsx(tmp_path):
    """Create a temporary .xlsx file with bar chart data: Control=[1,2,3], Drug=[4,5,6]."""
    path = str(tmp_path / "bar_data.xlsx")
    rows = [["Control", "Drug"], [1.0, 4.0], [2.0, 5.0], [3.0, 6.0]]
    pd.DataFrame(rows).to_excel(path, index=False, header=False)
    return path


@pytest.fixture
def xy_xlsx(tmp_path):
    """Create a temporary .xlsx file with XY data."""
    path = str(tmp_path / "xy_data.xlsx")
    rows = [["X", "Series1"], [1.0, 10.0], [2.0, 20.0], [3.0, 30.0], [4.0, 40.0], [5.0, 50.0]]
    pd.DataFrame(rows).to_excel(path, index=False, header=False)
    return path


# ============================================================================
# /health endpoint
# ============================================================================

class TestHealth:
    def test_returns_200_with_status_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


# ============================================================================
# /chart-types endpoint
# ============================================================================

class TestChartTypes:
    def test_returns_all_and_priority(self, client):
        resp = client.get("/chart-types")
        assert resp.status_code == 200
        data = resp.json()
        assert "all" in data
        assert "priority" in data

    def test_has_registered_types(self, client):
        data = client.get("/chart-types").json()
        assert len(data["all"]) >= 8

    def test_priority_is_subset_of_all(self, client):
        data = client.get("/chart-types").json()
        for ct in data["priority"]:
            assert ct in data["all"]

    def test_bar_is_in_priority(self, client):
        data = client.get("/chart-types").json()
        assert "bar" in data["priority"]


# ============================================================================
# /analyze endpoint
# ============================================================================

class TestAnalyzeBar:
    def test_basic_analyze_returns_chart_spec(self, client, bar_xlsx):
        resp = client.post("/analyze", json={
            "chart_type": "bar",
            "excel_path": bar_xlsx,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["chart_type"] == "bar"
        assert "groups" in data

    def test_two_groups_in_output(self, client, bar_xlsx):
        data = client.post("/analyze", json={
            "chart_type": "bar",
            "excel_path": bar_xlsx,
        }).json()
        assert len(data["groups"]) == 2

    def test_title_passed_through(self, client, bar_xlsx):
        data = client.post("/analyze", json={
            "chart_type": "bar",
            "excel_path": bar_xlsx,
            "config": {"title": "My Bar Chart"},
        }).json()
        assert data["title"] == "My Bar Chart"

    def test_three_groups(self, client, tmp_path):
        path = str(tmp_path / "three_groups.xlsx")
        rows = [["A", "B", "C"], [1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]
        pd.DataFrame(rows).to_excel(path, index=False, header=False)
        data = client.post("/analyze", json={
            "chart_type": "bar", "excel_path": path,
        }).json()
        assert data["ok"] is True
        assert len(data["groups"]) == 3


class TestAnalyzeOther:
    def test_scatter(self, client, xy_xlsx):
        data = client.post("/analyze", json={
            "chart_type": "scatter", "excel_path": xy_xlsx,
        }).json()
        assert data["ok"] is True

    def test_line(self, client, xy_xlsx):
        data = client.post("/analyze", json={
            "chart_type": "line", "excel_path": xy_xlsx,
        }).json()
        assert data["ok"] is True

    def test_box(self, client, bar_xlsx):
        data = client.post("/analyze", json={
            "chart_type": "box", "excel_path": bar_xlsx,
        }).json()
        assert data["ok"] is True

    def test_violin(self, client, bar_xlsx):
        data = client.post("/analyze", json={
            "chart_type": "violin", "excel_path": bar_xlsx,
        }).json()
        assert data["ok"] is True

    def test_histogram(self, client, bar_xlsx):
        data = client.post("/analyze", json={
            "chart_type": "histogram", "excel_path": bar_xlsx,
        }).json()
        assert data["ok"] is True


# ============================================================================
# /analyze error handling
# ============================================================================

class TestAnalyzeErrors:
    def test_unknown_chart_type(self, client):
        resp = client.post("/analyze", json={
            "chart_type": "nonexistent_chart",
            "excel_path": "/nonexistent/file.xlsx",
            "config": {},
        })
        data = resp.json()
        assert data["ok"] is False

    def test_missing_file(self, client):
        resp = client.post("/analyze", json={
            "chart_type": "bar",
            "excel_path": "/nonexistent/file.xlsx",
        })
        data = resp.json()
        assert data["ok"] is False
        assert "error" in data


# ============================================================================
# /upload endpoint
# ============================================================================

class TestUpload:
    def test_xlsx_accepted(self, client, tmp_path):
        path = str(tmp_path / "upload_test.xlsx")
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["A", "B"])
        ws.append([1, 4])
        wb.save(path)

        with open(path, "rb") as f:
            resp = client.post("/upload", files={
                "file": ("test.xlsx", f,
                         "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            })
        data = resp.json()
        assert data["ok"] is True
        assert os.path.exists(data["path"])
        os.unlink(data["path"])

    def test_txt_rejected(self, client, tmp_path):
        path = str(tmp_path / "bad.txt")
        with open(path, "w") as f:
            f.write("hello")
        with open(path, "rb") as f:
            resp = client.post("/upload", files={
                "file": ("bad.txt", f, "text/plain")
            })
        data = resp.json()
        assert data["ok"] is False

    def test_csv_accepted(self, client, tmp_path):
        path = str(tmp_path / "data.csv")
        pd.DataFrame({"A": [1, 2], "B": [3, 4]}).to_csv(path, index=False)
        with open(path, "rb") as f:
            resp = client.post("/upload", files={
                "file": ("data.csv", f, "text/csv")
            })
        data = resp.json()
        assert data["ok"] is True
        if os.path.exists(data.get("path", "")):
            os.unlink(data["path"])
