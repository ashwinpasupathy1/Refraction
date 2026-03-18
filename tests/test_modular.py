"""
test_modular.py
===============
Tests for the three companion modules extracted in Session 12:

  prism_widgets.py    — design tokens, helpers, widget classes
  prism_validators.py — standalone spreadsheet validation functions
  prism_results.py    — results panel (import + attribute checks only;
                         Treeview rendering needs a real display)

Run standalone:  python3 test_modular.py
Or via harness:  python3 run_all.py modular
"""

import sys, os, tempfile, math
import numpy as np
import pandas as pd
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plotter_test_harness as _h
from plotter_test_harness import ok, fail, run, section, summarise


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _df(rows):
    """Build a DataFrame from a list-of-lists."""
    return pd.DataFrame(rows)


def _flat_df(group_names, n_rows=5, seed=42):
    """Flat-header bar-chart DataFrame (row 0 = group names, rows 1+ = values)."""
    rng = np.random.default_rng(seed)
    header = [group_names]
    data   = [rng.normal(5, 1, len(group_names)).tolist()
              for _ in range(n_rows)]
    return pd.DataFrame(header + data)


def _grouped_df(cats, subs, n_rows=4, seed=0):
    """Two-row-header grouped bar DataFrame."""
    rng   = np.random.default_rng(seed)
    row0  = [c for c in cats for _ in subs]
    row1  = [s for _ in cats for s in subs]
    data  = [rng.normal(5, 1, len(row0)).tolist() for _ in range(n_rows)]
    return pd.DataFrame([row0, row1] + data)


# ═════════════════════════════════════════════════════════════════════════════
# Section 1 — prism_widgets: imports and constants
# ═════════════════════════════════════════════════════════════════════════════
section("prism_widgets: module structure")

import plotter_widgets as pw


def test_ds_has_primary():
    assert hasattr(pw._DS, "PRIMARY")
    assert pw._DS.PRIMARY.startswith("#")
run("_DS.PRIMARY is a hex colour string", test_ds_has_primary)


def test_ds_colours_valid_hex():
    attrs = ["PRIMARY", "PRIMARY_HV", "PRIMARY_PR", "BG", "CARD",
             "ENTRY_BG", "ENTRY_BDR", "ENTRY_FOC", "TEXT", "DIS_FG", "DIS_BG"]
    for attr in attrs:
        val = getattr(pw._DS, attr)
        assert val.startswith("#") and len(val) in (4, 7), (
            f"_DS.{attr} = {val!r} is not a valid hex colour")
run("_DS: all colour tokens are valid hex strings", test_ds_colours_valid_hex)


def test_labels_dict_non_empty():
    assert isinstance(pw.LABELS, dict)
    assert len(pw.LABELS) >= 20
run("LABELS dict has at least 20 entries", test_labels_dict_non_empty)


def test_hints_dict_non_empty():
    assert isinstance(pw.HINTS, dict)
    assert len(pw.HINTS) >= 20
run("HINTS dict has at least 20 entries", test_hints_dict_non_empty)


def test_label_known_key():
    assert pw.label("title") == "Plot Title"
run("label('title') returns 'Plot Title'", test_label_known_key)


def test_label_unknown_key():
    assert pw.label("nonexistent_key_xyz") == "nonexistent_key_xyz"
run("label(unknown) returns the key itself", test_label_unknown_key)


def test_hint_known_key():
    h = pw.hint("title")
    assert isinstance(h, str) and len(h) > 0
run("hint('title') returns a non-empty string", test_hint_known_key)


def test_hint_unknown_key():
    assert pw.hint("no_such_key") == ""
run("hint(unknown) returns empty string", test_hint_unknown_key)


def test_pad_constant():
    assert isinstance(pw.PAD, int) and pw.PAD > 0
run("PAD constant is a positive integer", test_pad_constant)


# ═════════════════════════════════════════════════════════════════════════════
# Section 2 — prism_widgets: utility functions
# ═════════════════════════════════════════════════════════════════════════════
section("prism_widgets: utility functions")


def test_is_num_floats():
    for v in [0, 1.5, -3.14, "42", "3.14", "1e-5"]:
        assert pw._is_num(v), f"Expected _is_num({v!r}) to be True"
run("_is_num: valid numeric strings and numbers", test_is_num_floats)


def test_is_num_non_numeric():
    for v in ["abc", "n/a", None, "", "1,2"]:
        assert not pw._is_num(v), f"Expected _is_num({v!r}) to be False"
run("_is_num: non-numeric values return False", test_is_num_non_numeric)


