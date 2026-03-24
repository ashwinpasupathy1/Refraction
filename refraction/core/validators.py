"""
plotter_validators.py
=====================
Standalone spreadsheet validation functions for Refraction.

Each validate_* function accepts a raw pandas DataFrame (read with
header=None so row indices are preserved) and returns a
(errors: list[str], warnings: list[str]) tuple.

An empty errors list means the sheet is valid. warnings are shown to
the user but do not block plotting.

These functions are pure - they take only a DataFrame and return strings.
The App class calls them inside _validate_spreadsheet() and displays
the results via _set_validate_text().

Chart-to-validator mapping
--------------------------
bar, box, violin, subcolumn_scatter, before_after,
repeated_measures, histogram, dot_plot
    -> validate_flat_header()  (via chart-specific thin wrappers)

line, scatter, curve_fit    -> validate_line()
grouped_bar, stacked_bar    -> validate_grouped_bar()
kaplan_meier                -> validate_kaplan_meier()
heatmap                     -> validate_heatmap()
two_way_anova               -> validate_two_way_anova()
contingency                 -> validate_contingency()
chi_square_gof              -> validate_chi_square_gof()
bland_altman                -> validate_bland_altman()
forest_plot                 -> validate_forest_plot()
area_chart, raincloud, qq_plot, lollipop, waterfall, ecdf
                            -> validate_bar()  (flat-header layout)
pyramid                     -> validate_pyramid()
"""

from __future__ import annotations

from typing import Any, List, Tuple

# Type alias for the (errors, warnings) return value.
ValidationResult = Tuple[List[str], List[str]]


# ---------------------------------------------------------------------------
# Lazy pandas access (mirrors the _pd() pattern in plotter_barplot_app)
# ---------------------------------------------------------------------------

def _pd() -> Any:
    """Return pandas, importing it lazily on first call."""
    import pandas as _p
    return _p


# ---------------------------------------------------------------------------
# Cell-level helpers  (duplicated here so this module is self-contained
# and can be unit-tested without importing the full App)
# ---------------------------------------------------------------------------

def _is_num(v: object) -> bool:
    """Return True if v can be cast to float."""
    try:
        float(v)  # type: ignore[arg-type]
        return True
    except (ValueError, TypeError):
        return False


def _non_numeric_values(series: Any, max_shown: int = 5) -> list[str]:
    """Return at most max_shown non-numeric cell string representations from series."""
    return [str(v) for v in series.dropna() if not _is_num(v)][:max_shown]


# ---------------------------------------------------------------------------
def validate_flat_header(df: Any,
                          min_groups: int = 2,
                          min_rows: int = 3,
                          chart_name: str = "bar graph") -> ValidationResult:
    """Validate a flat-header layout (Row 1 = group names, Rows 2+ = values).

    Used by: bar, box, violin, subcolumn_scatter, before_after,
             repeated_measures, histogram, dot_plot, and any future chart
             that uses the same row-1-header / rows-2+-data layout.

    Parameters
    ----------
    min_groups : minimum number of named columns to avoid a warning
    min_rows   : minimum number of data rows to support stats (warning only)
    chart_name : human-readable chart type for error messages

    Returns
    -------
    (errors, warnings)  -  both are lists of strings
    """
    pd = _pd()
    errors, warnings = [], []

    if df.shape[0] < 2:
        errors.append(
            f"Sheet has fewer than 2 rows. "
            f"Expected: Row 1 = group names, Rows 2+ = data values.")
        return errors, warnings
    if df.shape[1] < 1:
        errors.append("Sheet has no columns.")
        return errors, warnings

    headers    = df.iloc[0]
    empty_hdrs = [i for i, h in enumerate(headers)
                  if pd.isna(h) or str(h).strip() == ""]

    if len(empty_hdrs) == df.shape[1]:
        errors.append(
            "Row 1 is entirely empty. "
            "Row 1 should contain group names (e.g. 'Control', 'Treatment').")
    elif empty_hdrs:
        warnings.append(
            f"Row 1 has {len(empty_hdrs)} empty cell(s) in "
            f"column(s) {[i+1 for i in empty_hdrs]}. "
            "Each column should have a group name in row 1.")

    data = df.iloc[1:]
    for col_i in range(df.shape[1]):
        ch       = (str(headers.iloc[col_i])
                    if pd.notna(headers.iloc[col_i]) else f"Column {col_i+1}")
        col_vals = data.iloc[:, col_i].dropna()
        if len(col_vals) == 0:
            warnings.append(
                f"Column '{ch}' has no data values (all empty below row 1).")
            continue
        non_num = _non_numeric_values(col_vals)
        if non_num:
            errors.append(
                f"Column '{ch}' contains non-numeric values: "
                f"{non_num}. All data values (rows 2+) must be numbers.")
            continue
        num_vals = col_vals.apply(lambda v: float(v))
        if len(num_vals) == 1:
            warnings.append(
                f"Column '{ch}' has only 1 value. "
                "Statistical tests require at least 2 values per group.")
        elif len(num_vals) > 1 and num_vals.nunique() == 1:
            warnings.append(
                f"Column '{ch}' has all identical values ({num_vals.iloc[0]}). "
                "Standard deviation is zero — t-tests and ANOVA will produce NaN or fail.")

    if df.shape[1] < min_groups:
        warnings.append(
            f"Only {df.shape[1]} group/column(s) found. "
            f"{chart_name.capitalize()} work best with {min_groups}+ groups.")
    if df.shape[0] < min_rows + 1:  # +1 for header row
        warnings.append(
            f"Only {df.shape[0] - 1} data row(s) per group. "
            "Statistical tests require at least 3 replicates per group.")

    return errors, warnings

