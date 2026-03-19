"""
plotter_comparisons.py
======================
Custom pairwise comparison selection for statistical brackets.
Enables users to choose exactly which group pairs to test,
similar to a comparison selector in statistical software.
"""
from dataclasses import dataclass, field
from itertools import combinations
from typing import Optional
import tkinter as tk
from tkinter import ttk


@dataclass
class ComparisonSpec:
    """One pairwise comparison."""
    group_a: str
    group_b: str
    enabled: bool = True


@dataclass
class ComparisonSet:
    """Full comparison configuration for a plot."""
    mode: str = "all_pairwise"  # "all_pairwise" | "vs_control" | "custom"
    control: Optional[str] = None
    pairs: list = field(default_factory=list)  # list of ComparisonSpec

    def enabled_pairs(self) -> list:
        """Return [(group_a, group_b), ...] for enabled pairs only."""
        return [(c.group_a, c.group_b) for c in self.pairs if c.enabled]

    def to_dict(self) -> dict:
        """Serialize for .cplot files."""
        return {
            "mode": self.mode,
            "control": self.control,
            "pairs": [
                {"group_a": c.group_a, "group_b": c.group_b,
                 "enabled": c.enabled}
                for c in self.pairs
            ]
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ComparisonSet":
        """Deserialize from .cplot files."""
        cs = cls(mode=d.get("mode", "all_pairwise"),
                 control=d.get("control"))
        for p in d.get("pairs", []):
            cs.pairs.append(ComparisonSpec(
                group_a=p["group_a"], group_b=p["group_b"],
                enabled=p.get("enabled", True)))
        return cs

    @classmethod
    def from_groups(cls, group_names: list, mode: str = "all_pairwise"):
        """Generate all possible pairs from group names."""
        pairs = [ComparisonSpec(a, b)
                 for a, b in combinations(group_names, 2)]
        return cls(mode=mode, pairs=pairs)

    def set_mode(self, mode: str, control: str = None):
        """Switch mode and update enabled flags accordingly."""
        self.mode = mode
        self.control = control
        if mode == "all_pairwise":
            for p in self.pairs:
                p.enabled = True
        elif mode == "vs_control" and control:
            for p in self.pairs:
                p.enabled = (p.group_a == control or
                             p.group_b == control)
        # "custom" mode: leave enabled flags as-is


class ComparisonSelector:
    """Tkinter dialog for selecting which comparisons to make.

    Shows an upper-triangle matrix of checkboxes (groups x groups).
    Mode radio buttons: All pairwise / Each vs control / Custom.
    Select All / Clear All / Apply buttons.
    """

    def __init__(self, parent, group_names: list,
                 current: ComparisonSet = None):
        """
        parent: tk widget (parent window)
        group_names: list of group name strings
        current: existing ComparisonSet to pre-populate, or None
        """
        self.result = None  # Set to ComparisonSet when user clicks Apply
        self._group_names = group_names

        if current is None:
            self._comp = ComparisonSet.from_groups(group_names)
        else:
            self._comp = current

        self._build_dialog(parent)

    def _build_dialog(self, parent):
        """Build the Toplevel dialog window."""
        self._win = tk.Toplevel(parent)
        self._win.title("Custom Comparisons")
        self._win.transient(parent)
        self._win.grab_set()

        # Size based on number of groups
        n = len(self._group_names)
        width = max(400, 120 + n * 80)
        height = max(350, 180 + n * 40)
        self._win.geometry(f"{width}x{height}")

        # Mode selection frame at top
        mode_fr = ttk.LabelFrame(self._win, text="Comparison Mode")
        mode_fr.pack(fill="x", padx=10, pady=5)

        self._mode_var = tk.StringVar(value=self._comp.mode)
        for mode, label in [("all_pairwise", "All pairwise"),
                            ("vs_control", "Each vs. control"),
                            ("custom", "Custom selection")]:
            rb = ttk.Radiobutton(mode_fr, text=label, value=mode,
                                 variable=self._mode_var,
                                 command=self._on_mode_change)
            rb.pack(side="left", padx=10, pady=5)

        # Control group selector (visible only in vs_control mode)
        ctrl_fr = ttk.Frame(self._win)
        ctrl_fr.pack(fill="x", padx=10)
        self._ctrl_label = ttk.Label(ctrl_fr, text="Control group:")
        self._ctrl_combo = ttk.Combobox(ctrl_fr, values=self._group_names,
                                         state="readonly", width=20)
        if self._comp.control and self._comp.control in self._group_names:
            self._ctrl_combo.set(self._comp.control)
        elif self._group_names:
            self._ctrl_combo.set(self._group_names[0])
        self._ctrl_combo.bind("<<ComboboxSelected>>", self._on_control_change)
        self._ctrl_fr = ctrl_fr

        # Matrix frame
        matrix_fr = ttk.LabelFrame(self._win, text="Select Pairs")
        matrix_fr.pack(fill="both", expand=True, padx=10, pady=5)

        # Build upper-triangle checkbox matrix
        self._check_vars = {}
        groups = self._group_names

        # Header row
        for j, name in enumerate(groups):
            lbl = ttk.Label(matrix_fr, text=name, font=("Helvetica", 10, "bold"))
            lbl.grid(row=0, column=j+1, padx=4, pady=2)

        for i, name_a in enumerate(groups):
            lbl = ttk.Label(matrix_fr, text=name_a,
                           font=("Helvetica", 10, "bold"))
            lbl.grid(row=i+1, column=0, padx=4, pady=2, sticky="e")
            for j, name_b in enumerate(groups):
                if j <= i:
                    # Diagonal or lower triangle: dash
                    ttk.Label(matrix_fr, text="\u2014", foreground="gray").grid(
                        row=i+1, column=j+1, padx=4, pady=2)
                else:
                    # Upper triangle: checkbox
                    var = tk.BooleanVar(value=True)
                    # Find matching pair
                    for p in self._comp.pairs:
                        if ((p.group_a == name_a and p.group_b == name_b) or
                            (p.group_a == name_b and p.group_b == name_a)):
                            var.set(p.enabled)
                            break
                    cb = ttk.Checkbutton(matrix_fr, variable=var,
                                         command=self._on_check_change)
                    cb.grid(row=i+1, column=j+1, padx=4, pady=2)
                    self._check_vars[(name_a, name_b)] = var

        # Count label
        self._count_var = tk.StringVar()
        self._update_count()
        ttk.Label(self._win, textvariable=self._count_var).pack(pady=2)

        # Buttons
        btn_fr = ttk.Frame(self._win)
        btn_fr.pack(fill="x", padx=10, pady=10)
        ttk.Button(btn_fr, text="Select All",
                   command=self._select_all).pack(side="left", padx=5)
        ttk.Button(btn_fr, text="Clear All",
                   command=self._clear_all).pack(side="left", padx=5)
        ttk.Button(btn_fr, text="Cancel",
                   command=self._win.destroy).pack(side="right", padx=5)
        ttk.Button(btn_fr, text="Apply & Close",
                   command=self._apply).pack(side="right", padx=5)

        self._on_mode_change()

    def _on_mode_change(self):
        mode = self._mode_var.get()
        if mode == "vs_control":
            self._ctrl_label.pack(side="left", padx=5)
            self._ctrl_combo.pack(side="left", padx=5)
            self._on_control_change()
        else:
            self._ctrl_label.pack_forget()
            self._ctrl_combo.pack_forget()

        if mode == "all_pairwise":
            self._select_all()
        elif mode == "custom":
            pass  # leave as-is

    def _on_control_change(self, event=None):
        control = self._ctrl_combo.get()
        for (a, b), var in self._check_vars.items():
            var.set(a == control or b == control)
        self._update_count()

    def _on_check_change(self):
        self._mode_var.set("custom")
        self._update_count()

    def _select_all(self):
        for var in self._check_vars.values():
            var.set(True)
        self._update_count()

    def _clear_all(self):
        for var in self._check_vars.values():
            var.set(False)
        self._update_count()

    def _update_count(self):
        enabled = sum(1 for v in self._check_vars.values() if v.get())
        total = len(self._check_vars)
        self._count_var.set(f"Selected: {enabled} of {total} comparisons")

    def _apply(self):
        for (a, b), var in self._check_vars.items():
            for p in self._comp.pairs:
                if ((p.group_a == a and p.group_b == b) or
                    (p.group_a == b and p.group_b == a)):
                    p.enabled = var.get()
                    break
        self._comp.mode = self._mode_var.get()
        if self._comp.mode == "vs_control":
            self._comp.control = self._ctrl_combo.get()
        self.result = self._comp
        self._win.destroy()