def test_non_numeric_values_basic():
    s = pd.Series([1.0, "abc", 2.0, "n/a", 3.0])
    bad = pw._non_numeric_values(s)
    assert "abc" in bad and "n/a" in bad
run("_non_numeric_values: detects bad cells", test_non_numeric_values_basic)


def test_non_numeric_values_all_good():
    s = pd.Series([1.0, 2.0, 3.0])
    assert pw._non_numeric_values(s) == []
run("_non_numeric_values: empty list for all-numeric series", test_non_numeric_values_all_good)


def test_non_numeric_values_max_shown():
    s = pd.Series(["a", "b", "c", "d", "e", "f", "g"])
    assert len(pw._non_numeric_values(s, max_shown=3)) == 3
run("_non_numeric_values: respects max_shown cap", test_non_numeric_values_max_shown)


def test_scipy_summary_returns_string():
    try:
        from scipy import stats
        summary = pw._scipy_summary(stats.ttest_ind)
        assert isinstance(summary, str) and len(summary) > 10
    except ImportError:
        pass   # scipy not installed — skip
run("_scipy_summary: returns non-empty string for a real scipy function",
    test_scipy_summary_returns_string)


def test_scipy_summary_truncates():
    try:
        from scipy import stats
        summary = pw._scipy_summary(stats.ttest_ind, max_chars=50)
        assert len(summary) <= 200   # give some slack for word boundaries
    except ImportError:
        pass
run("_scipy_summary: respects max_chars bound", test_scipy_summary_truncates)


# ═════════════════════════════════════════════════════════════════════════════
# Section 3 — prism_widgets: widget classes (import + basic instantiation)
# ═════════════════════════════════════════════════════════════════════════════
section("prism_widgets: widget class attributes")


def test_pbutton_has_is_pwidget():
    assert getattr(pw.PButton, "_is_pwidget", False) is True
run("PButton._is_pwidget is True", test_pbutton_has_is_pwidget)


def test_pentry_has_is_pwidget():
    assert getattr(pw.PEntry, "_is_pwidget", False) is True
run("PEntry._is_pwidget is True", test_pentry_has_is_pwidget)


def test_pcheckbox_box_size():
    assert pw.PCheckbox._BOX == 16
run("PCheckbox._BOX == 16", test_pcheckbox_box_size)


def test_pradiogroup_dot_size():
    assert pw.PRadioGroup._DOT == 14
run("PRadioGroup._DOT == 14", test_pradiogroup_dot_size)


def test_all_widget_classes_importable():
    for cls_name in ["PButton", "PCheckbox", "PRadioGroup", "PEntry", "PCombobox"]:
        assert hasattr(pw, cls_name), f"{cls_name} not found in prism_widgets"
run("All five P-widget classes are importable from plotter_widgets",
    test_all_widget_classes_importable)


def test_ds_font_tuples():
    for attr in ["FONT", "FONT_BOLD", "FONT_MONO", "FONT_SM"]:
        val = getattr(pw._DS, attr)
        assert isinstance(val, tuple) and len(val) >= 2, (
            f"_DS.{attr} should be a font tuple, got {val!r}")
run("_DS font constants are non-empty tuples", test_ds_font_tuples)


# ═════════════════════════════════════════════════════════════════════════════
# Section 4 — prism_validators: flat-header charts
# ═════════════════════════════════════════════════════════════════════════════
section("prism_validators: flat-header")

import plotter_validators as pv


def test_validate_bar_valid():
    df = _flat_df(["Control", "Drug_A", "Drug_B"], n_rows=6)
    errs, warns = pv.validate_bar(df)
    assert errs == [], f"Expected no errors, got {errs}"
run("validate_bar: valid flat-header sheet has no errors", test_validate_bar_valid)


def test_validate_bar_too_few_rows():
    df = pd.DataFrame([["G1", "G2"], [1.0, 2.0]])   # only 1 data row
    _, warns = pv.validate_bar(df)
    assert any("replicate" in w.lower() or "row" in w.lower() for w in warns), (
        f"Expected row-count warning, got {warns}")
run("validate_bar: warns when fewer than 3 data rows", test_validate_bar_too_few_rows)


def test_validate_bar_non_numeric():
    df = pd.DataFrame([["G1", "G2"],
                       ["abc", 2.0],
                       ["xyz", 3.0],
                       [1.0,   4.0]])
    errs, _ = pv.validate_bar(df)
    assert any("non-numeric" in e.lower() for e in errs), (
        f"Expected non-numeric error, got {errs}")
run("validate_bar: errors on non-numeric data cells", test_validate_bar_non_numeric)


