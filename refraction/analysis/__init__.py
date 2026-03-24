"""Refraction analysis engine — renderer-independent chart analysis.

Usage:
    from refraction.analysis import analyze

    spec = analyze(
        data="path/to/data.xlsx",
        chart_type="bar",
        config={"error": "sem", "stats_test": "parametric"}
    )
    # spec is a dict any renderer can consume
"""

from refraction.analysis.engine import analyze

__all__ = ["analyze"]
