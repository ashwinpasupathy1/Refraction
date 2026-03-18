"""
test_phase2_infra.py
====================
Tests for Phase 2 infrastructure modules:
  plotter_undo, plotter_events, plotter_session,
  plotter_presets, plotter_errors, plotter_project,
  plotter_registry, plotter_types

No Tk / display required.

Run:
  python3 tests/test_phase2_infra.py
"""

import sys, os, json, tempfile, shutil

# tests/ directory (for plotter_test_harness) and project root (for modules)
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, ".."))
import plotter_test_harness as _h
from plotter_test_harness import run, section, summarise


# ---------------------------------------------------------------------------
# Helpers — lightweight stand-ins for tkinter StringVar / BooleanVar
# ---------------------------------------------------------------------------

class _Var:
    """Minimal .get() / .set() stand-in for tk.StringVar / BooleanVar."""
    def __init__(self, value=None):
        self._value = value

    def get(self):
        return self._value

    def set(self, v):
        self._value = v


# ===========================================================================
# 1. plotter_undo
# ===========================================================================

section("plotter_undo")

from plotter_undo import Command, CompoundCommand, UndoStack


def test_undo_basic_push_and_undo():
    stack = UndoStack()
    var = _Var("old")
    cmd = Command(description="change color", var_key="color",
                  old_value="old", new_value="blue")
    app_vars = {"color": var}
    stack.record(cmd)
    assert stack.can_undo
    stack.undo(app_vars)
    assert var.get() == "old"

run("UndoStack: push command then undo restores old value", test_undo_basic_push_and_undo)


def test_undo_redo():
    stack = UndoStack()
    var = _Var("old")
    cmd = Command(description="change", var_key="v", old_value="old", new_value="new")
    app_vars = {"v": var}
    stack.record(cmd)
    stack.undo(app_vars)
    assert var.get() == "old"
    assert stack.can_redo
    stack.redo(app_vars)
    assert var.get() == "new"

run("UndoStack: redo re-applies command after undo", test_undo_redo)


def test_undo_empty_does_not_crash():
    stack = UndoStack()
    result = stack.undo({})
    assert result is None
    assert not stack.can_undo

run("UndoStack: undo on empty stack returns None without crashing", test_undo_empty_does_not_crash)


def test_redo_empty_does_not_crash():
    stack = UndoStack()
    result = stack.redo({})
    assert result is None
    assert not stack.can_redo

run("UndoStack: redo on empty stack returns None without crashing", test_redo_empty_does_not_crash)


def test_undo_clears_redo_on_new_record():
    stack = UndoStack()
    var = _Var("a")
    app_vars = {"v": var}
    cmd1 = Command("c1", "v", "a", "b")
    cmd2 = Command("c2", "v", "b", "c")
    stack.record(cmd1)
    stack.undo(app_vars)
    assert stack.can_redo
    stack.record(cmd2)
    assert not stack.can_redo

run("UndoStack: recording new command clears redo history", test_undo_clears_redo_on_new_record)


def test_undo_max_depth():
    stack = UndoStack(max_depth=3)
    for i in range(10):
        stack.record(Command(f"cmd{i}", "v", i, i + 1))
    assert len(stack._undo) <= 3

run("UndoStack: honours max_depth limit", test_undo_max_depth)


def test_undo_description():
    stack = UndoStack()
    cmd = Command("set title", "title", "old", "new")
    stack.record(cmd)
    assert stack.undo_description == "set title"
    assert stack.redo_description is None

run("UndoStack: undo_description returns top command label", test_undo_description)


def test_compound_command():
    stack = UndoStack()
    var_a = _Var("a_old")
    var_b = _Var("b_old")
    app_vars = {"a": var_a, "b": var_b}
    stack.begin_compound("multi-change")
    stack.record(Command("set a", "a", "a_old", "a_new"))
    stack.record(Command("set b", "b", "b_old", "b_new"))
    stack.end_compound()
    assert len(stack._undo) == 1
    assert isinstance(stack._undo[0], CompoundCommand)
    stack.undo(app_vars)
    assert var_a.get() == "a_old"
    assert var_b.get() == "b_old"

run("CompoundCommand: groups multiple commands and reverses them together", test_compound_command)


def test_compound_command_empty_produces_no_entry():
    stack = UndoStack()
    stack.begin_compound("empty")
    stack.end_compound()
    assert len(stack._undo) == 0