def validate_bar(df: Any) -> ValidationResult:
    """Validate a bar-chart sheet (flat header: row 0 = group names, rows 1+ = values)."""
    return validate_flat_header(df, min_groups=2, min_rows=3,
                                  chart_name="bar graph")

def validate_line(df: Any) -> ValidationResult:
    """Validate a line/scatter-chart sheet (col 0 = X, col 1 = X-axis label, cols 2+ = series)."""
    pd = _pd()
    errors, warnings = [], []

    # Minimum shape
    if df.shape[0] < 2:
        errors.append("Sheet has fewer than 2 rows. "
                      "Expected: Row 1 = series names, Rows 2+ = data values.")
        return errors, warnings
    if df.shape[1] < 2:
        errors.append("Sheet needs at least 2 columns: "
                      "Col 1 = numeric X values, Col 2+ = Y replicates.")
        return errors, warnings

    # Row 1: col 1 can be anything (X axis title or blank), cols 2+ = series names
    series_hdrs = [str(h) if pd.notna(h) else ""
                   for h in df.iloc[0, 1:]]
    empty_series = [i+2 for i, h in enumerate(series_hdrs) if not h.strip()]
    if len(empty_series) == len(series_hdrs):
        errors.append("Row 1 (columns 2+) must contain series names. "
                      "All series name cells are empty.")
    elif empty_series:
        warnings.append(f"Row 1 has empty series name(s) in column(s) "
                        f"{empty_series}. Each Y column should have a series name.")

    # Col 1 (rows 2+): must be numeric X values
    x_col = df.iloc[1:, 0]
    non_num_x = _non_numeric_values(x_col)
    if non_num_x:
        errors.append(f"Column 1 must contain numeric X values, but found: "
                      f"{non_num_x}.")
    empty_x = x_col.isna().sum()
    if empty_x > 0:
        warnings.append(f"Column 1 (X values) has {empty_x} empty cell(s). "
                        "Each row should have a numeric X value.")

    # Cols 2+ (rows 2+): must be numeric Y values
    for col_i in range(1, df.shape[1]):
        ch = series_hdrs[col_i - 1] if series_hdrs[col_i - 1] else f"Column {col_i+1}"
        col_data = df.iloc[1:, col_i].dropna()
        non_num = _non_numeric_values(col_data)
        if non_num:
            errors.append(f"Column '{ch}' (col {col_i+1}) contains non-numeric values: "
                          f"{non_num}.")

    # Warn if fewer than 2 X points
    if df.shape[0] < 3:
        warnings.append("Only 1 data row found. "
                        "A line graph needs at least 2 X points to draw a line.")

    # Warn if any series has fewer than 3 replicates
    from collections import Counter
    counts = Counter(h for h in series_hdrs if h.strip())
    for s, n in counts.items():
        if n < 3:
            warnings.append(f"Series '{s}' has only {n} replicate column(s). "
                            "At least 3 replicates are recommended for error bars.")

    return errors, warnings

