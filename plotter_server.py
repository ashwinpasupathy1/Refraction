"""FastAPI server for Claude Plotter — serves Plotly chart specs
and receives edit events from the pywebview frontend."""

import json
import logging
import os
import threading
from typing import Any, Optional

_log = logging.getLogger(__name__)

_server_thread: Optional[threading.Thread] = None
_app_ref = None  # reference to the App instance, set during startup
_PORT = 7331


def get_port() -> int:
    return _PORT


def start_server(app_instance=None) -> None:
    """Start the FastAPI server in a background daemon thread."""
    global _server_thread, _app_ref
    if _server_thread and _server_thread.is_alive():
        return  # Already running

    _app_ref = app_instance

    def _run():
        import uvicorn
        uvicorn.run(_make_app(), host="127.0.0.1", port=_PORT,
                    log_level="warning", access_log=False)

    _server_thread = threading.Thread(target=_run, daemon=True, name="plotter-server")
    _server_thread.start()


def _make_app():
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel

    class RenderRequest(BaseModel):
        chart_type: str
        kw: dict[str, Any]

    class EventRequest(BaseModel):
        event: str
        value: Any = None
        extra: dict[str, Any] = {}

    from fastapi.responses import JSONResponse
    from fastapi import Request

    API_KEY = os.environ.get("PLOTTER_API_KEY", "")

    api = FastAPI(title="Claude Plotter API", version="1.0.0")

    api.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @api.middleware("http")
    async def check_auth(request: Request, call_next):
        """Require API key for non-local requests (if PLOTTER_API_KEY is set)."""
        host = request.headers.get("host", "")
        if host.startswith("127.0.0.1") or host.startswith("localhost"):
            return await call_next(request)
        if API_KEY and request.headers.get("x-api-key") != API_KEY:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        return await call_next(request)

    @api.post("/render")
    def render(req: RenderRequest):
        """Accept chart kwargs, return Plotly JSON."""
        try:
            spec_json = _build_spec(req.chart_type, req.kw)
            return {"ok": True, "spec": json.loads(spec_json)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @api.post("/event")
    def handle_event(req: EventRequest):
        """Receive edit events from the frontend (e.g. title changed)."""
        try:
            _dispatch_event(req.event, req.value, req.extra)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @api.post("/spec")
    def get_spec(req: RenderRequest):
        """Return raw Plotly JSON spec without rendering."""
        try:
            spec_json = _build_spec(req.chart_type, req.kw)
            return {"ok": True, "spec_json": spec_json}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @api.get("/chart-types")
    def chart_types():
        """List available chart types."""
        return {
            "priority": ["bar", "grouped_bar", "line", "scatter"],
            "all": ["bar", "grouped_bar", "line", "scatter",
                    "box", "violin", "heatmap", "histogram",
                    "kaplan_meier", "two_way_anova", "before_after",
                    "subcolumn_scatter", "curve_fit", "column_stats",
                    "contingency", "repeated_measures", "chi_square_gof",
                    "stacked_bar", "bubble", "dot_plot", "bland_altman",
                    "forest_plot", "area_chart", "raincloud", "qq_plot",
                    "lollipop", "waterfall", "pyramid", "ecdf"]
        }

    @api.get("/health")
    def health():
        return {"status": "ok"}

    # Serve React SPA static files if the build exists
    from fastapi.staticfiles import StaticFiles
    web_dist = os.path.join(os.path.dirname(__file__), "plotter_web", "dist")
    if os.path.isdir(web_dist):
        api.mount("/", StaticFiles(directory=web_dist, html=True), name="static")

    return api


def _build_spec(chart_type: str, kw: dict) -> str:
    """Route to the correct spec builder."""
    if chart_type == "bar":
        from plotter_spec_bar import build_bar_spec
        return build_bar_spec(kw)
    elif chart_type == "grouped_bar":
        from plotter_spec_grouped_bar import build_grouped_bar_spec
        return build_grouped_bar_spec(kw)
    elif chart_type == "line":
        from plotter_spec_line import build_line_spec
        return build_line_spec(kw)
    elif chart_type == "scatter":
        from plotter_spec_scatter import build_scatter_spec
        return build_scatter_spec(kw)
    else:
        return json.dumps({"error": f"Unknown chart type: {chart_type}"})


def _dispatch_event(event: str, value: Any, extra: dict) -> None:
    """Dispatch a frontend edit event back to the App form state."""
    if _app_ref is None:
        return
    app = _app_ref

    # Title changed in chart
    if event == "title_changed":
        _set_var(app, "title", value)

    # X-axis label changed
    elif event == "xlabel_changed":
        _set_var(app, "xlabel", value)

    # Y-axis label changed
    elif event == "ytitle_changed":
        _set_var(app, "ytitle", value)

    # Bar recolored
    elif event == "bar_recolored":
        # extra = {"group_index": int, "color": "#rrggbb"}
        pass  # Color sync TBD in Phase 3 polish

    # Y-axis range changed via drag
    elif event == "yrange_changed":
        # extra = {"ymin": float, "ymax": float}
        _set_var(app, "ymin", str(extra.get("ymin", "")))
        _set_var(app, "ymax", str(extra.get("ymax", "")))


def _set_var(app, key: str, value: str) -> None:
    """Safely set a tkinter StringVar on the main thread."""
    try:
        var = app._vars.get(key)
        if var is not None:
            app.after(0, lambda: var.set(value))
    except Exception:
        _log.debug("_set_var: could not set app var %r to %r", key, value, exc_info=True)