run("CompoundCommand: empty compound produces no undo entry", test_compound_command_empty_produces_no_entry)


def test_command_apply_and_reverse():
    var = _Var("original")
    cmd = Command("test", "v", "original", "modified")
    app_vars = {"v": var}
    cmd.apply(app_vars)
    assert var.get() == "modified"
    cmd.reverse(app_vars)
    assert var.get() == "original"

run("Command: apply/reverse directly manipulate var", test_command_apply_and_reverse)


def test_command_missing_var_key_does_not_crash():
    cmd = Command("test", "nonexistent", "old", "new")
    cmd.apply({})   # should not raise
    cmd.reverse({}) # should not raise

run("Command: missing var key in app_vars does not crash", test_command_missing_var_key_does_not_crash)


# ===========================================================================
# 2. plotter_events
# ===========================================================================

section("plotter_events")

from plotter_events import (
    EventBus,
    FILE_LOADED, PLOT_FINISHED, PLOT_FAILED, SETTINGS_CHANGED,
)


def test_event_subscribe_and_emit():
    bus = EventBus()
    calls = []
    bus.on(FILE_LOADED, lambda path="": calls.append(path))
    bus.emit(FILE_LOADED, path="/tmp/data.xlsx")
    assert calls == ["/tmp/data.xlsx"]

run("EventBus: subscribe and emit delivers payload", test_event_subscribe_and_emit)


def test_event_multiple_subscribers():
    bus = EventBus()
    log = []
    bus.on(PLOT_FINISHED, lambda: log.append("a"))
    bus.on(PLOT_FINISHED, lambda: log.append("b"))
    bus.emit(PLOT_FINISHED)
    assert len(log) == 2

run("EventBus: multiple subscribers all receive the event", test_event_multiple_subscribers)


def test_event_unsubscribe():
    bus = EventBus()
    log = []
    unsub = bus.on(PLOT_FINISHED, lambda: log.append(1))
    bus.emit(PLOT_FINISHED)
    unsub()
    bus.emit(PLOT_FINISHED)
    assert log == [1]

run("EventBus: unsubscribe prevents further delivery", test_event_unsubscribe)


def test_event_no_subscribers_does_not_crash():
    bus = EventBus()
    bus.emit("completely_unknown_event", foo="bar")

run("EventBus: emitting with no subscribers does not crash", test_event_no_subscribers_does_not_crash)


def test_event_once_fires_only_once():
    bus = EventBus()
    calls = []
    bus.once(SETTINGS_CHANGED, lambda: calls.append(1))
    bus.emit(SETTINGS_CHANGED)
    bus.emit(SETTINGS_CHANGED)
    assert calls == [1]

run("EventBus: once() handler fires exactly once then auto-unsubscribes", test_event_once_fires_only_once)


def test_event_clear_all():
    bus = EventBus()
    log = []
    bus.on(PLOT_FAILED, lambda: log.append(1))
    bus.clear()
    bus.emit(PLOT_FAILED)
    assert log == []

run("EventBus: clear() removes all handlers", test_event_clear_all)


def test_event_clear_single_event():
    bus = EventBus()
    log_a, log_b = [], []
    bus.on("event_a", lambda: log_a.append(1))
    bus.on("event_b", lambda: log_b.append(1))
    bus.clear("event_a")
    bus.emit("event_a")
    bus.emit("event_b")
    assert log_a == []
    assert log_b == [1]

run("EventBus: clear(event) removes only that event's handlers", test_event_clear_single_event)


def test_event_handler_exception_does_not_block_others():
    bus = EventBus()
    log = []

    def bad_handler():
        raise RuntimeError("boom")

    bus.on(PLOT_FINISHED, bad_handler)
    bus.on(PLOT_FINISHED, lambda: log.append("ok"))
    bus.emit(PLOT_FINISHED)
    assert log == ["ok"]

run("EventBus: exception in one handler does not block subsequent handlers", test_event_handler_exception_does_not_block_others)


def test_event_priority_ordering():
    bus = EventBus()
    order = []
    bus.on("ev", lambda: order.append("low"), priority=0)
    bus.on("ev", lambda: order.append("high"), priority=10)
    bus.emit("ev")
    assert order == ["high", "low"]

