"""Tests for refraction.analysis.layout — multi-panel layout engine."""

import json
import os
import sys
import tempfile

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def _make_bar_excel(groups, path=None):
    """Create a simple bar chart Excel file."""
    path = path or tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False).name
    max_n = max(len(v) for v in groups.values())
    data = {}
    for name, vals in groups.items():
        padded = list(vals) + [None] * (max_n - len(vals))
        data[name] = padded
    pd.DataFrame(data).to_excel(path, index=False)
    return path


@pytest.fixture
def bar_excel_path():
    path = _make_bar_excel({"Control": [1, 2, 3, 4, 5], "Drug": [4, 5, 6, 7, 8]})
    yield path
    os.unlink(path)


@pytest.fixture
def two_bar_excels():
    p1 = _make_bar_excel({"A": [1, 2, 3], "B": [4, 5, 6]})
    p2 = _make_bar_excel({"X": [10, 20], "Y": [30, 40]})
    yield p1, p2
    os.unlink(p1)
    os.unlink(p2)


class TestLayoutSpec:
    def test_layout_spec_creation(self):
        from refraction.analysis.layout import LayoutSpec, PanelSpec
        layout = LayoutSpec(rows=2, cols=2, title="Test")
        assert layout.rows == 2
        assert layout.cols == 2
        assert layout.title == "Test"
        assert layout.export_width_mm == 183.0

    def test_layout_spec_to_dict(self):
        from refraction.analysis.layout import LayoutSpec
        layout = LayoutSpec(rows=1, cols=2)
        d = layout.to_dict()
        assert isinstance(d, dict)
        assert d["rows"] == 1
        assert d["cols"] == 2
        assert "panels" in d

    def test_panel_spec_to_dict(self):
        from refraction.analysis.layout import PanelSpec
        panel = PanelSpec(row=0, col=1, chart_type="bar", label="B")
        d = panel.to_dict()
        assert d["row"] == 0
        assert d["col"] == 1
        assert d["label"] == "B"


class TestInferGrid:
    def test_single_panel(self):
        from refraction.analysis.layout import _infer_grid
        assert _infer_grid(1) == (1, 1)

    def test_two_panels(self):
        from refraction.analysis.layout import _infer_grid
        assert _infer_grid(2) == (1, 2)

    def test_four_panels(self):
        from refraction.analysis.layout import _infer_grid
        assert _infer_grid(4) == (2, 2)

    def test_six_panels(self):
        from refraction.analysis.layout import _infer_grid
        r, c = _infer_grid(6)
        assert r * c >= 6


class TestAnalyzeLayout:
    def test_single_panel(self, bar_excel_path):
        from refraction.analysis.layout import analyze_layout
        result = analyze_layout([
            {"chart_type": "bar", "config": {"excel_path": bar_excel_path}},
        ])
        assert result["ok"] is True
        layout = result["layout"]
        assert layout["rows"] == 1
        assert layout["cols"] == 1
        assert len(layout["panels"]) == 1
        assert layout["panels"][0]["label"] == "A"

    def test_two_panels_auto_position(self, two_bar_excels):
        from refraction.analysis.layout import analyze_layout
        p1, p2 = two_bar_excels
        result = analyze_layout([
            {"chart_type": "bar", "config": {"excel_path": p1}},
            {"chart_type": "bar", "config": {"excel_path": p2}},
        ])
        assert result["ok"] is True
        layout = result["layout"]
        assert layout["rows"] == 1
        assert layout["cols"] == 2
        assert len(layout["panels"]) == 2

    def test_explicit_positions(self, bar_excel_path):
        from refraction.analysis.layout import analyze_layout
        result = analyze_layout([
            {"chart_type": "bar", "config": {"excel_path": bar_excel_path},
             "position": [0, 0]},
            {"chart_type": "bar", "config": {"excel_path": bar_excel_path},
             "position": [1, 0]},
        ])
        layout = result["layout"]
        assert layout["rows"] >= 2

    def test_panel_labels_auto(self, two_bar_excels):
        from refraction.analysis.layout import analyze_layout
        p1, p2 = two_bar_excels
        result = analyze_layout([
            {"chart_type": "bar", "config": {"excel_path": p1}},
            {"chart_type": "bar", "config": {"excel_path": p2}},
        ])
        labels = [p["label"] for p in result["layout"]["panels"]]
        assert labels == ["A", "B"]

    def test_chart_specs_populated(self, bar_excel_path):
        from refraction.analysis.layout import analyze_layout
        result = analyze_layout([
            {"chart_type": "bar", "config": {"excel_path": bar_excel_path}},
        ])
        panel = result["layout"]["panels"][0]
        assert panel["chart_spec"] is not None
        assert "data" in panel["chart_spec"]

    def test_bad_chart_type_reports_error(self, bar_excel_path):
        from refraction.analysis.layout import analyze_layout
        result = analyze_layout([
            {"chart_type": "nonexistent", "config": {"excel_path": bar_excel_path}},
        ])
        assert len(result["errors"]) > 0

    def test_layout_title_passthrough(self, bar_excel_path):
        from refraction.analysis.layout import analyze_layout
        result = analyze_layout(
            [{"chart_type": "bar", "config": {"excel_path": bar_excel_path}}],
            title="My Figure",
        )
        assert result["layout"]["title"] == "My Figure"


class TestValidateLayout:
    def test_valid_layout(self):
        from refraction.analysis.layout import validate_layout
        errors = validate_layout({
            "rows": 2, "cols": 2,
            "panels": [
                {"row": 0, "col": 0},
                {"row": 0, "col": 1},
            ]
        })
        assert errors == []

    def test_zero_rows(self):
        from refraction.analysis.layout import validate_layout
        errors = validate_layout({"rows": 0, "cols": 1, "panels": [{"row": 0, "col": 0}]})
        assert any("row" in e.lower() for e in errors)

    def test_no_panels(self):
        from refraction.analysis.layout import validate_layout
        errors = validate_layout({"rows": 1, "cols": 1, "panels": []})
        assert any("panel" in e.lower() for e in errors)

    def test_duplicate_positions(self):
        from refraction.analysis.layout import validate_layout
        errors = validate_layout({
            "rows": 2, "cols": 2,
            "panels": [
                {"row": 0, "col": 0},
                {"row": 0, "col": 0},
            ]
        })
        assert any("duplicate" in e.lower() for e in errors)
