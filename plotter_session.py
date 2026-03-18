"""plotter_session.py — Session persistence for Claude Plotter."""

import json
import logging
import os
import time

_log = logging.getLogger(__name__)

PREFS_PATH = os.path.expanduser(
    "~/Library/Preferences/claude_plotter_session.json"
)


class Session:
    """Save and restore UI state across app launches."""

    def capture(self, app_vars: dict, plot_type: str = "",
                window_geometry: str = "") -> dict:
        """Snapshot all vars into a plain dict."""
        state = {
            "_timestamp": time.time(),
            "_plot_type": plot_type,
            "_window_geometry": window_geometry,
        }
        for key, var in app_vars.items():
            if hasattr(var, "get"):
                try:
                    state[key] = var.get()
                except Exception:
                    _log.debug("Session.capture: could not read var %r", key, exc_info=True)
        return state

    def restore(self, state: dict, app_vars: dict,
                set_plot_type_fn=None, set_geometry_fn=None) -> None:
        """Apply saved state to app vars."""
        for key, value in state.items():
            if key.startswith("_"):
                continue
            if key not in app_vars:
                continue
            var = app_vars[key]
            if hasattr(var, "set"):
                try:
                    var.set(value)
                except Exception:
                    _log.debug("Session.restore: could not set var %r to %r", key, value, exc_info=True)
        if set_plot_type_fn is not None and "_plot_type" in state:
            try:
                set_plot_type_fn(state["_plot_type"])
            except Exception:
                _log.debug("Session.restore: set_plot_type_fn failed for %r",
                           state["_plot_type"], exc_info=True)
        if set_geometry_fn is not None and "_window_geometry" in state:
            try:
                set_geometry_fn(state["_window_geometry"])
            except Exception:
                _log.debug("Session.restore: set_geometry_fn failed for %r",
                           state["_window_geometry"], exc_info=True)

    def save_to_disk(self, state: dict) -> None:
        """Atomic JSON write of state to disk."""
        tmp_path = PREFS_PATH + ".tmp"
        os.makedirs(os.path.dirname(PREFS_PATH), exist_ok=True)
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        os.replace(tmp_path, PREFS_PATH)

    def load_from_disk(self) -> dict:
        """Read saved state or return empty dict."""
        if not os.path.exists(PREFS_PATH):
            return {}
        try:
            with open(PREFS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            _log.debug("Session.load_from_disk: could not load %r", PREFS_PATH, exc_info=True)
            return {}

    def clear(self) -> None:
        """Delete the session file."""
        if os.path.exists(PREFS_PATH):
            os.remove(PREFS_PATH)
