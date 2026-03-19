"""Phase 6 desktop entry point for Spectra.

Starts the FastAPI server in a background daemon thread, waits for it to be
ready, then opens a full-screen pywebview window pointing at the React SPA
served by FastAPI.  No Tkinter is used at all.

Usage:
    python3 plotter_desktop.py
    python3 plotter_desktop.py --port 8080
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
import threading
import urllib.request
import urllib.error

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s  %(name)s: %(message)s",
)
_log = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

_DEFAULT_PORT = 7331
_WINDOW_TITLE = "Spectra"
_WINDOW_WIDTH = 1200
_WINDOW_HEIGHT = 800
_HEALTH_TIMEOUT = 30      # seconds to wait for server readiness
_HEALTH_INTERVAL = 0.25   # seconds between health-check polls


# ── CLI ───────────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Spectra — desktop launcher (pywebview, no Tk)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=_DEFAULT_PORT,
        metavar="PORT",
        help=f"Port for the FastAPI server (default: {_DEFAULT_PORT})",
    )
    return parser.parse_args()


# ── Server helpers ─────────────────────────────────────────────────────────────

def _start_server(port: int) -> threading.Thread:
    """Launch FastAPI/uvicorn in a background daemon thread on *port*.

    Imports plotter_server at call time so the module-level _PORT override
    takes effect before uvicorn binds.
    """
    import plotter_server as _srv

    # Override the module-level port so get_port() returns the right value.
    _srv._PORT = port  # noqa: SLF001

    def _run() -> None:
        try:
            import uvicorn
            uvicorn.run(
                _srv._make_app(),
                host="127.0.0.1",
                port=port,
                log_level="warning",
                access_log=False,
            )
        except Exception:
            _log.exception("Server thread encountered an unhandled error")

    t = threading.Thread(target=_run, daemon=True, name="plotter-server")
    t.start()
    return t


def _wait_for_server(port: int, timeout: float = _HEALTH_TIMEOUT) -> bool:
    """Poll GET /health until it returns 200 or *timeout* seconds elapse.

    Returns True if the server is ready, False if it timed out.
    """
    url = f"http://127.0.0.1:{port}/health"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(_HEALTH_INTERVAL)
    return False


# ── Banner ─────────────────────────────────────────────────────────────────────

def _print_banner(port: int) -> None:
    url = f"http://127.0.0.1:{port}"
    print()
    print("╔══════════════════════════════════════════╗")
    print("║              Spectra  (Phase 6)            ║")
    print("╠══════════════════════════════════════════╣")
    print(f"║  URL : {url:<34}║")
    print("║  Mode: pywebview desktop (no Tk)         ║")
    print("║  Close the window to quit.               ║")
    print("╚══════════════════════════════════════════╝")
    print()


# ── pywebview window ──────────────────────────────────────────────────────────

def _open_window(port: int) -> None:
    """Create and start the pywebview window.  Blocks until the window closes."""
    try:
        import webview
    except ImportError:
        print(
            "ERROR: pywebview is not installed.\n"
            "       Install it with:  pip install pywebview",
            file=sys.stderr,
        )
        sys.exit(1)

    url = f"http://127.0.0.1:{port}/"

    window = webview.create_window(
        title=_WINDOW_TITLE,
        url=url,
        width=_WINDOW_WIDTH,
        height=_WINDOW_HEIGHT,
        resizable=True,
        min_size=(_WINDOW_WIDTH // 2, _WINDOW_HEIGHT // 2),
    )

    # webview.start() blocks until the window is closed.
    # The daemon server thread will be killed automatically when this
    # process exits after start() returns.
    webview.start(debug=False)


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    args = _parse_args()
    port: int = args.port

    # 1. Start the FastAPI server in a daemon thread.
    print(f"Starting Spectra server on port {port}…")
    _start_server(port)

    # 2. Wait for the server to accept connections before opening the window.
    print("Waiting for server to be ready…", end="", flush=True)
    ready = _wait_for_server(port)
    if not ready:
        print(" FAILED")
        print(
            f"ERROR: Server did not become ready within {_HEALTH_TIMEOUT}s.\n"
            "       Check that the port is not already in use.",
            file=sys.stderr,
        )
        sys.exit(1)
    print(" OK")

    # 3. Print the startup banner.
    _print_banner(port)

    # 4. Open the pywebview window (blocks until closed).
    _open_window(port)

    # 5. Window closed — daemon thread exits automatically.
    print("Spectra closed.")


if __name__ == "__main__":
    main()