run("EventBus: higher-priority handlers fire first", test_event_priority_ordering)


# ===========================================================================
# 3. plotter_session
# ===========================================================================

section("plotter_session")

from plotter_session import Session


def test_session_capture():
    sess = Session()
    vars_ = {"color": _Var("blue"), "font_size": _Var("14")}
    state = sess.capture(vars_, plot_type="bar", window_geometry="800x600")
    assert state["color"] == "blue"
    assert state["font_size"] == "14"
    assert state["_plot_type"] == "bar"
    assert state["_window_geometry"] == "800x600"
    assert "_timestamp" in state

run("Session.capture: snapshots all var values with metadata", test_session_capture)


def test_session_restore():
    sess = Session()
    state = {"color": "red", "font_size": "16", "_plot_type": "box"}
    vars_ = {"color": _Var("blue"), "font_size": _Var("12")}
    sess.restore(state, vars_)
    assert vars_["color"].get() == "red"
    assert vars_["font_size"].get() == "16"

run("Session.restore: writes saved values back into vars", test_session_restore)


def test_session_restore_ignores_unknown_keys():
    sess = Session()
    state = {"unknown_key": "value", "color": "green"}
    vars_ = {"color": _Var("blue")}
    sess.restore(state, vars_)  # should not crash
    assert vars_["color"].get() == "green"

run("Session.restore: ignores keys not present in app_vars", test_session_restore_ignores_unknown_keys)


def test_session_round_trip(tmp_dir):
    sess = Session()
    # Temporarily redirect PREFS_PATH
    import plotter_session as _ps
    orig_path = _ps.PREFS_PATH
    _ps.PREFS_PATH = os.path.join(tmp_dir, "session.json")
    try:
        state = {"color": "purple", "font_size": "18", "_plot_type": "violin"}
        sess.save_to_disk(state)
        loaded = sess.load_from_disk()
        assert loaded["color"] == "purple"
        assert loaded["_plot_type"] == "violin"
    finally:
        _ps.PREFS_PATH = orig_path

run("Session: save_to_disk / load_from_disk round-trip preserves data",
    lambda: test_session_round_trip(tempfile.mkdtemp()))


def test_session_load_missing_file():
    sess = Session()
    import plotter_session as _ps
    orig_path = _ps.PREFS_PATH
    _ps.PREFS_PATH = "/tmp/__nonexistent_claude_plotter_session__.json"
    try:
        result = sess.load_from_disk()
        assert result == {}
    finally:
        _ps.PREFS_PATH = orig_path

run("Session.load_from_disk: returns empty dict when file does not exist",
    test_session_load_missing_file)


def test_session_restore_calls_set_plot_type():
    sess = Session()
    received = []
    state = {"_plot_type": "scatter"}
    sess.restore(state, {}, set_plot_type_fn=lambda t: received.append(t))
    assert received == ["scatter"]

run("Session.restore: calls set_plot_type_fn with saved plot type", test_session_restore_calls_set_plot_type)


# ===========================================================================
# 4. plotter_presets
# ===========================================================================

section("plotter_presets")

import plotter_presets as _pp


def test_presets_list_builtins():
    presets = _pp.list_presets()
    names = [p["name"] for p in presets]
    assert "Publication (B&W)" in names
    assert "Presentation" in names
    assert "Minimal" in names

run("plotter_presets: list_presets returns all built-in preset names", test_presets_list_builtins)


def test_presets_list_builtins_count():
    presets = _pp.list_presets()
    builtin = [p for p in presets if p["is_builtin"]]
    assert len(builtin) == 5  # 5 built-in presets defined in module

run("plotter_presets: exactly 5 built-in presets", test_presets_list_builtins_count)


def test_presets_load_builtin():
    p = _pp.load_preset("Publication (B&W)")
    assert p["color"] == "grayscale"
    assert p["_builtin"] is True
    assert p["_name"] == "Publication (B&W)"

run("plotter_presets: load_preset returns correct data for built-in", test_presets_load_builtin)


def test_presets_load_nonexistent_raises():
    raised = False
    try:
        _pp.load_preset("__does_not_exist__")
    except FileNotFoundError:
        raised = True
    assert raised

run("plotter_presets: load_preset raises FileNotFoundError for unknown preset",
    test_presets_load_nonexistent_raises)


