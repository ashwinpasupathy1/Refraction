You are Agent F for the Claude Plotter Phase 2 build.
You are the INTEGRATION agent. You run AFTER all Wave 1 agents.

BUDGET: Maximum $10. If approaching limit, commit completed work and exit.

ENVIRONMENT:
- Project root: the current working directory
- Python 3.12, run tests with: xvfb-run python3 run_all.py
- You are on branch: phase2/agent-f (already checked out)
- All Wave 1 agent branches have been merged into your branch already.
- All modules use "plotter_" prefix. Branding is "Claude Plotter".

CRITICAL SAFETY RULES:
1. Make ONE change at a time
2. Run xvfb-run python3 run_all.py AFTER each change
3. git commit AFTER each passing test run
4. If tests fail after a change, revert ONLY the last change:
   git checkout -- <file>
5. You should end up with 10-15 small commits, NOT one giant commit
6. If stuck on a particular integration, SKIP it and move on
7. If stuck overall, commit what works + create phase2/AGENT_F_STUCK.txt

APPROACH: Option B (safe). You will:
- Wire new modules via imports (additive)
- Add new UI elements and menu items (additive)
- Remove DUPLICATE code (import from existing modules instead)
- You will NOT restructure the App class or extract tab builders

TARGET: plotter_barplot_app.py goes from ~7500 to ~5500 lines.
The remaining code stays structurally identical.

=======================================================================
STEP 1: Verify starting state
=======================================================================

Run: xvfb-run python3 run_all.py
Record the pass count. It should be >= 520.
If it fails, check which Wave 1 changes caused issues and note them
in phase2/AGENT_F_ISSUES.txt. Try to fix. If you cannot fix,
proceed with the remaining steps that don't depend on the broken change.

Also verify all new modules import:
  python3 -c "from plotter_app_icons import ICON_FN; print('icons OK')"
  python3 -c "from plotter_presets import BUILT_IN_PRESETS; print('presets OK')"
  python3 -c "from plotter_session import Session; print('session OK')"
  python3 -c "from plotter_events import EventBus; print('events OK')"
  python3 -c "from plotter_types import PlotRequest; print('types OK')"
  python3 -c "from plotter_undo import UndoStack; print('undo OK')"
  python3 -c "from plotter_errors import reporter; print('errors OK')"
  python3 -c "from plotter_comparisons import ComparisonSet; print('comparisons OK')"
  python3 -c "from plotter_project import save_project; print('project OK')"
  python3 -c "from plotter_import_pzfx import import_pzfx; print('pzfx OK')"
  python3 -c "from plotter_wiki_content import WIKI_SECTIONS; print('wiki content OK')"
  python3 -c "from plotter_app_wiki import open_wiki_popup; print('wiki render OK')"

If any import fails, note it and skip integrating that module.

git commit -m "chore(agent-f): verify starting state after wave 1 merge"

=======================================================================
STEP 2: Remove duplicate widget code from plotter_barplot_app.py
=======================================================================

plotter_barplot_app.py contains copies of classes and functions that
already exist in plotter_widgets.py. Remove the duplicates and import
from plotter_widgets.py instead.

Open plotter_barplot_app.py and find these duplicated items. For each one:
- Confirm it exists in plotter_widgets.py (import and check)
- Delete the duplicate definition from plotter_barplot_app.py
- Add the import at the top of plotter_barplot_app.py if not already there

Items to deduplicate (find each in plotter_barplot_app.py):

a) _DS class — design system color/font constants
   Check: python3 -c "from plotter_widgets import _DS; print(_DS.PRIMARY)"
   If it exists in plotter_widgets, delete the _DS class from the app file.
   Add: from plotter_widgets import _DS (if not already imported)

b) PButton class — custom styled button
   Check: python3 -c "from plotter_widgets import PButton; print('OK')"
   Delete from app, import from plotter_widgets.

c) PCheckbox class — custom checkbox
   Check: python3 -c "from plotter_widgets import PCheckbox; print('OK')"
   Delete from app, import from plotter_widgets.

