"""
test_phase3_plotly.py — pytest tests for Plotly spec builders and server.
"""

import json
import os
import time

import numpy as np
import pytest

from tests.conftest import _bar_excel, _simple_xy_excel


# =========================================================================
# Plotly spec builders — bar
# =========================================================================

class TestBarSpec:
    def test_returns_json(self):
        xl = _bar_excel({"Control": np.array([1, 2, 3]), "Drug": np.array([4, 5, 6])})
        try:
            from refraction.specs.bar import build_bar_spec
            spec_json = build_bar_spec({"excel_path": xl, "title": "Test"})
            spec = json.loads(spec_json)
            assert "data" in spec, "Missing 'data' key"
            assert "layout" in spec, "Missing 'layout' key"
        finally:
            os.unlink(xl)

    def test_has_two_traces(self):
        xl = _bar_excel({"Control": np.array([1, 2, 3]), "Drug": np.array([4, 5, 6])})
        try:
            from refraction.specs.bar import build_bar_spec
            spec = json.loads(build_bar_spec({"excel_path": xl}))
            assert len(spec["data"]) == 2, f"Expected 2 traces, got {len(spec['data'])}"
        finally:
            os.unlink(xl)

    def test_means_correct(self):
        xl = _bar_excel({"A": np.array([10, 20, 30])})
        try:
            from refraction.specs.bar import build_bar_spec
            spec = json.loads(build_bar_spec({"excel_path": xl}))
            assert abs(spec["data"][0]["y"][0] - 20.0) < 0.01
        finally:
            os.unlink(xl)


# =========================================================================
# Plotly spec builders — line
# =========================================================================

class TestLineSpec:
    def test_returns_json(self):
        xl = _simple_xy_excel(np.array([1, 2, 3]), np.array([4, 5, 6]), "X", "Y1")
        try:
            from refraction.specs.line import build_line_spec
            spec = json.loads(build_line_spec({"excel_path": xl}))
            assert "data" in spec
        finally:
            os.unlink(xl)

    def test_mode(self):
        xl = _simple_xy_excel(np.array([1, 2, 3]), np.array([4, 5, 6]))
        try:
            from refraction.specs.line import build_line_spec
            spec = json.loads(build_line_spec({"excel_path": xl}))
            assert spec["data"][0]["mode"] == "lines+markers"
        finally:
            os.unlink(xl)


# =========================================================================
# Plotly spec builders — scatter
# =========================================================================

class TestScatterSpec:
    def test_returns_json(self):
        xl = _simple_xy_excel(np.array([1, 2, 3]), np.array([4, 5, 6]))
        try:
            from refraction.specs.scatter import build_scatter_spec
            spec = json.loads(build_scatter_spec({"excel_path": xl}))
            assert "data" in spec
        finally:
            os.unlink(xl)

    def test_mode_markers(self):
        xl = _simple_xy_excel(np.array([1, 2, 3]), np.array([4, 5, 6]))
        try:
            from refraction.specs.scatter import build_scatter_spec
            spec = json.loads(build_scatter_spec({"excel_path": xl}))
            assert spec["data"][0]["mode"] == "markers"
        finally:
            os.unlink(xl)


# =========================================================================
# Plotly theme
# =========================================================================

class TestTheme:
    def test_palette_length(self):
        from refraction.specs.theme import PRISM_PALETTE
        assert len(PRISM_PALETTE) == 10

    def test_template_structure(self):
        from refraction.specs.theme import PRISM_TEMPLATE
        assert "layout" in PRISM_TEMPLATE
        assert "xaxis" in PRISM_TEMPLATE["layout"]
        assert "yaxis" in PRISM_TEMPLATE["layout"]


# =========================================================================
# FastAPI server
# =========================================================================

class TestServer:
    def test_starts(self):
        from refraction.server.api import start_server, get_port
        import urllib.request
        start_server()
        time.sleep(2)
        try:
            resp = urllib.request.urlopen(f"http://127.0.0.1:{get_port()}/health", timeout=3)
            assert resp.status == 200
        except Exception as e:
            pytest.fail(f"Server did not start: {e}")

    def test_render_endpoint(self):
        from refraction.server.api import get_port
        import urllib.request
        xl = _bar_excel({"A": np.array([1, 2, 3]), "B": np.array([4, 5, 6])})
        try:
            payload = json.dumps({"chart_type": "bar", "kw": {"excel_path": xl}}).encode()
            req = urllib.request.Request(
                f"http://127.0.0.1:{get_port()}/render",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            resp = urllib.request.urlopen(req, timeout=5)
            data = json.loads(resp.read())
            assert data["ok"] is True, f"Render failed: {data}"
            assert "spec" in data
        finally:
            os.unlink(xl)