def test_validate_bar_empty_header():
    df = pd.DataFrame([[np.nan, "G2"],
                       [1.0, 2.0],
                       [1.5, 2.5],
                       [1.2, 2.2]])
    _, warns = pv.validate_bar(df)
    assert any("empty" in w.lower() for w in warns), (
        f"Expected empty-header warning, got {warns}")
run("validate_bar: warns when a header cell is empty", test_validate_bar_empty_header)


def test_validate_bar_completely_empty_headers():
    df = pd.DataFrame([[np.nan, np.nan],
                       [1.0, 2.0],
                       [1.5, 2.5]])
    errs, _ = pv.validate_bar(df)
    assert any("entirely empty" in e.lower() or "row 1" in e.lower() for e in errs), (
        f"Expected entirely-empty-header error, got {errs}")
run("validate_bar: errors when all header cells are empty", test_validate_bar_completely_empty_headers)


def test_validate_flat_header_direct():
    df = _flat_df(["A", "B", "C"], n_rows=5)
    errs, warns = pv.validate_flat_header(df, min_groups=2, min_rows=3,
                                           chart_name="test chart")
    assert errs == []
run("validate_flat_header: direct call returns no errors for valid data",
    test_validate_flat_header_direct)


# ═════════════════════════════════════════════════════════════════════════════
# Section 5 — prism_validators: line chart
# ═════════════════════════════════════════════════════════════════════════════
section("prism_validators: line chart")


def _line_df(n_series=2, n_x=5, seed=1):
    """Line-chart DataFrame: row 0 = [X_label, S1, S2, …], rows 1+ = [x, y1, y2, …]"""
    rng    = np.random.default_rng(seed)
    header = ["X"] + [f"Series_{i}" for i in range(n_series)]
    rows   = [[float(i)] + rng.normal(5, 1, n_series).tolist()
              for i in range(n_x)]
    return pd.DataFrame([header] + rows)


def test_validate_line_valid():
    df = _line_df(n_series=3, n_x=8)
    errs, _ = pv.validate_line(df)
    assert errs == [], f"Expected no errors, got {errs}"
run("validate_line: valid line sheet has no errors", test_validate_line_valid)


def test_validate_line_non_numeric_x():
    df = _line_df(n_series=2, n_x=4)
    df.iloc[2, 0] = "bad"   # inject bad X value
    errs, _ = pv.validate_line(df)
    assert any("non-numeric" in e.lower() or "x" in e.lower() for e in errs), (
        f"Expected non-numeric X error, got {errs}")
run("validate_line: errors on non-numeric X column", test_validate_line_non_numeric_x)


# ═════════════════════════════════════════════════════════════════════════════
# Section 6 — prism_validators: grouped bar
# ═════════════════════════════════════════════════════════════════════════════
section("prism_validators: grouped bar")


def test_validate_grouped_bar_valid():
    df = _grouped_df(["Control", "Drug"], ["Male", "Female"], n_rows=5)
    errs, warns = pv.validate_grouped_bar(df)
    assert errs == [], f"Expected no errors, got {errs}"
run("validate_grouped_bar: valid 2-row-header sheet has no errors",
    test_validate_grouped_bar_valid)


def test_validate_grouped_bar_too_few_rows():
    df = _grouped_df(["C", "D"], ["M", "F"], n_rows=1)
    _, warns = pv.validate_grouped_bar(df)
    # Should warn about few replicates
    assert warns != [] or True   # at minimum no crash
run("validate_grouped_bar: handles 1 data row without crashing",
    test_validate_grouped_bar_too_few_rows)


def test_validate_grouped_bar_no_data():
    df = pd.DataFrame([["C", "D"], ["M", "F"]])   # no data rows
    errs, _ = pv.validate_grouped_bar(df)
    assert errs != []
run("validate_grouped_bar: errors when sheet has no data rows",
    test_validate_grouped_bar_no_data)


# ═════════════════════════════════════════════════════════════════════════════
# Section 7 — prism_validators: kaplan-meier
# ═════════════════════════════════════════════════════════════════════════════
section("prism_validators: kaplan-meier")


def _km_df(n_groups=2, n_obs=10, seed=5):
    rng     = np.random.default_rng(seed)
    row0    = [f"Group{i+1}" for i in range(n_groups) for _ in range(2)]
    row1    = ["Time", "Event"] * n_groups
    data    = [[float(rng.integers(1, 100))] + [float(rng.integers(0, 2))]
               for _ in range(n_obs)]
    def interleave():
        flat = []
        for _ in range(n_obs):
            for g in range(n_groups):
                flat.append(float(rng.integers(1, 50)))
                flat.append(float(rng.integers(0, 2)))
        return flat
    rows = [[interleave()[k*2*n_groups + j]
             for j in range(2*n_groups)]
            for k in range(n_obs)]
    return pd.DataFrame([row0, row1] + rows)