def validate_grouped_bar(df: Any) -> ValidationResult:
    """Validate a grouped-bar sheet (row 0 = categories, row 1 = subgroups, rows 2+ = values)."""
    pd = _pd()
    from collections import Counter
    errors, warnings = [], []

    if df.shape[0] < 3:
        errors.append("Sheet needs at least 3 rows: "
                      "Row 1 = category names, Row 2 = subgroup names, Rows 3+ = data values.")
        return errors, warnings
    if df.shape[1] < 2:
        errors.append("Sheet needs at least 2 columns.")
        return errors, warnings

    row1 = [str(h) if pd.notna(h) else "" for h in df.iloc[0]]
    row2 = [str(h) if pd.notna(h) else "" for h in df.iloc[1]]

    # Row 1: category names
    empty_cats = [i+1 for i, h in enumerate(row1) if not h.strip()]
    if len(empty_cats) == len(row1):
        errors.append("Row 1 must contain category names  -  all cells are empty.")
    elif empty_cats:
        warnings.append(f"Row 1 has empty category name(s) in column(s) {empty_cats}.")

    # Row 2: subgroup names
    empty_subs = [i+1 for i, h in enumerate(row2) if not h.strip()]
    if len(empty_subs) == len(row2):
        errors.append("Row 2 must contain subgroup names  -  all cells are empty.")
    elif empty_subs:
        warnings.append(f"Row 2 has empty subgroup name(s) in column(s) {empty_subs}.")

    # Rows 3+: must be numeric
    data = df.iloc[2:]
    for col_i in range(df.shape[1]):
        ch = row2[col_i] if row2[col_i] else (row1[col_i] if row1[col_i] else f"Column {col_i+1}")
        non_num = _non_numeric_values(data.iloc[:, col_i])
        if non_num:
            errors.append(f"Column '{ch}' (col {col_i+1}) contains non-numeric values: "
                          f"{non_num}.")

    if df.shape[0] < 4:
        warnings.append("Only 1 data row  -  at least 3 replicates are recommended per subgroup.")

    # Check at least 2 subgroups per category (otherwise grouped chart is pointless)
    cats = list(dict.fromkeys(h for h in row1 if h.strip()))
    subs = list(dict.fromkeys(h for h in row2 if h.strip()))
    if len(subs) < 2:
        warnings.append("Only 1 subgroup found. "
                        "A grouped bar chart works best with 2+ subgroups per category.")

    # Warn if replicate counts are unequal across subgroups
    for cat in cats:
        sub_counts = Counter()
        for col_i in range(df.shape[1]):
            if row1[col_i] == cat and row2[col_i].strip():
                sub_counts[row2[col_i]] += 1
        counts = list(sub_counts.values())
        if counts and max(counts) != min(counts):
            warnings.append(f"Category '{cat}' has unequal replicate counts across subgroups "
                            f"{dict(sub_counts)}  -  this is allowed but worth checking.")

    return errors, warnings

def validate_kaplan_meier(df: Any) -> ValidationResult:
    """Validate a Kaplan-Meier survival sheet (row 0 = groups, row 1 = Time/Event headers)."""
    pd = _pd()
    errors, warnings = [], []
    if df.shape[0] < 3:
        errors.append("Sheet needs at least 3 rows: Row 1 = group names, "
                      "Row 2 = 'Time'/'Event' headers, Rows 3+ = data.")
        return errors, warnings
    if df.shape[1] < 2:
        errors.append("Sheet needs at least 2 columns (one Time + one Event column).")
        return errors, warnings

    row2 = [str(v).strip().lower() if pd.notna(v) else "" for v in df.iloc[1]]
    if not any("time" in h for h in row2):
        warnings.append("Row 2 should contain 'Time' / 'Event' column headers. "
                        "Could not find 'Time'  -  check the format.")

    data = df.iloc[2:]
    non_num_cols = []
    for ci in range(df.shape[1]):
        if _non_numeric_values(data.iloc[:, ci]):
            non_num_cols.append(ci + 1)
    if non_num_cols:
        errors.append(f"Non-numeric values found in column(s): {non_num_cols}. "
                      f"All time and event values must be numeric (events: 1=occurred, 0=censored).")

    if df.shape[1] % 2 != 0:
        warnings.append("Odd number of columns  -  each group needs exactly 2 columns "
                        "(Time and Event). Check column pairing.")

    return errors, warnings

def validate_heatmap(df: Any) -> ValidationResult:
    """Validate a heatmap sheet (row/col 0 = labels, interior = numeric values)."""
    pd = _pd()
    errors, warnings = [], []
    if df.shape[0] < 2:
        errors.append("Sheet needs at least 2 rows: Row 1 = column labels, Rows 2+ = data.")
        return errors, warnings
    if df.shape[1] < 2:
        errors.append("Sheet needs at least 2 columns: Column A = row labels, Cols B+ = data.")
        return errors, warnings
    data = df.iloc[1:, 1:]
    non_num_cells = sum(
        len([v for v in data.iloc[:, ci].dropna() if not _is_num(v)])
        for ci in range(data.shape[1])
    )
    if non_num_cells > 0:
        errors.append(f"Data region contains {non_num_cells} non-numeric value(s). "
                      "All values except row/column labels must be numeric.")
    if data.apply(pd.to_numeric, errors="coerce").isna().all().all():
        errors.append("No numeric data found in the data region.")
    if df.shape[0] < 3:
        warnings.append("Only 1 data row  -  heatmaps work best with multiple rows.")
    return errors, warnings