d) PRadioGroup class — custom radio button group
   Check: python3 -c "from plotter_widgets import PRadioGroup; print('OK')"
   Delete from app, import from plotter_widgets.

e) PEntry class — custom entry field
   Check: python3 -c "from plotter_widgets import PEntry; print('OK')"
   Delete from app, import from plotter_widgets.

f) PCombobox class — custom combobox
   Check: python3 -c "from plotter_widgets import PCombobox; print('OK')"
   Delete from app, import from plotter_widgets.

g) section_sep function — section separator widget
   Check: python3 -c "from plotter_widgets import section_sep; print('OK')"
   Delete from app, import from plotter_widgets.

h) _create_tooltip function
   Check: python3 -c "from plotter_widgets import _create_tooltip; print('OK')"
   Delete from app, import from plotter_widgets.

i) add_placeholder function
   Check: python3 -c "from plotter_widgets import add_placeholder; print('OK')"
   Delete from app, import from plotter_widgets.

j) _bind_scroll_recursive function
   Check: python3 -c "from plotter_widgets import _bind_scroll_recursive; print('OK')"
   Delete from app, import from plotter_widgets.

k) LABELS dict, HINTS dict, label() function, hint() function
   Check: python3 -c "from plotter_widgets import LABELS, HINTS, label, hint; print('OK')"
   Delete from app, import from plotter_widgets.

l) _is_num, _non_numeric_values, _scipy_summary functions
   Check: python3 -c "from plotter_widgets import _is_num; print('OK')"
   Delete from app, import from plotter_widgets.

m) _sys_bg function
   Check: python3 -c "from plotter_widgets import _sys_bg; print('OK')"
   Delete from app, import from plotter_widgets.

IMPORTANT PROCESS for each item:
1. Verify it exists in plotter_widgets.py first
2. If it does NOT exist there, SKIP it (do not delete)
3. If it DOES exist, check that the version in plotter_widgets.py has
   the same interface (same parameters, same return type)
4. If interfaces differ, SKIP it
5. Delete from app, add import
6. Run: xvfb-run python3 run_all.py
7. If tests pass: git commit -m "refactor: deduplicate <item> — import from plotter_widgets"
8. If tests fail: git checkout -- plotter_barplot_app.py and skip this item

Do these ONE AT A TIME. Not all at once.

=======================================================================
STEP 3: Replace inline icon functions with import
=======================================================================

plotter_barplot_app.py contains icon drawing functions (_icon_bar,
_icon_line, etc.) and an _ICON_FN dict. These now exist in
plotter_app_icons.py.

1. Check: python3 -c "from plotter_app_icons import ICON_FN; print(len(ICON_FN))"
2. If OK, find all _icon_* function definitions in plotter_barplot_app.py
3. Find the _ICON_FN dict in plotter_barplot_app.py
4. Delete all _icon_* functions and the _ICON_FN dict
5. Add at top: from plotter_app_icons import ICON_FN, SB_ITEM_H, SB_ICON_SIZE, SB_WIDTH
6. Find where the app references _ICON_FN and replace with ICON_FN
7. Find where the app references _SB_ITEM_H, _SB_ICON_SIZE, _SB_WIDTH
   and replace with the imported names (or alias them)
8. Run: xvfb-run python3 run_all.py
9. If pass: git commit -m "refactor: replace inline icons with plotter_app_icons import"
10. If fail: git checkout -- plotter_barplot_app.py and skip

=======================================================================
STEP 4: Wire EventBus into App.__init__
=======================================================================

In plotter_barplot_app.py, find the App.__init__ method.

Add near the top (after self._vars or similar initialization):

    from plotter_events import EventBus
    self._bus = EventBus()

Then find these methods and add event emissions:

a) In _load_sheets (or wherever file loading happens):
   Add: self._bus.emit("file.loaded", path=excel_path)

b) In _validate_spreadsheet (or wherever validation happens):
   Add: self._bus.emit("file.validated", path=path, errors=errors, warnings=warnings)

c) In _do_run (plot generation method):
   Add at start: self._bus.emit("plot.started", kw=kw)
   Add at end (success): self._bus.emit("plot.finished", fig=fig)

