You are Agent H for the Claude Plotter Phase 3 build.
You are the PLOTLY + PYWEBVIEW RENDERER agent.

BUDGET: Maximum $15. If approaching limit, commit completed work and exit.

ENVIRONMENT:
- Project root: the current working directory
- Python 3.12, run tests with: xvfb-run python3 run_all.py
- You are on branch: phase3/agent-h (already checked out)
- Phase 2 (Agent F + G) has been merged into master before this branch was cut.
- All modules use "plotter_" prefix. Branding is "Claude Plotter".

CRITICAL SAFETY RULES:
1. Make ONE change at a time
2. Run xvfb-run python3 run_all.py AFTER each change
3. git commit AFTER each passing test run
4. If tests fail after a change, revert ONLY the last change:
   git checkout -- <file>
5. You should end up with 10-20 small commits, NOT one giant commit
6. If stuck on a step, SKIP it and document in phase3/AGENT_H_ISSUES.txt
7. NEVER modify plotter_functions.py, plotter_validators.py, or any test file

GOAL:
Replace FigureCanvasTkAgg with a pywebview + Plotly.js panel for 4 priority
chart types: bar, grouped_bar, line, scatter.
Both renderers coexist — non-priority charts keep using FigureCanvasTkAgg.

=======================================================================
STEP 1: Verify starting state + install dependencies
=======================================================================

Run: xvfb-run python3 run_all.py
Record the pass count. It must be >= 520.
If it fails, stop and write phase3/AGENT_H_ISSUES.txt explaining why.

Install dependencies:
  pip install fastapi uvicorn plotly pywebview

Verify pywebview works on this macOS machine:
  python3 -c "import webview; print('pywebview OK')"

If pywebview import fails, try:
  pip install pywebview --upgrade

If pywebview still fails, document in AGENT_H_ISSUES.txt and proceed
with all steps EXCEPT those that require pywebview embedding (Steps 8-9).
You can still write all the Python spec and server files.

Verify plotly works:
  python3 -c "import plotly.graph_objects as go; print('plotly OK')"

git commit -m "chore(agent-h): verify starting state for phase 3"

=======================================================================
STEP 2: Create the Prism-style Plotly template
=======================================================================

Create plotter_plotly_theme.py with this content:

"""Prism-style Plotly theme matching Claude Plotter's matplotlib style."""

PRISM_PALETTE = [
    "#E8453C", "#2274A5", "#32936F", "#F18F01", "#A846A0",
    "#6B4226", "#048A81", "#D4AC0D", "#3B1F2B", "#44BBA4",
]

PRISM_TEMPLATE = {
    "layout": {
        "font": {"family": "Arial, sans-serif", "size": 12, "color": "#222222"},
        "paper_bgcolor": "white",
        "plot_bgcolor": "white",
        "colorway": PRISM_PALETTE,
        "xaxis": {
            "showgrid": False,
            "zeroline": False,
            "linecolor": "#222222",
            "linewidth": 1,
            "ticks": "outside",
            "ticklen": 5,
            "tickwidth": 1,
            "showline": True,
        },
        "yaxis": {
            "showgrid": False,
            "zeroline": False,
            "linecolor": "#222222",
            "linewidth": 1,
            "ticks": "outside",
            "ticklen": 5,
            "tickwidth": 1,
            "showline": True,
        },
        "margin": {"l": 60, "r": 20, "t": 50, "b": 60},
    }
}


def apply_open_spine(layout_update: dict) -> dict:
    """Return layout dict that shows only left+bottom axes (Prism default)."""
    layout_update.setdefault("xaxis", {}).update({
        "mirror": False,
        "showline": True,
        "linecolor": "#222222",
    })
    layout_update.setdefault("yaxis", {}).update({
        "mirror": False,
        "showline": True,
        "linecolor": "#222222",
    })
    return layout_update

Run: python3 -c "from plotter_plotly_theme import PRISM_TEMPLATE; print('theme OK')"
Run: xvfb-run python3 run_all.py (must still pass)
git commit -m "feat(agent-h): add Prism-style Plotly template"

=======================================================================
STEP 3: Create plotter_spec_bar.py
=======================================================================

Create plotter_spec_bar.py:

"""Builds a Plotly figure spec for bar charts from plotter kwargs."""

import json
import pandas as pd
from plotter_plotly_theme import PRISM_TEMPLATE, PRISM_PALETTE, apply_open_spine


