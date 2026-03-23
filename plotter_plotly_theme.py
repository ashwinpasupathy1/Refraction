"""Plotly theme matching Refraction's matplotlib style."""

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
