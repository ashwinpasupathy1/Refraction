#!/usr/bin/env python3
"""Spectra — Web Server

Starts the FastAPI server serving the React SPA and chart API.
Does NOT require a display or Tkinter.

Usage:
    python3 plotter_web_server.py [--port PORT] [--host HOST]
    PLOTTER_API_KEY=secret python3 plotter_web_server.py

Environment variables:
    PLOTTER_API_KEY  — API key for non-local requests (optional)
    PORT             — Server port (default: 7331)
    HOST             — Bind address (default: 0.0.0.0)
"""

import os
import sys
import argparse


def main():
    parser = argparse.ArgumentParser(description="Spectra Web Server")
    parser.add_argument("--port", type=int,
                        default=int(os.environ.get("PORT", 7331)))
    parser.add_argument("--host",
                        default=os.environ.get("HOST", "0.0.0.0"))
    parser.add_argument("--reload", action="store_true",
                        help="Enable hot reload")
    args = parser.parse_args()

    print(f"Spectra Web Server")
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