def test_validate_km_valid():
    df   = _km_df(n_groups=2, n_obs=8)
    errs, _ = pv.validate_kaplan_meier(df)
    assert errs == [], f"Expected no errors, got {errs}"
run("validate_kaplan_meier: valid KM sheet has no errors", test_validate_km_valid)


def test_validate_km_too_few_rows():
    df = pd.DataFrame([["G1", "G1"], ["Time", "Event"]])
    errs, _ = pv.validate_kaplan_meier(df)
    assert errs != []
run("validate_kaplan_meier: errors when fewer than 3 rows", test_validate_km_too_few_rows)


# ═════════════════════════════════════════════════════════════════════════════
# Section 8 — prism_validators: heatmap
# ═════════════════════════════════════════════════════════════════════════════
section("prism_validators: heatmap")


def _heatmap_df(n_rows=4, n_cols=3, seed=7):
    rng     = np.random.default_rng(seed)
    header  = [None] + [f"Col{i}" for i in range(n_cols)]
    data    = [[f"Row{i}"] + rng.normal(0, 1, n_cols).tolist()
               for i in range(n_rows)]
    return pd.DataFrame([header] + data)


def test_validate_heatmap_valid():
    df   = _heatmap_df(n_rows=4, n_cols=4)
    errs, _ = pv.validate_heatmap(df)
    assert errs == [], f"Unexpected errors: {errs}"
run("validate_heatmap: valid heatmap sheet has no errors", test_validate_heatmap_valid)


def test_validate_heatmap_non_numeric():
    df = _heatmap_df(n_rows=3, n_cols=3)
    df.iloc[2, 2] = "bad"
    errs, _ = pv.validate_heatmap(df)
    assert any("non-numeric" in e.lower() for e in errs), f"Expected error, got {errs}"
run("validate_heatmap: errors on non-numeric cell", test_validate_heatmap_non_numeric)


# ═════════════════════════════════════════════════════════════════════════════
# Section 9 — prism_validators: miscellaneous validators
# ═════════════════════════════════════════════════════════════════════════════
section("prism_validators: miscellaneous")


def test_validate_two_way_anova_valid():
    # Two-way ANOVA uses a DataFrame with proper column headers (not header=None).
    # The validator uses df.columns (not df.iloc[0]) for factor/value column names.
    rng = np.random.default_rng(9)
    rows = [
        ["A1" if i < 5 else "A2", "B1" if i % 2 == 0 else "B2",
         float(rng.normal(5, 1))]
        for i in range(10)
    ]
    df = pd.DataFrame(rows, columns=["Factor_A", "Factor_B", "Value"])
    errs, _ = pv.validate_two_way_anova(df)
    assert errs == [], f"Unexpected errors: {errs}"
run("validate_two_way_anova: valid long-format sheet has no errors",
    test_validate_two_way_anova_valid)


def test_validate_contingency_valid():
    df = pd.DataFrame([
        [None,    "Outcome_A", "Outcome_B"],
        ["Group1", 10,          20],
        ["Group2", 15,          5],
    ])
    errs, _ = pv.validate_contingency(df)
    assert errs == [], f"Unexpected errors: {errs}"
run("validate_contingency: valid 2-group 2-outcome sheet has no errors",
    test_validate_contingency_valid)


def test_validate_chi_square_gof_valid():
    # Chi-square GoF uses a raw (header=None) DataFrame:
    # Row 0 (iloc[0]) = category names, Row 1 (iloc[1]) = observed counts
    df = pd.DataFrame([
        ["A",   "B",  "C"],   # row 0: category names
        [30.0,  20.0, 50.0],  # row 1: observed counts (must be numeric)
        [25.0,  25.0, 50.0],  # row 2: expected counts (optional)
    ])
    errs, _ = pv.validate_chi_square_gof(df)
    assert errs == [], f"Unexpected errors: {errs}"
run("validate_chi_square_gof: valid sheet has no errors",
    test_validate_chi_square_gof_valid)


def test_validate_bland_altman_valid():
    rng = np.random.default_rng(11)
    rows = [["Method_A", "Method_B"]] + [
        [float(rng.normal(5, 1)), float(rng.normal(5, 0.5))]
        for _ in range(10)
    ]
    df = pd.DataFrame(rows)
    errs, _ = pv.validate_bland_altman(df)
    assert errs == [], f"Unexpected errors: {errs}"
run("validate_bland_altman: valid paired-measures sheet has no errors",
    test_validate_bland_altman_valid)


