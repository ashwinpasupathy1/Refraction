"""
test_pipeline.py
================
End-to-end pipeline tests: create Excel -> upload -> analyze -> verify.

These tests exercise the full data flow through the API and verify
that the output matches direct computation.
"""

import os

import numpy as np
import pandas as pd
import pytest

from refraction.server.api import _make_app

try:
    from starlette.testclient import TestClient
except ImportError:
    from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    app = _make_app()
    return TestClient(app, raise_server_exceptions=False)


class TestUploadAndAnalyze:
    """Upload an Excel file via /upload, then analyze it via /analyze."""

    def _upload_xlsx(self, client, tmp_path, filename, rows):
        """Helper: write rows to xlsx, upload, return server path."""
        path = str(tmp_path / filename)
        pd.DataFrame(rows).to_excel(path, index=False, header=False)
        with open(path, "rb") as f:
            resp = client.post("/upload", files={
                "file": (filename, f,
                         "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            })
        data = resp.json()
        assert data["ok"] is True, f"Upload failed: {data}"
        return data["path"]

    def test_bar_upload_then_analyze(self, client, tmp_path):
        server_path = self._upload_xlsx(client, tmp_path, "bar.xlsx",
            [["Control", "Drug"], [1.0, 4.0], [2.0, 5.0], [3.0, 6.0]])
        try:
            resp = client.post("/analyze", json={
                "chart_type": "bar",
                "excel_path": server_path,
            })
            data = resp.json()
            assert data["ok"] is True
            groups = data["groups"]
            assert len(groups) == 2
            # Verify means
            ctrl_mean = np.mean([1.0, 2.0, 3.0])
            drug_mean = np.mean([4.0, 5.0, 6.0])
            assert abs(groups[0]["mean"] - ctrl_mean) < 1e-10
            assert abs(groups[1]["mean"] - drug_mean) < 1e-10
        finally:
            if os.path.exists(server_path):
                os.unlink(server_path)

    def test_scatter_upload_then_analyze(self, client, tmp_path):
        server_path = self._upload_xlsx(client, tmp_path, "scatter.xlsx",
            [["X", "Y"], [1.0, 2.0], [2.0, 4.0], [3.0, 6.0], [4.0, 8.0]])
        try:
            resp = client.post("/analyze", json={
                "chart_type": "scatter",
                "excel_path": server_path,
            })
            data = resp.json()
            assert data["ok"] is True
            assert data["chart_type"] == "scatter"
        finally:
            if os.path.exists(server_path):
                os.unlink(server_path)

    def test_box_with_stats(self, client, tmp_path):
        rng = np.random.default_rng(42)
        ctrl = rng.normal(5, 1, 20).tolist()
        drug = rng.normal(8, 1, 20).tolist()
        max_n = max(len(ctrl), len(drug))
        rows = [["Control", "Drug"]]
        for i in range(max_n):
            rows.append([ctrl[i] if i < len(ctrl) else None,
                        drug[i] if i < len(drug) else None])
        server_path = self._upload_xlsx(client, tmp_path, "box_stats.xlsx", rows)
        try:
            resp = client.post("/analyze", json={
                "chart_type": "box",
                "excel_path": server_path,
                "config": {"stats_test": "parametric"},
            })
            data = resp.json()
            assert data["ok"] is True
        finally:
            if os.path.exists(server_path):
                os.unlink(server_path)
