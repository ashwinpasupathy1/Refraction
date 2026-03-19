You are Agent I for the Claude Plotter Phase 4 build.
You are the DEPLOYMENT READINESS agent.

BUDGET: Maximum $20. If approaching limit, commit completed work and exit.

PREREQUISITES: Phase 3 (Agent H) must be complete and merged to master.
If plotter_server.py does not exist, STOP and write phase4/AGENT_I_ISSUES.txt.

ENVIRONMENT:
- Project root: the current working directory
- Python 3.12, run tests with: xvfb-run python3 run_all.py
- You are on branch: phase4/agent-i (already checked out)
- Node.js and npm must be available (check: node --version && npm --version)
- All modules use "plotter_" prefix. Branding is "Claude Plotter".

CRITICAL SAFETY RULES:
1. Make ONE change at a time
2. Run xvfb-run python3 run_all.py AFTER each change that touches Python
3. git commit AFTER each passing test run
4. If tests fail, revert the last change: git checkout -- <file>
5. You should end up with 15-25 small commits, NOT one giant commit
6. If stuck on a step, SKIP it and document in phase4/AGENT_I_ISSUES.txt
7. NEVER modify plotter_functions.py, plotter_validators.py, or any test file
8. The React SPA goes in plotter_web/ (new directory, does NOT affect Python tests)

GOAL: Make Claude Plotter deployable as a web service while keeping the
desktop version working. Architecture:
  Desktop: pywebview wraps the React SPA (Phase 3 approach, upgraded)
  Web:     React SPA + FastAPI backend, served normally
  Both:    same Python business logic, same FastAPI server

=======================================================================
STEP 1: Verify starting state
=======================================================================

Run: xvfb-run python3 run_all.py
Record the pass count. Must be >= 520.

Verify Phase 3 modules exist:
  python3 -c "
  from plotter_server import start_server
  from plotter_spec_bar import build_bar_spec
  print('Phase 3 modules OK')
  "

If Phase 3 modules are missing, stop and write phase4/AGENT_I_ISSUES.txt.

Check Node.js is available:
  node --version
  npm --version

If Node.js is not available, skip Steps 3-6 (React SPA) but continue
with Steps 2, 7-12 (Python/FastAPI work).

git commit -m "chore(agent-i): verify starting state for phase 4"

=======================================================================
STEP 2: Upgrade plotter_server.py for production
=======================================================================

Open plotter_server.py and add:

a) Authentication middleware (simple API key for web deployment):

    Add to _make_app():

    from fastapi import Request, HTTPException
    import os

    API_KEY = os.environ.get("PLOTTER_API_KEY", "")

    @api.middleware("http")
    async def check_auth(request: Request, call_next):
        # Always allow local connections
        host = request.headers.get("host", "")
        if host.startswith("127.0.0.1") or host.startswith("localhost"):
            return await call_next(request)
        # For non-local, require API key if one is set
        if API_KEY and request.headers.get("x-api-key") != API_KEY:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        return await call_next(request)

b) A /spec endpoint that just returns the JSON without rendering:
    (This allows the React SPA to call /spec and render client-side)

    @api.post("/spec")
    def get_spec(req: RenderRequest):
        """Return raw Plotly JSON spec without rendering."""
        try:
            spec_json = _build_spec(req.chart_type, req.kw)
            return {"ok": True, "spec_json": spec_json}
        except Exception as e:
            return {"ok": False, "error": str(e)}

c) A /chart-types endpoint listing available chart types:

    @api.get("/chart-types")
    def chart_types():
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

Run: python3 -c "from plotter_server import _make_app; app = _make_app(); print('server OK')"
Run: xvfb-run python3 run_all.py
git commit -m "feat(agent-i): upgrade plotter_server with auth + /spec + /chart-types"

=======================================================================
STEP 3: Scaffold React SPA
=======================================================================

NOTE: The React SPA goes in plotter_web/. This directory is NOT part
of the Python package and does NOT affect tests.

Run:
  cd /tmp && npm create vite@latest plotter_web_temp -- --template react-ts
  cp -r /tmp/plotter_web_temp "$PWD/plotter_web"
  rm -rf /tmp/plotter_web_temp

