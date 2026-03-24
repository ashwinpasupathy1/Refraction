"""Tests for refraction.io.project_v2 — .refract project file format."""

import json
import os
import sys
import tempfile
import zipfile

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from refraction.io.project_v2 import (
    save_project,
    load_project,
    get_project_info,
    cleanup_project,
    EXTENSION,
    FORMAT_VERSION,
)


@pytest.fixture
def sample_excel():
    path = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False).name
    pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]}).to_excel(path, index=False)
    yield path
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass


@pytest.fixture
def sample_panels(sample_excel):
    return [
        {
            "chart_type": "bar",
            "config": {"excel_path": sample_excel, "title": "Panel A"},
            "data_path": sample_excel,
            "position": [0, 0],
            "label": "A",
        },
        {
            "chart_type": "box",
            "config": {"excel_path": sample_excel, "title": "Panel B"},
            "data_path": sample_excel,
            "position": [0, 1],
            "label": "B",
        },
    ]


@pytest.fixture
def temp_refract_path():
    path = tempfile.NamedTemporaryFile(suffix=".refract", delete=False).name
    yield path
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass


class TestSaveProject:
    def test_saves_zip_file(self, sample_panels, temp_refract_path):
        save_project(temp_refract_path, sample_panels)
        assert os.path.exists(temp_refract_path)
        assert zipfile.is_zipfile(temp_refract_path)

    def test_contains_required_files(self, sample_panels, temp_refract_path):
        save_project(temp_refract_path, sample_panels)
        with zipfile.ZipFile(temp_refract_path, "r") as zf:
            names = zf.namelist()
            assert "metadata.json" in names
            assert "project.json" in names

    def test_metadata_has_version(self, sample_panels, temp_refract_path):
        save_project(temp_refract_path, sample_panels)
        with zipfile.ZipFile(temp_refract_path, "r") as zf:
            meta = json.loads(zf.read("metadata.json").decode())
            assert meta["format_version"] == FORMAT_VERSION
            assert "app_version" in meta
            assert "created" in meta
            assert "created_iso" in meta

    def test_embeds_data_files(self, sample_panels, temp_refract_path):
        save_project(temp_refract_path, sample_panels)
        with zipfile.ZipFile(temp_refract_path, "r") as zf:
            data_files = [n for n in zf.namelist() if n.startswith("data/")]
            assert len(data_files) >= 1

    def test_project_json_has_panels(self, sample_panels, temp_refract_path):
        save_project(temp_refract_path, sample_panels)
        with zipfile.ZipFile(temp_refract_path, "r") as zf:
            project = json.loads(zf.read("project.json").decode())
            assert "panels" in project
            assert len(project["panels"]) == 2

    def test_no_absolute_paths_in_archive(self, sample_panels, temp_refract_path):
        save_project(temp_refract_path, sample_panels)
        with zipfile.ZipFile(temp_refract_path, "r") as zf:
            project = json.loads(zf.read("project.json").decode())
            for panel in project["panels"]:
                assert "data_path" not in panel
                config = panel.get("config", {})
                assert "excel_path" not in config

    def test_saves_layout(self, sample_panels, temp_refract_path):
        save_project(
            temp_refract_path, sample_panels,
            layout={"rows": 1, "cols": 2, "title": "Test Figure"},
        )
        with zipfile.ZipFile(temp_refract_path, "r") as zf:
            project = json.loads(zf.read("project.json").decode())
            assert project["layout"]["rows"] == 1
            assert project["layout"]["title"] == "Test Figure"

    def test_saves_settings(self, sample_panels, temp_refract_path):
        save_project(
            temp_refract_path, sample_panels,
            settings={"dark_mode": True},
        )
        with zipfile.ZipFile(temp_refract_path, "r") as zf:
            project = json.loads(zf.read("project.json").decode())
            assert project["settings"]["dark_mode"] is True

    def test_custom_metadata(self, sample_panels, temp_refract_path):
        save_project(
            temp_refract_path, sample_panels,
            metadata={"author": "Test User"},
        )
        with zipfile.ZipFile(temp_refract_path, "r") as zf:
            meta = json.loads(zf.read("metadata.json").decode())
            assert meta["author"] == "Test User"

    def test_auto_appends_extension(self, sample_panels):
        path = tempfile.NamedTemporaryFile(suffix="", delete=False).name
        try:
            result = save_project(path, sample_panels)
            assert result.endswith(EXTENSION)
            assert os.path.exists(result)
        finally:
            try:
                os.unlink(result)
            except FileNotFoundError:
                pass

    def test_thumbnails_saved(self, sample_panels, temp_refract_path):
        thumbnails = {"A": b"\x89PNG_fake_data"}
        save_project(temp_refract_path, sample_panels, thumbnails=thumbnails)
        with zipfile.ZipFile(temp_refract_path, "r") as zf:
            assert "thumbnails/A.png" in zf.namelist()


class TestLoadProject:
    def test_round_trip(self, sample_panels, temp_refract_path):
        save_project(temp_refract_path, sample_panels,
                     layout={"rows": 1, "cols": 2},
                     settings={"theme": "dark"})
        result = load_project(temp_refract_path)
        try:
            assert "metadata" in result
            assert "panels" in result
            assert "layout" in result
            assert "settings" in result
            assert len(result["panels"]) == 2
            assert result["layout"]["rows"] == 1
            assert result["settings"]["theme"] == "dark"
        finally:
            cleanup_project(result)

    def test_data_files_extracted(self, sample_panels, temp_refract_path):
        save_project(temp_refract_path, sample_panels)
        result = load_project(temp_refract_path)
        try:
            for panel in result["panels"]:
                data_path = panel.get("data_path", "")
                if data_path:
                    assert os.path.exists(data_path), f"Data file not extracted: {data_path}"
                    # Verify the data is readable
                    df = pd.read_excel(data_path)
                    assert len(df) > 0
        finally:
            cleanup_project(result)

    def test_panel_configs_restored(self, sample_panels, temp_refract_path):
        save_project(temp_refract_path, sample_panels)
        result = load_project(temp_refract_path)
        try:
            assert result["panels"][0]["chart_type"] == "bar"
            assert result["panels"][1]["chart_type"] == "box"
            assert result["panels"][0]["label"] == "A"
            assert result["panels"][1]["label"] == "B"
        finally:
            cleanup_project(result)

    def test_file_not_found_raises(self):
        with pytest.raises(FileNotFoundError):
            load_project("/nonexistent/path/file.refract")

    def test_metadata_version(self, sample_panels, temp_refract_path):
        save_project(temp_refract_path, sample_panels)
        result = load_project(temp_refract_path)
        try:
            assert result["metadata"]["format_version"] == FORMAT_VERSION
        finally:
            cleanup_project(result)


class TestGetProjectInfo:
    def test_returns_info(self, sample_panels, temp_refract_path):
        save_project(temp_refract_path, sample_panels,
                     layout={"rows": 1, "cols": 2})
        info = get_project_info(temp_refract_path)
        assert info["format_version"] == FORMAT_VERSION
        assert info["n_panels"] == 2
        assert "1x2" in info["layout_summary"]


class TestCleanup:
    def test_cleanup_removes_temp_dir(self, sample_panels, temp_refract_path):
        save_project(temp_refract_path, sample_panels)
        result = load_project(temp_refract_path)
        temp_dir = result["temp_dir"]
        assert os.path.isdir(temp_dir)
        cleanup_project(result)
        assert not os.path.exists(temp_dir)

    def test_cleanup_handles_missing_dir(self):
        # Should not raise
        cleanup_project({"temp_dir": "/nonexistent/path"})
        cleanup_project({})
