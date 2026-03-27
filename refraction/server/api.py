"""FastAPI server for Refraction -- serves the analysis API.

Endpoints:
    GET  /health       -- liveness check
    GET  /chart-types  -- list supported chart types
    POST /analyze      -- run analysis on uploaded data
    POST /upload       -- accept .xlsx/.xls/.csv files
"""

import atexit
import logging
import os
import pathlib
import shutil
import tempfile
import threading
import traceback
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


def _validate_data_path(path: str) -> str | None:
    """Validate data path. Returns error message or None if ok."""
    if not path:
        return "Missing file path"
    if not os.path.isfile(path):
        return f"File not found: {path}"
    ext = os.path.splitext(path)[1].lower()
    if ext not in (".xlsx", ".xls", ".csv"):
        return f"Unsupported file type: {ext}"
    return None


def _to_chart_spec(result: dict, config: dict) -> dict:
    """Transform analyze() output into the ChartSpec JSON schema."""
    palette = [
        "#E8453C", "#2274A5", "#32936F", "#F18F01", "#A846A0",
        "#6B4226", "#048A81", "#D4AC0D", "#3B1F2B", "#44BBA4",
    ]

    import math

    def _sanitize(v):
        """Replace NaN/Inf with None for JSON safety."""
        if v is None:
            return None
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            return None
        return v

    # -- groups: nest values into {raw, mean, sem, sd, ci95, n} --
    groups = []
    for g in result.get("groups", []):
        # Dedicated analyzers may return groups as plain strings (group names)
        if isinstance(g, str):
            continue
        raw = g.get("values", [])
        groups.append({
            "name": g.get("name", ""),
            "values": {
                "raw": raw if isinstance(raw, list) else [],
                "mean": _sanitize(g.get("mean")),
                "sem": _sanitize(g.get("sem")),
                "sd": _sanitize(g.get("sd")),
                "ci95": _sanitize(g.get("ci95")),
                "n": g.get("n", 0),
            },
            "color": g.get("color", palette[len(groups) % len(palette)]),
        })

    # -- comparisons -> stats + brackets --
    # Dedicated analyzers produce "annotations" (from StatsBracket);
    # the generic engine produces "comparisons".  Handle both.
    comparisons_out = []
    brackets = []
    group_names = [g["name"] for g in groups]
    raw_comparisons = result.get("comparisons", []) or result.get("annotations", [])
    for i, c in enumerate(raw_comparisons):
        if "error" in c:
            continue
        p = c.get("p_value", 1.0)
        label = c.get("stars", c.get("label", "ns"))
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

    # -- Compute Y-axis ticks from data --
    from refraction.core.stats import compute_axis_range
    y_values = []
    y_errors = []
    for g in groups:
        vals = g["values"]
        if vals["mean"] is not None:
            y_values.append(vals["mean"])
            err_key = error_type if error_type in ("sem", "sd", "ci95") else "sem"
            err = vals.get(err_key, 0) or 0
            y_errors.append(err)
        for rv in vals.get("raw", []):
            if isinstance(rv, (int, float)):
                y_values.append(rv)

    y_scale = config.get("yscale", "linear")
    y_axis_info = compute_axis_range(
        y_values,
        error_values=y_errors if y_errors else None,
        include_zero=True,
        scale=y_scale,
    )

    return {
        "chart_type": result.get("chart_type", "bar"),
        "groups": groups,
        "data": result.get("data", {}),
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
            "y_scale": y_scale,
            "x_range": None,
            "y_range": [y_axis_info["range_min"], y_axis_info["range_max"]],
            "y_ticks": y_axis_info["ticks"],
            "y_tick_labels": y_axis_info["tick_labels"],
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
        excel_path: str = ""
        data: dict[str, Any] | None = None  # {"columns": [...], "rows": [[...]]}
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
        """Run renderer-independent analysis on uploaded data.

        Accepts either:
        - ``excel_path``: path to a file on disk (legacy)
        - ``data``: inline JSON with ``columns`` and ``rows`` keys
        """
        try:
            df = None
            if req.data:
                # Inline data — convert to DataFrame directly
                import pandas as _pd
                columns = req.data.get("columns", [])
                rows = req.data.get("rows", [])
                df = _pd.DataFrame(rows, columns=columns)
            elif req.excel_path:
                path_err = _validate_data_path(req.excel_path)
                if path_err:
                    return JSONResponse(
                        {"ok": False, "error": path_err}, status_code=400
                    )
            else:
                return JSONResponse(
                    {"ok": False, "error": "Either excel_path or data must be provided"},
                    status_code=400,
                )
            from refraction.analysis import analyze
            result = analyze(req.chart_type, req.excel_path or "", req.config, df=df)
            if not result.get("ok"):
                return JSONResponse(result, status_code=400)
            return result
        except Exception as exc:
            _log.exception("Analyze failed for chart_type=%s", req.chart_type)
            return JSONResponse(
                {"ok": False, "error": str(exc), "traceback": traceback.format_exc()}, status_code=500
            )

    # ------------------------------------------------------------------
    # /render — bridge for the SwiftUI app
    # ------------------------------------------------------------------
    class RenderRequest(BaseModel):
        chart_type: str
        kw: dict[str, Any] = {}
        debug: bool = False

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
            debug_mode = kw.pop("_debug", False) or req.debug
            excel_path = kw.pop("excel_path", "")
            inline_data = kw.pop("data", None)

            # Build DataFrame from inline data if provided
            df = None
            if inline_data:
                import pandas as _pd
                columns = inline_data.get("columns", [])
                rows = inline_data.get("rows", [])
                df = _pd.DataFrame(rows, columns=columns)
            elif excel_path:
                path_err = _validate_data_path(excel_path)
                if path_err:
                    return JSONResponse(
                        {"ok": False, "error": path_err},
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

            # Collect engine trace
            trace = []
            trace.append(f"analyze(chart_type={req.chart_type!r}, path={os.path.basename(excel_path)!r}, inline={'yes' if df is not None else 'no'})")
            trace.append(f"config keys: {sorted(config.keys())}")

            result = analyze(req.chart_type, excel_path, config, df=df)

            if not result.get("ok"):
                return JSONResponse(
                    {"ok": False, "error": result.get("error", "Analysis failed"),
                     "_trace": trace + [f"FAILED: {result.get('error', '?')}"]},
                    status_code=400,
                )

            # Trace what the engine computed
            groups = result.get("groups", [])
            comparisons = result.get("comparisons", [])
            trace.append(f"result: ok={result.get('ok')}, {len(groups)} groups, {len(comparisons)} comparisons")
            if groups:
                for g in groups[:5]:
                    name = g.get("name", "?")
                    n = g.get("n", "?")
                    mean = g.get("mean")
                    mean_str = f"{mean:.4f}" if isinstance(mean, (int, float)) else "?"
                    trace.append(f"  group {name!r}: n={n}, mean={mean_str}")
            if comparisons:
                for c in comparisons[:5]:
                    ga = c.get("group_a", "?")
                    gb = c.get("group_b", "?")
                    p = c.get("p_value")
                    stars = c.get("stars", "")
                    p_str = f"{p:.6f}" if isinstance(p, (int, float)) else "?"
                    trace.append(f"  {ga} vs {gb}: p={p_str} {stars}")
            analyzer = result.get("_analyzer", "generic")
            trace.append(f"analyzer: {analyzer}")

            resp = {"ok": True, "spec": _to_chart_spec(result, config)}
            if debug_mode:
                resp["_trace"] = trace
            return resp

        except Exception as exc:
            _log.exception("Render failed for chart_type=%s", req.chart_type)
            tb_lines = traceback.format_exception(type(exc), exc, exc.__traceback__)
            tb_str = "".join(tb_lines)
            resp = {"ok": False, "error": str(exc), "traceback": tb_str}
            if debug_mode:
                resp["_trace"] = [f"EXCEPTION: {type(exc).__name__}: {exc}"] + [
                    line.rstrip() for line in tb_lines if line.strip()
                ]
            return JSONResponse(resp, status_code=500)

    # ------------------------------------------------------------------
    # File upload
    # ------------------------------------------------------------------
    UPLOAD_DIR = os.path.join(os.path.expanduser("~"), ".refraction", "data")
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    @api.post("/upload")
    async def upload_file(file: UploadFile = FastAPIFile(...)):
        """Accept .xlsx/.xls/.csv upload; return server-side path."""
        # Ensure upload dir exists (may have been cleaned by a previous server)
        os.makedirs(UPLOAD_DIR, exist_ok=True)
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

    # ── Sheet list (for Excel files) ─────────────────────────────
    class SheetListRequest(BaseModel):
        excel_path: str

    @api.post("/sheet-list")
    def sheet_list(req: SheetListRequest):
        """Return list of sheet names in an Excel file."""
        try:
            path_err = _validate_data_path(req.excel_path)
            if path_err:
                return JSONResponse(
                    {"ok": False, "error": path_err}, status_code=400
                )
            if req.excel_path.endswith(".csv"):
                return {"ok": True, "sheets": ["Sheet1"]}
            import openpyxl
            wb = openpyxl.load_workbook(req.excel_path, read_only=True)
            sheets = wb.sheetnames
            wb.close()
            return {"ok": True, "sheets": sheets}
        except Exception as exc:
            return JSONResponse(
                {"ok": False, "error": str(exc), "traceback": traceback.format_exc()}, status_code=400
            )

    # ── Validate table data ──────────────────────────────────────
    class ValidateTableRequest(BaseModel):
        excel_path: str
        table_type: str
        sheet: int | str = 0

    @api.post("/validate-table")
    def validate_table(req: ValidateTableRequest):
        """Validate that data matches the expected table type layout."""
        try:
            path_err = _validate_data_path(req.excel_path)
            if path_err:
                return JSONResponse(
                    {"ok": False, "error": path_err}, status_code=400
                )
            import pandas as pd
            from refraction.core.validators import (
                validate_bar, validate_line, validate_grouped_bar,
                validate_kaplan_meier, validate_heatmap,
                validate_two_way_anova, validate_contingency,
                validate_bland_altman, validate_forest_plot,
            )

            if req.excel_path.endswith(".csv"):
                df = pd.read_csv(req.excel_path, header=None)
            else:
                df = pd.read_excel(req.excel_path, sheet_name=req.sheet, header=None)

            # Map table_type to validator
            validator_map = {
                "column": validate_bar,
                "xy": validate_line,
                "grouped": validate_grouped_bar,
                "survival": validate_kaplan_meier,
                "contingency": validate_contingency,
                "multiple_variables": validate_heatmap,
                "two_way": validate_two_way_anova,
                "comparison": validate_bland_altman,
                "meta": validate_forest_plot,
            }

            validator = validator_map.get(req.table_type)
            if validator is None:
                # No specific validator — accept if it has numeric data
                return {
                    "ok": True,
                    "valid": True,
                    "errors": [],
                    "warnings": ["No specific validator for table type: " + req.table_type],
                    "shape": [len(df), len(df.columns)],
                }

            errors, warnings = validator(df)
            return {
                "ok": True,
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "shape": [len(df), len(df.columns)],
            }
        except Exception as exc:
            return JSONResponse(
                {"ok": False, "error": str(exc), "traceback": traceback.format_exc()}, status_code=400
            )

    # ── LaTeX rendering ─────────────────────────────────────────
    _latex_cache: dict[str, bytes] = {}

    class LatexRequest(BaseModel):
        latex: str
        dpi: int = 150
        fontsize: int = 14

    @api.post("/render-latex")
    def render_latex(req: LatexRequest):
        """Render a LaTeX formula to PNG using matplotlib's mathtext."""
        import base64
        import hashlib
        import io

        cache_key = f"{req.latex}_{req.dpi}_{req.fontsize}"
        if cache_key in _latex_cache:
            return {"ok": True, "png_base64": base64.b64encode(_latex_cache[cache_key]).decode()}

        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            from matplotlib import mathtext

            fig, ax = plt.subplots(figsize=(0.01, 0.01))
            ax.axis("off")
            fig.patch.set_alpha(0)

            # Render the LaTeX text
            text = ax.text(
                0, 0, f"${req.latex}$",
                fontsize=req.fontsize,
                verticalalignment="baseline",
                transform=ax.transAxes,
            )

            # Fit figure to text
            fig.canvas.draw()
            bbox = text.get_window_extent(fig.canvas.get_renderer())
            bbox = bbox.transformed(fig.dpi_scale_trans.inverted())
            fig.set_size_inches(bbox.width + 0.1, bbox.height + 0.1)

            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=req.dpi, transparent=True,
                       bbox_inches="tight", pad_inches=0.05)
            plt.close(fig)

            png_bytes = buf.getvalue()
            _latex_cache[cache_key] = png_bytes

            return {"ok": True, "png_base64": base64.b64encode(png_bytes).decode()}
        except Exception as exc:
            _log.exception("LaTeX render failed")
            return JSONResponse({"ok": False, "error": str(exc), "traceback": traceback.format_exc()}, status_code=400)

    # ── Data preview ──────────────────────────────────────────────
    class DataPreviewRequest(BaseModel):
        excel_path: str = ""
        data: dict[str, Any] | None = None
        sheet: int | str = 0

    @api.post("/data-preview")
    def data_preview(req: DataPreviewRequest):
        """Return raw contents of an Excel/CSV file as JSON for read-only display."""
        try:
            if req.data:
                # Inline data — return it directly
                columns = req.data.get("columns", [])
                rows = req.data.get("rows", [])
                return {
                    "ok": True,
                    "columns": columns,
                    "rows": rows,
                    "shape": [len(rows), len(columns)],
                }

            if not req.excel_path:
                return JSONResponse(
                    {"ok": False, "error": "Either excel_path or data must be provided"},
                    status_code=400,
                )

            path_err = _validate_data_path(req.excel_path)
            if path_err:
                return JSONResponse(
                    {"ok": False, "error": path_err}, status_code=400
                )
            import pandas as pd
            if req.excel_path.endswith(".csv"):
                df = pd.read_csv(req.excel_path, nrows=200)
            else:
                df = pd.read_excel(req.excel_path, sheet_name=req.sheet, nrows=200)

            columns = [str(c) for c in df.columns]
            rows = df.where(df.notna(), None).values.tolist()

            return {
                "ok": True,
                "columns": columns,
                "rows": rows,
                "shape": [len(df), len(df.columns)],
            }
        except Exception as exc:
            return JSONResponse(
                {"ok": False, "error": str(exc), "traceback": traceback.format_exc()}, status_code=400
            )

    # ── Recommend statistical test ──────────────────────────────────
    class RecommendTestRequest(BaseModel):
        excel_path: str = ""
        data: dict[str, Any] | None = None
        sheet: int | str = 0
        paired: bool = False
        table_type: str = "column"

    @api.post("/recommend-test")
    def recommend_test_endpoint(req: RecommendTestRequest):
        """Recommend the best statistical test based on data and table type."""
        try:
            import numpy as np
            import pandas as pd
            from refraction.core.stats import recommend_test

            if req.data:
                columns = req.data.get("columns", [])
                rows = req.data.get("rows", [])
                df = pd.DataFrame(rows, columns=columns)
            elif req.excel_path:
                path_err = _validate_data_path(req.excel_path)
                if path_err:
                    return JSONResponse(
                        {"ok": False, "error": path_err}, status_code=400
                    )
                if req.excel_path.endswith(".csv"):
                    df = pd.read_csv(req.excel_path)
                else:
                    df = pd.read_excel(req.excel_path, sheet_name=req.sheet)
            else:
                return JSONResponse(
                    {"ok": False, "error": "Either excel_path or data must be provided"},
                    status_code=400,
                )

            tt = req.table_type
            groups = {}
            paired = req.paired

            if tt == "column" or tt == "nested":
                # Each column is a group, rows are observations
                for col in df.columns:
                    vals = pd.to_numeric(df[col], errors="coerce").dropna().values
                    if len(vals) > 0:
                        groups[str(col)] = vals

            elif tt == "comparison":
                # Paired columns (Method A, Method B, ...)
                paired = True
                for col in df.columns:
                    vals = pd.to_numeric(df[col], errors="coerce").dropna().values
                    if len(vals) > 0:
                        groups[str(col)] = vals

            elif tt == "xy":
                # First column = X, rest = Y series (may have replicates)
                # Recommend correlation/regression tests
                n_cols = len(df.columns)
                if n_cols >= 2:
                    x_vals = pd.to_numeric(df.iloc[:, 0], errors="coerce").dropna().values
                    y_vals = pd.to_numeric(df.iloc[:, 1], errors="coerce").dropna().values
                    if len(x_vals) > 0 and len(y_vals) > 0:
                        # Check normality for correlation recommendation
                        from scipy import stats as sp_stats
                        _, p_x = sp_stats.shapiro(x_vals[:min(len(x_vals), 5000)])
                        _, p_y = sp_stats.shapiro(y_vals[:min(len(y_vals), 5000)])
                        both_normal = p_x > 0.05 and p_y > 0.05
                        test = "pearson" if both_normal else "spearman"
                        label = "Pearson correlation" if both_normal else "Spearman rank correlation"
                        just = (
                            f"XY data with {len(x_vals)} observations. "
                            f"{'Both variables are normally distributed — ' if both_normal else 'At least one variable is non-normal — '}"
                            f"{label} is recommended."
                        )
                        return {
                            "ok": True,
                            "test": test,
                            "test_label": label,
                            "posthoc": None,
                            "justification": just,
                            "checks": {
                                "n_groups": n_cols - 1,
                                "paired": False,
                                "min_n": len(x_vals),
                                "normality": {},
                                "all_normal": both_normal,
                                "equal_variance": True,
                                "levene_p": None,
                            },
                        }
                    return {"ok": False, "error": "No numeric XY data found"}

            elif tt == "grouped":
                # Row 0 = category labels, columns = subgroups
                # Extract numeric values per subgroup column
                for col in df.columns[1:]:
                    vals = pd.to_numeric(df[col], errors="coerce").dropna().values
                    if len(vals) > 0:
                        groups[str(col)] = vals
                if not groups:
                    # Try two-way: recommend two_way_anova directly
                    return {
                        "ok": True,
                        "test": "two_way_anova",
                        "test_label": "Two-way ANOVA",
                        "posthoc": "Tukey HSD",
                        "justification": "Grouped data with two factors — two-way ANOVA tests for main effects and interactions.",
                        "checks": {"n_groups": 0, "paired": False, "min_n": 0,
                                   "normality": {}, "all_normal": True, "equal_variance": True, "levene_p": None},
                    }

            elif tt == "contingency":
                # Count data — recommend chi-square or Fisher's exact
                # Flatten numeric cells to check expected counts
                numeric_vals = df.select_dtypes(include=[np.number]).values.flatten()
                numeric_vals = numeric_vals[~np.isnan(numeric_vals)]
                n_cells = len(numeric_vals)
                min_expected = float(np.min(numeric_vals)) if n_cells > 0 else 0
                if n_cells <= 4 or min_expected < 5:
                    test, label = "fisher_exact", "Fisher's exact test"
                    just = f"Contingency table with small expected counts (min = {min_expected:.0f}). Fisher's exact test is preferred."
                else:
                    test, label = "chi_square", "Chi-square test of independence"
                    just = f"Contingency table with sufficient expected counts (min = {min_expected:.0f}). Chi-square test is appropriate."
                return {
                    "ok": True, "test": test, "test_label": label, "posthoc": None,
                    "justification": just,
                    "checks": {"n_groups": n_cells, "paired": False, "min_n": int(min_expected),
                               "normality": {}, "all_normal": True, "equal_variance": True, "levene_p": None},
                }

            elif tt == "survival":
                # Time-to-event data — recommend log-rank
                return {
                    "ok": True,
                    "test": "log_rank",
                    "test_label": "Log-rank test",
                    "posthoc": None,
                    "justification": "Survival data with time-to-event observations. The log-rank test compares survival distributions between groups.",
                    "checks": {"n_groups": len(df.columns) // 2, "paired": False, "min_n": len(df),
                               "normality": {}, "all_normal": True, "equal_variance": True, "levene_p": None},
                }

            elif tt == "twoWay":
                # Long-format: Factor A, Factor B, Value
                return {
                    "ok": True,
                    "test": "two_way_anova",
                    "test_label": "Two-way ANOVA",
                    "posthoc": "Tukey HSD",
                    "justification": "Two-factor data — two-way ANOVA tests for main effects of each factor and their interaction.",
                    "checks": {"n_groups": 0, "paired": False, "min_n": len(df),
                               "normality": {}, "all_normal": True, "equal_variance": True, "levene_p": None},
                }

            elif tt == "meta":
                # Forest plot data — no statistical test to recommend
                return {
                    "ok": True,
                    "test": "descriptive",
                    "test_label": "Meta-analysis summary",
                    "posthoc": None,
                    "justification": "Meta-analysis data with pre-computed effect sizes and confidence intervals. No additional statistical test is needed.",
                    "checks": {"n_groups": len(df), "paired": False, "min_n": len(df),
                               "normality": {}, "all_normal": True, "equal_variance": True, "levene_p": None},
                }

            elif tt == "parts":
                return {
                    "ok": True,
                    "test": "descriptive",
                    "test_label": "Descriptive summary",
                    "posthoc": None,
                    "justification": "Parts-of-whole data. Descriptive statistics are reported; no comparison test applies.",
                    "checks": {"n_groups": len(df), "paired": False, "min_n": len(df),
                               "normality": {}, "all_normal": True, "equal_variance": True, "levene_p": None},
                }

            else:
                # Unknown table type — fall back to column-style extraction
                for col in df.columns:
                    vals = pd.to_numeric(df[col], errors="coerce").dropna().values
                    if len(vals) > 0:
                        groups[str(col)] = vals

            if not groups:
                return {"ok": False, "error": "No numeric data found"}

            result = recommend_test(groups, paired=paired)
            return {"ok": True, **result}
        except Exception as exc:
            return JSONResponse(
                {"ok": False, "error": str(exc), "traceback": traceback.format_exc()}, status_code=400
            )

    # ── Analyze Stats (standalone statistical analysis) ─────────────
    class AnalyzeStatsRequest(BaseModel):
        excel_path: str = ""
        data: dict[str, Any] | None = None
        sheet: int | str = 0
        analysis_type: str  # e.g. "unpaired_t", "anova", "kruskal_wallis"
        paired: bool = False
        posthoc: str = "Tukey HSD"
        mc_correction: str = "Holm-Bonferroni"
        control: str | None = None

    @api.post("/analyze-stats")
    def analyze_stats_endpoint(req: AnalyzeStatsRequest):
        """Run a statistical analysis and return results as JSON."""
        try:
            import math
            import pandas as pd
            from refraction.core.stats import (
                _run_stats, _cohens_d, _p_to_stars,
                calc_error, check_normality, descriptive_stats,
                recommend_test,
            )

            # Read data
            if req.data:
                columns = req.data.get("columns", [])
                rows = req.data.get("rows", [])
                df = pd.DataFrame(rows, columns=columns)
            elif req.excel_path:
                path_err = _validate_data_path(req.excel_path)
                if path_err:
                    return JSONResponse(
                        {"ok": False, "error": path_err}, status_code=400
                    )
                if req.excel_path.endswith(".csv"):
                    df = pd.read_csv(req.excel_path)
                else:
                    df = pd.read_excel(req.excel_path, sheet_name=req.sheet)
            else:
                return JSONResponse(
                    {"ok": False, "error": "Either excel_path or data must be provided"},
                    status_code=400,
                )

            # Extract numeric groups
            import numpy as np
            groups = {}
            for col in df.columns:
                vals = pd.to_numeric(df[col], errors="coerce").dropna().values
                if len(vals) > 0:
                    groups[str(col)] = vals

            if not groups:
                return JSONResponse(
                    {"ok": False, "error": "No numeric data found"},
                    status_code=400,
                )

            # Map analysis_type to _run_stats test_type
            _type_map = {
                "unpaired_t": "parametric",
                "welch_t": "parametric",
                "anova": "parametric",
                "paired_t": "paired",
                "wilcoxon": "paired",
                "mann_whitney": "nonparametric",
                "kruskal_wallis": "nonparametric",
                "permutation": "permutation",
                "one_sample": "one_sample",
                "descriptive": "none",
                "normality": "none",
            }
            test_type = _type_map.get(req.analysis_type, "parametric")

            # Human-readable labels
            _label_map = {
                "unpaired_t": "Unpaired t-test",
                "welch_t": "Welch's t-test",
                "anova": "Ordinary one-way ANOVA",
                "paired_t": "Paired t-test",
                "wilcoxon": "Wilcoxon matched-pairs signed rank test",
                "mann_whitney": "Mann-Whitney U test",
                "kruskal_wallis": "Kruskal-Wallis test",
                "permutation": "Permutation test",
                "one_sample": "One-sample t-test",
                "descriptive": "Descriptive statistics",
                "normality": "Normality tests",
            }
            analysis_label = _label_map.get(req.analysis_type, req.analysis_type)

            # Descriptive statistics for each group
            descriptive = []
            for name, vals in groups.items():
                ds = descriptive_stats(vals)
                ci95 = calc_error(vals, "ci95")[1] if len(vals) > 1 else float("nan")
                descriptive.append({
                    "group": name,
                    "n": ds["n"],
                    "mean": ds["mean"],
                    "sd": ds["sd"],
                    "sem": ds["sem"],
                    "median": ds["median"],
                    "ci95": ci95,
                })

            # Normality tests
            norm_raw = check_normality(groups)
            normality = {}
            for name, (stat, p, is_normal, warning) in norm_raw.items():
                normality[name] = {
                    "stat": stat,
                    "p": p,
                    "normal": is_normal,
                    "warning": warning,
                }

            # Run the statistical test
            comparisons = []
            summary = analysis_label
            if test_type != "none":
                raw_results = _run_stats(
                    groups,
                    test_type=test_type,
                    control=req.control,
                    mc_correction=req.mc_correction,
                    posthoc=req.posthoc,
                )
                for (ga, gb, p, stars) in raw_results:
                    comp = {
                        "group_a": ga,
                        "group_b": gb,
                        "p_value": p if not (isinstance(p, float) and math.isnan(p)) else None,
                        "stars": stars,
                    }
                    # Add effect size for pairwise comparisons
                    if ga in groups and gb in groups:
                        d = _cohens_d(groups[ga], groups[gb])
                        comp["effect_size"] = d if not math.isnan(d) else None
                        comp["effect_type"] = "Cohen's d"
                    comparisons.append(comp)

                # Build summary string
                labels = list(groups.keys())
                k = len(labels)
                if test_type == "parametric" and k >= 3:
                    from scipy import stats as sp_stats
                    f_stat, f_p = sp_stats.f_oneway(*[groups[g] for g in labels])
                    total_n = sum(len(groups[g]) for g in labels)
                    summary = f"One-way ANOVA: F({k-1},{total_n-k}) = {f_stat:.2f}, p = {f_p:.4g}"
                elif test_type == "parametric" and k == 2:
                    from scipy import stats as sp_stats
                    t_stat, t_p = sp_stats.ttest_ind(groups[labels[0]], groups[labels[1]])
                    summary = f"Unpaired t-test: t = {t_stat:.3f}, p = {t_p:.4g}"
                elif test_type == "nonparametric" and k == 2:
                    from scipy import stats as sp_stats
                    u_stat, u_p = sp_stats.mannwhitneyu(
                        groups[labels[0]], groups[labels[1]], alternative="two-sided"
                    )
                    summary = f"Mann-Whitney U = {u_stat:.1f}, p = {u_p:.4g}"
                elif test_type == "nonparametric" and k >= 3:
                    from scipy import stats as sp_stats
                    h_stat, h_p = sp_stats.kruskal(*[groups[g] for g in labels])
                    summary = f"Kruskal-Wallis H = {h_stat:.2f}, p = {h_p:.4g}"
                elif test_type == "paired" and k == 2:
                    from scipy import stats as sp_stats
                    n = min(len(groups[labels[0]]), len(groups[labels[1]]))
                    t_stat, t_p = sp_stats.ttest_rel(
                        groups[labels[0]][:n], groups[labels[1]][:n]
                    )
                    summary = f"Paired t-test: t = {t_stat:.3f}, p = {t_p:.4g}"

            # Get recommendation
            try:
                rec = recommend_test(groups, paired=req.paired)
                recommendation = {
                    "test": rec["test"],
                    "test_label": rec["test_label"],
                    "posthoc": rec.get("posthoc"),
                    "justification": rec["justification"],
                }
            except Exception:
                recommendation = None

            def _sanitize_val(v):
                if v is None:
                    return None
                if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                    return None
                if isinstance(v, (np.integer,)):
                    return int(v)
                if isinstance(v, (np.floating,)):
                    return float(v)
                return v

            # Sanitize all numeric values for JSON
            for d in descriptive:
                for key in d:
                    d[key] = _sanitize_val(d[key])
            for c in comparisons:
                for key in c:
                    c[key] = _sanitize_val(c[key])

            return {
                "ok": True,
                "analysis_type": req.analysis_type,
                "analysis_label": analysis_label,
                "recommendation": recommendation,
                "descriptive": descriptive,
                "normality": normality,
                "comparisons": comparisons,
                "summary": summary,
            }

        except Exception as exc:
            _log.exception("analyze-stats failed")
            return JSONResponse(
                {"ok": False, "error": str(exc), "traceback": traceback.format_exc()}, status_code=500
            )

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
            return JSONResponse({"ok": False, "error": str(e), "traceback": traceback.format_exc()}, status_code=500)

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
            return JSONResponse({"ok": False, "error": str(e), "traceback": traceback.format_exc()}, status_code=400)
        except Exception as e:
            _log.exception("curve-fit failed")
            return JSONResponse({"ok": False, "error": str(e), "traceback": traceback.format_exc()}, status_code=500)

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
            return JSONResponse({"ok": False, "error": str(e), "traceback": traceback.format_exc()}, status_code=400)
        except Exception as e:
            _log.exception("transform failed")
            return JSONResponse({"ok": False, "error": str(e), "traceback": traceback.format_exc()}, status_code=500)

    return api