def test_presets_save_and_load_custom(tmp_path):
    import plotter_presets as pp_mod
    orig_dir = pp_mod.PRESETS_DIR
    pp_mod.PRESETS_DIR = str(tmp_path) + os.sep
    try:
        app_vars = {
            "color": _Var("colorblind"),
            "font_size": _Var("14"),
            "axis_style": _Var("open"),
        }
        pp_mod.save_preset("My Custom", app_vars)
        loaded = pp_mod.load_preset("My Custom")
        assert loaded["color"] == "colorblind"
        assert loaded["font_size"] == "14"
        assert loaded["_name"] == "My Custom"
    finally:
        pp_mod.PRESETS_DIR = orig_dir

run("plotter_presets: save_preset then load_preset round-trip for custom preset",
    lambda: test_presets_save_and_load_custom(tempfile.mkdtemp()))


def test_presets_delete_builtin_returns_false():
    result = _pp.delete_preset("Publication (B&W)")
    assert result is False

run("plotter_presets: delete_preset returns False for built-ins", test_presets_delete_builtin_returns_false)


def test_presets_delete_custom(tmp_path):
    import plotter_presets as pp_mod
    orig_dir = pp_mod.PRESETS_DIR
    pp_mod.PRESETS_DIR = str(tmp_path) + os.sep
    try:
        app_vars = {"color": _Var("default")}
        pp_mod.save_preset("Temp Preset", app_vars)
        result = pp_mod.delete_preset("Temp Preset")
        assert result is True
        raised = False
        try:
            pp_mod.load_preset("Temp Preset")
        except FileNotFoundError:
            raised = True
        assert raised
    finally:
        pp_mod.PRESETS_DIR = orig_dir

run("plotter_presets: delete_preset removes custom preset from disk",
    lambda: test_presets_delete_custom(tempfile.mkdtemp()))


def test_presets_apply_preset():
    preset = {"color": "grayscale", "font_size": "14", "_name": "test", "_builtin": True}
    var_color = _Var("default")
    var_font = _Var("12")
    app_vars = {"color": var_color, "font_size": var_font}
    _pp.apply_preset(preset, app_vars)
    assert var_color.get() == "grayscale"
    assert var_font.get() == "14"

run("plotter_presets: apply_preset writes values into vars, ignores _ keys",
    test_presets_apply_preset)


# ===========================================================================
# 5. plotter_errors
# ===========================================================================

section("plotter_errors")

from plotter_errors import ErrorReporter, log_info, log_warning, log_error


def test_error_reporter_no_root_does_not_crash():
    er = ErrorReporter(root_tk=None)
    er.report("Test Error", "Something went wrong")

run("ErrorReporter: report() with no Tk root does not crash", test_error_reporter_no_root_does_not_crash)


def test_error_reporter_with_exception_does_not_crash():
    er = ErrorReporter(root_tk=None)
    try:
        raise ValueError("test exc")
    except ValueError as e:
        er.report("Value Error", "bad value", exc=e)

run("ErrorReporter: report() with exc= argument does not crash", test_error_reporter_with_exception_does_not_crash)


def test_error_reporter_wrap_thread():
    er = ErrorReporter(root_tk=None)
    results = []

    def good_fn(x):
        results.append(x)
        return x * 2

    wrapped = er.wrap_thread(good_fn, "BG Error")
    ret = wrapped(42)
    assert results == [42]
    assert ret == 84

run("ErrorReporter.wrap_thread: wrapped function runs normally when no exception",
    test_error_reporter_wrap_thread)


def test_error_reporter_wrap_thread_catches_exception():
    er = ErrorReporter(root_tk=None)
    calls = []

    def bad_fn():
        raise RuntimeError("oops")

    wrapped = er.wrap_thread(bad_fn, "BG Error")
    # Should not raise — exception is caught and reported internally
    wrapped()

run("ErrorReporter.wrap_thread: catches exception in wrapped function without re-raising",
    test_error_reporter_wrap_thread_catches_exception)


def test_log_functions_do_not_crash():
    log_info("info message")
    log_warning("warning message")
    log_error("error message")
    try:
        raise TypeError("for log_error")
    except TypeError as e:
        log_error("with exception", exc=e)

run("plotter_errors: log_info/log_warning/log_error do not crash", test_log_functions_do_not_crash)


def test_error_reporter_set_root():
    er = ErrorReporter()
    er.set_root(None)  # setting to None should not crash
    assert er._root is None

