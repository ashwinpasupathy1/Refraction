"""FastAPI server for Refraction -- serves the analysis API.

Endpoints:
    GET  /health       -- liveness check
    GET  /chart-types  -- list supported chart types
    POST /analyze      -- run analysis on uploaded data
    POST /upload       -- accept .xlsx/.xls/.csv files
"""

import logging
import os
import tempfile
import threading
import uuid
from typing import Any, Optional

_log = logging.getLogger(__name__)

# -- Logging setup ---------------------------------------------------------
_log_dir = os.path.expanduser("~/Library/Logs/Refraction")
os.makedirs(_log_dir, exist_ok=True)
_file_handler = logging.FileHandler(
    os.path.join(_log_dir, "api.log"), encoding="utf-8"
)
_file_handler.setFormatter(logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
))
logging.getLogger("refraction").addHandler(_file_handler)
logging.getLogger("refraction").setLevel(logging.DEBUG)

_server_thread: Optional[threading.Thread] = None
_PORT = 7331


def get_port() -> int:
    return _PORT


def start_server() -> None:
    """Start the FastAPI server in a background daemon thread."""
    global _server_thread
    if _server_thread and _server_thread.is_alive():
        return  # Already running

    def _run():
        import uvicorn
        uvicorn.run(_make_app(), host="127.0.0.1", port=_PORT,
                    log_level="warning", access_log=False)

    _server_thread = threading.Thread(target=_run, daemon=True,
                                      name="refraction-server")
    _server_thread.start()