def build_bar_spec(kw: dict) -> str:
    """Read Excel data and return a Plotly figure as JSON string.

    Args:
        kw: The same kwargs dict passed to prism_barplot().

    Returns:
        JSON string of a plotly.graph_objects.Figure.
    """
    import plotly.graph_objects as go

    excel_path = kw.get("excel_path", "")
    sheet = kw.get("sheet", 0)
    color = kw.get("color", None)
    title = kw.get("title", "")
    xlabel = kw.get("xlabel", "")
    ytitle = kw.get("ytitle", "")

    # Read data
    try:
        df = pd.read_excel(excel_path, sheet_name=sheet, header=0)
    except Exception as e:
        return json.dumps({"error": str(e)})

    groups = list(df.columns)
    values = {g: df[g].dropna().tolist() for g in groups}
    means = [sum(v) / len(v) if v else 0 for v in values.values()]

    # Colors
    if isinstance(color, list):
        colors = color
    elif isinstance(color, str):
        colors = [color] * len(groups)
    else:
        colors = PRISM_PALETTE[:len(groups)]

    # Build traces
    traces = []
    for i, (g, mean) in enumerate(zip(groups, means)):
        vals = values[g]
        sem = (sum((x - mean) ** 2 for x in vals) / len(vals)) ** 0.5 / (len(vals) ** 0.5) if len(vals) > 1 else 0
        traces.append(go.Bar(
            x=[g],
            y=[mean],
            name=g,
            marker_color=colors[i % len(colors)],
            error_y=dict(type="data", array=[sem], visible=True),
            showlegend=False,
        ))

    layout = go.Layout(
        template=PRISM_TEMPLATE,
        title=dict(text=title, font=dict(size=14)),
        xaxis=dict(title=xlabel),
        yaxis=dict(title=ytitle),
    )
    apply_open_spine(layout.to_plotly_json())

    fig = go.Figure(data=traces, layout=layout)
    return fig.to_json()


Run: python3 -c "from plotter_spec_bar import build_bar_spec; print('spec_bar OK')"
Run: xvfb-run python3 run_all.py (must still pass)
git commit -m "feat(agent-h): add plotter_spec_bar.py Plotly spec builder"

=======================================================================
STEP 4: Create plotter_spec_grouped_bar.py
=======================================================================

Create plotter_spec_grouped_bar.py following the same pattern as
plotter_spec_bar.py but reading grouped bar data (two-row header:
row 0 = category names, row 1 = subgroup names, rows 2+ = values).

"""Builds a Plotly figure spec for grouped bar charts."""

import json
import pandas as pd
from plotter_plotly_theme import PRISM_TEMPLATE, PRISM_PALETTE


def build_grouped_bar_spec(kw: dict) -> str:
    import plotly.graph_objects as go

    excel_path = kw.get("excel_path", "")
    sheet = kw.get("sheet", 0)
    title = kw.get("title", "")
    xlabel = kw.get("xlabel", "")
    ytitle = kw.get("ytitle", "")

    try:
        df = pd.read_excel(excel_path, sheet_name=sheet, header=[0, 1])
    except Exception as e:
        return json.dumps({"error": str(e)})

    # df has a MultiIndex column: (category, subgroup)
    categories = df.columns.get_level_values(0).unique().tolist()
    subgroups = df.columns.get_level_values(1).unique().tolist()

    traces = []
    for j, sg in enumerate(subgroups):
        y_vals = []
        for cat in categories:
            try:
                col_data = df[(cat, sg)].dropna()
                y_vals.append(col_data.mean() if len(col_data) > 0 else 0)
            except KeyError:
                y_vals.append(0)
        traces.append(go.Bar(
            name=sg,
            x=categories,
            y=y_vals,
            marker_color=PRISM_PALETTE[j % len(PRISM_PALETTE)],
        ))

    fig = go.Figure(data=traces, layout=go.Layout(
        template=PRISM_TEMPLATE,
        barmode="group",
        title=dict(text=title),
        xaxis=dict(title=xlabel),
        yaxis=dict(title=ytitle),
    ))
    return fig.to_json()

Run: python3 -c "from plotter_spec_grouped_bar import build_grouped_bar_spec; print('spec_grouped_bar OK')"
Run: xvfb-run python3 run_all.py
git commit -m "feat(agent-h): add plotter_spec_grouped_bar.py Plotly spec builder"