run("ErrorReporter.set_root: accepts None without crashing", test_error_reporter_set_root)


# ===========================================================================
# 6. plotter_project
# ===========================================================================

section("plotter_project")

from plotter_project import save_project, load_project, get_thumbnail, EXTENSION


def _make_excel(path):
    """Write a minimal .xlsx to path using openpyxl."""
    try:
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Sheet1"
        ws.append(["Control", "Drug"])
        ws.append([1, 4])
        ws.append([2, 5])
        ws.append([3, 6])
        wb.save(path)
        return True
    except ImportError:
        return False


def test_project_save_and_load_basic(tmp_path):
    excel_path = os.path.join(str(tmp_path), "data.xlsx")
    if not _make_excel(excel_path):
        return  # skip if openpyxl missing
    cplot_path = os.path.join(str(tmp_path), "project.cplot")
    app_vars = {"color": _Var("default"), "font_size": _Var("12")}
    save_project(cplot_path, app_vars, "bar", excel_path, sheet="Sheet1")
    result = load_project(cplot_path)
    assert result["plot_type"] == "bar"
    assert result["state"]["color"] == "default"
    assert result["state"]["font_size"] == "12"
    assert result["manifest"]["version"] == 1
    assert "Sheet1" in result["sheet_names"]

run("plotter_project: save_project / load_project round-trip preserves state and data",
    lambda: test_project_save_and_load_basic(tempfile.mkdtemp()))


def test_project_has_thumbnail_false_when_not_saved(tmp_path):
    cplot_path = os.path.join(str(tmp_path), "nothumbnail.cplot")
    save_project(cplot_path, {}, "scatter", excel_path=None)
    result = load_project(cplot_path)
    assert result["has_thumbnail"] is False

run("plotter_project: has_thumbnail is False when thumbnail not included",
    lambda: test_project_has_thumbnail_false_when_not_saved(tempfile.mkdtemp()))


def test_project_has_thumbnail_true_when_saved(tmp_path):
    cplot_path = os.path.join(str(tmp_path), "withthumb.cplot")
    fake_png = b"\x89PNG\r\nfakedata"
    save_project(cplot_path, {}, "bar", excel_path=None, thumbnail_bytes=fake_png)
    result = load_project(cplot_path)
    assert result["has_thumbnail"] is True

run("plotter_project: has_thumbnail is True when thumbnail bytes provided",
    lambda: test_project_has_thumbnail_true_when_saved(tempfile.mkdtemp()))


def test_project_get_thumbnail(tmp_path):
    cplot_path = os.path.join(str(tmp_path), "thumb.cplot")
    fake_png = b"\x89PNG\r\nfakedata"
    save_project(cplot_path, {}, "bar", excel_path=None, thumbnail_bytes=fake_png)
    data = get_thumbnail(cplot_path)
    assert data == fake_png

run("plotter_project: get_thumbnail returns embedded PNG bytes",
    lambda: test_project_get_thumbnail(tempfile.mkdtemp()))


def test_project_get_thumbnail_none_when_missing(tmp_path):
    cplot_path = os.path.join(str(tmp_path), "nothumb.cplot")
    save_project(cplot_path, {}, "bar", excel_path=None)
    result = get_thumbnail(cplot_path)
    assert result is None

run("plotter_project: get_thumbnail returns None when no thumbnail in file",
    lambda: test_project_get_thumbnail_none_when_missing(tempfile.mkdtemp()))


def test_project_load_nonexistent_raises(tmp_path):
    raised = False
    try:
        load_project(os.path.join(str(tmp_path), "ghost.cplot"))
    except Exception:
        raised = True
    assert raised

run("plotter_project: load_project raises when file does not exist",
    lambda: test_project_load_nonexistent_raises(tempfile.mkdtemp()))


def test_project_comparisons_round_trip(tmp_path):
    cplot_path = os.path.join(str(tmp_path), "comp.cplot")
    comp_data = {"pairs": [["Control", "Drug"]]}
    save_project(cplot_path, {}, "bar", excel_path=None, comparisons=comp_data)
    result = load_project(cplot_path)
    assert result["comparisons"] == comp_data

run("plotter_project: comparisons dict is preserved in round-trip",
    lambda: test_project_comparisons_round_trip(tempfile.mkdtemp()))