Or if vite is unavailable:
  mkdir -p plotter_web/src plotter_web/public
  # Create a minimal index.html + main.tsx manually (see below)

Verify:
  ls plotter_web/

Create plotter_web/.env.development with:
  VITE_API_BASE=http://127.0.0.1:7331

Create plotter_web/.env.production with:
  VITE_API_BASE=/api

git add plotter_web/
git commit -m "feat(agent-i): scaffold React SPA in plotter_web/"

=======================================================================
STEP 4: Create the chart rendering React component
=======================================================================

Create plotter_web/src/PlotterChart.tsx:

```tsx
import { useEffect, useRef, useState } from 'react';
import Plotly from 'plotly.js-dist-min';

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:7331';

interface ChartProps {
  chartType: string;
  kw: Record<string, unknown>;
  onEvent?: (event: string, value: unknown, extra: Record<string, unknown>) => void;
}

export function PlotterChart({ chartType, kw, onEvent }: ChartProps) {
  const divRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!divRef.current) return;

    setLoading(true);
    setError(null);

    fetch(`${API_BASE}/render`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chart_type: chartType, kw }),
    })
      .then((r) => r.json())
      .then((data) => {
        if (!data.ok) {
          setError(data.error ?? 'Unknown error');
          return;
        }
        const spec = data.spec;
        Plotly.newPlot(divRef.current!, spec.data, spec.layout, {
          responsive: true,
          displayModeBar: true,
          editable: true,
        });

        // Wire edit events back to Python
        const div = divRef.current as any;
        div.on('plotly_relayout', (update: Record<string, unknown>) => {
          if (update['title.text'] !== undefined)
            postEvent('title_changed', update['title.text']);
          if (update['xaxis.title.text'] !== undefined)
            postEvent('xlabel_changed', update['xaxis.title.text']);
          if (update['yaxis.title.text'] !== undefined)
            postEvent('ytitle_changed', update['yaxis.title.text']);
        });
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));

    function postEvent(
      event: string,
      value: unknown,
      extra: Record<string, unknown> = {}
    ) {
      fetch(`${API_BASE}/event`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ event, value, extra }),
      }).catch(console.error);
      onEvent?.(event, value, extra);
    }
  }, [chartType, JSON.stringify(kw)]);

  if (loading) return <div style={{ padding: 20 }}>Loading chart...</div>;
  if (error) return <div style={{ padding: 20, color: 'red' }}>Error: {error}</div>;
  return <div ref={divRef} style={{ width: '100%', height: '100%' }} />;
}
```

Also create plotter_web/src/App.tsx (minimal shell):

```tsx
import { useState } from 'react';
import { PlotterChart } from './PlotterChart';

export default function App() {
  const [chartType] = useState('bar');
  const [kw] = useState({ excel_path: '', title: 'Claude Plotter' });

  return (
    <div style={{ fontFamily: 'Arial, sans-serif', height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <header style={{ padding: '8px 16px', background: '#2274A5', color: 'white' }}>
        <h1 style={{ margin: 0, fontSize: 18 }}>Claude Plotter</h1>
      </header>
      <main style={{ flex: 1 }}>
        <PlotterChart chartType={chartType} kw={kw} />
      </main>
    </div>
  );
}
```

git add plotter_web/src/
git commit -m "feat(agent-i): add PlotterChart React component with Plotly rendering"

=======================================================================
STEP 5: Add build script and install deps
=======================================================================

Create plotter_web/package.json if it doesn't exist from vite scaffold:

{
  "name": "plotter-web",
  "version": "1.0.0",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "plotly.js-dist-min": "^2.27.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "@vitejs/plugin-react": "^4.0.0",
    "typescript": "^5.0.0",
    "vite": "^5.0.0"
  }
}

Install and build:
  cd plotter_web && npm install && npm run build

If build succeeds, a plotter_web/dist/ directory is created.

Serve the built app via FastAPI:
In plotter_server.py, add after the app is created:

    from fastapi.staticfiles import StaticFiles
    import os

    web_dist = os.path.join(os.path.dirname(__file__), "plotter_web", "dist")
    if os.path.isdir(web_dist):
        api.mount("/", StaticFiles(directory=web_dist, html=True), name="static")

