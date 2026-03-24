"""Spreadsheet validation mixin."""

import tkinter as tk
from tkinter import ttk
import pandas as pd


class ValidationMixin:
    """Extracted from plotter_barplot_app.py."""

    def _set_validate_text(self, text, color="gray"):
        """Update the validation label on all tabs with a status dot prefix."""
        _color_map = {
            "green":  "#2a8a2a",
            "orange": "#cc6600",
            "red":    "#cc0000",
            "gray":   "#aaaaaa",
        }
        hex_color = _color_map.get(color, color)
        dot       = "● " if text else ""
        for lbl in self._validate_lbls:
            lbl.config(text=f"{dot}{text}", foreground=hex_color)

    # ── Validation ────────────────────────────────────────────────────────────

    def _validate_spreadsheet(self):
        path = self._vars["excel_path"].get().strip()
        if not path:
            self._set_validate_text("", "gray"); return
        if not os.path.exists(path):
            # File moved or deleted  -  clear the stale path silently rather than
            # flashing a red error (common on startup if the file was renamed)
            self._vars["excel_path"].set("")
            self._set_validate_text("", "gray")
            return

        try:
            pd = _pd()
            sheet     = self._vars["sheet"].get().strip()
            sheet_arg = int(sheet) if sheet.lstrip("-").isdigit() else (sheet or 0)
            df        = pd.read_excel(path, sheet_name=sheet_arg, header=None)
        except Exception as e:
            self._set_validate_text(f"Could not read file: {e}", "red")
            messagebox.showerror("Validation Failed", f"Could not read the Excel file:\n\n{e}")
            self._validated = False
            self._run_btn.config(state="disabled", text="✗  Generate Plot")
            return

        mode = self._plot_type.get()
        spec = next((s for s in _REGISTRY_SPECS if s.key == mode), _REGISTRY_SPECS[0])

        # Prefer standalone validators from plotter_validators (pure functions).
        # Fall back to the App instance-method versions for any that weren't extracted.
        _STANDALONE_VALIDATORS = {
            "_validate_bar":           validate_bar           if _VALIDATORS_AVAILABLE else None,
            "_validate_line":          validate_line          if _VALIDATORS_AVAILABLE else None,
            "_validate_grouped_bar":   validate_grouped_bar   if _VALIDATORS_AVAILABLE else None,
            "_validate_kaplan_meier":  validate_kaplan_meier  if _VALIDATORS_AVAILABLE else None,
            "_validate_heatmap":       validate_heatmap       if _VALIDATORS_AVAILABLE else None,
            "_validate_two_way_anova": validate_two_way_anova if _VALIDATORS_AVAILABLE else None,
            "_validate_contingency":   validate_contingency   if _VALIDATORS_AVAILABLE else None,
            "_validate_chi_square_gof":validate_chi_square_gof if _VALIDATORS_AVAILABLE else None,
            "_validate_bland_altman":  validate_bland_altman  if _VALIDATORS_AVAILABLE else None,
            "_validate_forest_plot":   validate_forest_plot   if _VALIDATORS_AVAILABLE else None,
            "_validate_pyramid":       validate_pyramid       if _VALIDATORS_AVAILABLE else None,
        }
        standalone = _STANDALONE_VALIDATORS.get(spec.validate)
        if standalone is not None:
            errors, warnings = standalone(df)
        else:
            errors, warnings = getattr(self, spec.validate)(df)
        tw = spec.label  # full label e.g. "Bar Chart"

        if errors:
            msg = "\n\n".join(errors)
            self._set_validate_text(f"{len(errors)} error(s)", "red")
            messagebox.showerror(f"Validation Failed - {tw} Graph",
                                 "The spreadsheet has the following issues:\n\n" + msg)
            self._validated = False
            self._run_btn.config(state="disabled", text="✗  Generate Plot")
            # Lock all controls except file upload, sheet selector, and chart switcher
            if not self._validation_lock:
                self._validation_lock = True
                self._lock_form()
                # Ensure always-on items stay on after lock
                for cb in getattr(self, "_sheet_cbs", []):
                    try: cb.config(state="readonly")
                    except Exception: pass
        elif warnings:
            msg = "\n\n".join(warnings)
            self._set_validate_text(f"{len(warnings)} warning(s) - OK to run", "orange")
            messagebox.showwarning(f"Validation Warnings - {tw} Graph",
                                   "Spreadsheet looks OK but has some warnings:\n\n" + msg)
            self._validated = True
            if self._validation_lock:
                self._unlock_form()
            if self._pf_ready:
                self._run_btn.config(state="normal", text="Generate Plot")
            else:
                self._run_btn.config(state="disabled", text="Generate Plot")
        else:
            pd = _pd()
            n_cols, n_rows = df.shape[1], df.shape[0] - 1
            if mode == "line":
                hdrs  = [str(h) if pd.notna(h) else "" for h in df.iloc[0, 1:]]
                uniq  = list(dict.fromkeys(h for h in hdrs if h))
                mstr  = f"line ({len(uniq)} series, {n_rows} X points)"
            elif mode == "grouped_bar":
                cats  = list(dict.fromkeys(str(h) for h in df.iloc[0] if pd.notna(h) and str(h).strip()))
                subs  = list(dict.fromkeys(str(h) for h in df.iloc[1] if pd.notna(h) and str(h).strip()))
                mstr  = f"grouped bar ({len(cats)} categories, {len(subs)} subgroups)"
            elif mode == "box":
                mstr = f"box ({n_cols} groups, {n_rows} row(s))"
            elif mode == "scatter":
                hdrs  = [str(h) if pd.notna(h) else "" for h in df.iloc[0, 1:]]
                uniq  = list(dict.fromkeys(h for h in hdrs if h))
                mstr  = f"scatter ({len(uniq)} series, {n_rows} X points)"
            elif mode == "kaplan_meier":
                n_groups = df.shape[1] // 2
                mstr  = f"survival ({n_groups} group(s), {n_rows-1} observations)"
            elif mode == "heatmap":
                mstr = f"heatmap ({df.shape[1]-1} columns × {df.shape[0]-1} rows)"
            elif mode == "two_way_anova":
                mstr = f"two-way ({df.shape[0]-1} observations, {df.shape[1]} columns)"
            elif mode == "violin":
                mstr = f"violin ({n_cols} groups, {n_rows} row(s))"
            elif mode == "histogram":
                mstr = f"histogram ({n_cols} series, {n_rows} value(s))"
            elif mode == "before_after":
                mstr = f"before/after ({n_cols} conditions, {n_rows} subject(s))"
            elif mode == "subcolumn_scatter":
                mstr = f"subcolumn ({n_cols} groups, {n_rows} row(s))"
            elif mode == "curve_fit":
                hdrs  = [str(h) if pd.notna(h) else "" for h in df.iloc[0, 1:]]
                uniq  = list(dict.fromkeys(h for h in hdrs if h))
                mstr  = f"curve fit ({len(uniq)} series, {n_rows} X points)"
            elif mode == "column_stats":
                mstr = f"column stats ({n_cols} groups, {n_rows} row(s))"
            elif mode == "contingency":
                mstr = f"contingency ({df.shape[0]-1} rows × {df.shape[1]-1} outcomes)"
            elif mode == "repeated_measures":
                mstr = f"repeated measures ({n_cols} conditions, {n_rows} subject(s))"
            else:
                mstr = f"bar ({n_cols} groups)"
            self._set_validate_text(f"Valid {mstr}", "green")
            self._validated = True
            # Unlock any validation-triggered lock now that the sheet is valid
            if self._validation_lock:
                self._unlock_form()
            if self._pf_ready:
                self._run_btn.config(state="normal", text="Generate Plot")
            else:
                self._run_btn.config(state="disabled", text="Generate Plot")
            # Populate control group dropdown immediately from the sheet  - 
            # Prism lets you set the control before running the plot.
            # Extract group names according to each chart type's layout.
            if hasattr(self, "_control_cbs"):
                try:
                    pd = _pd()
                    grp_names = []

                    if mode in {"bar", "box", "violin", "subcolumn_scatter",
                                "before_after", "repeated_measures",
                                "histogram", "column_stats", "dot_plot"}:
                        # Row 1 = flat group headers
                        grp_names = [str(h) for h in df.iloc[0]
                                     if pd.notna(h) and str(h).strip()]

                    elif mode == "grouped_bar":
                        # Row 1 = category names (may repeat), Row 2 = subgroup names
                        # Control applies to subgroups (row 2 unique values)
                        grp_names = list(dict.fromkeys(
                            str(h) for h in df.iloc[1]
                            if pd.notna(h) and str(h).strip()
                        ))

                    elif mode in {"line", "scatter", "curve_fit"}:
                        # Row 1: col0 = x-label, cols 1+ = series names
                        grp_names = list(dict.fromkeys(
                            str(h) for h in df.iloc[0, 1:]
                            if pd.notna(h) and str(h).strip()
                        ))

                    elif mode == "two_way_anova":
                        # Long-format; Factor_A column values are the "groups"
                        try:
                            df_long = df.copy()
                            df_long.columns = df_long.iloc[0]
                            df_long = df_long.iloc[1:].reset_index(drop=True)
                            fa_col = next(
                                (c for c in df_long.columns
                                 if str(c).strip().lower() in ("factor_a", "factor a", "groupa", "group_a")),
                                df_long.columns[0] if len(df_long.columns) > 0 else None
                            )
                            if fa_col is not None:
                                grp_names = list(dict.fromkeys(
                                    str(v) for v in df_long[fa_col].dropna()
                                ))
                        except Exception:
                            pass

                    if grp_names:
                        # Store ONLY real group names — no "(none)" sentinel.
                        # _tog_control() decides enabled/disabled state and
                        # whether the dropdown shows these names or is locked.
                        for cb in self._control_cbs:
                            cb.config(values=grp_names)
                        # Preserve current selection if still valid; else clear
                        cur = self._vars["control"].get()
                        if cur not in grp_names:
                            self._vars["control"].set("")
                        # Let _tog_control apply all visibility/consistency rules
                        self._tog_control()
                except Exception:
                    pass

        # Sync the Help Analyze button state with current validation result
        self._sync_analyze_btn()

    # ── Shared validator helpers ──────────────────────────────────────────────

    def _validate_flat_header(self, df,
                              min_groups: int = 2,
                              min_rows: int = 3,
                              chart_name: str = "bar graph") -> tuple:
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

        if df.shape[1] < min_groups:
            warnings.append(
                f"Only {df.shape[1]} group/column(s) found. "
                f"{chart_name.capitalize()} work best with {min_groups}+ groups.")
        if df.shape[0] < min_rows + 1:  # +1 for header row
            warnings.append(
                f"Only {df.shape[0] - 1} data row(s) per group. "
                "Statistical tests require at least 3 replicates per group.")

        return errors, warnings

    def _validate_bar(self, df):
        return self._validate_flat_header(df, min_groups=2, min_rows=3,
                                          chart_name="bar graph")

    def _validate_line(self, df):
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

    def _validate_grouped_bar(self, df):
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

    def _validate_kaplan_meier(self, df):
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

    def _validate_heatmap(self, df):
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

    def _validate_two_way_anova(self, df):
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

    def _validate_contingency(self, df):
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

    def _validate_chi_square_gof(self, df):
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


    def _validate_bland_altman(self, df):
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

    def _validate_forest_plot(self, df):
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

    # ── Stats tab: Repeated Measures ─────────────────────────────────────────