def test_project_extension_constant():
    assert EXTENSION == ".cplot"

run("plotter_project: EXTENSION constant is '.cplot'", test_project_extension_constant)


# ===========================================================================
# 7. plotter_registry
# ===========================================================================

section("plotter_registry")

from plotter_registry import PlotTypeConfig, _REGISTRY_SPECS, ERROR_TYPE_MAP, STATS_TEST_MAP


def test_registry_not_empty():
    assert len(_REGISTRY_SPECS) > 0

run("plotter_registry: registry contains at least one entry", test_registry_not_empty)


def test_registry_has_29_entries():
    assert len(_REGISTRY_SPECS) == 29

run("plotter_registry: registry has exactly 29 chart type entries", test_registry_has_29_entries)


def test_registry_no_duplicate_keys():
    keys = [spec.key for spec in _REGISTRY_SPECS]
    assert len(keys) == len(set(keys))

run("plotter_registry: no duplicate keys across all entries", test_registry_no_duplicate_keys)


def test_registry_required_fields():
    for spec in _REGISTRY_SPECS:
        assert spec.key, f"Empty key in {spec}"
        assert spec.label, f"Empty label in {spec}"
        assert spec.fn_name, f"Empty fn_name in {spec}"
        assert spec.tab_mode, f"Empty tab_mode in {spec}"
        assert spec.stats_tab, f"Empty stats_tab in {spec}"
        assert spec.validate, f"Empty validate in {spec}"

run("plotter_registry: every entry has non-empty key, label, fn_name, tab_mode, stats_tab, validate",
    test_registry_required_fields)


def test_registry_fn_names_exist_in_plotter_functions():
    import plotter_functions as pf
    missing = []
    for spec in _REGISTRY_SPECS:
        if not hasattr(pf, spec.fn_name):
            missing.append(spec.fn_name)
    assert missing == [], f"fn_names not found in plotter_functions: {missing}"

run("plotter_registry: all fn_names correspond to actual functions in plotter_functions",
    test_registry_fn_names_exist_in_plotter_functions)


def test_registry_lookup_by_key():
    bar_specs = [s for s in _REGISTRY_SPECS if s.key == "bar"]
    assert len(bar_specs) == 1
    assert bar_specs[0].fn_name == "plotter_barplot"

run("plotter_registry: lookup by key 'bar' returns correct config", test_registry_lookup_by_key)


def test_registry_bar_flags():
    bar = next(s for s in _REGISTRY_SPECS if s.key == "bar")
    assert bar.has_points is True
    assert bar.has_error_bars is True
    assert bar.has_legend is False
    assert bar.has_stats is True

run("plotter_registry: bar chart config has correct capability flags", test_registry_bar_flags)


def test_registry_kaplan_meier_flags():
    km = next(s for s in _REGISTRY_SPECS if s.key == "kaplan_meier")
    assert km.has_points is False
    assert km.has_stats is False
    assert km.has_legend is True
    assert km.x_continuous is True

run("plotter_registry: kaplan_meier config has correct flags", test_registry_kaplan_meier_flags)


def test_registry_filter_kwargs():
    """filter_kwargs strips keys the function does not accept."""
    import plotter_functions as pf
    spec = next(s for s in _REGISTRY_SPECS if s.key == "bar")
    fn = getattr(pf, spec.fn_name)
    kw = {"excel_path": "/tmp/x.xlsx", "sheet": 0, "color": "default",
          "__garbage__": 99}
    filtered = spec.filter_kwargs(kw, fn)
    assert "__garbage__" not in filtered
    assert "excel_path" in filtered

run("PlotTypeConfig.filter_kwargs: strips unknown keys, keeps valid ones",
    test_registry_filter_kwargs)


def test_registry_error_type_map():
    assert ERROR_TYPE_MAP["SEM (Standard Error)"] == "sem"
    assert ERROR_TYPE_MAP["SD (Standard Deviation)"] == "sd"
    assert ERROR_TYPE_MAP["95% CI"] == "ci95"

run("plotter_registry: ERROR_TYPE_MAP has correct mappings", test_registry_error_type_map)


def test_registry_stats_test_map():
    assert STATS_TEST_MAP["Parametric"] == "parametric"
    assert STATS_TEST_MAP["Non-parametric"] == "nonparametric"
    assert STATS_TEST_MAP["Paired"] == "paired"