def validate_two_way_anova(df: Any) -> ValidationResult:
    """Validate a two-way ANOVA sheet (long format: Factor_A, Factor_B, Value columns)."""
    pd = _pd()
    errors, warnings = [], []
    if df.shape[0] < 2:
        errors.append("Sheet needs at least 2 rows: Row 1 = headers, Rows 2+ = data.")
        return errors, warnings
    if df.shape[1] < 3:
        errors.append("Need at least 3 columns: Factor_A, Factor_B, Value.")
        return errors, warnings
    num_cols = [c for c in df.columns
                if pd.to_numeric(df[c], errors="coerce").notna().any()]
    if not num_cols:
        errors.append("No numeric column found. The last column should contain numeric values.")
        return errors, warnings
    cat_cols = [c for c in df.columns if c not in num_cols]
    if len(cat_cols) < 2:
        errors.append("Need at least 2 categorical columns for Factor A and Factor B.")
        return errors, warnings
    fa, fb, dv = cat_cols[0], cat_cols[1], num_cols[-1]
    data = df[[fa, fb, dv]].dropna()
    if len(data) < 4:
        errors.append(f"Too few observations ({len(data)}). "
                      "Need at least 4 (ideally 2+ per cell).")
        return errors, warnings
    a_levels = sorted(data[fa].unique())
    b_levels = sorted(data[fb].unique())
    if len(a_levels) < 2:
        errors.append(f"Factor A ('{fa}') has only 1 level  -  need at least 2.")
    if len(b_levels) < 2:
        errors.append(f"Factor B ('{fb}') has only 1 level  -  need at least 2.")
    thin_cells = []
    for a in a_levels:
        for b in b_levels:
            n = len(data[(data[fa] == a) & (data[fb] == b)])
            if n == 0:
                errors.append(f"Missing cell: {fa}={a}, {fb}={b}. "
                              "All factor combinations must have data.")
            elif n == 1:
                thin_cells.append(f"{fa}={a}/{fb}={b}")
    if thin_cells:
        warnings.append(f"Cells with only 1 observation: {', '.join(thin_cells)}. "
                        "At least 2 replicates per cell are recommended.")
    return errors, warnings


def validate_contingency(df: Any) -> ValidationResult:
    """Validate a contingency table (row 0 = outcome labels, col 0 = group names)."""
    pd = _pd()
    errors, warnings = [], []
    if df.shape[0] < 3:
        errors.append("Need at least 2 data rows + 1 header row.\n"
                      "Row 1: column labels  |  Col A rows 2+: row labels  |  "
                      "Remaining cells: counts.")
        return errors, warnings
    if df.shape[1] < 3:
        errors.append("Need at least 2 outcome columns (plus row-label column A).")
        return errors, warnings
    data = df.iloc[1:, 1:]
    non_num = sum(1 for ci in range(data.shape[1])
                  for v in data.iloc[:, ci].dropna() if not _is_num(v))
    if non_num > 0:
        errors.append(f"Data cells must be numeric counts ({non_num} non-numeric found).")
    if data.apply(pd.to_numeric, errors="coerce").lt(0).any().any():
        warnings.append("Negative counts found  -  counts should be non-negative integers.")
    return errors, warnings


def validate_chi_square_gof(df: Any) -> ValidationResult:
    """Validate Chi-Square GoF layout.

    Row 1 : category names
    Row 2 : observed counts  (required, all numeric, all ≥ 0)
    Row 3 : expected proportions or counts (optional)
    """
    pd = _pd()
    errors, warnings = [], []
    if df.shape[0] < 2:
        errors.append("Need at least Row 1 (category names) and Row 2 (observed counts).")
        return errors, warnings
    if df.shape[1] < 2:
        errors.append("Need at least 2 categories (columns).")
        return errors, warnings

    headers = df.iloc[0]
    empty_hdrs = [i for i, h in enumerate(headers)
                  if pd.isna(h) or str(h).strip() == ""]
    if empty_hdrs:
        warnings.append(f"Row 1 has {len(empty_hdrs)} empty category name(s).")

    obs_row = pd.to_numeric(df.iloc[1], errors="coerce")
    if obs_row.isna().any():
        errors.append("Row 2 (observed counts) must contain only numeric values.")
    elif (obs_row < 0).any():
        errors.append("Observed counts (Row 2) must be non-negative.")
    elif (obs_row < 5).any():
        warnings.append("Some expected counts < 5  -  chi-square approximation may be unreliable.")

    if df.shape[0] >= 3:
        exp_row = pd.to_numeric(df.iloc[2], errors="coerce")
        if exp_row.isna().any():
            errors.append("Row 3 (expected) must be numeric if provided.")
        elif (exp_row <= 0).any():
            errors.append("Expected values (Row 3) must be positive.")

    return errors, warnings