Run: xvfb-run python3 run_all.py (Python tests must still pass)
git commit -m "feat(agent-i): serve React SPA dist/ via FastAPI static files"

=======================================================================
STEP 6: Update pywebview to load the React SPA
=======================================================================

Open plotter_webview.py.

Currently it uses an inline HTML template. Update it to load the React
SPA from the FastAPI server instead:

Change the PlotterWebView.show() method:

    def show(self) -> bool:
        """Create and embed the webview pointing at the React SPA."""
        try:
            import webview
            import time

            # Wait for the FastAPI server to be ready
            import urllib.request
            for _ in range(10):
                try:
                    urllib.request.urlopen(
                        f"http://127.0.0.1:{self._port}/health", timeout=1)
                    break
                except Exception:
                    time.sleep(0.5)

            url = f"http://127.0.0.1:{self._port}/"

            def _create():
                self._window = webview.create_window(
                    "Claude Plotter",
                    url=url,
                    width=900, height=700,
                    resizable=True,
                )
                self._ready.set()
                webview.start()

            t = threading.Thread(target=_create, daemon=True)
            t.start()
            self._ready.wait(timeout=10.0)
            return self._window is not None

        except ImportError:
            return False
        except Exception:
            return False

NOTE: Only make this change if the React SPA build succeeded in Step 5.
If Step 5 was skipped, keep the inline HTML approach from Phase 3.

Run: xvfb-run python3 run_all.py
git commit -m "feat(agent-i): update pywebview to load React SPA from FastAPI"

=======================================================================
STEP 7: Create Docker deployment config
=======================================================================