run("plotter_registry: STATS_TEST_MAP has correct mappings", test_registry_stats_test_map)


# ===========================================================================
# 8. plotter_types
# ===========================================================================

section("plotter_types")

from plotter_types import (
    DataSource, StyleParams, LabelParams, StatsParams,
    DisplayParams, PlotRequest,
)


def test_types_data_source_defaults():
    ds = DataSource()
    assert ds.excel_path == ""
    assert ds.sheet == 0

run("plotter_types: DataSource instantiates with correct defaults", test_types_data_source_defaults)


def test_types_style_params_defaults():
    sp = StyleParams()
    assert sp.color == "default"
    assert sp.axis_style == "open"
    assert sp.tick_dir == "out"
    assert sp.font_size == 12.0

run("plotter_types: StyleParams instantiates with correct defaults", test_types_style_params_defaults)


def test_types_label_params_defaults():
    lp = LabelParams()
    assert lp.title == ""
    assert lp.yscale == "linear"
    assert lp.ylim is None

run("plotter_types: LabelParams instantiates with correct defaults", test_types_label_params_defaults)


def test_types_stats_params_defaults():
    sp = StatsParams()
    assert sp.show_stats is False
    assert sp.stats_test == "auto"
    assert sp.posthoc == "tukey"
    assert sp.p_sig_threshold == 0.05

run("plotter_types: StatsParams instantiates with correct defaults", test_types_stats_params_defaults)


def test_types_display_params_defaults():
    dp = DisplayParams()
    assert dp.show_points is False
    assert dp.error == "sem"
    assert dp.figsize == (5.0, 5.0)

run("plotter_types: DisplayParams instantiates with correct defaults", test_types_display_params_defaults)


def test_types_plot_request_default():
    pr = PlotRequest()
    assert pr.chart_type == "bar"
    assert isinstance(pr.data, DataSource)
    assert isinstance(pr.style, StyleParams)
    assert isinstance(pr.labels, LabelParams)
    assert isinstance(pr.stats, StatsParams)
    assert isinstance(pr.display, DisplayParams)

run("plotter_types: PlotRequest instantiates with all sub-dataclasses as defaults",
    test_types_plot_request_default)


def test_types_plot_request_to_flat_dict():
    pr = PlotRequest()
    pr.data.excel_path = "/tmp/foo.xlsx"
    pr.style.color = "grayscale"
    pr.labels.title = "My Chart"
    flat = pr.to_flat_dict()
    assert flat["excel_path"] == "/tmp/foo.xlsx"
    assert flat["color"] == "grayscale"
    assert flat["title"] == "My Chart"
    assert flat["chart_type"] == "bar"

run("plotter_types: PlotRequest.to_flat_dict merges all sub-dicts", test_types_plot_request_to_flat_dict)


def test_types_plot_request_to_json():
    pr = PlotRequest()
    pr.labels.title = "JSON Test"
    js = pr.to_json()
    data = json.loads(js)
    assert data["title"] == "JSON Test"
    assert data["chart_type"] == "bar"

run("plotter_types: PlotRequest.to_json produces valid JSON with correct fields",
    test_types_plot_request_to_json)


def test_types_from_flat_dict():
    flat = {
        "excel_path": "/data/x.xlsx",
        "sheet": 1,
        "color": "prism",
        "title": "Test",
        "show_stats": True,
        "chart_type": "violin",
    }
    pr = PlotRequest.from_flat_dict(flat)
    assert pr.data.excel_path == "/data/x.xlsx"
    assert pr.data.sheet == 1
    assert pr.style.color == "prism"
    assert pr.labels.title == "Test"
    assert pr.stats.show_stats is True
    assert pr.chart_type == "violin"

run("plotter_types: PlotRequest.from_flat_dict reconstructs sub-dataclasses correctly",
    test_types_from_flat_dict)


def test_types_data_source_custom():
    ds = DataSource(excel_path="/tmp/data.xlsx", sheet="Sheet2")
    assert ds.excel_path == "/tmp/data.xlsx"
    assert ds.sheet == "Sheet2"

run("plotter_types: DataSource accepts custom values", test_types_data_source_custom)


# ===========================================================================
# Done
# ===========================================================================

summarise()
sys.exit(0 if _h.FAIL == 0 else 1)
