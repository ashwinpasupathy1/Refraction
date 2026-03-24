"""Multi-graph layout engine for Refraction.

Composes multiple chart specs into a single LayoutSpec for
multi-panel figures (e.g. A/B/C/D panels in a Nature figure).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Any

_log = logging.getLogger(__name__)


@dataclass
class PanelSpec:
    """A single panel within a multi-panel layout."""
    row: int
    col: int
    chart_type: str
    config: dict = field(default_factory=dict)
    data_path: str = ""
    chart_spec: dict | None = None
    label: str = ""          # e.g. "A", "B", "C"
    row_span: int = 1
    col_span: int = 1
    padding_px: int = 12

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class LayoutSpec:
    """Multi-panel layout specification."""
    rows: int = 1
    cols: int = 1
    panels: list[PanelSpec] = field(default_factory=list)
    title: str = ""
    export_width_mm: float = 183.0   # Nature double-column default
    export_height_mm: float = 247.0
    gap_px: int = 16
    panel_labels: bool = True        # Show A, B, C labels

    def to_dict(self) -> dict:
        d = asdict(self)
        d["panels"] = [p.to_dict() for p in self.panels]
        return d


_PANEL_LABELS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _auto_label(index: int) -> str:
    """Return A, B, C, ... for panel index."""
    if index < len(_PANEL_LABELS):
        return _PANEL_LABELS[index]
    return f"P{index + 1}"


def _infer_grid(n_panels: int) -> tuple[int, int]:
    """Infer a reasonable rows x cols grid for n panels."""
    if n_panels <= 1:
        return 1, 1
    if n_panels == 2:
        return 1, 2
    if n_panels <= 4:
        return 2, 2
    if n_panels <= 6:
        return 2, 3
    if n_panels <= 9:
        return 3, 3
    if n_panels <= 12:
        return 3, 4
    # 4 columns max, as many rows as needed
    cols = 4
    rows = (n_panels + cols - 1) // cols
    return rows, cols


def analyze_layout(panel_configs: list[dict], **layout_kw) -> dict:
    """Build a multi-panel layout by analyzing each panel independently.

    Args:
        panel_configs: list of dicts, each with:
            - chart_type: str (e.g. "bar", "scatter")
            - config: dict of chart kwargs (must include excel_path or data_path)
            - position: [row, col] (optional; auto-assigned if missing)
            - row_span / col_span: int (optional, default 1)
        layout_kw: optional overrides for LayoutSpec fields
            (title, export_width_mm, export_height_mm, gap_px, panel_labels)

    Returns:
        dict with keys: ok (bool), layout (LayoutSpec as dict), errors (list)
    """
    from refraction.analysis.engine import analyze as _analyze_chart

    errors: list[str] = []
    panels: list[PanelSpec] = []

    # Determine grid size
    explicit_positions = [
        pc.get("position") for pc in panel_configs if pc.get("position")
    ]

    if explicit_positions:
        max_row = max(p[0] for p in explicit_positions) + 1
        max_col = max(p[1] for p in explicit_positions) + 1
        rows = max(max_row, layout_kw.get("rows", 1))
        cols = max(max_col, layout_kw.get("cols", 1))
    else:
        rows, cols = _infer_grid(len(panel_configs))

    # Auto-assign positions for panels without explicit position
    used_positions: set[tuple[int, int]] = set()
    for pc in panel_configs:
        if pc.get("position"):
            used_positions.add(tuple(pc["position"]))

    auto_idx = 0
    for pc in panel_configs:
        if not pc.get("position"):
            while (auto_idx // cols, auto_idx % cols) in used_positions:
                auto_idx += 1
            pc["position"] = [auto_idx // cols, auto_idx % cols]
            used_positions.add(tuple(pc["position"]))
            auto_idx += 1

    # Build each panel's chart spec
    for i, pc in enumerate(panel_configs):
        chart_type = pc.get("chart_type", "bar")
        config = pc.get("config", {})
        pos = pc.get("position", [0, 0])

        # Merge data_path into config as excel_path if needed
        if "data_path" in pc and "excel_path" not in config:
            config["excel_path"] = pc["data_path"]

        panel = PanelSpec(
            row=pos[0],
            col=pos[1],
            chart_type=chart_type,
            config=config,
            data_path=config.get("excel_path", ""),
            label=pc.get("label", _auto_label(i)),
            row_span=pc.get("row_span", 1),
            col_span=pc.get("col_span", 1),
            padding_px=pc.get("padding_px", 12),
        )

        # Run analysis for this panel
        try:
            excel_path = config.get("excel_path", "")
            result = _analyze_chart(chart_type, excel_path, config)
            if isinstance(result, dict) and not result.get("ok", False):
                errors.append(f"Panel {panel.label}: {result.get('error', 'unknown error')}")
                panel.chart_spec = None
            else:
                panel.chart_spec = result
        except Exception as e:
            _log.exception("Layout panel %s failed", panel.label)
            errors.append(f"Panel {panel.label}: {e}")
            panel.chart_spec = None

        panels.append(panel)

    layout = LayoutSpec(
        rows=rows,
        cols=cols,
        panels=panels,
        title=layout_kw.get("title", ""),
        export_width_mm=layout_kw.get("export_width_mm", 183.0),
        export_height_mm=layout_kw.get("export_height_mm", 247.0),
        gap_px=layout_kw.get("gap_px", 16),
        panel_labels=layout_kw.get("panel_labels", True),
    )

    return {
        "ok": len(errors) == 0,
        "layout": layout.to_dict(),
        "errors": errors,
    }


def validate_layout(layout_dict: dict) -> list[str]:
    """Validate a layout specification dict. Returns list of error strings."""
    errors = []
    rows = layout_dict.get("rows", 0)
    cols = layout_dict.get("cols", 0)

    if rows < 1:
        errors.append("Layout must have at least 1 row")
    if cols < 1:
        errors.append("Layout must have at least 1 column")
    if rows > 10:
        errors.append("Layout cannot exceed 10 rows")
    if cols > 10:
        errors.append("Layout cannot exceed 10 columns")

    panels = layout_dict.get("panels", [])
    if not panels:
        errors.append("Layout must have at least 1 panel")

    positions = set()
    for i, p in enumerate(panels):
        pos = (p.get("row", 0), p.get("col", 0))
        if pos in positions:
            errors.append(f"Duplicate panel position: row={pos[0]}, col={pos[1]}")
        positions.add(pos)
        if pos[0] >= rows or pos[1] >= cols:
            errors.append(
                f"Panel {i} position ({pos[0]},{pos[1]}) exceeds grid ({rows}x{cols})"
            )

    return errors