Create Dockerfile in the project root:

    FROM python:3.12-slim

    WORKDIR /app

    # Install system dependencies
    RUN apt-get update && apt-get install -y \
        gcc \
        && rm -rf /var/lib/apt/lists/*

    # Copy Python files
    COPY plotter_functions.py plotter_validators.py plotter_results.py \
         plotter_registry.py plotter_widgets.py plotter_barplot_app.py \
         plotter_plotly_theme.py plotter_spec_bar.py plotter_spec_grouped_bar.py \
         plotter_spec_line.py plotter_spec_scatter.py plotter_server.py ./

    # Copy other plotter modules
    COPY plotter_*.py ./

    # Copy built React SPA (if exists)
    COPY plotter_web/dist ./plotter_web/dist/ 2>/dev/null || true

    # Install Python dependencies
    RUN pip install --no-cache-dir \
        fastapi uvicorn plotly pandas openpyxl scipy numpy

    # Expose port
    EXPOSE 7331

    # Run FastAPI server (web-only mode, no Tk)
    CMD ["python3", "-c", "from plotter_server import _make_app; import uvicorn; uvicorn.run(_make_app(), host='0.0.0.0', port=7331)"]

Create .dockerignore:

    __pycache__
    *.pyc
    .git
    .env
    venv
    .venv
    node_modules
    plotter_web/node_modules

Verify Dockerfile syntax:
  docker build --dry-run . 2>/dev/null || echo "docker not available, skipping build test"

git add Dockerfile .dockerignore
git commit -m "feat(agent-i): add Dockerfile for web deployment"

=======================================================================
STEP 8: Create requirements files
=======================================================================

Create requirements.txt (desktop, full):

    # Claude Plotter — Desktop requirements
    # Install with: pip install -r requirements.txt
    fastapi>=0.109.0
    uvicorn>=0.27.0
    plotly>=5.18.0
    pywebview>=4.4.0
    pandas>=2.0.0
    openpyxl>=3.1.0
    scipy>=1.11.0
    numpy>=1.26.0
    matplotlib>=3.8.0
    seaborn>=0.13.0
    xlrd>=2.0.1

Create requirements-web.txt (server, no Tk/matplotlib):

    # Claude Plotter — Web server requirements
    # Install with: pip install -r requirements-web.txt
    fastapi>=0.109.0
    uvicorn>=0.27.0
    plotly>=5.18.0
    pandas>=2.0.0
    openpyxl>=3.1.0
    scipy>=1.11.0
    numpy>=1.26.0

git add requirements.txt requirements-web.txt
git commit -m "feat(agent-i): add requirements.txt and requirements-web.txt"

=======================================================================
STEP 9: Create web-only entry point
=======================================================================

Create plotter_web_server.py (standalone web server, no Tk):

    #!/usr/bin/env python3
    """Claude Plotter — Web Server

    Starts the FastAPI server serving the React SPA and chart API.
    Does NOT require a display or Tkinter.

    Usage:
        python3 plotter_web_server.py [--port PORT] [--host HOST]
        PLOTTER_API_KEY=secret python3 plotter_web_server.py

    Environment variables:
        PLOTTER_API_KEY  — API key for non-local requests (optional)
        PORT             — Server port (default: 7331)
        HOST             — Bind address (default: 0.0.0.0 for web, 127.0.0.1 for local)
    """

    import os
    import sys
    import argparse

    def main():
        parser = argparse.ArgumentParser(description="Claude Plotter Web Server")
        parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 7331)))
        parser.add_argument("--host", default=os.environ.get("HOST", "0.0.0.0"))
        parser.add_argument("--reload", action="store_true", help="Enable hot reload")
        args = parser.parse_args()

        print(f"Claude Plotter Web Server")
        print(f"Listening on http://{args.host}:{args.port}")
        if os.environ.get("PLOTTER_API_KEY"):
            print("API key authentication enabled")

        import uvicorn
        from plotter_server import _make_app
        uvicorn.run(
            _make_app(),
            host=args.host,
            port=args.port,
            reload=args.reload,
            log_level="info",
        )

    if __name__ == "__main__":
        main()

Verify:
  python3 -c "import plotter_web_server; print('web server OK')"

git commit -m "feat(agent-i): add plotter_web_server.py standalone web entry point"

=======================================================================
STEP 10: Update CLAUDE.md with Phase 4 changes
=======================================================================

Open CLAUDE.md and add a new section after the existing content:

    ## Phase 4 — Deployment Readiness

    ### New files
    | File | Purpose |
    |---|---|
    | `plotter_web_server.py` | Standalone web server entry point (no Tk) |
    | `Dockerfile` | Docker deployment config |
    | `requirements.txt` | Desktop dependencies |
    | `requirements-web.txt` | Web server dependencies (no Tk/matplotlib) |
    | `plotter_web/` | React SPA (Vite + TypeScript + Plotly.js) |

    ### Running as a web service
    ```bash
    # Local development
    python3 plotter_web_server.py

    # With Docker
    docker build -t claude-plotter .
    docker run -p 7331:7331 claude-plotter

    # With API key authentication
    PLOTTER_API_KEY=your-secret python3 plotter_web_server.py
    ```

    ### Architecture
    ```
    Desktop mode:   Tk shell → pywebview → React SPA → FastAPI (127.0.0.1:7331)
    Web mode:       Browser → React SPA → FastAPI (0.0.0.0:7331)
    Both modes:     same Python business logic, same FastAPI server
    ```

    ### Phase 4 gotchas
    11. **pywebview on headless servers** — pywebview requires a display.
        Use `plotter_web_server.py` (no Tk, no pywebview) for headless deployment.
    12. **React SPA build** — Run `cd plotter_web && npm install && npm run build`
        before deployment. The dist/ directory must exist for static file serving.
    13. **CORS** — FastAPI allows all origins by default. In production, restrict
        `allow_origins` in plotter_server.py to your domain.
    14. **API key** — Set `PLOTTER_API_KEY` env var for non-local request auth.

Run: xvfb-run python3 run_all.py (must still pass)
git commit -m "docs(agent-i): update CLAUDE.md with Phase 4 deployment docs"

=======================================================================
STEP 11: Update README.md
=======================================================================

Open README.md and update:

1. Title: "# Claude Plotter"

2. Add badges section after title:
   ![Tests](https://img.shields.io/badge/tests-520%2B%20passing-brightgreen)
   ![Python](https://img.shields.io/badge/python-3.12-blue)

3. Update Features section to include:
   - Plotly.js interactive charts (Phase 3) for bar, grouped bar, line, scatter
   - FastAPI backend — runs as desktop app or web service
   - React SPA frontend
   - Docker deployment support
   - .cplot project files
   - .pzfx (GraphPad Prism) import
   - Statistical wiki popup

4. Add Quick Start section:
   ```bash
   # Desktop (requires macOS + display)
   python3 plotter_barplot_app.py

   # Web server (no display required)
   pip install -r requirements-web.txt
   python3 plotter_web_server.py
   # Open http://localhost:7331

   # Docker
   docker build -t claude-plotter .
   docker run -p 7331:7331 claude-plotter
   ```

5. Add Supported File Formats section:
   | Format | Read | Write |
   |--------|------|-------|
   | .xlsx / .xls | ✅ | — |
   | .cplot (Claude Plotter project) | ✅ | ✅ |
   | .pzfx (GraphPad Prism) | ✅ (import) | — |

git commit -m "docs(agent-i): update README with web deployment and new features"

=======================================================================
STEP 12: Create phase4/PHASE4_SUMMARY.md
=======================================================================

Create phase4/PHASE4_SUMMARY.md:

    # Phase 4 Build Summary

    ## Test Results
    - Total tests: [run xvfb-run python3 run_all.py and fill in]
    - Passing: [number]
    - Failing: [number]

    ## New Files Created
    - plotter_web_server.py: standalone web entry point
    - Dockerfile: Docker deployment config
    - requirements.txt: full desktop dependencies
    - requirements-web.txt: web-only dependencies
    - plotter_web/: React SPA (Vite + TypeScript + Plotly.js)

    ## Modified Files
    - plotter_server.py: auth middleware, /spec endpoint, /chart-types, static file serving
    - plotter_webview.py: loads React SPA from FastAPI instead of inline HTML
    - CLAUDE.md: Phase 4 docs added
    - README.md: updated with deployment instructions

    ## Features Added
    1. Web server mode (no Tk/display required)
    2. Docker deployment config
    3. React SPA with PlotterChart component
    4. API key authentication for web deployments
    5. /spec, /chart-types, /health API endpoints
    6. Static file serving of React build

    ## Known Issues
    [fill in anything from AGENT_I_ISSUES.txt]

    ## Deployment Checklist
    - [ ] All tests pass (xvfb-run python3 run_all.py)
    - [ ] FastAPI server starts and /health responds
    - [ ] React SPA builds successfully (npm run build)
    - [ ] Docker build succeeds
    - [ ] Dockerfile tested with docker run

git add phase4/PHASE4_SUMMARY.md
git commit -m "docs(agent-i): add Phase 4 build summary"

=======================================================================
FINAL VERIFICATION
=======================================================================

1. xvfb-run python3 run_all.py
   Must pass >= 520 tests, 0 failures

2. python3 -c "
   from plotter_server import _make_app
   from plotter_web_server import main
   print('All Phase 4 Python modules OK')
   "

3. ls plotter_web/dist/ 2>/dev/null && echo 'React SPA built' || echo 'React SPA not built'

4. docker build --dry-run . 2>/dev/null || echo 'docker not available'

5. git log --oneline | head -25

6. Final commit:
   git commit --allow-empty -m "feat(agent-i): Phase 4 complete — deployment readiness

   New files:
   - plotter_web_server.py: standalone web entry point
   - Dockerfile: Docker deployment config
   - requirements.txt / requirements-web.txt: dependency files
   - plotter_web/: React SPA (Vite + TypeScript + Plotly.js)
   - plotter_web/src/PlotterChart.tsx: Plotly rendering component
   - phase4/PHASE4_SUMMARY.md: build summary

   Modified:
   - plotter_server.py: auth + /spec + /chart-types + static file serving
   - plotter_webview.py: loads React SPA from FastAPI
   - CLAUDE.md / README.md: deployment documentation

   All 520+ tests passing.
   Desktop mode: python3 plotter_barplot_app.py
   Web mode: python3 plotter_web_server.py"