If you cannot find these exact method names, search for the
functionality (file loading, validation, plot generation) and add
emissions at appropriate points.

Run tests, commit if pass.
git commit -m "feat: wire EventBus into App lifecycle events"

=======================================================================
STEP 5: Wire UndoStack into App.__init__
=======================================================================

In App.__init__, add:

    from plotter_undo import UndoStack
    self._undo_stack = UndoStack(max_depth=50)

Then add keyboard bindings in _build or _build_menubar:

    self.bind_all("<Command-z>", lambda e: self._do_undo())
    self.bind_all("<Command-Shift-z>", lambda e: self._do_redo())
    # Linux fallback:
    self.bind_all("<Control-z>", lambda e: self._do_undo())
    self.bind_all("<Control-Shift-z>", lambda e: self._do_redo())

Add these methods to the App class:

    def _do_undo(self):
        desc = self._undo_stack.undo(self._vars)
        if desc:
            self._status_var.set(f"Undo: {desc}") if hasattr(self, '_status_var') else None

    def _do_redo(self):
        desc = self._undo_stack.redo(self._vars)
        if desc:
            self._status_var.set(f"Redo: {desc}") if hasattr(self, '_status_var') else None

Run tests, commit if pass.
git commit -m "feat: wire UndoStack with Cmd+Z / Cmd+Shift+Z"

=======================================================================
STEP 6: Wire ErrorReporter
=======================================================================

In App.__init__, add:

    from plotter_errors import reporter
    reporter.set_root(self)

Find where _do_run is launched as a thread. It likely looks like:
    threading.Thread(target=self._do_run, args=(...), daemon=True).start()

Change to:
    threading.Thread(target=reporter.wrap_thread(self._do_run, "Plot Error"),
                     args=(...), daemon=True).start()

Run tests, commit if pass.
git commit -m "feat: wire ErrorReporter for background thread safety"

=======================================================================
STEP 7: Wire Presets into Data tab
=======================================================================

Find the _tab_data method (or wherever the Data tab UI is built).

Add a preset section near the top, below the file picker:

    from plotter_presets import (list_presets, load_preset,
                                 apply_preset, save_preset,
                                 delete_preset, BUILT_IN_PRESETS)

    # Preset selector
    section_sep(parent_frame, "Style Preset")
    preset_names = [p["name"] for p in list_presets()]
    preset_var = tk.StringVar()
    preset_cb = PCombobox(parent_frame, textvariable=preset_var,
                          values=preset_names, state="readonly")
    preset_cb.pack(fill="x", padx=PAD, pady=2)

    def _on_preset_select(event=None):
        name = preset_var.get()
        if name:
            preset = load_preset(name)
            if preset:
                apply_preset(preset, self._vars)

    preset_cb.bind("<<ComboboxSelected>>", _on_preset_select)

IMPORTANT: Find the correct parent frame variable name by reading
the existing _tab_data code. It might be called fr, frame, data_fr, etc.
Also find where PAD is defined or imported.

If you cannot cleanly add this without breaking layout, SKIP this step.

Run tests, commit if pass.
git commit -m "feat: add style preset selector to Data tab"

=======================================================================
STEP 8: Wire Session persistence
=======================================================================

In App.__init__, add:

    from plotter_session import Session
    self._session = Session()

At the END of __init__ (after _build is complete), add restore logic:

    # Offer to restore previous session
    saved = self._session.load_from_disk()
    if saved and saved.get("vars"):
        try:
            from tkinter import messagebox
            if messagebox.askyesno("Restore Session",
                    "Restore your previous session?"):
                self._session.restore(saved, self._vars)
        except Exception:
            pass

    # Start auto-save timer
    self._auto_save()

Add auto-save method to the App class:

    def _auto_save(self):
        try:
            state = self._session.capture(
                self._vars,
                self._plot_type.get() if hasattr(self, '_plot_type') else "bar",
                self.geometry())
            self._session.save_to_disk(state)
        except Exception:
            pass
        self.after(30000, self._auto_save)  # every 30 seconds

