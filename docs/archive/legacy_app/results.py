"""
plotter_results.py
==================
Results panel logic for Refraction — decoupled from the App class.

The three public functions receive the ``app`` object (an App instance)
as their first argument so they can read ``app._results_inner``,
``app._results_tsv_data``, etc. without being methods of App.

Public API
----------
populate_results(app, excel_path, sheet, plot_type, kw_snapshot)
    Compute and display per-group descriptive statistics, a statistical test,
    post-hoc pairwise comparisons, and a Shapiro-Wilk normality table.
    All four tables are rendered as sortable ttk.Treeview widgets inside
    app._results_inner.  Overwrites app._results_tsv_data with a TSV snapshot
    of every table.

export_results_csv(app)
    Show a Save dialog and write the TSV data as a CSV file.

copy_results_tsv(app)
    Copy the TSV snapshot to the system clipboard.

Design notes
------------
- Functions are *best-effort*: any exception is swallowed so a bug here
  never crashes the plot.
- The Treeview tables support click-to-sort on every column.  Numeric
  columns (p-values, means, SDs) sort as floats; string columns sort
  case-insensitively.
- The panel auto-opens to 220 px on the first successful populate call.
"""

from __future__ import annotations
import logging
import numpy as np

_log = logging.getLogger(__name__)