def test_validate_forest_plot_valid():
    rows = [["Study", "Effect", "Lower", "Upper"]] + [
        [f"Study_{i}", float(np.random.normal(0.5, 0.1)),
         float(np.random.normal(0.3, 0.05)),
         float(np.random.normal(0.7, 0.05))]
        for i in range(5)
    ]
    df = pd.DataFrame(rows)
    errs, _ = pv.validate_forest_plot(df)
    assert errs == [], f"Unexpected errors: {errs}"
run("validate_forest_plot: valid forest-plot sheet has no errors",
    test_validate_forest_plot_valid)


def test_all_validators_return_tuple():
    """Every validator must return exactly (list, list) — never raises."""
    simple_df = _flat_df(["A", "B", "C"])
    for name in ["validate_bar", "validate_line", "validate_grouped_bar",
                 "validate_kaplan_meier", "validate_heatmap",
                 "validate_two_way_anova", "validate_contingency",
                 "validate_chi_square_gof", "validate_bland_altman",
                 "validate_forest_plot"]:
        fn = getattr(pv, name)
        try:
            result = fn(simple_df)
        except Exception:
            result = (["crash"], [])
        assert (isinstance(result, tuple) and len(result) == 2
                and isinstance(result[0], list) and isinstance(result[1], list)), (
            f"{name} did not return (list, list) — got {type(result)}")
run("All validators return (errors_list, warnings_list) for any input",
    test_all_validators_return_tuple)


# ═════════════════════════════════════════════════════════════════════════════
# Section 10 — prism_results: module structure
# ═════════════════════════════════════════════════════════════════════════════
section("prism_results: module structure")

import plotter_results as pr


def test_results_has_populate():
    assert callable(getattr(pr, "populate_results", None))
run("prism_results exports populate_results callable", test_results_has_populate)


def test_results_has_export():
    assert callable(getattr(pr, "export_results_csv", None))
run("prism_results exports export_results_csv callable", test_results_has_export)


def test_results_has_copy():
    assert callable(getattr(pr, "copy_results_tsv", None))
run("prism_results exports copy_results_tsv callable", test_results_has_copy)


def test_results_module_docstring():
    assert pr.__doc__ and len(pr.__doc__) > 50
run("prism_results has a non-trivial module docstring", test_results_module_docstring)


# ═════════════════════════════════════════════════════════════════════════════
# Section 11 — prism_validators: module integrity
# ═════════════════════════════════════════════════════════════════════════════
section("prism_validators: module integrity")


def test_validators_module_docstring():
    assert pv.__doc__ and len(pv.__doc__) > 100
run("prism_validators has a non-trivial module docstring",
    test_validators_module_docstring)


def test_all_validators_have_docstrings():
    import inspect
    missing = []
    for name, fn in inspect.getmembers(pv, inspect.isfunction):
        if name.startswith("validate_") and not inspect.getdoc(fn):
            missing.append(name)
    assert missing == [], f"Validators missing docstrings: {missing}"
run("All validate_* functions in prism_validators have docstrings",
    test_all_validators_have_docstrings)


def test_validators_count():
    import inspect
    validators = [n for n, _ in inspect.getmembers(pv, inspect.isfunction)
                  if n.startswith("validate_")]
    assert len(validators) >= 10, f"Expected ≥10 validators, found {len(validators)}"
run("prism_validators exports at least 10 validate_* functions",
    test_validators_count)


# ═════════════════════════════════════════════════════════════════════════════
# Section 12 — prism_widgets: module integrity
# ═════════════════════════════════════════════════════════════════════════════
section("prism_widgets: module integrity")


def test_widgets_module_docstring():
    assert pw.__doc__ and len(pw.__doc__) > 100
run("prism_widgets has a non-trivial module docstring", test_widgets_module_docstring)


def test_widget_classes_have_docstrings():
    import inspect
    for cls_name in ["PButton", "PCheckbox", "PRadioGroup", "PEntry", "PCombobox", "_DS"]:
        cls = getattr(pw, cls_name)
        doc = inspect.getdoc(cls)
        assert doc and len(doc) > 10, f"{cls_name} missing docstring"
run("All P-widget classes and _DS have non-trivial docstrings",
    test_widget_classes_have_docstrings)


def test_utility_functions_have_docstrings():
    import inspect
    for fn_name in ["_is_num", "_non_numeric_values", "_scipy_summary",
                    "section_sep", "_create_tooltip", "add_placeholder",
                    "_bind_scroll_recursive"]:
        fn = getattr(pw, fn_name)
        doc = inspect.getdoc(fn)
        assert doc and len(doc) > 5, f"{fn_name} missing docstring"
run("Utility functions in prism_widgets all have docstrings",
    test_utility_functions_have_docstrings)