Find the window close handler (WM_DELETE_WINDOW protocol). It might
be in __init__ or _build. Add save-before-quit:

    # Find existing: self.protocol("WM_DELETE_WINDOW", self._on_close)
    # Or add it if it doesn't exist

    def _on_close(self):
        try:
            state = self._session.capture(
                self._vars,
                self._plot_type.get() if hasattr(self, '_plot_type') else "bar",
                self.geometry())
            self._session.save_to_disk(state)
        except Exception:
            pass
        self.destroy()

If there's already an _on_close or _quit method, add the session
save logic at the beginning of it, before destroy().

Run tests, commit if pass.
git commit -m "feat: wire session persistence with auto-save and restore"

=======================================================================
STEP 9: Wire .cplot project file support
=======================================================================

Find the menu bar construction (likely _build_menubar or similar).

Add to the File menu:

    from plotter_project import save_project, load_project, extract_to_temp_excel

    # In the File menu:
    file_menu.add_command(label="Save Project...",
                          command=self._save_project,
                          accelerator="Cmd+S")
    file_menu.add_command(label="Open Project...",
                          command=self._open_project,
                          accelerator="Cmd+O")
    file_menu.add_separator()

    # Bind keyboard shortcuts
    self.bind_all("<Command-s>", lambda e: self._save_project())
    self.bind_all("<Command-o>", lambda e: self._open_project())
    # Linux fallback:
    self.bind_all("<Control-s>", lambda e: self._save_project())
    self.bind_all("<Control-o>", lambda e: self._open_project())

Add these methods to the App class:

    def _save_project(self):
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            defaultextension=".cplot",
            filetypes=[("Claude Plotter Project", "*.cplot")])
        if not path:
            return
        try:
            excel_path = self._vars.get("excel_path")
            ep = excel_path.get() if excel_path else ""
            pt = self._plot_type.get() if hasattr(self, '_plot_type') else "bar"
            save_project(path, self._vars, pt, ep)
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Save Error", str(e))

    def _open_project(self):
        from tkinter import filedialog, messagebox
        path = filedialog.askopenfilename(
            filetypes=[("Claude Plotter Project", "*.cplot"),
                       ("GraphPad Prism", "*.pzfx"),
                       ("Excel files", "*.xlsx *.xls"),
                       ("All files", "*.*")])
        if not path:
            return
        if path.endswith(".cplot"):
            self._open_cplot(path)
        elif path.endswith(".pzfx"):
            self._open_pzfx(path)
        else:
            # Regular Excel — set the path variable
            if "excel_path" in self._vars:
                self._vars["excel_path"].set(path)

    def _open_cplot(self, path):
        try:
            from plotter_project import load_project, extract_to_temp_excel
            project = load_project(path)
            temp_xlsx = extract_to_temp_excel(path)
            # Restore state
            for key, value in project.get("state", {}).items():
                if key in self._vars:
                    try:
                        self._vars[key].set(value)
                    except Exception:
                        pass
            # Point to temp Excel
            if "excel_path" in self._vars:
                self._vars["excel_path"].set(temp_xlsx)
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Open Error", str(e))

    def _open_pzfx(self, path):
        try:
            from plotter_import_pzfx import import_pzfx
            from tkinter import messagebox
            result = import_pzfx(path)
            if not result.success:
                messagebox.showerror("Import Error",
                    "\n".join(result.errors))
                return
            if "excel_path" in self._vars:
                self._vars["excel_path"].set(result.temp_excel_path)
            if result.warnings:
                messagebox.showinfo("Import Notes",
                    "\n".join(result.warnings))
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Import Error", str(e))

IMPORTANT: If you cannot find the File menu or menu bar construction,
search for "Menu(" or "add_command" in the file to locate it.

Run tests, commit if pass.
git commit -m "feat: wire .cplot save/open and .pzfx import via File menu"

=======================================================================
STEP 10: Wire keyboard chart navigation
=======================================================================

Find where keyboard bindings are set up (likely in _build or __init__).

