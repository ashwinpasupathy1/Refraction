"""Refraction analysis engine -- renderer-independent statistical analysis.

This module provides the ``analyze()`` function which accepts a chart type,
an Excel file path, and configuration options.  It reads the data, runs the
appropriate statistical tests via ``refraction.core.chart_helpers``, and
returns a plain dict of results (means, errors, p-values, etc.) that any
renderer (SwiftUI Charts, Plotly, matplotlib) can consume.
"""

from refraction.analysis.engine import analyze

__all__ = ["analyze"]
