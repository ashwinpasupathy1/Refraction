"""Stats tab builder mixin — extracted from plotter_barplot_app.py."""

import tkinter as tk
from tkinter import ttk
from plotter_widgets import (
    PCombobox, PCheckbox, PEntry, section_sep,
    add_placeholder, label, hint, _create_tooltip,
)

# This mixin is mixed into the App class via multiple inheritance.
# All self.* references resolve to App instance attributes.


class StatsTabMixin:
    """Methods that build the statistics configuration tabs."""

    def _tab_stats(self, f):
        self._init_vars({
            "show_stats": False, "show_ns": False, "show_p_values": False,
            "show_effect_size": False, "show_test_name": False,
            "show_normality_warning": True,
            "stats_test": "Parametric", "n_permutations": "",
            "mc_correction": "Holm-Bonferroni", "posthoc": "Tukey HSD",
            "control": "", "p_sig_threshold": "0.05",
        })

        try:
            from scipy import stats as _st
            sep = "\n\n"
            TEST_INFO = {
                "Paired":        "Paired t-test (2 groups) or repeated pairwise paired t-tests (3+ groups). Requires equal n per group  -  values are matched by row order.",
                "Parametric":    "2 groups: " + _scipy_summary(_st.ttest_ind, 160) + sep +
                                 "3+ groups: " + _scipy_summary(_st.f_oneway, 160),
                "Non-parametric":"2 groups: " + _scipy_summary(_st.mannwhitneyu, 160) + sep +
                                 "3+ groups: " + _scipy_summary(_st.kruskal, 180),
                "Permutation":   _scipy_summary(_st.permutation_test, 320),
            }
        except Exception:
            _log.debug("App._tab_stats: scipy TEST_INFO build failed", exc_info=True)
            TEST_INFO = {
                "Paired":         "Paired t-test (matched observations, same n per group).",
                "Parametric":     "Welch's t-test (2 groups, unequal variance OK) or one-way ANOVA + Tukey HSD (3+ groups).",
                "Non-parametric": "Mann-Whitney U (2 groups) or Kruskal-Wallis + Dunn's (3+ groups).",
                "Permutation":    "Permutation test on difference of means + Holm-Bonferroni.",
            }

        g = f; r = 0

        r = self._checkbox(g, r, "show_stats",       f" {label('show_stats')}")
        r = self._sep(g, r)
        r = self._checkbox(g, r, "show_ns",          " Show 'ns' brackets (non-significant)")
        r = self._sep(g, r)

        # ── Significance threshold ─────────────────────────────────────────────
        r = self._section_label(g, r, "Significance Threshold")
        thresh_row = ttk.Frame(g)
        thresh_row.grid(row=r, column=0, columnspan=3, sticky="w", padx=PAD, pady=(2, 0)); r += 1
        ttk.Label(thresh_row, text="Show brackets only when p ≤",
                  font=("Helvetica Neue", 12)).pack(side="left")
        _thresh_cb = PCombobox(thresh_row, textvariable=self._vars["p_sig_threshold"],
                               values=["0.05", "0.01", "0.001", "0.0001"],
                               state="normal", width=8, font=("Menlo", 12))
        _thresh_cb.pack(side="left", padx=(8, 0))
        add_placeholder(_thresh_cb, self._vars["p_sig_threshold"], "0.05")
        r = self._hint(g, r, "Default 0.05 (one star). Set to 0.01 to show only ** *** **** "
                             "brackets, hiding borderline * results. Matches Prism's α setting. "
                             "Type any value or choose from the list.")
        r = self._sep(g, r)

        # ── Bracket style (P16) ────────────────────────────────────────────────
        r = self._section_label(g, r, "Bracket Style")
        _bs_row = ttk.Frame(g)
        _bs_row.grid(row=r, column=0, columnspan=3, sticky="w", padx=PAD, pady=(2, 4)); r += 1
        if "bracket_style" not in self._vars:
            self._vars["bracket_style"] = tk.StringVar(value="Lines")
        for _bs_val, _bs_lbl in (("Lines", "Lines (default)"),
                                  ("Bracket", "Square brackets"),
                                  ("Asterisks only", "Asterisks only")):
            tk.Radiobutton(_bs_row, text=_bs_lbl,
                           variable=self._vars["bracket_style"],
                           value=_bs_val,
                           font=("Helvetica Neue", 12),
                           bg="#ffffff" if hasattr(self, "_bg") else None
                           ).pack(side="left", padx=(0, 10))
        r = self._sep(g, r)

        r = self._checkbox(g, r, "show_p_values",    " Show raw p-values (instead of stars)")
        r = self._sep(g, r)
        r = self._checkbox(g, r, "show_effect_size", " Show effect size (Cohen's d)")
        r = self._sep(g, r)
        r = self._checkbox(g, r, "show_test_name",   " Show test name below plot")
        r = self._sep(g, r)

        r = self._section_label(g, r, "Normality Check")
        r = self._checkbox(g, r, "show_normality_warning", " Show normality warning on plot")
        r = self._hint(g, r, "When Show Significance Brackets is on, a Shapiro-Wilk test "
                             "is run automatically. An orange warning appears on the plot "
                             "if any group fails normality (p\u22640.05) and Parametric is selected.")
        r = self._sep(g, r)

        _l, r = _lbl(g, r, "stats_test")
        cb2 = PCombobox(g, textvariable=self._vars["stats_test"],
                           values=["Paired", "Parametric", "Non-parametric", "Permutation",
                                   "One-sample"],
                           state="readonly", width=22, font=("Helvetica Neue", 12))
        cb2.grid(row=r, column=0, sticky="w", padx=PAD, pady=4); r += 1

        self._test_info_lbl = ttk.Label(g, text=TEST_INFO.get("Parametric", ""),
                                        foreground="gray", wraplength=520,
                                        justify="left", font=("Helvetica Neue", 11))
        self._test_info_lbl.grid(row=r, column=0, columnspan=3, sticky="ew",
                                 padx=PAD, pady=(0, 4)); r += 1
        self._test_info_lbl.bind("<Configure>",
            lambda e: self._test_info_lbl.config(wraplength=max(200, e.width - 8)))
        self._TEST_INFO = TEST_INFO

        # One-sample μ₀ field (shown only when One-sample is selected)
        self._init_vars({"one_sample_mu0": "0"})
        _mu0_frame = ttk.Frame(g)
        _mu0_frame.grid(row=r, column=0, columnspan=3, sticky="w", padx=PAD, pady=(0, 4))
        ttk.Label(_mu0_frame, text="Null hypothesis μ₀ =",
                  font=("Helvetica Neue", 12)).pack(side="left")
        _mu0_entry = PEntry(_mu0_frame, textvariable=self._vars["one_sample_mu0"],
                            width=10, font=("Menlo", 12))
        _mu0_entry.pack(side="left", padx=(6, 0))
        add_placeholder(_mu0_entry, self._vars["one_sample_mu0"], "e.g. 0")
        self._mu0_frame = _mu0_frame
        r += 1

        def _on_test_change(e=None):
            test = self._vars["stats_test"].get()
            self._test_info_lbl.config(text=TEST_INFO.get(test, ""))
            self._tog_perm()
            self._tog_posthoc()
            self._tog_control()
            # Show/hide μ₀ field
            if test == "One-sample":
                self._mu0_frame.grid()
            else:
                self._mu0_frame.grid_remove()
        cb2.bind("<<ComboboxSelected>>", _on_test_change)
        # Initialise visibility
        if self._get_var("stats_test", "Parametric") != "One-sample":
            _mu0_frame.grid_remove()
        r = self._sep(g, r)

        # Post-hoc (shown/hidden by _tog_posthoc)
        self._posthoc_label = ttk.Label(g, text=label("posthoc"),
                                        font=("Helvetica Neue", 13, "bold"))
        self._posthoc_cb    = PCombobox(g, textvariable=self._vars["posthoc"],
                                           values=["Tukey HSD", "Bonferroni", "Sidak",
                                                   "Fisher LSD", "Dunnett (vs control)"],
                                           state="readonly", width=26,
                                           font=("Helvetica Neue", 12))
        self._posthoc_sep   = ttk.Separator(g)
        # Non-parametric hint: Dunn's test is always used, no selector needed
        self._posthoc_dunn_hint = ttk.Label(
            g,
            text="Post-hoc: Dunn's test  (Kruskal-Wallis pairwise rank-sum comparisons)\n"
                 "Correction method is controlled by the Multiple Comparisons setting below.",
            foreground="#555555", wraplength=480, justify="left",
            font=("Helvetica Neue", 11))
        self._posthoc_r     = r; r += 3

        # Wire posthoc change to _tog_control so Dunnett activates the control selector
        self._posthoc_cb.bind("<<ComboboxSelected>>",
                              lambda e: (self._tog_control(), self._tog_posthoc()))

        _l, r = _lbl(g, r, "mc_correction")
        PCombobox(g, textvariable=self._vars["mc_correction"],
                     values=["Holm-Bonferroni", "Bonferroni",
                             "Benjamini-Hochberg (FDR)", "None (uncorrected)"],
                     state="readonly", width=26, font=("Helvetica Neue", 12)
                     ).grid(row=r, column=0, sticky="w", padx=PAD, pady=4); r += 1
        r = self._sep(g, r)

        # Permutation entry (shown/hidden by _tog_perm)
        self._perm_label   = ttk.Label(g, text=label("n_permutations"),
                                       font=("Helvetica Neue", 13, "bold"))
        self._perm_hint    = ttk.Label(g, text=hint("n_permutations"))
        self._perm_entry   = PEntry(g, textvariable=self._vars["n_permutations"],
                                       width=14, font=("Menlo", 12))
        add_placeholder(self._perm_entry, self._vars["n_permutations"], "e.g. 9999")
        self._perm_sep     = ttk.Separator(g)
        self._perm_r_start = r; r += 4

        # ── Comparison Mode  -  Prism-style: all-pairs vs. vs-control ──────
        r = self._section_label(g, r, "Comparison Mode")
        self._init_vars({"comparison_mode": 0})  # 0=all-pairwise, 1=vs-control
        _cmode_rg = PRadioGroup(g, variable=self._vars["comparison_mode"],
                                options=["All pairwise", "Each group vs. control"],
                                command=self._tog_control)
        _cmode_rg.grid(row=r, column=0, columnspan=3, sticky="w", padx=PAD, pady=4)
        # Store ref so _tog_control can disable it when the mode is forced
        self._cmode_rg_widget = _cmode_rg
        r += 1
        r = self._hint(g, r,
                       "All pairwise: every group compared to every other group.\n"
                       "Each group vs. control: only brackets between the selected "
                       "control and each other group. Use Dunnett for the most "
                       "statistically appropriate control comparison.")
        r = self._sep(g, r)

        # Control group dropdown
        r = self._section_label(g, r, "Control Group")
        control_cb = PCombobox(g, textvariable=self._vars["control"],
                                  values=["(none \u2014 all pairwise)"],
                                  state="disabled", width=28, font=("Menlo", 12))
        control_cb.grid(row=r, column=0, columnspan=2, sticky="w", padx=PAD, pady=4)
        tip(control_cb, "control")
        control_hint_lbl = ttk.Label(g,
                                     text="Load a file to populate group names",
                                     foreground="gray", font=("Helvetica Neue", 10),
                                     wraplength=300)
        control_hint_lbl.grid(row=r+1, column=0, columnspan=3, sticky="w",
                               padx=PAD, pady=(0, 4))
        r += 2

        if not hasattr(self, "_control_cbs"):
            self._control_cbs       = []
            self._control_hint_lbls = []
        self._control_cbs.append(control_cb)
        self._control_hint_lbls.append(control_hint_lbl)
        self._control_cb       = control_cb
        self._control_hint_lbl = control_hint_lbl

        # Wire comparison_mode changes to toggle the control dropdown state
        self._vars["comparison_mode"].trace_add("write",
            lambda *_: self._tog_control())

        self._perm_visible    = False
        self._posthoc_visible = False
        self._tog_perm()
        self._tog_posthoc()
        self._tog_control()
        self._tab_footer(g, r)

    def _tab_stats_grouped_bar(self, f):
        """Stats tab for Grouped Bar  -  standard pairwise options plus per-category ANOVA."""
        self._init_vars({"show_anova_per_group": False})
        # Render the full shared stats UI (uses grid on f)
        self._tab_stats(f)
        # Append the ANOVA section using grid, after whatever rows _tab_stats used.
        # grid_size() returns (cols, rows)  -  rows is the count of occupied rows.
        r = f.grid_size()[1]
        section_sep(f, r, "Per-Category One-Way ANOVA"); r += 1
        PCheckbox(f,
                  variable=self._vars["show_anova_per_group"],
                  text=" Run one-way ANOVA on each category cluster"
                  ).grid(row=r, column=0, columnspan=3, sticky="w",
                         padx=PAD, pady=(0, 4)); r += 1
        ttk.Label(f,
                  text="Shows F-statistic and p-value above each category cluster, "
                       "testing whether the subgroups within that cluster differ. "
                       "Independent of the pairwise brackets above.",
                  foreground="gray", wraplength=380, justify="left",
                  font=("Helvetica Neue", 11)
                  ).grid(row=r, column=0, columnspan=3, sticky="w",
                         padx=PAD, pady=(0, 8))

    def _tab_stats_scatter(self, f):
        """Stats tab specific to scatter plot  -  correlation + regression options."""
        self._init_vars({
            "show_regression": False, "show_ci_band": False,
            "show_prediction_band": False, "show_correlation": False,
            "correlation_type": "Pearson", "show_regression_table": False,
        })

        g = f; r = 0

        r = self._section_label(g, r, "Regression")
        r = self._checkbox(g, r, "show_regression",       " Show linear regression line")
        r = self._checkbox(g, r, "show_ci_band",          " Show 95% confidence band")
        r = self._checkbox(g, r, "show_prediction_band",  " Show 95% prediction band")
        r = self._checkbox(g, r, "show_regression_table", " Show full regression table (slope, F, runs test)")
        r = self._hint(g, r, "Full table: slope ± SE, 95% CI, intercept ± SE, "
                             "F-statistic, R, R², adjusted R², runs test for linearity. "
                             "Single-series only.")
        r = self._sep(g, r)

        r = self._section_label(g, r, "Correlation")
        r = self._checkbox(g, r, "show_correlation", " Show correlation annotation")

        ttk.Label(g, text="Correlation Type",
                  font=("Helvetica Neue", 13, "bold")
                  ).grid(row=r, column=0, sticky="w", padx=PAD, pady=(4, 2)); r += 1
        PCombobox(g, textvariable=self._vars["correlation_type"],
                     values=["Pearson", "Spearman"],
                     state="readonly", width=18, font=("Helvetica Neue", 12)
                     ).grid(row=r, column=0, sticky="w", padx=PAD, pady=4); r += 1
        r = self._hint(g, r, "Pearson: linear correlation (assumes normality).\n"
                             "Spearman: rank-based, non-parametric.")
        r = self._sep(g, r)

        r = self._section_label(g, r, "Reference Line")
        ref_row = ttk.Frame(g)
        ref_row.grid(row=r, column=0, columnspan=3, sticky="w", padx=PAD, pady=(4, 2)); r += 1
        PCheckbox(ref_row, variable=self._vars["ref_line_enabled"],
                        text=" Show at Y =").pack(side="left")
        _e_ref = PEntry(ref_row, textvariable=self._vars["ref_line_y"],
                           width=8, font=("Menlo", 12))
        _e_ref.pack(side="left", padx=(6, 0))
        add_placeholder(_e_ref, self._vars["ref_line_y"], "e.g. 0")
        ref_lbl_row = ttk.Frame(g)
        ref_lbl_row.grid(row=r, column=0, columnspan=3, sticky="w", padx=PAD, pady=(0, 4)); r += 1
        ttk.Label(ref_lbl_row, text="Label:", font=("Helvetica Neue", 11)).pack(side="left")
        _e_ref_lbl = PEntry(ref_lbl_row, textvariable=self._vars["ref_line_label"],
                               width=20, font=("Menlo", 12))
        _e_ref_lbl.pack(side="left", padx=(6, 0))
        add_placeholder(_e_ref_lbl, self._vars["ref_line_label"], "blank = show y=…")

        self._tab_footer(g, r)

    # ── Helpers ───────────────────────────────────────────────────────────────

    # ── UI widget helpers  -  eliminate repeated boilerplate in tab builders ────

    def _tab_stats_kaplan_meier(self, f):
        """Stats tab specific to Kaplan-Meier  -  log-rank options."""
        self._init_vars({
            "show_stats": False, "show_p_values": False,
            "show_ci": True, "show_censors": True, "show_at_risk": False,
        })
        g = f; r = 0

        r = self._section_label(g, r, "Survival Curve Options")
        r = self._checkbox(g, r, "show_ci",      " Show 95% confidence band")
        r = self._checkbox(g, r, "show_censors", " Show censoring tick marks")
        r = self._checkbox(g, r, "show_at_risk", " Show at-risk table below plot")
        r = self._sep(g, r)

        r = self._section_label(g, r, "Log-Rank Test")
        r = self._checkbox(g, r, "show_stats",    " Show log-rank p-values on plot")
        r = self._checkbox(g, r, "show_p_values", " Show raw p-values (instead of stars)")
        r = self._hint(g, r, "Mantel-Cox log-rank test. Each pair of groups is compared.\n"
                             "Censored observations (Event=0) are handled automatically.")
        r = self._sep(g, r)

        r = self._section_label(g, r, "Reference Line")
        ref_row = ttk.Frame(g)
        ref_row.grid(row=r, column=0, columnspan=3, sticky="w", padx=PAD, pady=(4, 2)); r += 1
        PCheckbox(ref_row, variable=self._vars["ref_line_enabled"],
                        text=" Show at Y =").pack(side="left")
        _e_ref = PEntry(ref_row, textvariable=self._vars["ref_line_y"],
                           width=8, font=("Menlo", 12))
        _e_ref.pack(side="left", padx=(6, 0))
        add_placeholder(_e_ref, self._vars["ref_line_y"], "e.g. 0.5")
        ref_lbl_row = ttk.Frame(g)
        ref_lbl_row.grid(row=r, column=0, columnspan=3, sticky="w", padx=PAD, pady=(0, 4)); r += 1
        ttk.Label(ref_lbl_row, text="Label:", font=("Helvetica Neue", 11)).pack(side="left")
        _e_lbl = PEntry(ref_lbl_row, textvariable=self._vars["ref_line_label"],
                           width=20, font=("Menlo", 12))
        _e_lbl.pack(side="left", padx=(6, 0))
        add_placeholder(_e_lbl, self._vars["ref_line_label"], "blank = show y=…")
        self._tab_footer(g, r)

    # ── Stats tab: Before/After ───────────────────────────────────────────────

    def _tab_stats_before_after(self, f):
        """Options for the Before/After paired plot."""
        self._init_vars({"show_stats": False, "show_p_values": False,
                         "show_n_labels": False, "show_normality_warning": True})
        g = f; r = 0

        r = self._section_label(g, r, "Paired Statistics")
        r = self._checkbox(g, r, "show_stats",    " Show paired t-test bracket (2 groups only)")
        r = self._checkbox(g, r, "show_p_values", " Show raw p-value (instead of stars)")
        r = self._checkbox(g, r, "show_n_labels", " Show n= on x-axis")
        r = self._sep(g, r)
        r = self._section_label(g, r, "Normality Check")
        r = self._checkbox(g, r, "show_normality_warning", " Show normality warning on plot")
        r = self._sep(g, r)
        r = self._hint(g, r, "Each subject is connected by a gray line. "
                             "The mean ± SD bar is drawn per group. "
                             "Paired t-test requires equal n in both groups "
                             "(matched by row order).")
        self._tab_footer(g, r)

    # ── Stats tab: Histogram ──────────────────────────────────────────────────

    def _tab_stats_histogram(self, f):
        """Bin and display options for Histogram."""
        self._init_vars({"hist_bins": "0", "hist_density": False, "hist_overlay_normal": False})
        g = f; r = 0

        r = self._section_label(g, r, "Bins")
        fr_bins = ttk.Frame(g)
        fr_bins.grid(row=r, column=0, columnspan=3, sticky="w", padx=PAD, pady=4); r += 1
        ttk.Label(fr_bins, text="Number of bins:", font=("Helvetica Neue", 12)).pack(side="left")
        _e_bins = PEntry(fr_bins, textvariable=self._vars["hist_bins"],
                            width=6, font=("Menlo", 12))
        _e_bins.pack(side="left", padx=(6, 0))
        add_placeholder(_e_bins, self._vars["hist_bins"], "0 = auto")
        ttk.Label(fr_bins, text="  (0 = auto via Sturges)",
                  foreground="gray", font=("Helvetica Neue", 11)).pack(side="left")
        r = self._sep(g, r)

        r = self._section_label(g, r, "Display")
        r = self._checkbox(g, r, "hist_density",        " Density mode (area = 1, not count)")
        r = self._checkbox(g, r, "hist_overlay_normal", " Overlay fitted normal curve")
        r = self._sep(g, r)
        r = self._hint(g, r, "All series share the same bin edges so bars "
                             "are directly comparable across groups.")
        self._tab_footer(g, r)

    # ── Stats tab: Curve Fit ──────────────────────────────────────────────────

    def _tab_stats_curve_fit(self, f):
        """Model selector and display options for nonlinear curve fitting."""
        _default_model = "4PL Sigmoidal (EC50/IC50)"
        self._init_vars({
            "curve_model":       _default_model,
            "cf_show_ci":        True,  "cf_show_residuals": False,
            "cf_show_equation":  True,  "cf_show_r2":        True,
            "cf_show_params":    True,
        })
        g = f; r = 0

        r = self._section_label(g, r, "Model")
        _model_names = list(getattr(
            __import__("sys").modules.get(
                "plotter_functions", type("M", (), {"CURVE_MODELS": {}})()),
            "CURVE_MODELS", {}
        ).keys()) or [
            "4PL Sigmoidal (EC50/IC50)", "3PL Sigmoidal (no bottom)",
            "One-phase exponential decay", "One-phase exponential growth",
            "Two-phase exponential decay", "Michaelis-Menten",
            "Hill equation", "Gaussian (bell curve)", "Log-normal",
            "Linear", "Polynomial (2nd order)",
        ]
        _model_cb = PCombobox(g, textvariable=self._vars["curve_model"],
                                 values=_model_names, state="readonly",
                                 width=34, font=("Helvetica Neue", 12))
        _model_cb.grid(row=r, column=0, columnspan=3, sticky="w", padx=PAD, pady=4); r += 1
        _desc_lbl = ttk.Label(g, text="", foreground="#666",
                              wraplength=380, justify="left", font=("Helvetica Neue", 10))
        _desc_lbl.grid(row=r, column=0, columnspan=3, sticky="w", padx=PAD, pady=(0, 6)); r += 1

        _MODEL_DESC = {
            "4PL Sigmoidal (EC50/IC50)":   "4-parameter logistic. Bottom, Top, EC50 (inflection), HillSlope. Standard for dose-response curves.",
            "3PL Sigmoidal (no bottom)":   "3-parameter logistic. Bottom fixed at 0. Simpler dose-response.",
            "One-phase exponential decay": "Y = Plateau + (Y0 − Plateau)·e^(−K·X). Single-phase decay to a plateau.",
            "One-phase exponential growth":"Y = Plateau − (Plateau − Y0)·e^(−K·X). Single-phase association.",
            "Two-phase exponential decay": "Biphasic decay  -  fast and slow components. Adds Fraction_fast parameter.",
            "Michaelis-Menten":            "Y = Vmax·X / (Km + X). Enzyme kinetics, receptor binding.",
            "Hill equation":               "Generalised Michaelis-Menten with cooperativity exponent n.",
            "Gaussian (bell curve)":       "Symmetric bell. Amplitude, Mean, SD.",
            "Log-normal":                  "Log-normal bell curve. Peak position on log scale.",
            "Linear":                      "Y = Slope·X + Intercept.",
            "Polynomial (2nd order)":      "Y = A·X² + B·X + C.",
        }
        def _on_model_change(e=None):
            _desc_lbl.config(text=_MODEL_DESC.get(self._vars["curve_model"].get(), ""))
        _model_cb.bind("<<ComboboxSelected>>", _on_model_change)
        _on_model_change()
        r = self._sep(g, r)

        r = self._section_label(g, r, "Display")
        r = self._checkbox(g, r, "cf_show_ci",        " Show 95% confidence band")
        r = self._checkbox(g, r, "cf_show_r2",        " Show R² on plot")
        r = self._checkbox(g, r, "cf_show_params",    " Show parameter estimates on plot")
        r = self._checkbox(g, r, "cf_show_equation",  " Show equation on plot")
        r = self._checkbox(g, r, "cf_show_residuals", " Show residuals panel below plot")
        r = self._sep(g, r)
        r = self._hint(g, r, "Uses the same Excel format as Scatter  -  Col 1 is X, "
                             "remaining columns are Y replicates with series names in Row 1. "
                             "Each series is fitted independently.")
        self._tab_footer(g, r)

    # ── Stats tab: Column Statistics ─────────────────────────────────────────

    def _tab_stats_column_stats(self, f):
        self._init_vars({"cs_show_normality": True, "cs_show_ci": True, "cs_show_cv": True})
        g = f; r = 0

        r = self._section_label(g, r, "Table Contents")
        r = self._checkbox(g, r, "cs_show_ci",        " 95% Confidence Interval (low / high)")
        r = self._checkbox(g, r, "cs_show_cv",        " Coefficient of Variation (CV%)")
        r = self._checkbox(g, r, "cs_show_normality", " Shapiro-Wilk normality test")
        r = self._sep(g, r)
        r = self._hint(g, r, "Always shown: N, Mean, SD, SEM, Median, Min, Max.\n"
                             "Table rows = groups; columns = statistics.")
        self._tab_footer(g, r)

    # ── Stats tab: Contingency ───────────────────────────────────────────────

    def _tab_stats_contingency(self, f):
        self._init_vars({"ct_show_pct": True, "ct_show_expected": False})
        g = f; r = 0

        r = self._section_label(g, r, "Display")
        r = self._checkbox(g, r, "ct_show_pct",      " Show row % on bars")
        r = self._checkbox(g, r, "ct_show_expected", " Show expected counts (dashed line)")
        r = self._sep(g, r)
        r = self._hint(g, r, "2×2 tables: Fisher's exact test + Odds Ratio.\n"
                             "Larger tables: Chi-square test of independence.\n"
                             "Statistics are shown automatically on the plot.")
        self._tab_footer(g, r)

    def _tab_stats_repeated_measures(self, f):
        self._init_vars({
            "rm_show_lines": True, "show_stats": False,
            "show_p_values": False, "rm_test_type": "Parametric",
            "show_normality_warning": True,
        })
        g = f; r = 0

        r = self._section_label(g, r, "Display")
        r = self._checkbox(g, r, "rm_show_lines", " Show subject connecting lines")
        r = self._checkbox(g, r, "show_stats",    " Show significance brackets")
        r = self._checkbox(g, r, "show_p_values", " Show raw p-values (instead of stars)")
        r = self._sep(g, r)

        r = self._section_label(g, r, "Statistical Test")
        PCombobox(g, textvariable=self._vars["rm_test_type"],
                     values=["Parametric", "Non-parametric"],
                     state="readonly", width=22, font=("Helvetica Neue", 12)
                     ).grid(row=r, column=0, sticky="w", padx=PAD, pady=4); r += 1
        r = self._sep(g, r)

        r = self._section_label(g, r, "Normality Check")
        r = self._checkbox(g, r, "show_normality_warning", " Show normality warning on plot")
        r = self._sep(g, r)

        r = self._hint(g, r,
                       "Parametric: RM-ANOVA (requires pingouin) with Holm post-hoc, "
                       "or pairwise paired t-tests if pingouin is unavailable.\n\n"
                       "Non-parametric: Friedman test + Dunn's post-hoc "
                       "(Holm-Bonferroni corrected).\n\n"
                       "Each row = one subject. Subjects matched by row order.")
        self._tab_footer(g, r)

    def _tab_stats_chi_square_gof(self, f):
        """Statistics tab for Chi-Square Goodness of Fit."""
        self._init_vars({"gof_expected_equal": True})
        g = f; r = 0

        r = self._section_label(g, r, "Expected Frequencies")
        r = self._checkbox(g, r, "gof_expected_equal",
                           " Equal expected proportions (ignore Row 3)")
        r = self._hint(g, r,
                       "If unchecked, Row 3 of your spreadsheet is read as expected "
                       "proportions or counts.\n\n"
                       "Dashed bars on the plot show expected values.\n\n"
                       "Layout:\n  Row 1: category names\n"
                       "  Row 2: observed counts\n"
                       "  Row 3: expected proportions (optional)")
        self._tab_footer(g, r)




    def _tab_stats_stacked_bar(self, f):
        """Stats tab for Stacked Bar  -  stack mode, orientation (P17), labels (P18)."""
        self._init_vars({"stacked_mode": "absolute", "stacked_value_labels": False,
                         "stacked_horizontal": False, "xtick_labels_str": ""})
        g = f; r = 0
        r = self._section_label(g, r, "Stack Mode")
        PRadioGroup(g, variable=self._vars["stacked_mode"],
                    options=["absolute", "percent"],
                    ).grid(row=r, column=0, columnspan=3, sticky="w", padx=PAD, pady=4); r += 1
        r = self._hint(g, r,
                       "absolute  -  bars show raw mean values stacked.\n"
                       "percent   -  each bar normalized to 100% (proportional composition).")
        r = self._sep(g, r)
        r = self._checkbox(g, r, "stacked_value_labels", " Show value label in each segment")
        r = self._sep(g, r)
        # P17: Horizontal orientation
        r = self._section_label(g, r, "Orientation (P17)")
        r = self._checkbox(g, r, "stacked_horizontal", " Horizontal stacked bars")
        r = self._hint(g, r, "Mirrors the grouped bar horizontal option  -  bars run left-to-right.")
        r = self._sep(g, r)
        # P18: Custom x-tick labels
        r = self._section_label(g, r, "Custom Category Labels (P18)")
        ttk.Label(g, text="Override labels (comma-separated):",
                  font=("Helvetica Neue", 12)).grid(row=r, column=0, sticky="w", padx=PAD); r += 1
        _xt_e = PEntry(g, textvariable=self._vars["xtick_labels_str"], width=38)
        _xt_e.grid(row=r, column=0, columnspan=3, sticky="ew", padx=PAD, pady=2); r += 1
        add_placeholder(_xt_e, self._vars["xtick_labels_str"], "e.g. Control, Drug A, Drug B")
        r = self._hint(g, r, "Leave blank to use category names from the spreadsheet. "
                             "Must match the number of categories exactly.")
        self._tab_footer(g, r)

    def _tab_stats_bubble(self, f):
        """Stats tab for Bubble Chart  -  size scaling and labels."""
        self._init_vars({"bubble_scale": "1.0", "bubble_show_labels": False})
        g = f; r = 0
        r = self._section_label(g, r, "Bubble Sizing")
        r = self._slider(g, r, "bubble_scale", "Bubble Scale", 0.1, 5.0, ".1f", 1.0)
        r = self._sep(g, r)
        r = self._checkbox(g, r, "bubble_show_labels", " Label each bubble with its size value")
        r = self._hint(g, r,
                       "Excel layout:\n"
                       "  Row 1 : X-label | Series name(s)\n"
                       "  Rows 2+: X | Y | Size  (repeat triple per series)\n\n"
                       "Bubble area is proportional to the Size column.\n"
                       "Median size maps to a standard area; Scale adjusts all bubbles.")
        self._tab_footer(g, r)

    def _tab_stats_dot_plot(self, f):
        """Stats tab for Dot Plot  -  mean/median overlay."""
        self._init_vars({"dp_show_mean": True, "dp_show_median": False})
        g = f; r = 0
        r = self._section_label(g, r, "Summary Lines")
        r = self._checkbox(g, r, "dp_show_mean",   " Show mean line")
        r = self._checkbox(g, r, "dp_show_median", " Show median line (dashed)")
        r = self._hint(g, r,
                       "Dot plot shows individual data points jittered horizontally.\n"
                       "No bar fill  -  ideal for small samples where distribution matters.\n\n"
                       "Same Excel layout as bar chart:\n"
                       "  Row 1 : group names\n  Rows 2+: values")
        self._tab_footer(g, r)

    def _tab_stats_bland_altman(self, f):
        """Stats tab for Bland-Altman plot."""
        self._init_vars({"ba_show_ci": True})
        g = f; r = 0
        r = self._section_label(g, r, "Display")
        r = self._checkbox(g, r, "ba_show_ci",
                           " Show 95% CI bands around mean diff and limits of agreement")
        r = self._hint(g, r,
                       "Bland-Altman plot assesses agreement between two measurement methods.\n\n"
                       "X-axis: mean of the two measurements\n"
                       "Y-axis: difference (Method A − Method B)\n\n"
                       "Solid line = mean difference\n"
                       "Dashed lines = ±1.96 SD (limits of agreement)\n\n"
                       "Excel layout:\n"
                       "  Row 1 : method names (2 columns)\n"
                       "  Rows 2+: paired values per subject")
        self._tab_footer(g, r)

    def _tab_stats_forest_plot(self, f):
        """Stats tab for Forest Plot  -  reference line, weights, summary."""
        self._init_vars({
            "fp_ref_value": "0",
            "fp_show_weights": True,
            "fp_show_summary": True,
        })
        g = f; r = 0
        r = self._section_label(g, r, "Reference Line")

        ref_row = ttk.Frame(g)
        ref_row.grid(row=r, column=0, columnspan=3, sticky="w", padx=PAD, pady=4); r += 1
        ttk.Label(ref_row, text="Null value (e.g. 0 for MD, 1 for OR):",
                  font=("Helvetica Neue", 12)).pack(side="left")
        _e = PEntry(ref_row, textvariable=self._vars["fp_ref_value"],
                    width=8, font=("Menlo", 12))
        _e.pack(side="left", padx=(8, 0))
        add_placeholder(_e, self._vars["fp_ref_value"], "e.g. 0")

        r = self._sep(g, r)
        r = self._section_label(g, r, "Display")
        r = self._checkbox(g, r, "fp_show_weights", " Show weight values beside studies")
        r = self._checkbox(g, r, "fp_show_summary",
                           " Show pooled-effect summary diamond")
        r = self._hint(g, r,
                       "Excel layout (header row required):\n"
                       "  Study | Effect | CI_lo | CI_hi | Weight\n\n"
                       "Weight column is optional (uniform if absent).\n"
                       "Summary diamond = inverse-variance weighted pooled estimate.")
        self._tab_footer(g, r)

    def _tab_stats_heatmap(self, f):
        """Options tab for heatmap  -  color scale, clustering, annotations."""
        self._init_vars({
            "annotate": False, "cluster_rows": False, "cluster_cols": False,
            "robust": False, "heatmap_vmin": "", "heatmap_vmax": "",
            "heatmap_center": "", "heatmap_fmt": "",
        })
        g = f; r = 0

        r = self._section_label(g, r, "Color Map")
        _hm_color_cb = PCombobox(
            g, textvariable=self._vars["color"],
            values=["Default (Blue-Red)", "Viridis", "Mako", "Plasma",
                    "Coolwarm", "Spectral", "YlOrRd", "Blues", "Greens", "RdYlGn"],
            state="readonly", width=22, font=("Helvetica Neue", 12))
        _hm_color_cb.grid(row=r, column=0, sticky="w", padx=PAD, pady=4); r += 1
        add_placeholder(_hm_color_cb, self._vars["color"], "Default (Blue-Red)")
        r = self._sep(g, r)

        r = self._section_label(g, r, "Color Scale")
        for row_label, key, ph in [("Min", "heatmap_vmin", "auto"),
                                    ("Max", "heatmap_vmax", "auto"),
                                    ("Center", "heatmap_center", "none")]:
            fr = ttk.Frame(g)
            fr.grid(row=r, column=0, columnspan=3, sticky="w", padx=PAD, pady=2); r += 1
            ttk.Label(fr, text=f"{row_label}:", width=7,
                      font=("Helvetica Neue", 12)).pack(side="left")
            _e = PEntry(fr, textvariable=self._vars[key], width=10, font=("Menlo", 12))
            _e.pack(side="left", padx=(4, 0))
            add_placeholder(_e, self._vars[key], ph)
        r = self._checkbox(g, r, "robust", " Robust scale (2nd–98th percentile)")
        r = self._sep(g, r)

        r = self._section_label(g, r, "Annotations")
        r = self._checkbox(g, r, "annotate", " Show values in cells")
        fr_fmt = ttk.Frame(g)
        fr_fmt.grid(row=r, column=0, columnspan=3, sticky="w", padx=PAD, pady=(0, 8)); r += 1
        ttk.Label(fr_fmt, text="Format:", font=("Helvetica Neue", 12)).pack(side="left")
        _fmt_cb = PCombobox(fr_fmt, textvariable=self._vars["heatmap_fmt"],
                               values=[".2f", ".1f", ".0f", ".3f", ".2e", ".1%"],
                               state="normal", width=8, font=("Menlo", 12))
        _fmt_cb.pack(side="left", padx=(6, 0))
        add_placeholder(_fmt_cb, self._vars["heatmap_fmt"], "e.g. .2f")
        r = self._sep(g, r)

        r = self._section_label(g, r, "Clustering")
        r = self._checkbox(g, r, "cluster_rows", " Cluster rows (hierarchical)")
        r = self._checkbox(g, r, "cluster_cols", " Cluster columns (hierarchical)")
        r = self._hint(g, r, "Average-linkage Euclidean clustering. "
                             "Reorders rows/columns by similarity.")
        self._tab_footer(g, r)

    def _tab_stats_two_way_anova(self, f):
        """Stats tab for two-way ANOVA."""
        self._init_vars({
            "show_stats": False, "show_posthoc": False,
            "show_p_values": False, "show_effect_size": False,
            "show_normality_warning": True,
        })
        g = f; r = 0

        r = self._section_label(g, r, "Two-Way ANOVA")
        r = self._checkbox(g, r, "show_stats",       " Show ANOVA table on plot")
        r = self._checkbox(g, r, "show_posthoc",     " Show post-hoc brackets (pairwise t-tests, Holm corrected)")
        r = self._checkbox(g, r, "show_p_values",    " Show raw p-values (instead of stars)")
        r = self._checkbox(g, r, "show_effect_size", " Show effect size (partial η²)")
        r = self._sep(g, r)
        r = self._section_label(g, r, "Normality Check")
        r = self._checkbox(g, r, "show_normality_warning", " Show normality warning on plot")
        r = self._sep(g, r)
        r = self._hint(g, r,
                       "Type II Sum of Squares. Tests each main effect after "
                       "controlling for the other. Interaction term tests whether "
                       "the effect of Factor A differs across levels of Factor B.\n\n"
                       "Data must be in long format: one row per observation, "
                       "with separate columns for Factor A, Factor B, and Value.")
        self._tab_footer(g, r)

    # ── Help Analyze ─────────────────────────────────────────────────────────

    # Flat row-1-header charts: group names in row 0, values in rows 1+
    _HELP_ANALYZE_FLAT_MODES = {
        "bar", "box", "violin", "subcolumn_scatter", "dot_plot",
        "histogram", "column_stats", "before_after", "repeated_measures",
    }

    # Charts with full separate implementations
    _HELP_ANALYZE_FULL_MODES = {"grouped_bar", "scatter", "line", "two_way_anova"}

    # Charts where Help Analyze shows an informational panel (no live decision tree)
    _HELP_ANALYZE_INFO_MODES = {
        "kaplan_meier", "heatmap", "contingency", "chi_square_gof",
        "stacked_bar", "bubble", "bland_altman", "forest_plot", "curve_fit",
    }