Add:

    # Chart type shortcuts: Cmd+1 through Cmd+9
    for i in range(1, 10):
        self.bind_all(f"<Command-Key-{i}>",
                      lambda e, n=i: self._jump_to_chart(n))
        self.bind_all(f"<Control-Key-{i}>",
                      lambda e, n=i: self._jump_to_chart(n))

Add this method:

    def _jump_to_chart(self, number):
        """Switch to chart type by keyboard shortcut number."""
        try:
            from plotter_registry import KEYBOARD_SHORTCUTS
            key = KEYBOARD_SHORTCUTS.get(number)
            if key:
                # Find the sidebar index for this chart type key
                # and trigger the same action as clicking it
                # This depends on how the sidebar is built.
                # Look for _sb_select or _show_pane or _on_tab_change
                pass  # Implement based on actual sidebar structure
        except Exception:
            pass

IMPORTANT: The actual implementation of _jump_to_chart depends on how
the sidebar works. Read the sidebar code to understand:
- How chart types are listed (probably an ordered list)
- How clicking a chart type works (what methods are called)
- Then replicate that behavior in _jump_to_chart

If you cannot figure out the sidebar mechanism, just add the keybindings
and a stub method with a comment explaining what needs to happen.

Run tests, commit if pass.
git commit -m "feat: add Cmd+1-9 keyboard shortcuts for chart types"

=======================================================================
STEP 11: Apply bug fixes from Agent C's notes
=======================================================================

These fixes could not be applied by Agent C because they are in
plotter_barplot_app.py which only you can modify.

BUG FIX A: Canvas mode toggle misses grouped_bar
Find: a condition that checks plot_type == "bar" in a canvas toggle method
(might be called _toggle_canvas_mode or similar)
Replace: plot_type == "bar" with plot_type in ("bar", "grouped_bar")

BUG FIX B: Missing _validate_pyramid fallback
Add this method to the App class:

    def _validate_pyramid(self, df):
        try:
            from plotter_validators import validate_pyramid
            return validate_pyramid(df)
        except ImportError:
            return [], ["Pyramid validator not available"]

For each fix:
- Make the change
- Run: xvfb-run python3 run_all.py
- If pass: git commit
- If fail: revert

git commit -m "fix: canvas toggle for grouped_bar + pyramid validator fallback"

=======================================================================
STEP 12: Wire wiki popup
=======================================================================

Find where the wiki/help popup is opened. Search for "wiki" or
"_open_wiki" in plotter_barplot_app.py.

If there's an existing _open_wiki_popup method with inline content,
replace its body:

    def _open_wiki_popup(self):
        try:
            from plotter_app_wiki import open_wiki_popup
            open_wiki_popup(self)
        except Exception as e:
            from tkinter import messagebox
            messagebox.showinfo("Wiki", f"Wiki unavailable: {e}")

If there's no existing wiki method, add one and wire it to the
Help menu or sidebar wiki button.

Run tests, commit if pass.
git commit -m "feat: wire statistical wiki popup from plotter_app_wiki"

=======================================================================
FINAL VERIFICATION:
=======================================================================

1. xvfb-run python3 run_all.py
   Must pass >= 520 tests, 0 failures

2. python3 -c "import plotter_barplot_app; print('import OK')"

3. Count lines:
   wc -l plotter_barplot_app.py
   Should be significantly less than original (~5500 target)

4. git log --oneline
   Should show 8-12 small incremental commits

5. If all good, final commit:
   git commit --allow-empty -m "feat(agent-f): integration complete

Summary of changes to plotter_barplot_app.py:
- Removed duplicate widget code (import from plotter_widgets)
- Removed inline icons (import from plotter_app_icons)
- Wired EventBus for lifecycle events
- Wired UndoStack with Cmd+Z/Cmd+Shift+Z
- Wired ErrorReporter for thread safety
- Added style preset selector to Data tab
- Added session persistence with auto-save
- Added .cplot project save/open to File menu
- Added .pzfx import support
- Added Cmd+1-9 chart type shortcuts
- Wired statistical wiki popup
- Fixed canvas toggle for grouped_bar
- Added _validate_pyramid fallback

All tests passing."
