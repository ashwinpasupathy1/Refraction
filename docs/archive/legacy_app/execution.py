"""Plot execution, analysis, and zoom mixin."""

import threading
import tkinter as tk
from tkinter import ttk, messagebox


class ExecutionMixin:
    """Extracted from plotter_barplot_app.py."""

    def _help_analyze(self):
        """Dispatcher: validate then route to the correct analysis path."""
        if not self._validated:
            messagebox.showwarning(
                "Help Analyze",
                "Please validate the spreadsheet first (click Validate Spreadsheet).")
            return
        mode = self._plot_type.get()
        if mode in self._HELP_ANALYZE_FLAT_MODES:
            self._help_analyze_flat()
        elif mode == "grouped_bar":
            self._help_analyze_grouped_bar()
        elif mode == "scatter":
            self._help_analyze_scatter()
        elif mode == "line":
            self._help_analyze_line()
        elif mode == "two_way_anova":
            self._help_analyze_two_way_anova()
        elif mode in self._HELP_ANALYZE_INFO_MODES:
            self._help_analyze_info_only(mode)
        else:
            label_map = {s.key: s.label for s in _REGISTRY_SPECS}
            messagebox.showinfo(
                "Help Analyze",
                f"Help Analyze is not yet implemented for "
                f"{label_map.get(mode, mode)} charts.")

    # ── Shared data / stats helpers ───────────────────────────────────────────

    def _ha_load_df(self, header=None):
        """Load the active Excel sheet.  Returns DataFrame or None on error."""
        pd = _pd()
        path      = self._vars["excel_path"].get().strip()
        sheet     = self._vars["sheet"].get().strip()
        sheet_arg = int(sheet) if sheet.lstrip("-").isdigit() else (sheet or 0)
        try:
            return pd.read_excel(path, sheet_name=sheet_arg, header=header)
        except Exception as e:
            messagebox.showerror("Help Analyze", f"Could not read file:\n{e}")
            return None

    def _ha_run_normality(self, groups: dict) -> dict:
        """Shapiro-Wilk per group.  Returns {name: {n, stat, p, normal, note}}."""
        from scipy import stats as _st
        out = {}
        for name, vals in groups.items():
            n = len(vals)
            if n < 3:
                out[name] = dict(n=n, stat=None, p=None, normal=True,
                                 note="too few values  -  assumed normal")
            elif n > 5000:
                out[name] = dict(n=n, stat=None, p=None, normal=True,
                                 note="n>5000  -  Shapiro-Wilk skipped")
            else:
                w, p = _st.shapiro(vals)
                out[name] = dict(n=n, stat=w, p=p, normal=(p > 0.05),
                                 note=f"W={w:.4f}, p={p:.4f}")
        return out

    def _ha_flat_decision_tree(self, groups, normality, mode):
        """Shared parametric/nonparametric/paired decision tree.
        Returns (rec_title, reasoning, test, posthoc, mc).

        Statistical decision tree:
        - 2 groups: Welch's t-test (handles unequal variances)
        - 3+ groups, normal + equal var: One-way ANOVA + Tukey HSD (all-pairwise)
        - 3+ groups, normal + unequal var: Welch's ANOVA (Brown-Forsythe)  -  note only,
          app falls back to Parametric (one-way ANOVA) since Welch's ANOVA is not yet
          in the function library; flag is shown as a warning.
        - Non-normal: Mann-Whitney / Kruskal-Wallis + Dunn's (Holm corrected)
        - Paired: Paired t-test / Repeated pairwise / Friedman
        """
        from scipy import stats as _st
        k         = len(groups)
        ns        = {n: len(v) for n, v in groups.items()}
        all_norm  = all(d["normal"] for d in normality.values())
        equal_n   = len(set(ns.values())) == 1
        is_paired = mode in ("before_after", "repeated_measures")

        reasoning = []
        test, posthoc, mc, rec_title = "Parametric", "Tukey HSD", "Holm-Bonferroni", ""

        reasoning.append(("📊", f"{k} group(s): {', '.join(groups.keys())}"))

        if not all_norm:
            failing = [n for n, d in normality.items() if not d["normal"]]
            reasoning.append(("✗", f"Normality (Shapiro-Wilk): FAILED for "
                              f"{', '.join(failing)}."))
        else:
            reasoning.append(("✓", "Normality (Shapiro-Wilk): all groups pass (p > 0.05)."))

        # Levene equal-variance test (run for all group counts, not just k==2)
        levene_p = None
        if all_norm and len(groups) >= 2:
            try:
                _, levene_p = _st.levene(*list(groups.values()))
            except Exception:
                pass

        if is_paired:
            if equal_n:
                reasoning.append(("✓", "Equal n  -  paired comparison is appropriate."))
            else:
                reasoning.append(("⚠", "Unequal n  -  paired test requires equal n; "
                                   "defaulting to unpaired."))

        if is_paired and equal_n:
            if k == 2:
                test, rec_title = "Paired", "Paired t-test"
                reasoning.append((" -> ", "RECOMMENDATION: Paired t-test"))
                reasoning.append(("ℹ", "Each subject measured twice; differences are "
                                   "normally distributed by CLT. Paired t-test is the "
                                   "Prism default for 2-condition within-subjects designs."))
            elif all_norm:
                test, rec_title = "Paired", "Repeated-measures paired t-tests (Holm corrected)"
                reasoning.append((" -> ", "RECOMMENDATION: Repeated pairwise paired t-tests "
                                   "+ Holm-Bonferroni correction"))
                reasoning.append(("ℹ", "Multiple conditions, same subjects. Prism 11 uses "
                                   "repeated-measures one-way ANOVA with optional "
                                   "Geisser-Greenhouse correction for non-sphericity. "
                                   "Refraction uses pairwise paired t-tests with "
                                   "Holm correction as a robust equivalent."))
            else:
                test, rec_title = "Non-parametric", "Friedman test + Dunn's post-hoc (Holm corrected)"
                reasoning.append((" -> ", "RECOMMENDATION: Non-parametric  -  Friedman + Dunn's"))
                reasoning.append(("ℹ", "Non-normal repeated data: Friedman test is the "
                                   "non-parametric analogue of RM-ANOVA. Dunn's post-hoc "
                                   "performs rank-based pairwise comparisons (Prism 11, "
                                   "Non-parametric comparisons section)."))
        elif k == 2:
            if all_norm:
                test, rec_title = "Parametric", "Welch's unpaired t-test"
                reasoning.append((" -> ", "RECOMMENDATION: Welch's unpaired t-test (parametric)"))
                reasoning.append(("ℹ", "Two groups, normally distributed. Welch's t-test "
                                   "is the recommended default  -  it "
                                   "does not assume equal variances, so it is correct "
                                   "regardless of the Levene result."))
                if levene_p is not None and levene_p < 0.05:
                    reasoning.append(("⚠", f"Levene's test: unequal variances "
                                      f"(p={levene_p:.4f}). Welch's handles this correctly "
                                      " -  no action needed."))
                else:
                    if levene_p is not None:
                        reasoning.append(("✓", f"Levene's test: equal variances "
                                          f"(p={levene_p:.4f}). Welch's t-test is still preferred."))
            else:
                test, rec_title = "Non-parametric", "Mann-Whitney U test"
                reasoning.append((" -> ", "RECOMMENDATION: Mann-Whitney U (non-parametric)"))
                reasoning.append(("ℹ", "Two groups, non-normal. Mann-Whitney U compares "
                                   "rank sums. Non-parametric alternative to Welch's t-test "
                                   "(Prism 11, Non-parametric comparisons guide)."))
        else:  # k >= 3
            if all_norm:
                test, rec_title = "Parametric", "One-way ANOVA + Tukey HSD post-hoc"
                reasoning.append((" -> ", "RECOMMENDATION: One-way ANOVA + Tukey HSD (all-pairwise)"))
                reasoning.append(("ℹ", f"{k} groups, normally distributed. One-way ANOVA "
                                   "tests for any group difference; Tukey HSD controls "
                                   "family-wise error across all pairwise comparisons  -  "
                                   "the Prism 11 default for 3+ parametric groups."))
                if levene_p is not None and levene_p < 0.05:
                    reasoning.append(("⚠",
                                      f"Levene's test: unequal variances (p={levene_p:.4f}). "
                                      "Prism 8+ offers Welch's ANOVA and Brown-Forsythe ANOVA "
                                      "as alternatives when equal variances cannot be assumed. "
                                      "Consider this if group SDs differ substantially."))
                elif levene_p is not None:
                    reasoning.append(("✓", f"Levene's test: equal variances "
                                      f"(p={levene_p:.4f}). Standard ANOVA assumption holds."))
            else:
                test, rec_title = "Non-parametric", "Kruskal-Wallis + Dunn's post-hoc (Holm corrected)"
                reasoning.append((" -> ", "RECOMMENDATION: Kruskal-Wallis + Dunn's post-hoc"))
                reasoning.append(("ℹ", f"{k} groups, non-normal. Kruskal-Wallis is the "
                                   "non-parametric one-way ANOVA equivalent (rank-based). "
                                   "Dunn's test with Holm-Bonferroni correction performs "
                                   "pairwise comparisons on ranked data "
                                   "(Prism 11, Non-parametric comparisons guide)."))

        return rec_title, reasoning, test, posthoc, mc

    def _ha_apply_standard_stats(self, test, posthoc, mc):
        """Write standard stats dropdowns and refresh the dependent widgets.

        Always resets comparison_mode to 0 (all-pairwise)  -  Help Analyze
        always recommends an omnibus comparison. User can override afterwards.
        """
        self._vars["stats_test"].set(test)
        self._vars["posthoc"].set(posthoc)
        self._vars["mc_correction"].set(mc)
        self._vars["show_stats"].set(True)
        self._vars["show_normality_warning"].set(True)
        # Reset comparison mode to all-pairwise (Prism default for omnibus tests)
        try:
            self._vars["comparison_mode"].set(0)
        except Exception:
            pass
        if hasattr(self, "_test_info_lbl") and hasattr(self, "_TEST_INFO"):
            self._test_info_lbl.config(text=self._TEST_INFO.get(test, ""))
        for fn in ("_tog_posthoc", "_tog_perm", "_tog_control"):
            try:
                getattr(self, fn)()
            except Exception:
                pass

    # ── Flat-layout analysis ──────────────────────────────────────────────────

    def _help_analyze_flat(self):
        """Full decision-tree analysis for flat row-1-header charts."""
        pd  = _pd()
        mode = self._plot_type.get()
        df   = self._ha_load_df()
        if df is None:
            return

        groups = {}
        for ci in range(df.shape[1]):
            hdr = df.iloc[0, ci]
            if pd.isna(hdr) or not str(hdr).strip():
                continue
            name = str(hdr).strip()
            vals = pd.to_numeric(df.iloc[1:, ci], errors="coerce").dropna().values
            if len(vals) >= 1:
                groups[name] = vals

        if len(groups) < 2:
            messagebox.showwarning("Help Analyze",
                                   "Need at least 2 groups with numeric data to recommend a test.")
            return

        normality = self._ha_run_normality(groups)
        rec_title, reasoning, test, posthoc, mc = self._ha_flat_decision_tree(
            groups, normality, mode)
        self._ha_apply_standard_stats(test, posthoc, mc)
        self._show_analyze_dialog(rec_title, groups, normality, reasoning, test, posthoc, mc)

    # ── Grouped Bar ───────────────────────────────────────────────────────────

    def _help_analyze_grouped_bar(self):
        """Two-factor decision tree for grouped bar charts.
        Pools values per subgroup across all categories for the normality check,
        then applies the standard parametric/non-parametric branch."""
        import numpy as np
        pd = _pd()
        df = self._ha_load_df()
        if df is None:
            return
        if df.shape[0] < 3:
            messagebox.showwarning("Help Analyze",
                                   "Need at least 3 rows: Row 1=categories, "
                                   "Row 2=subgroups, Rows 3+=data.")
            return

        row1 = [str(h) if pd.notna(h) else "" for h in df.iloc[0]]
        row2 = [str(h) if pd.notna(h) else "" for h in df.iloc[1]]
        cats = list(dict.fromkeys(h for h in row1 if h.strip()))
        subs = list(dict.fromkeys(h for h in row2 if h.strip()))

        # Pool all values per subgroup across categories for normality
        groups = {}
        for ci in range(df.shape[1]):
            sub = row2[ci] if ci < len(row2) else ""
            if not sub.strip():
                continue
            vals = pd.to_numeric(df.iloc[2:, ci], errors="coerce").dropna().values
            if len(vals) < 1:
                continue
            groups[sub] = np.concatenate([groups[sub], vals]) if sub in groups else vals

        if len(groups) < 2:
            messagebox.showwarning("Help Analyze", "Need at least 2 subgroups with data.")
            return

        normality  = self._ha_run_normality(groups)
        all_normal = all(d["normal"] for d in normality.values())
        k          = len(subs)

        reasoning = []
        reasoning.append(("📊",
            f"{len(cats)} categor{'y' if len(cats) == 1 else 'ies'} × "
            f"{k} subgroup{'s' if k != 1 else ''}  -  "
            f"cats: {', '.join(cats[:4])}{'…' if len(cats) > 4 else ''}; "
            f"subs: {', '.join(subs)}"))
        reasoning.append(("ℹ",
            "Pairwise stats compare subgroups within each category cluster. "
            "'Per-Category ANOVA' additionally tests within each cluster independently."))

        if all_normal:
            reasoning.append(("✓", "Normality (Shapiro-Wilk, pooled per subgroup): all pass."))
            test, posthoc, mc = "Parametric", "Tukey HSD", "Holm-Bonferroni"
            verb = "Welch's t-test" if k == 2 else f"One-way ANOVA + Tukey HSD"
            rec_title = f"{verb} across {k} subgroup{'s' if k != 1 else ''}"
            reasoning.append((" -> ", f"RECOMMENDATION: Parametric  -  {verb} across subgroups"))
            reasoning.append(("ℹ",
                "Also enabling 'Per-Category ANOVA' to test within each "
                "category cluster independently."))
        else:
            failing = [n for n, d in normality.items() if not d["normal"]]
            reasoning.append(("✗", f"Normality FAILED for: {', '.join(failing)}."))
            test, posthoc, mc = "Non-parametric", "Tukey HSD", "Holm-Bonferroni"
            rec_title = "Kruskal-Wallis + Dunn's post-hoc (Holm corrected) across subgroups"
            reasoning.append((" -> ",
                "RECOMMENDATION: Non-parametric  -  Kruskal-Wallis + Dunn's across subgroups"))
            reasoning.append(("ℹ",
                "'Per-Category ANOVA' is disabled for non-parametric tests."))

        self._ha_apply_standard_stats(test, posthoc, mc)
        try:
            self._vars["show_anova_per_group"].set(all_normal)
        except Exception:
            pass
        self._show_analyze_dialog(rec_title, groups, normality, reasoning, test, posthoc, mc)

    # ── Scatter ───────────────────────────────────────────────────────────────

    def _help_analyze_scatter(self):
        """Pearson vs Spearman decision based on regression-residual normality."""
        import numpy as np
        pd = _pd()
        df = self._ha_load_df()
        if df is None:
            return

        # Row 0 col 1+ = series names; col 0 = X; rows 1+ = data
        series_names = [
            str(df.iloc[0, ci]) if pd.notna(df.iloc[0, ci]) else f"Series {ci}"
            for ci in range(1, df.shape[1])
        ]
        x_raw = pd.to_numeric(df.iloc[1:, 0], errors="coerce")
        if x_raw.dropna().empty:
            messagebox.showwarning("Help Analyze",
                                   "Column 1 must contain numeric X values.")
            return

        series_data = {}
        for i, name in enumerate(series_names):
            y_raw = pd.to_numeric(df.iloc[1:, i + 1], errors="coerce")
            mask  = x_raw.notna() & y_raw.notna()
            if mask.sum() >= 3:
                series_data[name] = (x_raw[mask].values, y_raw[mask].values)

        if not series_data:
            messagebox.showwarning("Help Analyze",
                                   "No series with 3+ paired X/Y values found.")
            return

        from scipy import stats as _st
        # Normality on residuals  -  the correct Pearson assumption
        resid_groups = {}
        for name, (x, y) in series_data.items():
            slope, intercept, *_ = _st.linregress(x, y)
            resid_groups[f"{name} (residuals)"] = y - (slope * x + intercept)

        normality  = self._ha_run_normality(resid_groups)
        all_normal = all(d["normal"] for d in normality.values())

        reasoning = []
        reasoning.append(("📊", f"{len(series_data)} series: {', '.join(series_data.keys())}"))
        reasoning.append(("ℹ",
            "Pearson's assumption of bivariate normality is tested via "
            "Shapiro-Wilk on the regression residuals  -  the standard diagnostic approach."))

        if all_normal:
            reasoning.append(("✓",
                "Residual normality (Shapiro-Wilk): all series pass (p > 0.05)."))
            corr_type = "Pearson"
            rec_title = "Pearson r correlation + linear regression"
            reasoning.append((" -> ",
                "RECOMMENDATION: Pearson r  -  parametric linear correlation"))
            reasoning.append(("ℹ",
                "Pearson r measures linear association. Enable 'Regression line' "
                "and '95% CI band' for a complete GraphPad-style scatter output."))
        else:
            failing = [n.replace(" (residuals)", "")
                       for n, d in normality.items() if not d["normal"]]
            reasoning.append(("✗",
                f"Residual normality FAILED for: {', '.join(failing)}."))
            corr_type = "Spearman"
            rec_title = "Spearman ρ rank correlation"
            reasoning.append((" -> ",
                "RECOMMENDATION: Spearman ρ  -  non-parametric rank correlation"))
            reasoning.append(("ℹ",
                "Spearman ρ ranks X and Y independently and correlates the ranks. "
                "Robust to outliers and non-linearity. A regression line is still "
                "shown for visual reference."))

        # Pearson vs Spearman discrepancy hint
        for name, (x, y) in series_data.items():
            rp, _ = _st.pearsonr(x, y)
            rs, _ = _st.spearmanr(x, y)
            if abs(abs(rp) - abs(rs)) > 0.10:
                reasoning.append(("⚠",
                    f"Series '{name}': Pearson r={rp:.3f} vs Spearman ρ={rs:.3f} "
                    "(>0.10 gap). This suggests non-linearity or influential outliers  -  "
                    "inspect a residuals plot."))

        # Apply settings
        try:
            self._vars["correlation_type"].set(
                "Pearson" if corr_type == "Pearson" else "Spearman")
            self._vars["show_correlation"].set(True)
            self._vars["show_regression"].set(True)
            self._vars["show_ci_band"].set(True)
        except Exception:
            pass

        self._show_analyze_dialog(
            rec_title, resid_groups, normality, reasoning,
            corr_type, " - ", " - ",
            norm_label="Normality Check  -  Regression Residuals (Shapiro-Wilk)",
            settings_override={
                "Correlation type":         (corr_type,
                    "Pearson: linear, parametric  |  Spearman: rank-based, robust"),
                "Show correlation annotation": ("✓ Enabled", ""),
                "Show regression line":        ("✓ Enabled", ""),
                "Show 95% CI band":            ("✓ Enabled", ""),
            })

    # ── Line graph ────────────────────────────────────────────────────────────

    def _help_analyze_line(self):
        """Decision tree for line graphs  -  each Y series is treated as a group."""
        import numpy as np
        pd   = _pd()
        df   = self._ha_load_df()
        if df is None:
            return

        # Row 0 col 1+ = series names, rows 1+ = Y data per series
        series_names = [
            str(df.iloc[0, ci]) if pd.notna(df.iloc[0, ci]) else f"Series {ci}"
            for ci in range(1, df.shape[1])
        ]
        groups = {}
        for i, name in enumerate(series_names):
            vals = pd.to_numeric(df.iloc[1:, i + 1], errors="coerce").dropna().values
            if len(vals) >= 1:
                groups[name] = (np.concatenate([groups[name], vals])
                                if name in groups else vals)

        if len(groups) < 2:
            messagebox.showwarning("Help Analyze",
                                   "Need at least 2 series with numeric data.")
            return

        normality = self._ha_run_normality(groups)
        rec_title, reasoning, test, posthoc, mc = self._ha_flat_decision_tree(
            groups, normality, "line")

        # Inject line-specific context after the group count line
        reasoning.insert(1, ("ℹ",
            "Line-graph series are treated as independent groups  -  "
            "each Y-column's values are compared across series "
            "(one test per series pair or omnibus across all)."))

        self._ha_apply_standard_stats(test, posthoc, mc)
        self._show_analyze_dialog(rec_title, groups, normality, reasoning, test, posthoc, mc)

    # ── Two-Way ANOVA ─────────────────────────────────────────────────────────

    def _help_analyze_two_way_anova(self):
        """Normality + Levene checks for two-way ANOVA (long-format data)."""
        from scipy import stats as _st
        # Two-way ANOVA uses header=0 (first row is column names)
        df = self._ha_load_df(header=0)
        if df is None:
            return

        num_cols = [c for c in df.columns
                    if _pd().to_numeric(df[c], errors="coerce").notna().any()]
        cat_cols = [c for c in df.columns if c not in num_cols]

        if len(cat_cols) < 2 or not num_cols:
            messagebox.showwarning("Help Analyze",
                                   "Need ≥2 categorical columns (Factor A, Factor B) "
                                   "and 1 numeric column (Value).")
            return

        fa, fb, dv = cat_cols[0], cat_cols[1], num_cols[-1]
        data     = df[[fa, fb, dv]].dropna()
        a_levels = sorted(data[fa].unique())
        b_levels = sorted(data[fb].unique())

        # One group per cell (Factor A × Factor B)
        groups = {}
        for a in a_levels:
            for b in b_levels:
                key  = f"{a} / {b}"
                vals = data[(data[fa] == a) & (data[fb] == b)][dv].values
                if len(vals) >= 1:
                    groups[key] = vals.astype(float)

        if not groups:
            messagebox.showwarning("Help Analyze", "No data cells found after filtering.")
            return

        normality  = self._ha_run_normality(groups)
        all_normal = all(d["normal"] for d in normality.values())

        levene_p = None
        try:
            eligible = [v for v in groups.values() if len(v) >= 2]
            if len(eligible) >= 2:
                _, levene_p = _st.levene(*eligible)
        except Exception:
            pass

        reasoning = []
        n_cells = len(a_levels) * len(b_levels)
        reasoning.append(("📊",
            f"Design: {len(a_levels)} levels of '{fa}' × "
            f"{len(b_levels)} levels of '{fb}' = {n_cells} cells,  DV = '{dv}'"))
        reasoning.append(("ℹ",
            f"Two-way ANOVA partitions variance into: main effect of '{fa}', "
            f"main effect of '{fb}', and their interaction ('{fa}' × '{fb}'). "
            "Type II SS  -  each main effect is tested after controlling for the other."))

        if all_normal:
            reasoning.append(("✓",
                "Normality (Shapiro-Wilk, per cell): all cells pass (p > 0.05)."))
        else:
            failing = [n for n, d in normality.items() if not d["normal"]]
            reasoning.append(("✗",
                f"Normality FAILED in {len(failing)} cell(s): "
                f"{', '.join(failing[:4])}{'…' if len(failing) > 4 else ''}."))
            reasoning.append(("⚠",
                "Two-way ANOVA is moderately robust to non-normality when cell sizes "
                "are equal (balanced design). Consider log-transforming a right-skewed DV."))

        if levene_p is not None:
            if levene_p < 0.05:
                reasoning.append(("⚠",
                    f"Levene's test: unequal variances across cells (p={levene_p:.4f}). "
                    "Two-way ANOVA assumes homoscedasticity  -  interpret with caution "
                    "if cell sizes are very unequal."))
            else:
                reasoning.append(("✓",
                    f"Levene's test: homogeneous variances across cells (p={levene_p:.4f})."))

        rec_title = f"Two-Way ANOVA: '{fa}' × '{fb}'"
        reasoning.append((" -> ",
            f"RECOMMENDATION: Two-Way ANOVA  -  main effects of '{fa}' and '{fb}' "
            "plus interaction term"))
        reasoning.append(("ℹ",
            "Enabling post-hoc pairwise comparisons (Holm corrected) and "
            "partial η² effect sizes  -  standard Prism output for two-way ANOVA."))

        # Apply settings
        try:
            self._vars["show_stats"].set(True)
            self._vars["show_posthoc"].set(True)
            self._vars["show_effect_size"].set(True)
            self._vars["show_normality_warning"].set(True)
            self._vars["show_p_values"].set(False)
        except Exception:
            pass

        self._show_analyze_dialog(
            rec_title, groups, normality, reasoning,
            "Parametric", "Holm-Bonferroni post-hoc", "Holm-Bonferroni",
            norm_label=f"Normality Check  -  Per Cell ({fa} × {fb}, Shapiro-Wilk)",
            settings_override={
                "Test":                    ("Two-Way ANOVA (Type II SS)",
                    f"Main effects: '{fa}', '{fb}' + interaction term"),
                "Post-hoc":                ("Pairwise t-tests, Holm corrected",
                    "✓ Enabled"),
                "Effect size":             ("Partial η²",
                    "✓ Enabled"),
                "Normality warning on plot": ("✓ Enabled", ""),
            })

    # ── Informational stubs ───────────────────────────────────────────────────

    _HELP_ANALYZE_INFO = {
        "kaplan_meier": {
            "title":     "Kaplan-Meier Survival Curve",
            "purpose":   "Estimates the survival function S(t)  -  the probability of surviving "
                         "beyond time t  -  from censored time-to-event data. Each step in the "
                         "curve corresponds to one or more observed events.",
            "test":      "Log-rank test (Mantel-Cox) compares survival distributions between "
                         "groups. It is non-parametric and handles right-censored observations "
                         "correctly. Output: χ² statistic and p-value.",
            "interpret": "Curves that diverge early and stay separated indicate a large, early "
                         "survival difference. Crossing curves suggest time-varying treatment "
                         "effects  -  the log-rank test has low power in this case; consider "
                         "Breslow (Gehan) or Tarone-Ware weighted alternatives.",
            "apply":     "Enable 'Show censors' to display tick marks for censored observations. "
                         "Enable 'Show at-risk table' for a publication-quality plot. "
                         "The log-rank p-value is computed automatically when 2+ groups are present.",
        },
        "heatmap": {
            "title":     "Heatmap",
            "purpose":   "Visualises a numeric matrix as a color grid. Common uses: gene "
                         "expression data, correlation matrices, and confusion tables.",
            "test":      "No statistical test is embedded in the heatmap. For expression data, "
                         "apply differential-expression analysis (DESeq2, edgeR) upstream. "
                         "For correlation matrices, each cell is a pre-computed Pearson or "
                         "Spearman r coefficient.",
            "interpret": "Color saturation encodes magnitude. Hierarchical clustering (enable "
                         "in Options) reorders rows/columns by similarity  -  look for block "
                         "structure indicating co-regulated genes or correlated variables. "
                         "Use a diverging palette for data centred at zero (fold-changes, z-scores).",
            "apply":     "Enable 'Show values in cells' for small matrices (≤10×10). "
                         "Enable row and/or column clustering to reveal structure. "
                         "Use Coolwarm or RdBu for data centred at zero; Viridis or Mako for "
                         "magnitude-only data.",
        },
        "contingency": {
            "title":     "Contingency Table",
            "purpose":   "Displays observed counts for combinations of two categorical variables, "
                         "with optional expected counts and row/column percentages.",
            "test":      "Chi-square test of independence (Pearson χ²) when all expected cells "
                         "≥ 5, otherwise Fisher's exact test. Tests whether the row and column "
                         "variables are associated. Cramér's V gives effect size (0=no association, "
                         "1=perfect association).",
            "interpret": "p < 0.05 means the variables are not independent. Inspect the "
                         "residuals (observed − expected) to see which cells drive the association. "
                         "Fisher's exact is preferred for small N or sparse tables "
                         "(any expected cell < 5).",
            "apply":     "Enable 'Show expected counts' to verify the chi-square assumption. "
                         "Enable '% of row' or '% of column' to compare proportions across groups.",
        },
        "chi_square_gof": {
            "title":     "Chi-Square Goodness of Fit",
            "purpose":   "Tests whether observed categorical counts match a specified theoretical "
                         "distribution  -  for example, equal proportions (uniform null) or Hardy-"
                         "Weinberg equilibrium.",
            "test":      "Pearson chi-square: χ² = Σ(O − E)²/E, df = k − 1. "
                         "Expected counts can be equal (uniform) or user-specified proportions "
                         "entered in row 3 of the spreadsheet.",
            "interpret": "Reject H₀ when p < 0.05 (observed deviates from expected). "
                         "Calculate each term (O−E)²/E to see which categories contribute most. "
                         "The test requires expected count ≥ 5 per cell; merge rare categories "
                         "if this is violated.",
            "apply":     "Select 'Equal expected proportions' for a uniform null hypothesis. "
                         "Enter custom expected values in row 3 to test a different distribution.",
        },
        "stacked_bar": {
            "title":     "Stacked Bar Chart",
            "purpose":   "Shows part-to-whole composition  -  each bar is divided into segments "
                         "for sub-categories, displayed as absolute values or as percentages "
                         "of the bar total.",
            "test":      "No statistical test is performed on stacked bars directly. "
                         "For count data, use a Contingency or Chi-Square GoF analysis on the "
                         "same data. For continuous sub-category data, analyze each component "
                         "separately with a Bar or Box plot.",
            "interpret": "Use 'Percent mode' to compare proportions independent of group size. "
                         "Stacked bars are best for 3–6 sub-categories; with more segments, "
                         "a grouped bar chart is easier to read.",
            "apply":     "Switch to 'Percent' mode (Options tab) for proportional comparison. "
                         "Enable 'Value labels' to annotate each segment with its value.",
        },
        "bubble": {
            "title":     "Bubble Chart",
            "purpose":   "Extends a scatter plot with a third quantitative dimension encoded "
                         "as bubble area. Each series provides X, Y, and Size columns.",
            "test":      "No statistical test is performed automatically. "
                         "For X–Y correlation: use a Scatter plot with Pearson or Spearman. "
                         "For size vs. X or Y: run a separate scatter/regression analysis on "
                         "those two variables.",
            "interpret": "Bubble area encodes magnitude  -  ensure the scale is labelled. "
                         "Overlap obscures data; reduce 'Bubble scale' if needed. "
                         "Avoid bubble charts when precise size comparisons are critical.",
            "apply":     "Adjust 'Bubble scale' in the Options tab. Enable 'Show labels' to "
                         "identify individual observations by name.",
        },
        "bland_altman": {
            "title":     "Bland-Altman Agreement Plot",
            "purpose":   "Assesses agreement between two measurement methods by plotting the "
                         "difference (Method A − Method B) against the mean of the two methods "
                         "for each subject.",
            "test":      "No formal hypothesis test is required. Key statistics: mean difference "
                         "(systematic bias) and 95% limits of agreement (mean diff ± 1.96 SD). "
                         "A one-sample t-test on the differences tests whether bias ≠ 0.",
            "interpret": "The limits of agreement define the range within which 95% of "
                         "differences fall. They should be clinically acceptable for the methods "
                         "to be interchangeable. A trend in difference vs. mean indicates "
                         "proportional bias  -  consider log-transforming before analysis.",
            "apply":     "Enable '95% CI bands' to show uncertainty around the mean difference "
                         "and limits of agreement. Small N (< 30) makes the limits imprecise; "
                         "report them with CIs in papers.",
        },
        "forest_plot": {
            "title":     "Forest Plot (Meta-Analysis)",
            "purpose":   "Displays effect estimates and confidence intervals from multiple "
                         "studies alongside a pooled summary estimate.",
            "test":      "Pooled estimate: inverse-variance weighted mean. "
                         "Heterogeneity: Cochran's Q test + I² statistic. "
                         "I² > 50% suggests substantial between-study heterogeneity  -  a "
                         "random-effects model is then preferred over fixed-effects.",
            "interpret": "Studies whose CI excludes the null line are individually significant. "
                         "The summary diamond's width is the pooled 95% CI. "
                         "High I² means the studies may not be estimating the same effect  -  "
                         "explore subgroup analyzes or moderators.",
            "apply":     "Set the null reference line to 0 (mean difference) or 1 (odds ratio / "
                         "hazard ratio) in the Stats tab. Enable 'Show weights' to display each "
                         "study's inverse-variance contribution to the pooled estimate.",
        },
        "curve_fit": {
            "title":     "Nonlinear Curve Fit",
            "purpose":   "Fits a parametric model (sigmoidal, exponential, Michaelis-Menten, "
                         "Gaussian, etc.) to XY data using nonlinear least-squares regression.",
            "test":      "R² and RMSE measure goodness of fit. Fitted parameters are reported "
                         "with 95% confidence intervals derived from the covariance matrix. "
                         "For sigmoidal models the inflection point is EC50/IC50.",
            "interpret": "A good fit has R² > 0.95 and small, random residuals. "
                         "A systematic pattern in the residuals means the model is misspecified  -  "
                         "try a different equation. Hill coefficient n > 1 indicates positive "
                         "cooperativity; n < 1 negative cooperativity.",
            "apply":     "Select the model that matches your biological mechanism. "
                         "Enable 'Show residuals' subplot to diagnose fit quality. "
                         "Enable 'Show parameter table' for EC50/IC50 with confidence intervals "
                         " -  required for publication.",
        },
    }

    def _help_analyze_info_only(self, mode):
        """Show an informational Help Analyze panel for charts without a live decision tree."""
        info = self._HELP_ANALYZE_INFO.get(mode)
        if info is None:
            label_map = {s.key: s.label for s in _REGISTRY_SPECS}
            messagebox.showinfo("Help Analyze",
                                f"Help Analyze is not yet available for "
                                f"{label_map.get(mode, mode)} charts.")
            return
        self._show_analyze_info_dialog(info)

    def _show_analyze_info_dialog(self, info: dict):
        """Informational modal for charts without a statistical decision tree."""
        dlg = tk.Toplevel(self)
        dlg.title("Help Analyze")
        dlg.resizable(True, True)
        dlg.geometry("620x480")
        dlg.configure(bg="#ffffff")
        dlg.grab_set()
        self._track_popup(dlg)  # suspend background scroll

        # Header
        hdr = tk.Frame(dlg, bg="#1a4f7a", height=56)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="✦  Help Analyze", bg="#1a4f7a", fg="white",
                 font=("Helvetica Neue", 16, "bold")).pack(side="left", padx=18, pady=14)
        tk.Label(hdr, text=info["title"], bg="#1a4f7a", fg="#a8cce0",
                 font=("Helvetica Neue", 11)).pack(side="left", padx=(0, 18), pady=14)

        # Scrollable body
        body_outer = tk.Frame(dlg, bg="#ffffff")
        body_outer.pack(fill="both", expand=True)
        canvas    = tk.Canvas(body_outer, bg="#ffffff", highlightthickness=0)
        scrollbar = ttk.Scrollbar(body_outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        body = tk.Frame(canvas, bg="#ffffff")
        cw   = canvas.create_window((0, 0), window=body, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(cw, width=e.width))
        body.bind("<Configure>",
                  lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        def _scroll(e):
            import sys
            raw = getattr(e, "delta", 0) or (120 if getattr(e, "num", 0) == 4 else -120)
            if not raw: return
            bbox = canvas.bbox("all")
            if not bbox: return
            ch, vh = bbox[3] - bbox[1], canvas.winfo_height()
            if ch <= vh: return
            scale = 8.0 if sys.platform == "darwin" and abs(raw) < 40 else 4.0
            canvas.yview_moveto(
                max(0., min(1. - vh / ch, canvas.yview()[0] - raw * scale / ch)))

        def _scroll_linux(e):
            raw = 120 if e.num == 4 else -120
            _scroll(type("E", (), {"delta": raw, "num": e.num})())

        dlg.after(50, lambda: _bind_scroll_recursive(dlg, _scroll, _scroll_linux, _scroll_linux))

        PAD2 = 20
        for title, bg, fg, key in [
            ("What it shows",        "#f4f7fb", "#1a4f7a", "purpose"),
            ("Statistical test",     "#f4f7fb", "#1a4f7a", "test"),
            ("How to interpret",     "#f4f7fb", "#1a4f7a", "interpret"),
            ("Recommended settings", "#fffbec", "#666633", "apply"),
        ]:
            frm = tk.Frame(body, bg=bg)
            frm.pack(fill="x", padx=PAD2, pady=(10, 2))
            tk.Label(frm, text=title, bg=bg, fg=fg,
                     font=("Helvetica Neue", 12, "bold")
                     ).pack(anchor="w", padx=10, pady=(8, 4))
            tk.Label(frm, text=info[key], bg=bg, fg="#222222",
                     font=("Helvetica Neue", 11),
                     wraplength=540, justify="left", anchor="nw"
                     ).pack(anchor="w", padx=14, pady=(0, 10), fill="x")

        # Footer
        ttk.Separator(dlg).pack(fill="x")
        foot = tk.Frame(dlg, bg="#ffffff")
        foot.pack(fill="x", padx=PAD2, pady=10)
        PButton(foot, text="Close", style="primary",
                command=dlg.destroy).pack(side="right")

    def _show_analyze_dialog(self, rec_title, groups, normality,
                             reasoning, test, posthoc, mc,
                             norm_label=None, settings_override=None):
        """Show the Help Analyze explanation modal  -  mirrors Prism's Analyze dialog."""
        import tkinter.font as tkfont

        dlg = tk.Toplevel(self)
        dlg.title("Help Analyze")
        dlg.resizable(True, True)
        dlg.geometry("620x560")
        dlg.configure(bg="#ffffff")
        dlg.grab_set()
        self._track_popup(dlg)  # suspend background scroll

        # ── Header ────────────────────────────────────────────────────────────
        hdr = tk.Frame(dlg, bg="#1a4f7a", height=56)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="✦  Help Analyze", bg="#1a4f7a", fg="white",
                 font=("Helvetica Neue", 16, "bold")).pack(side="left", padx=18, pady=14)
        tk.Label(hdr, text="Recommended statistical test based on your data",
                 bg="#1a4f7a", fg="#a8cce0",
                 font=("Helvetica Neue", 11)).pack(side="left", padx=(0, 18), pady=14)

        # ── Scrollable body ───────────────────────────────────────────────────
        body_outer = tk.Frame(dlg, bg="#ffffff")
        body_outer.pack(fill="both", expand=True, padx=0, pady=0)
        canvas   = tk.Canvas(body_outer, bg="#ffffff", highlightthickness=0)
        scrollbar = ttk.Scrollbar(body_outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        body = tk.Frame(canvas, bg="#ffffff")
        canvas_win = canvas.create_window((0, 0), window=body, anchor="nw")

        def _on_resize(e):
            canvas.itemconfig(canvas_win, width=e.width)
        canvas.bind("<Configure>", _on_resize)
        body.bind("<Configure>",
                  lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        def _scroll(e):
            import sys
            raw = getattr(e, "delta", 0)
            if not raw:
                raw = 120 if getattr(e, "num", 0) == 4 else -120
            bbox = canvas.bbox("all")
            if not bbox: return
            content_h = bbox[3] - bbox[1]
            view_h    = canvas.winfo_height()
            if content_h <= view_h: return
            scale = 8.0 if sys.platform == "darwin" and abs(raw) < 40 else 4.0
            frac = -raw * scale / content_h
            cur  = canvas.yview()[0]
            canvas.yview_moveto(max(0.0, min(1.0 - view_h / content_h, cur + frac)))

        def _scroll_linux(e):
            raw = 120 if e.num == 4 else -120
            _scroll(type("E", (), {"delta": raw, "num": e.num})())

        # Bind only to this popup's widget tree  -  avoids capturing parent window scroll
        dlg.after(50, lambda: _bind_scroll_recursive(dlg, _scroll, _scroll_linux, _scroll_linux))

        body.bind("<Configure>", lambda e:
            canvas.configure(scrollregion=canvas.bbox("all")))

        PAD2 = 20

        def _section(parent, title, bg="#f4f7fb"):
            frm = tk.Frame(parent, bg=bg, bd=0)
            frm.pack(fill="x", padx=PAD2, pady=(10, 2))
            tk.Label(frm, text=title, bg=bg, fg="#1a4f7a",
                     font=("Helvetica Neue", 12, "bold")
                     ).pack(anchor="w", padx=10, pady=(8, 4))
            return frm

        def _row(parent, icon, text, fg="#222222", bg="#f4f7fb"):
            r = tk.Frame(parent, bg=bg)
            r.pack(fill="x", padx=10, pady=1)
            tk.Label(r, text=icon, bg=bg, fg=fg,
                     font=("Helvetica Neue", 12), width=2,
                     anchor="n").pack(side="left", padx=(0, 6), pady=2)
            tk.Label(r, text=text, bg=bg, fg=fg,
                     font=("Helvetica Neue", 11),
                     wraplength=500, justify="left", anchor="nw"
                     ).pack(side="left", fill="x", expand=True, pady=2)

        # ── Recommendation pill ───────────────────────────────────────────────
        pill_frm = tk.Frame(body, bg="#e8f4e8", bd=0)
        pill_frm.pack(fill="x", padx=PAD2, pady=(14, 4))
        tk.Label(pill_frm, text="Recommended Test", bg="#e8f4e8", fg="#2d6a2d",
                 font=("Helvetica Neue", 10, "bold")).pack(anchor="w", padx=14, pady=(8, 0))
        tk.Label(pill_frm, text=rec_title, bg="#e8f4e8", fg="#1a4a1a",
                 font=("Helvetica Neue", 14, "bold")).pack(anchor="w", padx=14, pady=(2, 8))

        # ── Decision reasoning ────────────────────────────────────────────────
        reas_frm = _section(body, "Decision Reasoning")
        icon_color = {
            "✓": "#2d7d2d", "✗": "#c0392b", "⚠": "#c07a00",
            " -> ": "#1a4f7a", "ℹ": "#555555", "📊": "#333333",
        }
        for icon, text in reasoning:
            fg = icon_color.get(icon, "#333333")
            _row(reas_frm, icon, text, fg=fg, bg="#f4f7fb")

        # ── Per-group normality table ─────────────────────────────────────────
        norm_frm = _section(body, norm_label or "Normality Check (Shapiro-Wilk)")
        hdr_row = tk.Frame(norm_frm, bg="#dce6f2")
        hdr_row.pack(fill="x", padx=10, pady=(0, 2))
        for txt, w in [("Group", 16), ("n", 5), ("W stat", 10), ("p-value", 10), ("Result", 8)]:
            tk.Label(hdr_row, text=txt, bg="#dce6f2", fg="#1a4f7a",
                     font=("Helvetica Neue", 10, "bold"), width=w, anchor="w"
                     ).pack(side="left", padx=2, pady=3)

        for name, d in normality.items():
            row_bg = "#fff8f8" if not d["normal"] else "#f4f7fb"
            data_row = tk.Frame(norm_frm, bg=row_bg)
            data_row.pack(fill="x", padx=10, pady=1)
            stat_str = f"{d['stat']:.4f}" if d["stat"] is not None else " - "
            p_str    = f"{d['p']:.4f}"    if d["p"]    is not None else " - "
            res_str  = ("✗ FAIL" if not d["normal"] else "✓ pass")
            res_fg   = ("#c0392b" if not d["normal"] else "#2d7d2d")
            for txt, w, fg in [
                (name[:22], 16, "#222222"),
                (str(d["n"]), 5, "#555555"),
                (stat_str, 10, "#555555"),
                (p_str, 10, "#555555"),
                (res_str, 8, res_fg),
            ]:
                tk.Label(data_row, text=txt, bg=row_bg, fg=fg,
                         font=("Helvetica Neue", 10), width=w, anchor="w"
                         ).pack(side="left", padx=2, pady=2)

        # ── Applied settings summary ──────────────────────────────────────────
        app_frm = _section(body, "Settings Applied to Stats Tab", bg="#fffbec")
        if settings_override:
            # Custom settings table for charts with non-standard controls
            for lbl, (val, note) in settings_override.items():
                r2 = tk.Frame(app_frm, bg="#fffbec")
                r2.pack(fill="x", padx=10, pady=2)
                tk.Label(r2, text=lbl + ":", bg="#fffbec", fg="#666633",
                         font=("Helvetica Neue", 10, "bold"), width=28, anchor="w"
                         ).pack(side="left")
                tk.Label(r2, text=val, bg="#fffbec", fg="#222200",
                         font=("Helvetica Neue", 10), anchor="w"
                         ).pack(side="left")
                if note:
                    tk.Label(r2, text=f"  ({note})", bg="#fffbec", fg="#999977",
                             font=("Helvetica Neue", 9), anchor="w"
                             ).pack(side="left")
        else:
            settings_map = {
                "Parametric":     ("Statistical Test", test,
                                   "2 groups  ->  Welch's t-test  |  3+ groups  ->  One-way ANOVA"),
                "Non-parametric": ("Statistical Test", test,
                                   "2 groups  ->  Mann-Whitney U  |  3+ groups  ->  Kruskal-Wallis + Dunn's"),
                "Paired":         ("Statistical Test", test,
                                   "2 groups  ->  Paired t-test  |  3+ groups  ->  Repeated pairwise paired t-tests"),
            }
            s_label, s_val, s_note = settings_map.get(test, ("Statistical Test", test, ""))
            for lbl, val, note in [
                (s_label, s_val, s_note),
                ("Post-hoc (parametric)", posthoc if test == "Parametric" else "Dunn's test",
                 "Controls which pairs are compared after omnibus test"),
                ("Multiple Comparisons", mc,
                 "Correction applied to all pairwise p-values"),
                ("Show Significance Brackets", "✓ Enabled", ""),
                ("Normality Warning on Plot", "✓ Enabled", ""),
            ]:
                r2 = tk.Frame(app_frm, bg="#fffbec")
                r2.pack(fill="x", padx=10, pady=2)
                tk.Label(r2, text=lbl + ":", bg="#fffbec", fg="#666633",
                         font=("Helvetica Neue", 10, "bold"), width=28, anchor="w"
                         ).pack(side="left")
                tk.Label(r2, text=val, bg="#fffbec", fg="#222200",
                         font=("Helvetica Neue", 10), anchor="w"
                         ).pack(side="left")
                if note:
                    tk.Label(r2, text=f"  ({note})", bg="#fffbec", fg="#999977",
                             font=("Helvetica Neue", 9), anchor="w"
                             ).pack(side="left")

        # ── Prism reference note ──────────────────────────────────────────────
        ref_frm = tk.Frame(body, bg="#f0f0f0")
        ref_frm.pack(fill="x", padx=PAD2, pady=(8, 4))
        tk.Label(ref_frm,
                 text="ℹ  Follows standard statistical decision logic. Welch's t-test "
                      "is the default as it does not assume equal variances. You can "
                      "override any setting in the Stats tab before generating the plot.",
                 bg="#f0f0f0", fg="#666666", wraplength=560, justify="left",
                 font=("Helvetica Neue", 10)
                 ).pack(anchor="w", padx=12, pady=8)

        # ── Footer buttons ────────────────────────────────────────────────────
        ttk.Separator(dlg).pack(fill="x", pady=0)
        foot = tk.Frame(dlg, bg="#ffffff")
        foot.pack(fill="x", padx=PAD2, pady=10)
        PButton(foot, text="Apply & Close", style="primary",
                command=dlg.destroy).pack(side="right")
        PButton(foot, text="Apply & Generate Plot", style="primary",
                command=lambda: (dlg.destroy(), self._run())
                ).pack(side="right", padx=(0, 8))
        PButton(foot, text="Close", style="ghost",
                command=lambda: (
                    self._vars["show_stats"].set(False),
                    dlg.destroy()
                )).pack(side="left")

    # ── Run ───────────────────────────────────────────────────────────────────

    def _run(self):
        if self._running: return
        if not self._validated:
            messagebox.showwarning("Validate first",
                                   "Please run Validate Spreadsheet before plotting."); return
        if self._pf is None:
            messagebox.showerror("Not ready", "Functions not loaded yet."); return
        excel = self._vars["excel_path"].get().strip()
        if not excel:
            messagebox.showwarning("Missing input", "Select an Excel file first."); return
        kw = self._collect(excel)
        if kw is None: return
        # Push a snapshot to the undo history before running
        import copy
        self._kw_history.append(copy.deepcopy(kw))
        self._undo_btn.config(state="normal")

        # Tag this render job to the active tab for thread safety
        tab    = self._tab_manager.active if self._tab_manager else None
        job_id = uuid.uuid4().hex
        if tab is not None:
            tab.render_job_id = job_id

        self._running = True
        self._run_btn.config(state="disabled")
        self._set_status("Generating plot...")
        self._start_spinner()
        tab_id = tab.tab_id if tab is not None else None
        threading.Thread(
            target=self._do_run,
            args=(kw, tab_id, job_id),
            daemon=True,
        ).start()

    def _undo(self):
        """Re-run the previous plot configuration (⌘Z)."""
        if self._running or len(self._kw_history) < 2:
            return
        # Pop the current state, leaving the one before it on top
        self._kw_history.pop()
        kw = self._kw_history[-1]
        import copy
        self._running = True
        self._run_btn.config(state="disabled")
        self._set_status("Undoing…")
        self._start_spinner()
        if len(self._kw_history) < 2:
            self._undo_btn.config(state="disabled")
        tab    = self._tab_manager.active if self._tab_manager else None
        job_id = uuid.uuid4().hex
        if tab is not None:
            tab.render_job_id = job_id
        tab_id = tab.tab_id if tab is not None else None
        threading.Thread(
            target=self._do_run,
            args=(copy.deepcopy(kw), tab_id, job_id),
            daemon=True,
        ).start()

    def _do_redo(self):
        """Redo using the UndoStack (⌘⇧Z)."""
        if hasattr(self, "_undo_stack") and self._undo_stack.can_redo():
            self._undo_stack.redo(self._vars)
            self._set_status("Redone")

    def _compute_data_ymin(self, excel_path, sheet, plot_type):
        """Return the true minimum Y-data value for 'Start at data min'.

        Each Excel layout needs a different slicing strategy to isolate
        Y-values (avoiding X-axis values, row/column labels, or count data
        that shouldn't influence the Y scale).

        Returns float or None if the minimum cannot be determined.
        """
        pd = _pd()
        import numpy as np
        try:
            df = pd.read_excel(excel_path, sheet_name=sheet, header=None)
        except Exception:
            return None

        try:
            # Charts where col-0 is X and cols 1+ are Y replicates
            # (line, scatter, curve_fit): exclude col-0 (X values) and
            # row-0 (series names) before computing the minimum.
            if plot_type in ("line", "scatter", "curve_fit"):
                y_vals = pd.to_numeric(
                    df.iloc[1:, 1:].values.flatten(), errors="coerce")

            # Grouped bar: rows 0-1 are category/subgroup headers,
            # rows 2+ are the numeric data.
            elif plot_type == "grouped_bar":
                y_vals = pd.to_numeric(
                    df.iloc[2:].values.flatten(), errors="coerce")

            # Two-way ANOVA: long-format with a header row.
            # The "Value" column holds the Y data; other columns are factors.
            elif plot_type == "two_way_anova":
                df_long = pd.read_excel(excel_path, sheet_name=sheet, header=0)
                val_col = next(
                    (c for c in df_long.columns
                     if str(c).strip().lower() == "value"), None)
                if val_col is None:
                    # Fall back to last numeric column
                    num_cols = df_long.select_dtypes(include="number").columns
                    val_col  = num_cols[-1] if len(num_cols) else None
                if val_col is None:
                    return None
                y_vals = pd.to_numeric(df_long[val_col], errors="coerce").values

            # Heatmap: row-0 = column labels, col-0 = row labels.
            # Numeric matrix is rows 1+, cols 1+.
            elif plot_type == "heatmap":
                y_vals = pd.to_numeric(
                    df.iloc[1:, 1:].values.flatten(), errors="coerce")

            # KM survival: Y axis is survival probability (0–1) computed
            # internally; the Excel time/event values don't map to Y.
            # Contingency: count table; Y axis is counts or percentages.
            # Column stats: summary table, not a simple scatter Y axis.
            # These chart types don't benefit from "start at data min"
            # in a meaningful way  -  return None to leave the axis unchanged.
            elif plot_type in ("kaplan_meier", "contingency", "column_stats",
                               "chi_square_gof", "bland_altman", "forest_plot"):
                return None

            # Stacked bar: same 2-row header layout as grouped_bar
            elif plot_type == "stacked_bar":
                y_vals = pd.to_numeric(
                    df.iloc[2:].values.flatten(), errors="coerce")

            # Bubble: X/Y/Size triples starting col 1; skip col 0 (X label)
            elif plot_type == "bubble":
                y_vals = pd.to_numeric(
                    df.iloc[1:, 2::3].values.flatten(), errors="coerce")

            # All flat-header charts (bar, box, violin, subcolumn_scatter,
            # before_after, repeated_measures, histogram):
            # row 0 = group names, rows 1+ = numeric values.
            else:
                y_vals = pd.to_numeric(
                    df.iloc[1:].values.flatten(), errors="coerce")

            valid = y_vals[~np.isnan(y_vals)]
            return float(valid.min()) if len(valid) > 0 else None

        except Exception:
            return None

    def _ensure_scipy(self):
        """Lazily load scipy.stats for statistical computations."""
        if self._pf is not None and not getattr(self, "_scipy_loaded", False):
            from scipy import stats as _stats  # noqa: F401
            self._scipy_loaded = True

    def _do_run(self, kw, tab_id=None, job_id=None):
        try:
            pd = _pd()

            # Strip internal-only keys
            kw.pop("_ylim_data_min", False)
            kw.pop("_xlim", None)
            kw.pop("show_ns", False)
            kw.pop("p_sig_threshold", 0.05)
            kw.pop("show_normality_warning", True)

            # ── Excel parse cache ─────────────────────────────────────────────
            _excel_path  = kw.get("excel_path", "")
            _excel_sheet = kw.get("sheet", 0)
            _cache_key   = (_excel_path, _excel_sheet)
            if self._parse_cache_key != _cache_key:
                try:
                    self._parse_cache_df  = pd.read_excel(
                        _excel_path, sheet_name=_excel_sheet, header=None)
                    self._parse_cache_key = _cache_key
                except Exception:
                    self._parse_cache_df  = None
                    self._parse_cache_key = None

            groups = []
            if self._parse_cache_df is not None:
                try:
                    groups = [str(c) for c in
                              self._parse_cache_df.iloc[0].dropna().tolist()]
                except Exception:
                    pass

            pt = self._plot_type.get()
            spec = next((s for s in _REGISTRY_SPECS if s.key == pt), _REGISTRY_SPECS[0])

            # Call chart-specific extra_collect hook
            if spec.extra_collect is not None:
                spec.extra_collect(self, kw)

            # Capture for results panel
            import copy as _copy
            _kw_snap = _copy.deepcopy(kw)
            _ep = kw.get("excel_path", "")
            _sh = kw.get("sheet", 0)

            # Schedule webview embed on main thread
            self.after(0, lambda: self._embed_plot(
                None, groups, kw=_kw_snap, tab_id=tab_id, job_id=job_id))
            self.after(80, lambda: self._populate_results(_ep, _sh, pt, _kw_snap))
        except Exception:
            err = traceback.format_exc()
            short = err.strip().splitlines()[-1]
            self.after(0, lambda: self._set_status(f"Error: {short}", err=True))
            self.after(0, lambda: messagebox.showerror("Runtime error", err))
            self.after(0, self._reset_btn)

    def _try_webview_embed(self, plot_frame: "tk.Frame", chart_type: str, kw: dict) -> bool:
        """Embed a Plotly chart via pywebview. Returns True on success."""
        if not getattr(self, "_web_server_running", False):
            return False
        try:
            from refraction.server.webview import PlotterWebView
            from refraction.server.api import get_port
            pv = PlotterWebView(plot_frame, port=get_port())
            if not pv.show():
                return False
            pv.render(chart_type, kw)
            self._plotly_views[id(plot_frame)] = pv
            return True
        except Exception:
            _log.debug("App._try_webview_embed: webview embed failed for %r", chart_type, exc_info=True)
            return False

    def _embed_plot(self, fig, groups=None, kw=None, tab_id=None, job_id=None):
        """Display a Plotly chart in the right pane via pywebview.

        Parameters
        ----------
        fig    : ignored (kept for API compat; always None in Plotly-only mode)
        groups : list of group names (for control-group dropdown)
        kw     : full plot kwargs dict
        tab_id : tab this render belongs to (thread-safety guard)
        job_id : render job id (superseded-job guard)
        """
        try:
            # ── Validate: discard stale or orphaned renders ───────────────────
            if self._tab_manager is not None and tab_id is not None:
                tab = self._tab_manager.get_tab(tab_id)
                if tab is None or tab.render_job_id != job_id:
                    return
                target_frame = tab.plot_frame
            else:
                target_frame = self._plot_frame
                tab = None

            # Store last successful render state for journal export
            if kw:
                import copy as _copy_embed
                self._last_kw = _copy_embed.deepcopy(kw)
            _pt_web = kw.get("plot_type", "") if kw else ""
            if not _pt_web and hasattr(self, "_plot_type"):
                _pt_web = self._plot_type.get()
            if hasattr(_pt_web, "get"):
                _pt_web = _pt_web.get()
            self._last_chart_type = str(_pt_web) if _pt_web else None

            # ── Render via Plotly webview ──────────────────────────────────────
            if kw and self._try_webview_embed(target_frame, str(_pt_web), kw):
                self._plot_frame = target_frame
                if tab is not None:
                    tab.canvas_widget = None
            else:
                # Webview failed — show error in the plot frame
                for child in target_frame.winfo_children():
                    child.destroy()
                lbl = tk.Label(target_frame,
                               text="Could not render chart.\n"
                                    "Ensure the FastAPI server is running.",
                               fg="#cc6600", bg="white", font=("Arial", 12))
                lbl.pack(expand=True)
                self._plot_frame = target_frame

            # Hide the empty state overlay
            try:
                self._empty_state_frame.place_forget()
                self._plot_canvas.itemconfigure(self._empty_state_id, state="hidden")
            except Exception:
                pass

            if groups:
                opts = list(groups)
                for cb in self._control_cbs:
                    cb.config(values=opts, state="readonly")
                for lbl in self._control_hint_lbls:
                    lbl.config(text=f"{len(groups)} group(s) found")
                if self._vars["control"].get() not in opts:
                    self._vars["control"].set(opts[0])
                self._tog_control()

            self._set_status("Done")
            self._export_btn.config(state="normal")
            self._copy_btn.config(state="normal")
            self._copy_transparent_btn.config(state="normal")
            self._copy_svg_btn.config(state="normal")
            self._zoom_reset_btn.config(state="normal")
            self._zoom_in_btn.config(state="normal")
            self._zoom_out_btn.config(state="normal")

            # Save to recent files
            path = self._vars["excel_path"].get().strip()
            if path and os.path.exists(path):
                _add_recent(path)

        except Exception:
            err = traceback.format_exc()
            self._set_status(f"Embed error: {err.strip().splitlines()[-1]}", err=True)
        finally:
            self._reset_btn()

    def _zoom_plot(self, raw):
        """No-op — Plotly has built-in zoom via its mode bar."""
        pass

    def _zoom_plot_factor(self, factor):
        """No-op — Plotly has built-in zoom via its mode bar."""
        pass

    def _apply_zoom(self):
        """No-op — Plotly has built-in zoom via its mode bar."""
        pass

    def _reset_zoom(self):
        """Reset scroll position."""
        self._plot_canvas.xview_moveto(0)
        self._plot_canvas.yview_moveto(0)

    # ── Live preview ──────────────────────────────────────────────────────────

    # Variables that, when changed, should trigger a re-render without requiring
    # the user to click "Generate Plot".  Data-loading variables (excel_path,
    # sheet) are excluded — those go through the validate pipeline instead.
    _LIVE_PREVIEW_VARS = (
        "color", "axis_style", "tick_dir", "fig_bg", "minor_ticks",
        "show_points", "error", "yscale", "gridlines", "grid_style",
        "show_value_labels", "show_n_labels", "spine_width",
        "ref_line_enabled", "legend_pos", "bar_alpha",
        "title", "xlabel", "ytitle",
    )

    def _setup_live_preview(self):
        """Wire trace callbacks on display variables so any change triggers a
        debounced re-render (400 ms delay prevents re-running on every keystroke)."""
        for key in self._LIVE_PREVIEW_VARS:
            v = self._vars.get(key)
            if v is not None:
                v.trace_add("write", lambda *_, _k=key: self._schedule_preview())

        # Keep the active tab's label in sync with the chart title field.
        # Guarded by _switching_tabs so tab-switch var restores don't corrupt labels.
        title_v = self._vars.get("title")
        if title_v is not None:
            title_v.trace_add("write", lambda *_: self._sync_active_tab_label())

    def _schedule_preview(self):
        """Cancel any pending preview and schedule a new one in 400 ms."""
        if not self._live_preview_enabled:
            return
        if self._preview_after_id is not None:
            try:
                self.after_cancel(self._preview_after_id)
            except Exception:
                _log.debug("App._schedule_preview: after_cancel failed", exc_info=True)
        self._preview_after_id = self.after(400, self._live_preview_run)

    def _live_preview_run(self):
        """Fire a silent re-run if a plot is already showing and we are not busy."""
        self._preview_after_id = None
        if (self._last_chart_type is not None
                and self._validated
                and not self._running
                and self._pf is not None):
            excel = self._vars.get("excel_path", None)
            if excel and excel.get().strip():
                self._run()

    # ── (canvas-mode renderer removed in Phase 1; replaced by mpl_connect) ───



    def _start_spinner(self):
        """Animate the Generate Plot button while running."""
        frames = ["Generating", "Generating.", "Generating..", "Generating..."]
        self._spinner_idx = 0
        def _tick():
            if not self._running: return
            self._run_btn.config(text=frames[self._spinner_idx % len(frames)])
            self._spinner_idx += 1
            self.after(400, _tick)
        _tick()

    def _reset_btn(self):
        self._running = False
        self._run_btn.config(state="normal", text="Generate Plot")

    def _set_status(self, msg, err=False):
        self._status_var.set(msg)
        if err:
            fg_color = "#cc0000"
        elif any(w in msg.lower() for w in ("done", "saved", "copied", "ready")):
            fg_color = "#2a8a2a"
        elif any(w in msg.lower() for w in ("warning", "validat")):
            fg_color = "#cc6600"
        else:
            fg_color = "#555555"
        self._status_lbl.config(foreground=fg_color)
        # Auto-fade success messages after 3 s
        if fg_color == "#2a8a2a":
            if hasattr(self, "_status_fade_id") and self._status_fade_id:
                try: self.after_cancel(self._status_fade_id)
                except Exception: pass
            self._status_fade_id = self.after(3000, lambda: (
                self._status_var.set(""),
                self._status_lbl.config(foreground="#555555")
            ))


