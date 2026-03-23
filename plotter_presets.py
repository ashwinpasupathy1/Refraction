"""plotter_presets.py — Style preset system for Refraction."""

import json
import logging
import os
import time

_log = logging.getLogger(__name__)

PRESETS_DIR = os.path.expanduser(
    "~/Library/Application Support/Refraction/presets/"
)

PRESET_KEYS = [
    "error", "show_points", "show_n_labels", "show_value_labels",
    "color", "yscale", "font_size", "bar_width", "line_width", "marker_style",
    "marker_size", "axis_style", "tick_dir", "minor_ticks", "point_size",
    "point_alpha", "cap_size", "legend_pos", "spine_width", "fig_bg",
    "grid_style", "open_points", "bar_alpha", "show_stats", "stats_test",
    "mc_correction", "posthoc", "bracket_style", "show_p_values",
    "show_effect_size", "show_test_name", "show_normality_warning",
    "p_sig_threshold",
]

BUILT_IN_PRESETS = {
    "Publication (B&W)": {
        "color": "grayscale",
        "font_size": "14",
        "spine_width": "1.2",
        "axis_style": "open",
        "tick_dir": "out",
        "minor_ticks": False,
        "fig_bg": "white",
        "grid_style": "none",
        "open_points": False,
    },
    "Presentation": {
        "color": "default",
        "font_size": "16",
        "spine_width": "1.5",
        "axis_style": "open",
        "tick_dir": "out",
        "minor_ticks": False,
        "fig_bg": "white",
        "grid_style": "none",
        "open_points": False,
    },
    "Poster": {
        "color": "default",
        "font_size": "18",
        "spine_width": "2.0",
        "axis_style": "open",
        "tick_dir": "out",
        "minor_ticks": False,
        "fig_bg": "white",
        "grid_style": "none",
        "open_points": False,
    },
    "Colorblind Safe": {
        "color": "colorblind",
        "font_size": "12",
        "spine_width": "1.0",
        "axis_style": "open",
        "tick_dir": "out",
        "minor_ticks": False,
        "fig_bg": "white",
        "grid_style": "none",
        "open_points": True,
    },
    "Minimal": {
        "color": "grayscale",
        "font_size": "12",
        "spine_width": "0.8",
        "axis_style": "none",
        "tick_dir": "out",
        "minor_ticks": False,
        "fig_bg": "white",
        "grid_style": "horizontal",
        "open_points": False,
    },
}


def save_preset(name: str, app_vars: dict) -> str:
    """Save current app vars as a named preset. Returns file path."""
    os.makedirs(PRESETS_DIR, exist_ok=True)
    data = {}
    for key in PRESET_KEYS:
        if key in app_vars:
            var = app_vars[key]
            if hasattr(var, "get"):
                data[key] = var.get()
            else:
                data[key] = var
    data["_name"] = name
    data["_timestamp"] = time.time()
    safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in name)
    path = os.path.join(PRESETS_DIR, f"{safe_name}.json")
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp_path, path)
    return path


def load_preset(name: str) -> dict:
    """Load preset by name. Checks built-ins first, then user dir."""
    if name in BUILT_IN_PRESETS:
        result = dict(BUILT_IN_PRESETS[name])
        result["_name"] = name
        result["_builtin"] = True
        return result
    safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in name)
    path = os.path.join(PRESETS_DIR, f"{safe_name}.json")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Preset not found: {name!r}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def apply_preset(preset_dict: dict, app_vars: dict) -> None:
    """Write preset values into StringVar/BooleanVar app vars."""
    for key, value in preset_dict.items():
        if key.startswith("_"):
            continue
        if key not in app_vars:
            continue
        var = app_vars[key]
        if hasattr(var, "set"):
            try:
                var.set(value)
            except Exception:
                _log.debug("apply_preset: could not set var %r to %r", key, value, exc_info=True)


def list_presets() -> list:
    """Return list of {name, is_builtin, timestamp} dicts."""
    results = []
    for name in BUILT_IN_PRESETS:
        results.append({"name": name, "is_builtin": True, "timestamp": None})
    if os.path.isdir(PRESETS_DIR):
        for fname in sorted(os.listdir(PRESETS_DIR)):
            if not fname.endswith(".json"):
                continue
            path = os.path.join(PRESETS_DIR, fname)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                pname = data.get("_name", fname[:-5])
                ts = data.get("_timestamp")
                results.append({"name": pname, "is_builtin": False, "timestamp": ts})
            except Exception:
                _log.debug("list_presets: could not read preset file %r", path, exc_info=True)
    return results


def delete_preset(name: str) -> bool:
    """Delete a user preset. Returns False for built-ins."""
    if name in BUILT_IN_PRESETS:
        return False
    safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in name)
    path = os.path.join(PRESETS_DIR, f"{safe_name}.json")
    if os.path.exists(path):
        os.remove(path)
        return True
    return False
