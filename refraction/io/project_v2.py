"""Project file format v2 — .refract archives.

A .refract file is a ZIP archive containing:
    project.json   — layout, panel configs, chart types, settings
    metadata.json  — version, created date, app version, author
    data/          — copies of all referenced Excel/CSV files
    thumbnails/    — optional panel thumbnail PNGs

This module handles save/load round-trips for multi-panel projects.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import tempfile
import time
import zipfile
from typing import Any

_log = logging.getLogger(__name__)

EXTENSION = ".refract"
FORMAT_VERSION = 2
APP_VERSION = "10.0.0"


def save_project(
    path: str,
    panels: list[dict],
    metadata: dict | None = None,
    *,
    layout: dict | None = None,
    settings: dict | None = None,
    thumbnails: dict[str, bytes] | None = None,
) -> str:
    """Save a multi-panel project as a .refract ZIP archive.

    Args:
        path: Output file path (should end with .refract).
        panels: List of panel config dicts. Each panel has:
            - chart_type: str
            - config: dict of chart kwargs
            - data_path: str (path to Excel/CSV file)
            - position: [row, col]
            - label: str (e.g. "A")
        metadata: Optional dict with author, description, tags, etc.
        layout: Optional layout config (rows, cols, title, export dims).
        settings: Optional global settings dict.
        thumbnails: Optional dict of {panel_label: png_bytes}.

    Returns:
        The path written to.
    """
    if not path.endswith(EXTENSION):
        path += EXTENSION

    metadata = metadata or {}
    layout = layout or {}
    settings = settings or {}
    thumbnails = thumbnails or {}

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        # Metadata
        meta = {
            "format_version": FORMAT_VERSION,
            "app_version": APP_VERSION,
            "created": time.time(),
            "created_iso": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            **metadata,
        }
        zf.writestr("metadata.json", json.dumps(meta, indent=2))

        # Project definition — panels + layout + settings
        # Strip data_path from panels in the project.json (data is embedded)
        sanitized_panels = []
        data_file_map: dict[str, str] = {}  # original_path -> archive_name

        for i, panel in enumerate(panels):
            p = dict(panel)
            data_path = p.get("data_path", "")
            if data_path and os.path.exists(data_path):
                # Deduplicate: if we already added this file, reuse the name
                if data_path not in data_file_map:
                    ext = os.path.splitext(data_path)[1]
                    archive_name = f"data/panel_{i}{ext}"
                    data_file_map[data_path] = archive_name
                p["data_ref"] = data_file_map[data_path]
            else:
                p["data_ref"] = ""

            # Don't store absolute paths in the archive
            p.pop("data_path", None)
            if "config" in p:
                p["config"] = {k: v for k, v in p["config"].items()
                              if k != "excel_path"}
            sanitized_panels.append(p)

        project = {
            "panels": sanitized_panels,
            "layout": layout,
            "settings": settings,
        }
        zf.writestr("project.json", json.dumps(project, indent=2))

        # Embed data files
        for original_path, archive_name in data_file_map.items():
            zf.write(original_path, archive_name)

        # Thumbnails
        for label, png_bytes in thumbnails.items():
            zf.writestr(f"thumbnails/{label}.png", png_bytes)

    return path


def load_project(path: str) -> dict:
    """Load a .refract project archive.

    Returns dict with keys:
        metadata: dict
        panels: list of panel configs (with data_path pointing to temp files)
        layout: dict
        settings: dict
        temp_dir: str (caller should clean up when done)
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Project file not found: {path}")

    temp_dir = tempfile.mkdtemp(prefix="refraction_project_")

    result = {
        "metadata": {},
        "panels": [],
        "layout": {},
        "settings": {},
        "temp_dir": temp_dir,
    }

    with zipfile.ZipFile(path, "r") as zf:
        names = zf.namelist()

        # Metadata
        if "metadata.json" in names:
            result["metadata"] = json.loads(zf.read("metadata.json").decode())

        # Project
        if "project.json" in names:
            project = json.loads(zf.read("project.json").decode())
            result["layout"] = project.get("layout", {})
            result["settings"] = project.get("settings", {})

            # Extract data files and reconstruct panels
            for panel in project.get("panels", []):
                data_ref = panel.get("data_ref", "")
                if data_ref and data_ref in names:
                    # Extract to temp dir
                    dest = os.path.join(temp_dir, os.path.basename(data_ref))
                    with zf.open(data_ref) as src, open(dest, "wb") as dst:
                        dst.write(src.read())
                    panel["data_path"] = dest
                    if "config" in panel:
                        panel["config"]["excel_path"] = dest
                else:
                    panel["data_path"] = ""

                panel.pop("data_ref", None)
                result["panels"].append(panel)

    return result


def get_project_info(path: str) -> dict:
    """Read metadata from a .refract file without fully loading it.

    Returns dict with: format_version, app_version, created_iso,
    n_panels, layout_summary.
    """
    info = {
        "format_version": None,
        "app_version": None,
        "created_iso": None,
        "n_panels": 0,
        "layout_summary": "",
    }

    with zipfile.ZipFile(path, "r") as zf:
        names = zf.namelist()

        if "metadata.json" in names:
            meta = json.loads(zf.read("metadata.json").decode())
            info["format_version"] = meta.get("format_version")
            info["app_version"] = meta.get("app_version")
            info["created_iso"] = meta.get("created_iso")

        if "project.json" in names:
            project = json.loads(zf.read("project.json").decode())
            panels = project.get("panels", [])
            info["n_panels"] = len(panels)
            layout = project.get("layout", {})
            rows = layout.get("rows", 1)
            cols = layout.get("cols", 1)
            info["layout_summary"] = f"{rows}x{cols} grid, {len(panels)} panels"

    return info


def cleanup_project(result: dict) -> None:
    """Remove temporary files created by load_project."""
    temp_dir = result.get("temp_dir", "")
    if temp_dir and os.path.isdir(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)