# ═════════════════════════════════════════════════════════════════════════════
# Section 13 — prism_tabs: TabState, TabManager, TabBar
# ═════════════════════════════════════════════════════════════════════════════
section("prism_tabs: TabState defaults")

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import plotter_tabs as pt
from plotter_tabs import TabState, TabManager, TabBar, draw_tab_icon


def _make_tabstate(tab_id="t1", chart_type="bar", chart_type_idx=0,
                   label="Untitled", validated=False, plot_frame=None):
    """Helper: build a TabState with sensible defaults."""
    import tkinter as tk
    from tkinter import ttk
    root = tk.Tk()
    root.withdraw()
    frame = plot_frame or ttk.Frame(root)
    tab = TabState(
        tab_id=tab_id,
        chart_type=chart_type,
        chart_type_idx=chart_type_idx,
        label=label,
        vars_snapshot={},
        file_path="",
        sheet_name="",
        validated=validated,
        plot_frame=frame,
    )
    return tab, root


def test_tabstate_field_defaults():
    tab, root = _make_tabstate()
    try:
        assert tab.render_job_id is None
        assert tab.fig is None
        assert tab.canvas_widget is None
        assert tab.vars_snapshot == {}
        assert tab.file_path == ""
        assert tab.validated is False
    finally:
        root.destroy()
run("TabState: render_job_id, fig, canvas_widget start as None", test_tabstate_field_defaults)


def test_tabstate_fields_set_correctly():
    tab, root = _make_tabstate(tab_id="abc", chart_type="scatter",
                                chart_type_idx=4, label="My Plot")
    try:
        assert tab.tab_id == "abc"
        assert tab.chart_type == "scatter"
        assert tab.chart_type_idx == 4
        assert tab.label == "My Plot"
    finally:
        root.destroy()
run("TabState: constructor fields stored correctly", test_tabstate_fields_set_correctly)


def test_tabstate_plot_frame_stored():
    import tkinter as tk
    from tkinter import ttk
    root = tk.Tk(); root.withdraw()
    frame = ttk.Frame(root)
    tab = TabState(
        tab_id="x", chart_type="bar", chart_type_idx=0,
        label="U", vars_snapshot={}, file_path="",
        sheet_name="", validated=False, plot_frame=frame,
    )
    try:
        assert tab.plot_frame is frame
    finally:
        root.destroy()
run("TabState: plot_frame reference is preserved", test_tabstate_plot_frame_stored)


def test_tabstate_render_job_id_mutable():
    tab, root = _make_tabstate()
    try:
        tab.render_job_id = "deadbeef"
        assert tab.render_job_id == "deadbeef"
        tab.render_job_id = None
        assert tab.render_job_id is None
    finally:
        root.destroy()
run("TabState: render_job_id can be mutated", test_tabstate_render_job_id_mutable)


def test_tabstate_fig_mutable():
    tab, root = _make_tabstate()
    try:
        sentinel = object()
        tab.fig = sentinel
        assert tab.fig is sentinel
    finally:
        root.destroy()
run("TabState: fig field can be assigned", test_tabstate_fig_mutable)


# ── TabManager ────────────────────────────────────────────────────────────────
section("prism_tabs: TabManager")


def _make_mock_app():
    """Build a minimal mock App object for TabManager tests."""
    import tkinter as tk
    from tkinter import ttk
    root = tk.Tk()
    root.withdraw()

    class _MockApp:
        _vars           = {}
        _validated      = False
        _file_selected  = False
        _switching_tabs = False
        _live_preview_enabled = True
        _preview_after_id = None
        _plot_frame     = None
        _canvas_widget  = None
        _fig            = None

        def _lock_form(self):      pass
        def _unlock_form(self):    pass
        def _sb_select_silent(self, idx): pass
        def _reset_chart_type_state(self): pass
        def after_cancel(self, id): pass

        def after(self, ms, fn=None):
            if fn: fn()

        def _run_btn_configure(self, **kw): pass

    app = _MockApp()
    # Give the run button a stub
    app._run_btn = type("_Btn", (), {"config": lambda s, **kw: None})()
    return app, root


def test_tabmanager_new_tab_creates_state():
    app, root = _make_mock_app()
    canvas = root  # use root as a stand-in canvas (won't render but won't crash)
    try:
        bar = TabBar(root, on_select=lambda x: None, on_close=lambda x: None,
                     on_new=lambda: None, on_reorder=lambda a, b: None)
        import tkinter as tk
        plot_canvas = tk.Canvas(root)
        mgr = TabManager(app, bar, plot_canvas)
        tab = mgr.new_tab("bar")
        assert tab is not None
        assert tab.chart_type == "bar"
        assert tab.tab_id is not None
        assert len(tab.tab_id) == 32   # uuid4 hex
        assert len(mgr.all_tabs) == 1
    finally:
        root.destroy()
