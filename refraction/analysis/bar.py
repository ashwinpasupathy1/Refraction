"""Bar chart analyzer — returns renderer-independent ChartSpec."""

from __future__ import annotations

import numpy as np

from refraction.analysis.schema import ChartSpec, StyleSpec
from refraction.analysis.helpers import read_data, resolve_colors, extract_config
from refraction.analysis.stats_annotator import annotate_stats


def analyze_bar(config: dict) -> ChartSpec:
    """Analyze data for a bar chart.

    Config keys:
        excel_path / data_path: path to Excel/CSV file
        sheet: sheet index (default 0)
        title, xlabel, ylabel: axis labels
        color: single hex, list of hex, or None for palette
        error: "sem" | "sd" | "ci95" (default "sem")
        show_points: bool (default False) — include raw_points in output
        jitter: float (default 0.15)
        point_opacity: float (default 0.8)

        # Stats options (all optional):
        stats_test: "parametric" | "nonparametric" | "paired" | "permutation" | "one_sample"
        posthoc: posthoc method name
        mc_correction: correction method name
        control: control group name
        show_ns: include non-significant brackets
        p_threshold: significance threshold
    """
    from scipy import stats as _stats  # for CI95

    ck = extract_config(config)
    df = read_data(ck["data_path"], ck["sheet"])

    error_type = config.get("error", "sem")
    show_points = config.get("show_points", False)

    # Extract groups from columns
    groups_data: list[dict] = []
    groups_raw: dict[str, list[float]] = {}

    for col in df.columns:
        vals = df[col].dropna().tolist()
        numeric_vals = [float(v) for v in vals if _is_numeric(v)]
        if not numeric_vals:
            continue

        n = len(numeric_vals)
        mean = float(np.mean(numeric_vals))
        sd = float(np.std(numeric_vals, ddof=1)) if n > 1 else 0.0

        if error_type == "sem":
            error = sd / np.sqrt(n) if n > 0 else 0.0
        elif error_type == "sd":
            error = sd
        else:  # ci95
            t_crit = _stats.t.ppf(0.975, df=max(n - 1, 1))
            error = t_crit * sd / np.sqrt(max(n, 1))

        group_entry: dict = {
            "name": str(col),
            "values": {
                "mean": round(mean, 6),
                "error": round(float(error), 6),
                "error_type": error_type,
                "n": n,
            },
        }

        # Raw points only if requested (avoids large payloads)
        if show_points:
            group_entry["raw_points"] = [round(v, 6) for v in numeric_vals]

        groups_data.append(group_entry)
        groups_raw[str(col)] = numeric_vals

    # Resolve colors explicitly
    colors = resolve_colors(ck["color"], len(groups_data))

    # Compute suggested Y range
    all_means = [g["values"]["mean"] for g in groups_data]
    all_errors = [g["values"]["error"] for g in groups_data]
    y_max = max(m + e for m, e in zip(all_means, all_errors)) if all_means else 1.0
    y_min = min(0, min(m - e for m, e in zip(all_means, all_errors))) if all_means else 0.0

    # Build axes
    axes = {
        "x": {
            "label": ck["xlabel"],
            "type": "categorical",
            "categories": [g["name"] for g in groups_data],
        },
        "y": {
            "label": ck["ylabel"],
            "type": config.get("yscale", "linear"),
            "suggested_range": [round(y_min, 6), round(y_max * 1.15, 6)],
        },
        "title": ck["title"],
    }

    # Run stats if requested
    stats_result = None
    brackets = []
    stats_test = config.get("stats_test")
    if stats_test and len(groups_raw) >= 2:
        stats_result, brackets = annotate_stats(
            groups_raw,
            stats_test=stats_test,
            posthoc=config.get("posthoc", "Tukey HSD"),
            mc_correction=config.get("mc_correction", "Holm-Bonferroni"),
            control=config.get("control"),
            n_permutations=config.get("n_permutations", 9999),
            mu0=config.get("mu0", 0.0),
            p_threshold=config.get("p_threshold", 0.05),
            show_ns=config.get("show_ns", False),
        )

        # Assign bracket stacking order (renderer uses this for Y positioning)
        # Sort by span width (narrower brackets drawn lower, wider ones higher)
        categories = [g["name"] for g in groups_data]
        cat_idx = {name: i for i, name in enumerate(categories)}
        for i, bracket in enumerate(brackets):
            a_idx = cat_idx.get(bracket.group_a, 0)
            b_idx = cat_idx.get(bracket.group_b, 0)
            bracket_span = abs(b_idx - a_idx)
            # Stacking order: 0 = lowest bracket, higher = further from bars
            brackets[i] = bracket  # preserved; order established by sort below

        brackets.sort(key=lambda b: abs(
            cat_idx.get(b.group_b, 0) - cat_idx.get(b.group_a, 0)
        ))
        # Add stacking_order to annotation dicts
        bracket_annotations = []
        for order, b in enumerate(brackets):
            bracket_annotations.append({
                "group_a": b.group_a,
                "group_b": b.group_b,
                "label": b.label,
                "p": round(b.p, 6),
                "stacking_order": order,
            })
    else:
        bracket_annotations = []

    return ChartSpec(
        chart_type="bar",
        data={"groups": groups_data},
        axes=axes,
        statistics=stats_result,
        annotations={
            "brackets": bracket_annotations,
            "reference_lines": [],
        },
        style=StyleSpec(
            colors=colors,
            show_points=show_points,
            show_error_bars=config.get("show_error_bars", True),
            show_brackets=bool(bracket_annotations),
            jitter=config.get("jitter", 0.15),
            point_opacity=config.get("point_opacity", 0.8),
            error_type=error_type,
        ),
    )


def _is_numeric(v) -> bool:
    """Check if a value is numeric (int, float, numpy number)."""
    try:
        float(v)
        return True
    except (TypeError, ValueError):
        return False