=======================================================================
STEP 5: Create plotter_spec_line.py
=======================================================================

Create plotter_spec_line.py for line graph data (row 0 = X label +
series names, rows 1+ = X value + Y replicates per series).

"""Builds a Plotly figure spec for line graphs."""

import json
import pandas as pd
from plotter_plotly_theme import PRISM_TEMPLATE, PRISM_PALETTE


def build_line_spec(kw: dict) -> str:
    import plotly.graph_objects as go

    excel_path = kw.get("excel_path", "")
    sheet = kw.get("sheet", 0)
    title = kw.get("title", "")
    xlabel = kw.get("xlabel", "")
    ytitle = kw.get("ytitle", "")

    try:
        df = pd.read_excel(excel_path, sheet_name=sheet, header=0)
    except Exception as e:
        return json.dumps({"error": str(e)})

    if df.shape[1] < 2:
        return json.dumps({"error": "Need at least 2 columns (X, Y1)"})

    x_col = df.columns[0]
    y_cols = df.columns[1:]
    x_vals = df[x_col].dropna().tolist()

    traces = []
    for i, col in enumerate(y_cols):
        y_vals = df[col].tolist()
        traces.append(go.Scatter(
            x=x_vals,
            y=y_vals,
            mode="lines+markers",
            name=str(col),
            line=dict(color=PRISM_PALETTE[i % len(PRISM_PALETTE)], width=2),
            marker=dict(size=6),
        ))

    fig = go.Figure(data=traces, layout=go.Layout(
        template=PRISM_TEMPLATE,
        title=dict(text=title),
        xaxis=dict(title=xlabel),
        yaxis=dict(title=ytitle),
    ))
    return fig.to_json()

Run: python3 -c "from plotter_spec_line import build_line_spec; print('spec_line OK')"
Run: xvfb-run python3 run_all.py
git commit -m "feat(agent-h): add plotter_spec_line.py Plotly spec builder"

=======================================================================
STEP 6: Create plotter_spec_scatter.py
=======================================================================

Create plotter_spec_scatter.py for XY scatter data (same layout as
line but rendered as markers only, no connecting lines).

"""Builds a Plotly figure spec for scatter plots."""

import json
import pandas as pd
from plotter_plotly_theme import PRISM_TEMPLATE, PRISM_PALETTE


def build_scatter_spec(kw: dict) -> str:
    import plotly.graph_objects as go

    excel_path = kw.get("excel_path", "")
    sheet = kw.get("sheet", 0)
    title = kw.get("title", "")
    xlabel = kw.get("xlabel", "")
    ytitle = kw.get("ytitle", "")

    try:
        df = pd.read_excel(excel_path, sheet_name=sheet, header=0)
    except Exception as e:
        return json.dumps({"error": str(e)})

    if df.shape[1] < 2:
        return json.dumps({"error": "Need at least 2 columns (X, Y)"})

    x_col = df.columns[0]
    y_cols = df.columns[1:]
    x_vals = df[x_col].dropna().tolist()

    traces = []
    for i, col in enumerate(y_cols):
        y_vals = df[col].tolist()
        traces.append(go.Scatter(
            x=x_vals,
            y=y_vals,
            mode="markers",
            name=str(col),
            marker=dict(
                color=PRISM_PALETTE[i % len(PRISM_PALETTE)],
                size=8,
                opacity=0.8,
            ),
        ))

    fig = go.Figure(data=traces, layout=go.Layout(
        template=PRISM_TEMPLATE,
        title=dict(text=title),
        xaxis=dict(title=xlabel),
        yaxis=dict(title=ytitle),
    ))
    return fig.to_json()

Run: python3 -c "from plotter_spec_scatter import build_scatter_spec; print('spec_scatter OK')"
Run: xvfb-run python3 run_all.py
git commit -m "feat(agent-h): add plotter_spec_scatter.py Plotly spec builder"

=======================================================================
STEP 7: Create plotter_server.py (FastAPI backend)
=======================================================================

Create plotter_server.py:

"""FastAPI server for Claude Plotter — serves Plotly chart specs
and receives edit events from the pywebview frontend."""

from __future__ import annotations
import json
import threading
from typing import Any