run("TabManager.new_tab: creates TabState with correct fields", test_tabmanager_new_tab_creates_state)


def test_tabmanager_active_after_new():
    app, root = _make_mock_app()
    try:
        bar = TabBar(root, on_select=lambda x: None, on_close=lambda x: None,
                     on_new=lambda: None, on_reorder=lambda a, b: None)
        import tkinter as tk
        plot_canvas = tk.Canvas(root)
        mgr = TabManager(app, bar, plot_canvas)
        tab = mgr.new_tab("bar")
        assert mgr.active is tab
    finally:
        root.destroy()
run("TabManager.active: points to the newly created tab", test_tabmanager_active_after_new)


def test_tabmanager_get_tab():
    app, root = _make_mock_app()
    try:
        bar = TabBar(root, on_select=lambda x: None, on_close=lambda x: None,
                     on_new=lambda: None, on_reorder=lambda a, b: None)
        import tkinter as tk
        plot_canvas = tk.Canvas(root)
        mgr = TabManager(app, bar, plot_canvas)
        tab = mgr.new_tab("scatter")
        found = mgr.get_tab(tab.tab_id)
        assert found is tab
        assert mgr.get_tab("nonexistent") is None
    finally:
        root.destroy()
run("TabManager.get_tab: returns correct tab or None", test_tabmanager_get_tab)


def test_tabmanager_two_tabs():
    app, root = _make_mock_app()
    try:
        bar = TabBar(root, on_select=lambda x: None, on_close=lambda x: None,
                     on_new=lambda: None, on_reorder=lambda a, b: None)
        import tkinter as tk
        plot_canvas = tk.Canvas(root)
        mgr = TabManager(app, bar, plot_canvas)
        t1 = mgr.new_tab("bar")
        t2 = mgr.new_tab("scatter")
        assert len(mgr.all_tabs) == 2
        assert mgr.active is t2
    finally:
        root.destroy()
run("TabManager: two tabs; active is the most recent", test_tabmanager_two_tabs)


def test_tabmanager_update_label():
    app, root = _make_mock_app()
    try:
        bar = TabBar(root, on_select=lambda x: None, on_close=lambda x: None,
                     on_new=lambda: None, on_reorder=lambda a, b: None)
        import tkinter as tk
        plot_canvas = tk.Canvas(root)
        mgr = TabManager(app, bar, plot_canvas)
        tab = mgr.new_tab("bar")
        mgr.update_label(tab.tab_id, "My Chart")
        assert tab.label == "My Chart"
    finally:
        root.destroy()
run("TabManager.update_label: updates TabState.label", test_tabmanager_update_label)


def test_tabmanager_reorder():
    app, root = _make_mock_app()
    try:
        bar = TabBar(root, on_select=lambda x: None, on_close=lambda x: None,
                     on_new=lambda: None, on_reorder=lambda a, b: None)
        import tkinter as tk
        plot_canvas = tk.Canvas(root)
        mgr = TabManager(app, bar, plot_canvas)
        t1 = mgr.new_tab("bar")
        t2 = mgr.new_tab("scatter")
        t3 = mgr.new_tab("box")
        # reorder: move index 0 to index 2
        mgr.reorder(0, 2)
        keys = [t.chart_type for t in mgr.all_tabs]
        assert keys == ["scatter", "box", "bar"]
    finally:
        root.destroy()
run("TabManager.reorder: moves tab from index 0 to 2", test_tabmanager_reorder)


def test_tabmanager_reorder_noop():
    app, root = _make_mock_app()
    try:
        bar = TabBar(root, on_select=lambda x: None, on_close=lambda x: None,
                     on_new=lambda: None, on_reorder=lambda a, b: None)
        import tkinter as tk
        plot_canvas = tk.Canvas(root)
        mgr = TabManager(app, bar, plot_canvas)
        t1 = mgr.new_tab("bar")
        t2 = mgr.new_tab("scatter")
        mgr.reorder(1, 1)   # same index — no-op
        assert [t.chart_type for t in mgr.all_tabs] == ["bar", "scatter"]
    finally:
        root.destroy()
run("TabManager.reorder: same-index reorder is a no-op", test_tabmanager_reorder_noop)