def validate_bland_altman(df: Any) -> ValidationResult:
    """Validate Bland-Altman layout: Row 1 = two method names, Rows 2+ = paired values."""
    pd = _pd()
    errors, warnings = [], []
    if df.shape[0] < 3:
        errors.append("Need Row 1 (method names) + at least 2 data rows.")
        return errors, warnings
    if df.shape[1] < 2:
        errors.append("Need exactly 2 columns: Method A and Method B.")
        return errors, warnings
    if df.shape[1] > 2:
        warnings.append("Only the first 2 columns are used (Method A, Method B).")
    for ci in range(min(2, df.shape[1])):
        col_vals = pd.to_numeric(df.iloc[1:, ci], errors="coerce").dropna()
        if len(col_vals) == 0:
            errors.append(f"Column {ci+1} has no numeric data.")
    n_a = pd.to_numeric(df.iloc[1:, 0], errors="coerce").dropna().shape[0]
    n_b = pd.to_numeric(df.iloc[1:, 1], errors="coerce").dropna().shape[0]
    if abs(n_a - n_b) > 0:
        warnings.append(f"Column lengths differ ({n_a} vs {n_b}); shorter column will be truncated.")
    if min(n_a, n_b) < 3:
        errors.append("Need at least 3 paired observations for a meaningful plot.")
    return errors, warnings


def validate_forest_plot(df: Any) -> ValidationResult:
    """Validate Forest plot layout: Row 1 = headers, Rows 2+ = studies."""
    pd = _pd()
    errors, warnings = [], []
    if df.shape[0] < 3:
        errors.append("Need a header row + at least 2 study rows.")
        return errors, warnings
    if df.shape[1] < 4:
        errors.append("Need at least 4 columns: Study, Effect, CI_lo, CI_hi.")
        return errors, warnings
    for ci, name in ((1, "Effect"), (2, "CI_lo"), (3, "CI_hi")):
        col = pd.to_numeric(df.iloc[1:, ci], errors="coerce")
        if col.isna().all():
            errors.append(f"Column '{name}' (column {ci+1}) must be numeric.")
    if not errors:
        effects = pd.to_numeric(df.iloc[1:, 1], errors="coerce")
        ci_lo   = pd.to_numeric(df.iloc[1:, 2], errors="coerce")
        ci_hi   = pd.to_numeric(df.iloc[1:, 3], errors="coerce")
        if (ci_lo > effects).any() or (ci_hi < effects).any():
            warnings.append("Some CI bounds are inverted (CI_lo > Effect or CI_hi < Effect).")
    return errors, warnings


def validate_pyramid(df: Any) -> ValidationResult:
    """Validate Population Pyramid layout: Row 1 = headers, Rows 2+ = values.

    Expected 3 columns: Category, Left series, Right series.
    """
    pd = _pd()
    errors, warnings = [], []
    if df.shape[1] < 3:
        errors.append(
            "Need exactly 3 columns: Category, Left series, Right series.")
        return errors, warnings
    if df.shape[0] < 2:
        errors.append("Need a header row + at least 1 data row.")
        return errors, warnings
    for ci, name in ((1, "Left series"), (2, "Right series")):
        col = pd.to_numeric(df.iloc[1:, ci], errors="coerce")
        if col.isna().all():
            errors.append(
                f"{name} (column {ci + 1}) contains no numeric data.")
    if not errors:
        left  = pd.to_numeric(df.iloc[1:, 1], errors="coerce").dropna()
        right = pd.to_numeric(df.iloc[1:, 2], errors="coerce").dropna()
        if len(left) == 0 or len(right) == 0:
            errors.append("Left and right series must have at least one value each.")
        elif len(left) != len(right):
            warnings.append(
                f"Left series has {len(left)} rows, right has {len(right)}; "
                "unequal lengths will be truncated to the shorter.")
    return errors, warnings


# ── Stats tab: Repeated Measures ─────────────────────────────────────────