_server_thread: threading.Thread | None = None
_app_ref = None  # weakref to the App instance, set during startup
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

    api = FastAPI(title="Claude Plotter API", version="1.0.0")

    api.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    class RenderRequest(BaseModel):
        chart_type: str
        kw: dict[str, Any]

    class EventRequest(BaseModel):
        event: str
        value: Any = None
        extra: dict[str, Any] = {}

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

    @api.get("/health")
    def health():
        return {"status": "ok"}

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
        import json
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
        pass

Verify:
  python3 -c "from plotter_server import start_server, get_port; print('server OK')"
Run: xvfb-run python3 run_all.py
git commit -m "feat(agent-h): add plotter_server.py FastAPI render+event server"

=======================================================================
STEP 8: Create plotter_webview.py (pywebview panel wrapper)
=======================================================================

Create plotter_webview.py:

"""pywebview panel for rendering Plotly charts inside the Tk window.

On macOS, pywebview uses WKWebView which embeds cleanly.
The HTML page loads Plotly.js from CDN and renders the spec.
Edit events are posted back to the FastAPI /event endpoint.
"""

from __future__ import annotations
import json
import threading
import tkinter as tk
from typing import Optional


# HTML template served to pywebview
_HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  body { margin: 0; padding: 0; background: white; }
  #plot { width: 100vw; height: 100vh; }
</style>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
</head>
<body>
  <div id="plot"></div>
  <script>
    const API_BASE = "http://127.0.0.1:{PORT}";

    async function renderChart(chartType, kw) {{
      try {{
        const resp = await fetch(API_BASE + "/render", {{
          method: "POST",
          headers: {{"Content-Type": "application/json"}},
          body: JSON.stringify({{chart_type: chartType, kw: kw}})
        }});
        const data = await resp.json();
        if (!data.ok) {{
          console.error("Render error:", data.error);
          return;
        }}
        const spec = data.spec;
        Plotly.newPlot("plot", spec.data, spec.layout, {{
          responsive: true,
          displayModeBar: true,
          editable: true,
        }});

        // Listen for editable title/axis changes
        const plotDiv = document.getElementById("plot");
        plotDiv.on("plotly_relayout", function(update) {{
          if (update["title.text"] !== undefined) {{
            postEvent("title_changed", update["title.text"]);
          }}
          if (update["xaxis.title.text"] !== undefined) {{
            postEvent("xlabel_changed", update["xaxis.title.text"]);
          }}
          if (update["yaxis.title.text"] !== undefined) {{
            postEvent("ytitle_changed", update["yaxis.title.text"]);
          }}
          if (update["yaxis.range[0]"] !== undefined) {{
            postEvent("yrange_changed", null, {{
              ymin: update["yaxis.range[0]"],
              ymax: update["yaxis.range[1]"]
            }});
          }}
        }});
      }} catch (e) {{
        console.error("renderChart error:", e);
      }}
    }}

    async function postEvent(event, value, extra) {{
      try {{
        await fetch(API_BASE + "/event", {{
          method: "POST",
          headers: {{"Content-Type": "application/json"}},
          body: JSON.stringify({{event, value, extra: extra || {{}}}})
        }});
      }} catch (e) {{
        console.error("postEvent error:", e);
      }}
    }}

    // Called from Python via webview.evaluate_js
    window.plotterRender = renderChart;
  </script>
