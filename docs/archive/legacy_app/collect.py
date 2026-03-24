"""Data collection mixin — assembles kwargs from UI variables."""

import tkinter as tk


class CollectMixin:
    """Extracted from plotter_barplot_app.py."""

    def _get_float(self, key: str, default: float) -> float:
        """Get a float from a tkvar, returning default on any conversion failure."""
        try:
            return float(self._get_var(key, str(default)))
        except (ValueError, TypeError):
            return default

    def _get_var(self, key, default=None):
        """Safely get a tkvar value, returning default if not present."""
        v = self._vars.get(key)
        if v is None:
            if default is None:
                return None
            if isinstance(default, bool):
                v = tk.BooleanVar(value=default)
            elif isinstance(default, int):
                v = tk.IntVar(value=default)
            else:
                v = tk.StringVar(value=str(default))
        return v.get()

    # ── Collect helpers  -  each gathers one logical group of kwargs ────────────

    def _collect_display(self, kw: dict):
        """Populate display/rendering kwargs from UI vars."""
        kw["error"]         = ERROR_TYPE_MAP.get(self._vars["error"].get(),
                                                   self._vars["error"].get())
        kw["show_points"]      = self._vars["show_points"].get()
        kw["show_n_labels"]    = self._vars["show_n_labels"].get()
        kw["show_value_labels"] = self._get_var("show_value_labels", False)
        kw["error_below_bar"] = self._get_var("error_below_bar", False)
        kw["gridlines"]       = self._get_var("gridlines", False)  # legacy compat
        # Grid style  -  "None"/"Horizontal"/"Full (H + V)"  ->  "none"/"horizontal"/"full"
        _gs_map = {"None": "none", "Horizontal": "horizontal", "Full (H + V)": "full"}
        raw_gs = self._get_var("grid_style", "None")
        kw["grid_style"] = _gs_map.get(raw_gs, "none")
        # Keep legacy gridlines bool in sync for functions that still check it
        kw["gridlines"]  = kw["grid_style"] != "none"
        kw["open_points"]   = self._get_var("open_points", False)
        kw["horizontal"]    = self._get_var("horizontal", False)
        kw["show_median"]   = self._get_var("show_median", False)
        kw["notch"]         = self._get_var("notch_box", False)
        kw["alpha"]         = self._get_float("bar_alpha", 0.85)
        kw["xscale"]        = "log" if self._get_var("xscale", "Linear") == "Log" else "linear"

        # ── Priority-1 styling params ─────────────────────────────────────────
        from refraction.core.chart_helpers import AXIS_STYLES, TICK_DIRS, LEGEND_POSITIONS
        raw_axis  = self._get_var("axis_style",  "Open (default)")
        raw_tick  = self._get_var("tick_dir",    "Outward (default)")
        raw_leg   = self._get_var("legend_pos",  "Upper right")
        kw["axis_style"]  = AXIS_STYLES.get(raw_axis,  "open")
        kw["tick_dir"]    = TICK_DIRS.get(raw_tick,    "out")
        kw["minor_ticks"] = self._get_var("minor_ticks", False)
        kw["point_size"]  = self._get_float("point_size",  6.0)
        kw["point_alpha"] = self._get_float("point_alpha", 0.80)
        kw["cap_size"]    = self._get_float("cap_size",    4.0)
        kw["legend_pos"]  = LEGEND_POSITIONS.get(raw_leg, "upper right")
        kw["spine_width"] = self._get_float("spine_width", 0.8)

        # Background color
        FIG_BG_MAP = {
            "White":       "white",
            "Light gray":  "#f5f5f5",
            "Transparent": "none",
            "Black":       "black",
        }
        raw_bg = self._get_var("fig_bg", "White")
        kw["fig_bg"] = FIG_BG_MAP.get(raw_bg, raw_bg.lower() if raw_bg else "white")

        cr = self._vars["color"].get().strip()
        if not cr or cr.lower() in ("none", "default (prism)"):
            kw["color"] = None
        elif cr.startswith("["):
            try:
                kw["color"] = json.loads(cr)
            except Exception:
                messagebox.showerror("Invalid color", f"Cannot parse: {cr}")
                return False
        else:
            kw["color"] = cr.strip("\"'")
        return True

    def _collect_labels(self, kw: dict):
        """Populate title/axis label kwargs."""
        for k in ("title", "xlabel", "ytitle"):
            kw[k] = self._vars[k].get().strip()
        kw["yscale"] = "log" if self._vars["yscale"].get() == "Log" else "linear"

        ylim_mode = self._get_var("ylim_mode", 0)
        if ylim_mode == 0:   # Auto
            kw["ylim"]           = None
            kw["_ylim_data_min"] = False
        elif ylim_mode == 1:  # Start at data min
            kw["ylim"]           = None
            kw["_ylim_data_min"] = True
        else:                 # Manual range
            kw["_ylim_data_min"] = False
            try:
                kw["ylim"] = (float(self._vars["ylim_lo"].get()),
                               float(self._vars["ylim_hi"].get()))
            except ValueError:
                messagebox.showerror("Invalid Y limits", "Enter numbers for both Y limit fields.")
                return False

        # X limits  -  only collected when continuous-x tab built the fields
        xlim_mode = self._get_var("xlim_mode", 0)
        if xlim_mode == 1 and hasattr(self, "_xl_lo"):
            try:
                kw["_xlim"] = (float(self._vars["xlim_lo"].get()),
                               float(self._vars["xlim_hi"].get()))
            except ValueError:
                messagebox.showerror("Invalid X limits", "Enter numbers for both X limit fields.")
                return False
        else:
            kw["_xlim"] = None

        kw["ref_line"] = None
        if self._vars["ref_line_enabled"].get():
            try:
                kw["ref_line"] = float(self._vars["ref_line_y"].get())
            except ValueError:
                pass
        kw["ref_line_label"] = (self._vars["ref_line_label"].get().strip()
                                if "ref_line_label" in self._vars else "")

        # Tick intervals  -  convert blank/invalid entries to 0 (= auto)
        def _parse_interval(key):
            raw = self._get_var(key, "").strip()
            try:
                v = float(raw)
                return v if v > 0 else 0.0
            except (ValueError, TypeError):
                return 0.0
        kw["ytick_interval"] = _parse_interval("ytick_interval")
        kw["xtick_interval"] = _parse_interval("xtick_interval")
        return True

    def _collect_stats(self, kw: dict):
        """Populate statistics kwargs."""
        kw["show_stats"]             = self._vars["show_stats"].get()
        kw["show_ns"]                = self._vars["show_ns"].get()
        kw["show_p_values"]          = self._vars["show_p_values"].get()
        kw["show_effect_size"]       = self._vars["show_effect_size"].get()
        kw["show_test_name"]         = self._vars["show_test_name"].get()
        kw["show_normality_warning"] = self._get_var("show_normality_warning", True)
        kw["stats_test"]       = STATS_TEST_MAP.get(self._vars["stats_test"].get(),
                                                     self._vars["stats_test"].get())
        kw["mc_correction"]    = self._vars["mc_correction"].get()
        kw["posthoc"]          = self._vars["posthoc"].get()
        try:
            kw["n_permutations"] = int(self._vars["n_permutations"].get())
        except ValueError:
            kw["n_permutations"] = 9999

        # Significance threshold  -  default 0.05 (Prism standard α)
        try:
            raw = self._vars["p_sig_threshold"].get().strip()
            kw["p_sig_threshold"] = float(raw) if raw else 0.05
        except (ValueError, TypeError):
            kw["p_sig_threshold"] = 0.05

        # Comparison mode: 0 = all pairwise, 1 = vs. control
        # When mode is 0 (all pairwise) we always pass control=None regardless
        # of what the dropdown says  -  matches Prism's explicit comparison selector.
        cmode = self._get_var("comparison_mode", 0)
        if cmode == 1:
            ctrl = self._vars["control"].get().strip()
            kw["control"] = (None if (not ctrl or ctrl.startswith("(none"))
                             else ctrl)
        else:
            kw["control"] = None

        # One-sample mu0
        try:
            kw["mu0"] = float(self._get_var("one_sample_mu0", "0") or 0)
        except (ValueError, TypeError):
            kw["mu0"] = 0.0

        # P16: bracket style
        _bs_map = {"Lines": "lines", "Bracket": "bracket", "Asterisks only": "asterisks_only"}
        kw["bracket_style"] = _bs_map.get(self._get_var("bracket_style", "Lines"), "lines")

    def _collect_figsize(self, kw: dict):
        """Populate figsize and chart-geometry kwargs."""
        try:
            fw = self._vars["figw"].get().strip()
            fh = self._vars["figh"].get().strip()
            if fw and fh:
                kw["figsize"] = (float(fw), float(fh))
            else:
                pane_w = max(300, self._plot_canvas.winfo_width()  or 600)
                pane_h = max(300, self._plot_canvas.winfo_height() or 600)
                side   = round(min(pane_w * 0.88 / 120, pane_h * 0.82 / 120, 7.0), 1)
                kw["figsize"] = (side, side)
        except (ValueError, TypeError):
            kw["figsize"] = (5.0, 5.0)

        if self._plot_type.get() in ("bar", "grouped_bar", "box"):
            kw["bar_width"] = self._get_float("bar_width", 0.6)
        else:
            kw["line_width"]   = self._get_float("line_width", 1.5)
            kw["marker_style"] = MARKER_STYLE_MAP.get(
                self._get_var("marker_style", "Different Markers"), "auto")
            kw["marker_size"]  = self._get_float("marker_size", 7.0)

        kw["font_size"]     = self._get_float("font_size", 12.0)
        kw["jitter_amount"] = self._get_float("jitter_amount", 0.0)

    def _collect(self, excel):
        """Assemble the full kwargs dict for the plot function."""
        sr = self._vars["sheet"].get().strip()
        kw = {
            "excel_path": excel,
            "sheet": int(sr) if sr.lstrip("-").isdigit() else (sr if sr else 0),
        }
        if not self._collect_display(kw): return None
        if not self._collect_labels(kw):  return None
        self._collect_stats(kw)
        self._collect_figsize(kw)
        return kw

