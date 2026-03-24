"""Shared helpers for the analysis engine."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from refraction.specs.theme import PRISM_PALETTE


def resolve_colors(color: Any, n: int) -> List[str]:
    """Return a list of *n* hex colour strings.

    - ``None``        -> cycle through PRISM_PALETTE
    - single string   -> repeat it n times
    - list            -> cycle to fill n entries
    """
    if color is None:
        return [PRISM_PALETTE[i % len(PRISM_PALETTE)] for i in range(n)]
    if isinstance(color, str):
        return [color] * n
    # list / tuple — cycle
    return [color[i % len(color)] for i in range(n)]


def extract_config(kw: Dict[str, Any]) -> Dict[str, Any]:
    """Normalise user-facing kwargs into internal config keys.

    Maps common aliases so that analyzers can use a consistent set of
    names regardless of how the caller labelled them.
    """
    cfg: Dict[str, Any] = dict(kw)  # shallow copy

    # ytitle -> ylabel
    if "ytitle" in cfg and "ylabel" not in cfg:
        cfg["ylabel"] = cfg.pop("ytitle")

    # title -> title (already canonical, but keep for completeness)

    # error_type aliases
    et = cfg.get("error_type", cfg.get("error_bar_type", "SEM"))
    cfg["error_type"] = et

    # show_points
    cfg.setdefault("show_points", False)

    # stats_test
    cfg.setdefault("stats_test", None)

    return cfg