</body>
</html>"""


class PlotterWebView:
    """Wraps a pywebview window for embedding Plotly charts.

    Usage:
        pv = PlotterWebView(parent_frame, port=7331)
        pv.show()
        pv.render("bar", kw_dict)
    """

    def __init__(self, parent: tk.Frame, port: int = 7331):
        self._parent = parent
        self._port = port
        self._window = None
        self._ready = threading.Event()

    def show(self) -> bool:
        """Create and embed the webview. Returns True on success."""
        try:
            import webview

            html = _HTML_TEMPLATE.replace("{PORT}", str(self._port))

            def _create():
                self._window = webview.create_window(
                    "Claude Plotter Chart",
                    html=html,
                    width=800, height=600,
                    resizable=True,
                    frameless=False,
                )
                self._ready.set()
                webview.start()

            t = threading.Thread(target=_create, daemon=True)
            t.start()
            self._ready.wait(timeout=5.0)
            return self._window is not None

        except ImportError:
            return False
        except Exception:
            return False

    def render(self, chart_type: str, kw: dict) -> bool:
        """Call JavaScript to render a chart. Returns True on success."""
        if self._window is None:
            return False
        try:
            kw_json = json.dumps(kw)
            js = f"window.plotterRender('{chart_type}', {kw_json})"
            self._window.evaluate_js(js)
            return True
        except Exception:
            return False

    def destroy(self) -> None:
        """Close the webview window."""
        try:
            if self._window is not None:
                self._window.destroy()
        except Exception:
            pass

Verify:
  python3 -c "from plotter_webview import PlotterWebView; print('webview OK')"
Run: xvfb-run python3 run_all.py
git commit -m "feat(agent-h): add plotter_webview.py pywebview panel wrapper"

=======================================================================
STEP 9: Wire the web renderer into plotter_barplot_app.py
=======================================================================

PRIORITY CHART TYPES that get the Plotly renderer:
  "bar", "grouped_bar", "line", "scatter"

In plotter_barplot_app.py, find the App class __init__ method.
Add near the end of __init__ (after _build()):

    # Phase 3: start FastAPI server
    try:
        from plotter_server import start_server
        start_server(app_instance=self)
        self._web_server_running = True
    except Exception:
        self._web_server_running = False

    # Phase 3: web view instances per tab (or single global)
    self._plotly_views: dict = {}   # tab_id -> PlotterWebView

Add a new method _try_webview_embed to the App class:

    _WEBVIEW_CHART_TYPES = {"bar", "grouped_bar", "line", "scatter"}

    def _try_webview_embed(self, plot_frame: tk.Frame, chart_type: str, kw: dict) -> bool:
        """Try to embed a Plotly chart via pywebview. Returns True on success."""
        if not getattr(self, "_web_server_running", False):
            return False
        if chart_type not in self._WEBVIEW_CHART_TYPES:
            return False
        try:
            from plotter_webview import PlotterWebView
            from plotter_server import get_port
            pv = PlotterWebView(plot_frame, port=get_port())
            if not pv.show():
                return False
            pv.render(chart_type, kw)
            # Store for later updates
            self._plotly_views[id(plot_frame)] = pv
            return True
        except Exception:
            return False

Now find the _embed_plot method. It currently always uses FigureCanvasTkAgg.
Modify it to try the webview path first for priority chart types:

BEFORE the FigureCanvasTkAgg embedding code, add:

    # Phase 3: try Plotly webview for priority chart types
    plot_type = kw.get("plot_type", "") or getattr(self, "_plot_type", None)
    if hasattr(plot_type, "get"):
        plot_type = plot_type.get()
    if self._try_webview_embed(plot_frame, str(plot_type), kw):
        return   # Successfully embedded via pywebview

IMPORTANT: Find the actual variable name for the plot frame (it might be
self._plot_frame, self._right_pane, or similar). Read the existing code
carefully before making changes.

FALLBACK: If _try_webview_embed returns False, execution falls through
to the existing FigureCanvasTkAgg code. No existing functionality is lost.

Run: xvfb-run python3 run_all.py
If tests pass: git commit -m "feat(agent-h): wire Plotly webview into _embed_plot with matplotlib fallback"
If tests fail: git checkout -- plotter_barplot_app.py
               Document in phase3/AGENT_H_ISSUES.txt and skip this step.

=======================================================================
STEP 10: Add a canvas_mode toggle for web rendering
=======================================================================

Find where the canvas mode toggle is in plotter_barplot_app.py
(search for "canvas_mode" or "_canvas_mode" or "_use_canvas").

Add a similar toggle for web rendering mode:
- Add a BooleanVar: self._use_webview = tk.BooleanVar(value=True)
- Add a checkbox or menu item "Use Web Renderer (Plotly)"
- When toggled off, fall back to matplotlib for ALL chart types

If canvas mode toggle doesn't exist, skip this step.

Run: xvfb-run python3 run_all.py
git commit -m "feat(agent-h): add web renderer toggle (Plotly on/off)"

=======================================================================
STEP 11: Write import verification check
=======================================================================

Run this and save the output:

python3 -c "
modules = [
    'plotter_plotly_theme', 'plotter_spec_bar', 'plotter_spec_grouped_bar',
    'plotter_spec_line', 'plotter_spec_scatter', 'plotter_server',
    'plotter_webview',
]
failed = []
for mod in modules:
    try:
        __import__(mod)
        print(f'  OK: {mod}')
    except Exception as e:
        print(f'  FAIL: {mod} -- {e}')
        failed.append(mod)
if failed:
    print(f'\n{len(failed)} modules failed to import')
else:
    print(f'\nAll {len(modules)} new Phase 3 modules import successfully')
" 2>&1 | tee phase3/import_results.txt

=======================================================================
STEP 12: Add tests to test_comprehensive.py
=======================================================================

Open tests/test_comprehensive.py (or test_comprehensive.py at root —
check which exists).

Add a new test section at the end:

    # ===================================================================
    # PHASE 3 — Plotly spec builders
    # ===================================================================

    section("Phase 3: Plotly spec builders")

    def test_bar_spec_returns_json():
        with bar_excel({"Control": [1,2,3], "Drug": [4,5,6]}) as path:
            from plotter_spec_bar import build_bar_spec
            spec_json = build_bar_spec({"excel_path": path, "title": "Test"})
            import json
            spec = json.loads(spec_json)
            assert "data" in spec
            assert "layout" in spec
    run("plotter_spec_bar: returns valid Plotly JSON", test_bar_spec_returns_json)

    def test_bar_spec_has_two_traces():
        with bar_excel({"Control": [1,2,3], "Drug": [4,5,6]}) as path:
            from plotter_spec_bar import build_bar_spec
            import json
            spec = json.loads(build_bar_spec({"excel_path": path}))
            assert len(spec["data"]) == 2
    run("plotter_spec_bar: two groups = two traces", test_bar_spec_has_two_traces)

    def test_line_spec_returns_json():
        with line_excel({"X": [1,2,3], "Y1": [4,5,6]}) as path:
            from plotter_spec_line import build_line_spec
            import json
            spec = json.loads(build_line_spec({"excel_path": path}))
            assert "data" in spec
    run("plotter_spec_line: returns valid Plotly JSON", test_line_spec_returns_json)

    def test_scatter_spec_mode_markers():
        with line_excel({"X": [1,2,3], "Y1": [4,5,6]}) as path:
            from plotter_spec_scatter import build_scatter_spec
            import json
            spec = json.loads(build_scatter_spec({"excel_path": path}))
            assert spec["data"][0]["mode"] == "markers"
    run("plotter_spec_scatter: mode is markers", test_scatter_mode_markers)

    def test_server_starts():
        from plotter_server import start_server, get_port
        import time, urllib.request
        start_server()
        time.sleep(2)
        try:
            resp = urllib.request.urlopen(f"http://127.0.0.1:{get_port()}/health", timeout=3)
            assert resp.status == 200
        except Exception as e:
            assert False, f"Server did not start: {e}"
    run("plotter_server: /health endpoint responds", test_server_starts)

IMPORTANT: The fixture `line_excel` may use a different format.
Check what fixtures are available in prism_test_harness.py (now
plotter_test_harness.py or similar) and use the correct ones.

Run: xvfb-run python3 run_all.py
git commit -m "test(agent-h): add Phase 3 Plotly spec builder tests"

=======================================================================
FINAL VERIFICATION
=======================================================================

1. xvfb-run python3 run_all.py
   Must pass >= 520 tests (ideally more with new Phase 3 tests), 0 failures

2. python3 -c "
   from plotter_plotly_theme import PRISM_TEMPLATE
   from plotter_spec_bar import build_bar_spec
   from plotter_spec_grouped_bar import build_grouped_bar_spec
   from plotter_spec_line import build_line_spec
   from plotter_spec_scatter import build_scatter_spec
   from plotter_server import start_server, get_port
   from plotter_webview import PlotterWebView
   print('All Phase 3 modules import OK')
   "

3. git log --oneline | head -20
   Should show 8-15 small incremental commits

4. Final commit:
   git commit --allow-empty -m "feat(agent-h): Phase 3 complete — Plotly/pywebview renderer

   New files:
   - plotter_plotly_theme.py: Prism-style Plotly layout template
   - plotter_spec_bar.py: Plotly spec builder for bar charts
   - plotter_spec_grouped_bar.py: Plotly spec builder for grouped bar
   - plotter_spec_line.py: Plotly spec builder for line graphs
   - plotter_spec_scatter.py: Plotly spec builder for scatter plots
   - plotter_server.py: FastAPI /render + /event server (background thread)
   - plotter_webview.py: pywebview panel wrapper

   Modified:
   - plotter_barplot_app.py: _embed_plot routes bar/grouped_bar/line/scatter
     through Plotly webview with matplotlib fallback

   All 520+ tests passing."