def populate_results(app, excel_path, sheet, plot_type, kw_snapshot):
    """Compute and display per-group descriptive stats, statistical test,
    post-hoc comparisons, and normality results in the bottom results panel.
    Called from the main thread after _embed_plot succeeds."""
    try:
        import numpy as np
        pd = _pd()
        # Clear previous content
        for w in app._results_inner.winfo_children():
            w.destroy()
        app._results_tsv_data = ""

        # ── Load data ────────────────────────────────────────────────────
        # Grouped/stacked bar charts have a two-row header (category, subgroup).
        # Read with header=[0,1] to preserve that structure, then flatten the
        # MultiIndex column labels into "Category / Subgroup" keys.
        _two_row_types = ("grouped_bar", "stacked_bar")
        if plot_type in _two_row_types:
            df = pd.read_excel(excel_path, sheet_name=sheet, header=[0, 1])
            groups = {}
            for col in df.columns:
                cat, sub = str(col[0]).strip(), str(col[1]).strip()
                label = f"{cat} / {sub}"
                vals = pd.to_numeric(df[col], errors="coerce").dropna().to_numpy(dtype=float)
                if len(vals) > 0:
                    groups[label] = vals
        else:
            df = pd.read_excel(excel_path, sheet_name=sheet, header=0)
            numeric_cols = df.select_dtypes(include="number").columns.tolist()
            if not numeric_cols:
                tk.Label(app._results_inner, text="No numeric columns found.",
                         bg="#f4f7fb", fg="#888888", font=("Helvetica Neue", 11)
                         ).pack(anchor="w", padx=12, pady=8)
                return
            groups = {c: df[c].dropna().to_numpy(dtype=float)
                      for c in numeric_cols if len(df[c].dropna()) > 0}

        if not groups:
            return

        from scipy import stats as _scipy_stats

        # ── Style constants ───────────────────────────────────────────────
        HDR_BG  = "#2274A5"
        HDR_FG  = "white"
        ROW_BG  = ["#ffffff", "#eef4fb"]
        SEC_BG  = "#dde8f5"
        SEC_FG  = "#1a4f7a"
        FONT_H  = ("Helvetica Neue", 10, "bold")
        FONT_S  = ("Helvetica Neue", 11, "bold")
        FONT_D  = ("Menlo", 10)
        FONT_L  = ("Helvetica Neue", 11)
        PAD_X   = 10
        PAD_Y   = 3
        OUTER   = app._results_inner

        def _fmt(v, dec=3):
            if np.isnan(v): return " - "
            if abs(v) >= 10000 or (abs(v) < 0.001 and v != 0):
                return f"{v:.3e}"
            return f"{v:.{dec}f}"

        def _p_stars(p):
            if np.isnan(p): return "ns"
            if p < 0.0001: return "****"
            if p < 0.001:  return "***"
            if p < 0.01:   return "**"
            if p < 0.05:   return "*"
            return "ns"

        def _section_header(text):
            f = tk.Frame(OUTER, bg=SEC_BG)
            f.pack(fill="x", padx=8, pady=(10, 0))
            tk.Label(f, text=text, bg=SEC_BG, fg=SEC_FG, font=FONT_S,
                     padx=10, pady=4).pack(anchor="w")

        def _make_table(parent, headers, rows):
            """
            Render data as a ttk.Treeview table.

            Columns are auto-sized; clicking a header sorts by that column.
            Returns the Treeview widget so callers can reference it later.
            """
            frame = tk.Frame(parent, bg="#f4f7fb")
            frame.pack(fill="x", padx=8, pady=(2, 6))

            style = ttk.Style()
            style.configure("Results.Treeview",
                             rowheight=22, font=("Menlo", 10),
                             fieldbackground="#ffffff", background="#ffffff")
            style.configure("Results.Treeview.Heading",
                             font=("Helvetica Neue", 10, "bold"),
                             background=HDR_BG, foreground=HDR_FG,
                             relief="flat", padding=(PAD_X, PAD_Y))
            style.map("Results.Treeview",
                       background=[("selected", "#cce0f5")],
                       foreground=[("selected", "#000000")])

            tv = ttk.Treeview(frame, columns=headers, show="headings",
                               height=min(len(rows), 8),
                               style="Results.Treeview")

            # Column widths: first col wider, others equal
            first_w = max(110, max((len(str(r[0])) for r in rows), default=8) * 8)
            other_w = 80
            for i, h in enumerate(headers):
                w = first_w if i == 0 else other_w
                tv.heading(h, text=h,
                           command=lambda _h=h, _tv=tv: _sort_treeview(_tv, _h))
                tv.column(h, width=w, minwidth=50,
                           anchor="w" if i == 0 else "e", stretch=(i == 0))

            # Alternating row tags
            tv.tag_configure("odd",  background="#ffffff")
            tv.tag_configure("even", background="#eef4fb")

            for i, row in enumerate(rows):
                tag = "odd" if i % 2 == 0 else "even"
                tv.insert("", "end", values=row, tags=(tag,))

            tv.pack(side="left", fill="x", expand=True)

            vsb = ttk.Scrollbar(frame, orient="vertical", command=tv.yview)
            tv.configure(yscrollcommand=vsb.set)
            if len(rows) > 8:
                vsb.pack(side="right", fill="y")

            return tv

        def _sort_treeview(tv, col):
            """Toggle-sort a Treeview by column col (ascending/descending)."""
            items = [(tv.set(k, col), k) for k in tv.get_children("")]
            try:
                items.sort(key=lambda x: float(x[0].replace(" - ", "nan")
                                                   .replace("ns","1").replace("****","0.00001")
                                                   .replace("***","0.0001").replace("**","0.001")
                                                   .replace("*","0.01").split()[0]))
            except (ValueError, IndexError):
                items.sort(key=lambda x: x[0].lower())
            # Toggle direction
            _sort_key = f"_sort_{col}"
            reverse   = getattr(tv, _sort_key, False)
            if reverse:
                items.reverse()
            setattr(tv, _sort_key, not reverse)
            for i, (_, k) in enumerate(items):
                tv.move(k, "", i)
                tag = "odd" if i % 2 == 0 else "even"
                tv.item(k, tags=(tag,))

        tsv_sections = []

        # ════════════════════════════════════════════════════════════════
        # Section 1  -  Descriptive Statistics
        # ════════════════════════════════════════════════════════════════
        _section_header("  Descriptive Statistics")
        stat_keys = ["N", "Mean", "SD", "SEM", "95% CI (lo)", "95% CI (hi)",
                     "Median", "Min", "Max", "CV%", "Shapiro p"]
        desc_rows = []
        shapiro_results = {}
        for name, vals in groups.items():
            n   = len(vals)
            mn  = float(np.mean(vals))
            sd  = float(np.std(vals, ddof=1)) if n > 1 else float("nan")
            sem = sd / np.sqrt(n)             if n > 1 else float("nan")
            ci  = _scipy_stats.t.interval(0.95, df=n - 1, loc=mn, scale=sem) if n > 1 \
                  else (float("nan"), float("nan"))
            med = float(np.median(vals))
            mn_ = float(np.min(vals))
            mx  = float(np.max(vals))
            cv  = (sd / abs(mn) * 100) if mn != 0 and not np.isnan(sd) else float("nan")
            try:
                sh_p = float(_scipy_stats.shapiro(vals).pvalue) if 3 <= n <= 5000 else float("nan")
            except Exception:
                sh_p = float("nan")
            shapiro_results[name] = (float(_scipy_stats.shapiro(vals).statistic)
                                      if 3 <= n <= 5000 else float("nan"), sh_p)
            desc_rows.append([str(name), str(n), _fmt(mn), _fmt(sd), _fmt(sem),
                               _fmt(ci[0]), _fmt(ci[1]), _fmt(med),
                               _fmt(mn_), _fmt(mx), _fmt(cv, 1), _fmt(sh_p)])

        _make_table(OUTER, ["Group"] + stat_keys, desc_rows)
        tsv_sections.append("\t".join(["Group"] + stat_keys))
        for row in desc_rows:
            tsv_sections.append("\t".join(row))

        # ════════════════════════════════════════════════════════════════
        # Section 2  -  Statistical Test
        # ════════════════════════════════════════════════════════════════
        test_name = stat_str = df_str = p_str = overall_p = None
        group_arrays = list(groups.values())
        group_names  = list(groups.keys())
        n_groups = len(group_arrays)

        if n_groups >= 2:
            try:
                all_normal = all(sh_p >= 0.05 for _, sh_p in shapiro_results.values()
                                 if not np.isnan(sh_p))
                if n_groups == 2:
                    a, b = group_arrays[0], group_arrays[1]
                    if all_normal:
                        t_stat, p_val = _scipy_stats.ttest_ind(a, b)
                        test_name = "Two-sample t-test (Welch)"
                        stat_str  = f"t = {t_stat:.4f}"
                        dof = (a.var(ddof=1)/len(a) + b.var(ddof=1)/len(b))**2 / \
                              ((a.var(ddof=1)/len(a))**2/(len(a)-1) + (b.var(ddof=1)/len(b))**2/(len(b)-1))
                        df_str = f"{dof:.1f}"
                    else:
                        u_stat, p_val = _scipy_stats.mannwhitneyu(a, b, alternative="two-sided")
                        test_name = "Mann-Whitney U test"
                        stat_str  = f"U = {u_stat:.1f}"
                        df_str    = " - "
                else:
                    if all_normal:
                        f_stat, p_val = _scipy_stats.f_oneway(*group_arrays)
                        test_name = "One-way ANOVA"
                        stat_str  = f"F = {f_stat:.4f}"
                        n_total   = sum(len(v) for v in group_arrays)
                        df_str    = f"{n_groups - 1}, {n_total - n_groups}"
                    else:
                        h_stat, p_val = _scipy_stats.kruskal(*group_arrays)
                        test_name = "Kruskal-Wallis H test"
                        stat_str  = f"H = {h_stat:.4f}"
                        df_str    = f"{n_groups - 1}"
                overall_p = p_val
                p_str = f"{p_val:.4f}" if p_val >= 0.0001 else f"{p_val:.3e}"

                _section_header("  Statistical Test")
                test_rows = [[test_name, stat_str, df_str, p_str, _p_stars(p_val)]]
                _make_table(OUTER, ["Test", "Statistic", "df", "p-value", "Sig."], test_rows)
                tsv_sections.append("")
                tsv_sections.append("\t".join(["Test", "Statistic", "df", "p-value", "Sig."]))
                tsv_sections.append("\t".join(test_rows[0]))
            except Exception:
                _log.debug("populate_results: statistical test section failed", exc_info=True)

        # ════════════════════════════════════════════════════════════════
        # Section 3  -  Post-hoc Pairwise Comparisons (3+ groups only)
        # ════════════════════════════════════════════════════════════════
        if n_groups >= 3 and overall_p is not None:
            try:
                from itertools import combinations
                pairs = list(combinations(range(n_groups), 2))
                raw_ps = []
                delta_means = []
                for i, j in pairs:
                    a, b = group_arrays[i], group_arrays[j]
                    if all_normal:
                        _, rp = _scipy_stats.ttest_ind(a, b)
                    else:
                        _, rp = _scipy_stats.mannwhitneyu(a, b, alternative="two-sided")
                    raw_ps.append(rp)
                    delta_means.append(float(np.mean(a)) - float(np.mean(b)))

                # Holm-Bonferroni correction
                sorted_idx = sorted(range(len(raw_ps)), key=lambda i: raw_ps[i])
                adj_ps = [0.0] * len(raw_ps)
                m = len(raw_ps)
                for rank, idx in enumerate(sorted_idx):
                    adj_ps[idx] = min(1.0, raw_ps[idx] * (m - rank))

                ph_rows = []
                for k, (i, j) in enumerate(pairs):
                    ap = adj_ps[k]
                    ph_rows.append([
                        str(group_names[i]),
                        str(group_names[j]),
                        _fmt(delta_means[k]),
                        f"{raw_ps[k]:.4f}" if raw_ps[k] >= 0.0001 else f"{raw_ps[k]:.3e}",
                        f"{ap:.4f}" if ap >= 0.0001 else f"{ap:.3e}",
                        _p_stars(ap)
                    ])

                _section_header("  Post-hoc Pairwise Comparisons  (Holm-Bonferroni corrected)")
                _make_table(OUTER, ["Group A", "Group B", "Δ Mean",
                                    "Raw p", "Adj. p", "Sig."], ph_rows)
                tsv_sections.append("")
                tsv_sections.append("\t".join(["Group A", "Group B", "Δ Mean",
                                                "Raw p", "Adj. p", "Sig."]))
                for row in ph_rows:
                    tsv_sections.append("\t".join(row))
            except Exception:
                _log.debug("populate_results: post-hoc comparisons section failed", exc_info=True)

        # ════════════════════════════════════════════════════════════════
        # Section 4  -  Normality (Shapiro-Wilk)
        # ════════════════════════════════════════════════════════════════
        if shapiro_results:
            try:
                norm_rows = []
                for name, (w_stat, sh_p) in shapiro_results.items():
                    result = "Pass ✓" if (not np.isnan(sh_p) and sh_p >= 0.05) \
                             else ("Fail ✗" if not np.isnan(sh_p) else " - ")
                    norm_rows.append([str(name), _fmt(w_stat, 4),
                                       f"{sh_p:.4f}" if not np.isnan(sh_p) else " - ",
                                       result])
                _section_header("  Normality  (Shapiro-Wilk,  α = 0.05)")
                _make_table(OUTER, ["Group", "W", "p-value", "Normal?"], norm_rows)
                tsv_sections.append("")
                tsv_sections.append("\t".join(["Group", "W", "p-value", "Normal?"]))
                for row in norm_rows:
                    tsv_sections.append("\t".join(row))
            except Exception:
                _log.debug("populate_results: normality section failed", exc_info=True)

        # ── Store TSV for copy ────────────────────────────────────────────
        app._results_tsv_data = "\n".join(tsv_sections)

        # ── Auto-show / update the panel ─────────────────────────────────
        n_g   = len(groups)
        label = f"▼ Results  ({n_g} group{'s' if n_g != 1 else ''})"
        if not app._results_visible:
            # Auto-open to a comfortable height (220 px) on first plot
            app._results_strip.config(height=220)
            app._results_toggle_arrow.config(text=label)
            app._results_visible = True
        else:
            app._results_toggle_arrow.config(text=label)
        # Reflect group count in the main status bar too
        app._set_status(
            f"Done  ·  {n_g} group{'s' if n_g != 1 else ''}  ·  "
            f"results panel updated")

    except Exception:
        _log.debug("populate_results: unhandled error in results panel", exc_info=True)
        # results panel is best-effort — never crash the plot




def export_results_csv(app):
    """Export the results table as a CSV file (replaces Copy TSV)."""
    data = getattr(app, "_results_tsv_data", "")
    if not data:
        app._set_status("No results to export yet  -  generate a plot first.", err=True)
        return
    from tkinter import filedialog
    path = filedialog.asksaveasfilename(
        title="Save Results as CSV",
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        initialfile="refraction_results.csv"
    )
    if not path:
        return
    try:
        # TSV data uses tabs  -  convert to commas for CSV
        csv_data = data.replace("\t", ",")
        with open(path, "w", newline="", encoding="utf-8") as fh:
            fh.write(csv_data)
        app._set_status(f"Results saved: {path}")
    except Exception as exc:
        app._set_status(f"Export error: {exc}", err=True)



def copy_results_tsv(app):
    """Copy the results table as tab-separated text."""
    data = getattr(app, "_results_tsv_data", "")
    if data:
        app.clipboard_clear()
        app.clipboard_append(data)
        app._set_status("Results copied as TSV ✓")