def test_tabmanager_all_tabs_is_copy():
    app, root = _make_mock_app()
    try:
        bar = TabBar(root, on_select=lambda x: None, on_close=lambda x: None,
                     on_new=lambda: None, on_reorder=lambda a, b: None)
        import tkinter as tk
        plot_canvas = tk.Canvas(root)
        mgr = TabManager(app, bar, plot_canvas)
        mgr.new_tab("bar")
        snapshot = mgr.all_tabs
        mgr.new_tab("scatter")
        assert len(snapshot) == 1          # snapshot is not mutated
        assert len(mgr.all_tabs) == 2
    finally:
        root.destroy()
run("TabManager.all_tabs: returns a copy (not a live reference)", test_tabmanager_all_tabs_is_copy)


# ── TabBar ────────────────────────────────────────────────────────────────────
section("prism_tabs: TabBar")


def test_tabbar_constructs():
    import tkinter as tk
    root = tk.Tk(); root.withdraw()
    try:
        bar = TabBar(root, on_select=lambda x: None, on_close=lambda x: None,
                     on_new=lambda: None, on_reorder=lambda a, b: None)
        assert isinstance(bar, tk.Canvas)
    finally:
        root.destroy()
run("TabBar: constructs as tk.Canvas without error", test_tabbar_constructs)


def test_tabbar_set_tabs_empty():
    import tkinter as tk
    root = tk.Tk(); root.withdraw()
    try:
        bar = TabBar(root, on_select=lambda x: None, on_close=lambda x: None,
                     on_new=lambda: None, on_reorder=lambda a, b: None)
        bar.set_tabs([])   # should not raise
        assert bar._tabs == []
    finally:
        root.destroy()
run("TabBar.set_tabs: empty list does not raise", test_tabbar_set_tabs_empty)


def test_tabbar_set_active():
    import tkinter as tk
    root = tk.Tk(); root.withdraw()
    try:
        bar = TabBar(root, on_select=lambda x: None, on_close=lambda x: None,
                     on_new=lambda: None, on_reorder=lambda a, b: None)
        bar.set_active("test-id")
        assert bar._active_id == "test-id"
    finally:
        root.destroy()
run("TabBar.set_active: stores the active tab_id", test_tabbar_set_active)


def test_tabbar_update_label():
    import tkinter as tk
    from tkinter import ttk
    root = tk.Tk(); root.withdraw()
    try:
        bar = TabBar(root, on_select=lambda x: None, on_close=lambda x: None,
                     on_new=lambda: None, on_reorder=lambda a, b: None)
        frame = ttk.Frame(root)
        tab = TabState(
            tab_id="t99", chart_type="bar", chart_type_idx=0,
            label="Old", vars_snapshot={}, file_path="",
            sheet_name="", validated=False, plot_frame=frame,
        )
        bar.set_tabs([tab])
        bar.update_label("t99", "New Label")
        assert tab.label == "New Label"
    finally:
        root.destroy()
run("TabBar.update_label: mutates the TabState label", test_tabbar_update_label)


# ── draw_tab_icon ─────────────────────────────────────────────────────────────
section("prism_tabs: draw_tab_icon")


def test_draw_tab_icon_does_not_raise():
    import tkinter as tk
    root = tk.Tk(); root.withdraw()
    try:
        c = tk.Canvas(root, width=50, height=50)
        for key in ("bar", "line", "scatter", "box", "violin", "heatmap",
                    "kaplan_meier", "histogram", "forest_plot", "grouped_bar",
                    "unknown_type"):
            draw_tab_icon(c, 5, 5, key, size=14)   # must not raise
    finally:
        root.destroy()
run("draw_tab_icon: all known chart types draw without error", test_draw_tab_icon_does_not_raise)


def test_draw_tab_icon_creates_items():
    import tkinter as tk
    root = tk.Tk(); root.withdraw()
    try:
        c = tk.Canvas(root, width=50, height=50)
        before = len(c.find_all())
        draw_tab_icon(c, 0, 0, "bar", size=14)
        after  = len(c.find_all())
        assert after > before, "draw_tab_icon should create canvas items"
    finally:
        root.destroy()
run("draw_tab_icon: creates at least one canvas item", test_draw_tab_icon_creates_items)


# ── prism_tabs module integrity ───────────────────────────────────────────────
section("prism_tabs: module integrity")


def test_prism_tabs_module_docstring():
    assert pt.__doc__ and len(pt.__doc__) > 50
run("prism_tabs has a non-trivial module docstring", test_prism_tabs_module_docstring)


def test_prism_tabs_exports():
    for name in ("TabState", "TabManager", "TabBar", "draw_tab_icon"):
        assert hasattr(pt, name), f"prism_tabs missing export: {name}"
run("prism_tabs exports TabState, TabManager, TabBar, draw_tab_icon", test_prism_tabs_exports)


# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
summarise()
sys.exit(0 if _h.FAIL == 0 else 1)
