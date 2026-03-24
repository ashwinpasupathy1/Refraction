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

    return api