def _make_app():
    from fastapi import FastAPI, Request, UploadFile, File as FastAPIFile
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel

    # ------------------------------------------------------------------
    # Request models
    # ------------------------------------------------------------------
    class AnalyzeRequest(BaseModel):
        chart_type: str
        excel_path: str
        config: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # App & middleware
    # ------------------------------------------------------------------
    API_KEY = os.environ.get("REFRACTION_API_KEY", "")

    api = FastAPI(title="Refraction API", version="0.1.0")

    api.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @api.middleware("http")
    async def check_auth(request: Request, call_next):
        """Require API key for non-local requests (if set)."""
        client_ip = request.client.host if request.client else ""
        if client_ip in ("127.0.0.1", "localhost", "::1"):
            return await call_next(request)
        if API_KEY and request.headers.get("x-api-key") != API_KEY:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        return await call_next(request)

    # ------------------------------------------------------------------
    # Endpoints
    # ------------------------------------------------------------------
    @api.get("/health")
    def health():
        return {"status": "ok"}

    @api.get("/chart-types")
    def chart_types():
        """List available chart types."""
        return {
            "priority": ["bar", "grouped_bar", "line", "scatter"],
            "all": [
                "bar", "grouped_bar", "line", "scatter",
                "box", "violin", "heatmap", "histogram",
                "kaplan_meier", "two_way_anova", "before_after",
                "subcolumn_scatter", "curve_fit", "column_stats",
                "contingency", "repeated_measures", "chi_square_gof",
                "stacked_bar", "bubble", "dot_plot", "bland_altman",
                "forest_plot", "area_chart", "raincloud", "qq_plot",
                "lollipop", "waterfall", "pyramid", "ecdf",
            ],
        }

    @api.post("/analyze")
    def analyze_endpoint(req: AnalyzeRequest):
        """Run renderer-independent analysis on uploaded data."""
        try:
            from refraction.analysis import analyze
            result = analyze(req.chart_type, req.excel_path, req.config)
            if not result.get("ok"):
                return JSONResponse(result, status_code=400)
            return result
        except Exception as exc:
            _log.exception("Analyze failed for chart_type=%s", req.chart_type)
            return JSONResponse(
                {"ok": False, "error": str(exc)}, status_code=500
            )

    # ------------------------------------------------------------------
    # /render — bridge for the SwiftUI app
    # ------------------------------------------------------------------
    class RenderRequest(BaseModel):
        chart_type: str
        kw: dict[str, Any] = {}

    @api.post("/render")
    def render_endpoint(req: RenderRequest):
        """Bridge endpoint for the SwiftUI app.

        Accepts the format the Swift APIClient sends, transforms into
        an analyze() call, then reshapes the response into the ChartSpec
        JSON schema the Swift RenderResponse / ChartSpec structs expect.
        """
        try:
            from refraction.analysis import analyze

            kw = dict(req.kw)
            excel_path = kw.pop("excel_path", "")
            if not excel_path:
                return JSONResponse(
                    {"ok": False, "error": "Missing excel_path"},
                    status_code=400,
                )

            # Map Swift config keys to engine config keys
            config = dict(kw)
            if "error" in config and "error_type" not in config:
                config["error_type"] = config.pop("error")
            if "xlabel" in config and "x_label" not in config:
                config["x_label"] = config.get("xlabel", "")
            if "ytitle" in config and "y_label" not in config:
                config["y_label"] = config.get("ytitle", "")

            result = analyze(req.chart_type, excel_path, config)

            if not result.get("ok"):
                return JSONResponse(
                    {"ok": False, "error": result.get("error", "Analysis failed")},
                    status_code=400,
                )

            return {"ok": True, "spec": _to_chart_spec(result, config)}

        except Exception as exc:
            _log.exception("Render failed for chart_type=%s", req.chart_type)
            return JSONResponse(
                {"ok": False, "error": str(exc)}, status_code=500,
            )

    def _to_chart_spec(result: dict, config: dict) -> dict:
        """Transform analyze() output into the ChartSpec JSON schema."""
        palette = [
            "#E8453C", "#2274A5", "#32936F", "#F18F01", "#A846A0",
            "#6B4226", "#048A81", "#D4AC0D", "#3B1F2B", "#44BBA4",
        ]

        # -- groups: nest values into {raw, mean, sem, sd, ci95, n} --
        groups = []
        for g in result.get("groups", []):
            raw = g.get("values", [])
            groups.append({
                "name": g.get("name", ""),
                "values": {
                    "raw": raw if isinstance(raw, list) else [],
                    "mean": g.get("mean"),
                    "sem": g.get("sem"),
                    "sd": g.get("sd"),
                    "ci95": g.get("ci95"),
                    "n": g.get("n", 0),
                },
                "color": g.get("color", palette[len(groups) % len(palette)]),
            })

        # -- comparisons → stats + brackets --
        comparisons_out = []
        brackets = []
        group_names = [g["name"] for g in groups]
        for i, c in enumerate(result.get("comparisons", [])):
            if "error" in c:
                continue
            p = c.get("p_value", 1.0)
            label = c.get("stars", "ns")
            comparisons_out.append({
                "group_1": c.get("group_a", ""),
                "group_2": c.get("group_b", ""),
                "p_value": p,
                "significant": p < config.get("p_sig_threshold", 0.05),
                "label": label,
            })
            # Build bracket indices
            left = group_names.index(c["group_a"]) if c.get("group_a") in group_names else i
            right = group_names.index(c["group_b"]) if c.get("group_b") in group_names else i + 1
            brackets.append({
                "left_index": left,
                "right_index": right,
                "label": label,
                "stacking_order": i,
            })

        stats_test = config.get("stats_test", "none")
        stats = None
        if stats_test != "none" and comparisons_out:
            stats = {
                "test_name": stats_test,
                "p_value": comparisons_out[0]["p_value"] if len(comparisons_out) == 1 else None,
                "statistic": None,
                "comparisons": comparisons_out,
                "normality": None,
                "effect_size": None,
                "warning": None,
            }

        error_type = config.get("error_type", config.get("error", "sem"))

        return {
            "chart_type": result.get("chart_type", "bar"),
            "groups": groups,
            "style": {
                "colors": [g["color"] for g in groups] or palette[:1],
                "show_points": bool(config.get("show_points", False)),
                "show_brackets": True,
                "point_size": config.get("point_size", 6.0),
                "point_alpha": config.get("point_alpha", 0.8),
                "bar_width": config.get("bar_width", 0.6),
                "error_type": error_type,
                "axis_style": config.get("axis_style", "open"),
            },
            "axes": {
                "title": result.get("title", ""),
                "x_label": result.get("x_label", ""),
                "y_label": result.get("y_label", ""),
                "x_scale": "linear",
                "y_scale": config.get("yscale", "linear"),
                "x_range": None,
                "y_range": config.get("ylim"),
                "tick_direction": config.get("tick_dir", "out"),
                "spine_width": config.get("spine_width", 1.0),
                "font_size": config.get("font_size", 12.0),
            },
            "stats": stats,
            "brackets": brackets if stats else [],
            "reference_line": (
                {"y": config["ref_line"], "label": config.get("ref_line_label", "")}
                if "ref_line" in config else None
            ),
        }

    # ------------------------------------------------------------------
    # File upload
    # ------------------------------------------------------------------
    UPLOAD_DIR = os.path.join(tempfile.gettempdir(), "refraction-uploads")
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    @api.post("/upload")
    async def upload_file(file: UploadFile = FastAPIFile(...)):
        """Accept .xlsx/.xls/.csv upload; return server-side path."""
        ext = os.path.splitext(file.filename or "")[1].lower()
        if ext not in (".xlsx", ".xls", ".csv"):
            return JSONResponse(
                {"ok": False, "error": f"Unsupported file type: {ext}"},
                status_code=400,
            )
        contents = await file.read()
        if len(contents) > 10 * 1024 * 1024:  # 10 MB limit
            return JSONResponse(
                {"ok": False, "error": "File too large (max 10 MB)"},
                status_code=413,
            )
        safe_name = f"{uuid.uuid4().hex}{ext}"
        dest = os.path.join(UPLOAD_DIR, safe_name)
        with open(dest, "wb") as f:
            f.write(contents)
        return {"ok": True, "path": dest, "filename": file.filename}

    # ── Phase 10a: Multi-panel layout ──────────────────────────────
    class LayoutRequest(BaseModel):
        panels: list[dict[str, Any]]
        title: str = ""
        export_width_mm: float = 183.0
        export_height_mm: float = 247.0
        gap_px: int = 16
        panel_labels: bool = True

    @api.post("/analyze-layout")
    def analyze_layout_endpoint(req: LayoutRequest):
        """Analyze a multi-panel layout, returning combined specs."""
        try:
            from refraction.analysis.layout import analyze_layout
            result = analyze_layout(
                req.panels,
                title=req.title,
                export_width_mm=req.export_width_mm,
                export_height_mm=req.export_height_mm,
                gap_px=req.gap_px,
                panel_labels=req.panel_labels,
            )
            return result
        except Exception as e:
            _log.exception("analyze-layout failed")
            return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

    # ── Phase 10b: Curve models ──────────────────────────────────
    @api.get("/curve-models")
    def list_curve_models():
        """List all available curve fitting models by category."""
        from refraction.analysis.curve_models import list_models_by_category, model_count
        return {
            "ok": True,
            "models": list_models_by_category(),
            "total": model_count(),
        }

    class CurveFitRequest(BaseModel):
        x: list[float]
        y: list[float]
        model_name: str
        initial_params: list[float] | None = None

    @api.post("/curve-fit")
    def curve_fit_endpoint(req: CurveFitRequest):
        """Fit a curve model to X/Y data."""
        try:
            import numpy as _np
            from refraction.analysis.curve_fit import fit_curve
            result = fit_curve(
                _np.array(req.x),
                _np.array(req.y),
                req.model_name,
                initial_params=req.initial_params,
            )
            return {"ok": True, "fit": result.to_dict()}
        except ValueError as e:
            return JSONResponse({"ok": False, "error": str(e)}, status_code=400)
        except Exception as e:
            _log.exception("curve-fit failed")
            return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

    # ── Phase 10d: Column transforms ─────────────────────────────
    @api.get("/transforms")
    def list_transforms_endpoint():
        """List all available column transformations."""
        from refraction.analysis.transforms import list_transforms, transform_count
        return {
            "ok": True,
            "transforms": list_transforms(),
            "total": transform_count(),
        }

    class TransformRequest(BaseModel):
        data_path: str
        column: str | int
        operation: str
        params: dict[str, Any] = {}
        sheet: int | str = 0

    @api.post("/transform")
    def transform_endpoint(req: TransformRequest):
        """Apply a transform to a column; return path to new Excel file."""
        try:
            import pandas as _pd
            from refraction.analysis.transforms import transform_column

            df = _pd.read_excel(req.data_path, sheet_name=req.sheet)
            result_series = transform_column(df, req.column, req.operation, **req.params)

            # Write to new temp file
            new_df = df.copy()
            col_name = req.column if isinstance(req.column, str) else df.columns[req.column]
            new_df[f"{col_name}_{req.operation}"] = result_series

            dest = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}.xlsx")
            new_df.to_excel(dest, index=False)
            return {"ok": True, "path": dest, "column": f"{col_name}_{req.operation}"}
        except ValueError as e:
            return JSONResponse({"ok": False, "error": str(e)}, status_code=400)
        except Exception as e:
            _log.exception("transform failed")
            return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

    # ── Phase 10e: Project files ─────────────────────────────────
    class ProjectSaveRequest(BaseModel):
        panels: list[dict[str, Any]]
        layout: dict[str, Any] = {}
        settings: dict[str, Any] = {}
        metadata: dict[str, Any] = {}

    @api.post("/project/save")
    def project_save(req: ProjectSaveRequest):
        """Save a multi-panel project as .refract archive."""
        try:
            from refraction.io.project_v2 import save_project
            dest = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}.refract")
            path = save_project(
                dest,
                req.panels,
                metadata=req.metadata,
                layout=req.layout,
                settings=req.settings,
            )
            return {"ok": True, "path": path}
        except Exception as e:
            _log.exception("project save failed")
            return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

    @api.post("/project/load")
    async def project_load(file: UploadFile = FastAPIFile(...)):
        """Upload and load a .refract project file."""
        try:
            from refraction.io.project_v2 import load_project
            ext = os.path.splitext(file.filename or "")[1].lower()
            if ext not in (".refract",):
                return JSONResponse(
                    {"ok": False, "error": f"Unsupported file type: {ext}"},
                    status_code=400,
                )
            contents = await file.read()
            dest = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}.refract")
            with open(dest, "wb") as f:
                f.write(contents)
            result = load_project(dest)
            # Don't return temp_dir in API response
            result.pop("temp_dir", None)
            return {"ok": True, "project": result}
        except Exception as e:
            _log.exception("project load failed")
            return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

    return api
