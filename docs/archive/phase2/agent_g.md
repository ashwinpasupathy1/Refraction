You are Agent G for the Claude Plotter Phase 2 build.
You are the VERIFICATION agent. You run LAST, after Agent F.

BUDGET: Maximum $5. If approaching limit, commit completed work and exit.

ENVIRONMENT:
- Project root: the current working directory
- Python 3.12, run tests with: xvfb-run python3 run_all.py
- You are on branch: phase2/agent-g (already checked out)
- All previous agents have completed their work.
- All modules use "plotter_" prefix. Branding is "Claude Plotter".

RULES:
1. Your PRIMARY job is verification, not new code
2. You may fix small issues you discover
3. You may update documentation
4. You must NOT make large structural changes
5. Every fix must be followed by: xvfb-run python3 run_all.py

=======================================================================
CHECK 1: Full test suite
=======================================================================

Run: xvfb-run python3 run_all.py 2>&1 | tee phase2/test_results.txt

Record the output. The pass count must be >= 520.
If there are failures, attempt to fix them if the fix is small
(under 10 lines). If not fixable, document in phase2/KNOWN_ISSUES.txt.

=======================================================================
CHECK 2: All modules import cleanly
=======================================================================

Run this and save output:

python3 -c "
modules = [
    'plotter_barplot_app', 'plotter_functions', 'plotter_widgets',
    'plotter_validators', 'plotter_results', 'plotter_registry',
    'plotter_tabs', 'plotter_app_icons', 'plotter_presets',
    'plotter_session', 'plotter_events', 'plotter_types',
    'plotter_undo', 'plotter_errors', 'plotter_comparisons',
    'plotter_project', 'plotter_import_pzfx',
    'plotter_wiki_content', 'plotter_app_wiki',
]
failed = []
for mod in modules:
    try:
        __import__(mod)
        print(f'  OK: {mod}')
    except Exception as e:
        print(f'  FAIL: {mod} — {e}')
        failed.append(mod)
if failed:
    print(f'\n{len(failed)} modules failed to import')
else:
    print(f'\nAll {len(modules)} modules import successfully')
" 2>&1 | tee phase2/import_results.txt

If any module fails to import, investigate and fix if possible.

=======================================================================
CHECK 3: No duplicate definitions
=======================================================================

Run:

python3 -c "
import re, os
from collections import Counter

defs = Counter()
locations = {}

for root, dirs, files in os.walk('.'):
    dirs[:] = [d for d in dirs if d not in
               ('__pycache__', '.git', 'venv', '.venv', 'phase2')]
    for f in files:
        if f.endswith('.py') and not f.startswith('test_'):
            path = os.path.join(root, f)
            with open(path) as fh:
                for lineno, line in enumerate(fh, 1):
                    m = re.match(r'^class (\w+)', line)
                    if m:
                        name = f'class:{m.group(1)}'
                        defs[name] += 1
                        locations.setdefault(name, []).append(f'{path}:{lineno}')
                    m = re.match(r'^def (\w+)', line)
                    if m:
                        name = f'def:{m.group(1)}'
                        defs[name] += 1
                        locations.setdefault(name, []).append(f'{path}:{lineno}')

allowed = {'def:__init__', 'def:setup', 'def:teardown', 'def:main',
           'def:run', 'def:test', 'def:setUp', 'def:tearDown'}
dupes = {k: v for k, v in defs.items() if v > 1 and k not in allowed}

if dupes:
    print('DUPLICATE DEFINITIONS FOUND:')
    for name, count in sorted(dupes.items()):
        print(f'  {name} ({count}x):')
        for loc in locations[name]:
            print(f'    {loc}')
else:
    print('No duplicate definitions found')
" 2>&1 | tee phase2/duplicate_check.txt

If duplicates are found between plotter_barplot_app.py and plotter_widgets.py
(or other modules), remove the duplicate from plotter_barplot_app.py and
replace with an import. Run tests after each fix.

=======================================================================
CHECK 4: No leftover "prism_" references in code
=======================================================================

Run:

grep -rn "import prism_\|from prism_\|prism_barplot\|prism_functions\|prism_widgets\|prism_validators\|prism_results\|prism_registry" \
    --include="*.py" --exclude-dir=.git --exclude-dir=phase2 \
    --exclude-dir=__pycache__ . 2>&1 | tee phase2/prism_refs_check.txt

If any results appear, fix them (change prism_ to plotter_).
Exceptions: references TO "GraphPad Prism" in wiki content or comments
are OK and should be left as-is.

=======================================================================
CHECK 5: No TODO/FIXME/HACK left behind
=======================================================================

Run:

grep -rn "TODO\|FIXME\|HACK\|XXX\|PLACEHOLDER" \
    --include="*.py" --exclude-dir=.git --exclude-dir=phase2 \
    --exclude-dir=__pycache__ . 2>&1 | tee phase2/todo_check.txt

Review each result. If it's from a previous agent leaving a stub,
try to complete it. If not completable, document in KNOWN_ISSUES.txt.

=======================================================================
CHECK 6: Wiki content integrity
=======================================================================

Run:

python3 -c "
from plotter_wiki_content import WIKI_SECTIONS, MASTER_REFERENCES
print(f'Sections: {len(WIKI_SECTIONS)}')
print(f'References: {len(MASTER_REFERENCES)}')
issues = []
for i, s in enumerate(WIKI_SECTIONS):
    title = s.get('title', f'UNTITLED #{i}')
    subs = s.get('subsections', [])
    if not title or title.startswith('UNTITLED'):
        issues.append(f'Section {i}: missing title')
    if len(subs) < 2:
        issues.append(f'{title}: only {len(subs)} subsections')
    for sub in subs:
        if sub.get('type') == 'latex_block':
            exprs = sub.get('expressions', [])
            for expr, desc in exprs:
                if not expr.startswith(r'$') and not expr.startswith('$'):
                    issues.append(f'{title}/{sub[\"heading\"]}: expression not in math mode')
if issues:
    print(f'\n{len(issues)} issues found:')
    for issue in issues:
        print(f'  - {issue}')
else:
    print('All wiki content looks good')
" 2>&1 | tee phase2/wiki_check.txt

=======================================================================
CHECK 7: Line counts
=======================================================================

Run:

echo "=== Line Counts ==="
for f in plotter_barplot_app.py plotter_functions.py plotter_widgets.py \
         plotter_validators.py plotter_results.py plotter_registry.py \
         plotter_tabs.py plotter_app_icons.py plotter_presets.py \
         plotter_session.py plotter_events.py plotter_types.py \
         plotter_undo.py plotter_errors.py plotter_comparisons.py \
         plotter_project.py plotter_import_pzfx.py \
         plotter_wiki_content.py plotter_app_wiki.py; do
    if [ -f "$f" ]; then
        lines=$(wc -l < "$f")
        printf "  %-35s %5d lines\n" "$f" "$lines"
    else
        printf "  %-35s MISSING\n" "$f"
    fi
done

=======================================================================
TASK: Update documentation
=======================================================================

Update CLAUDE.md with:

1. Updated file map showing ALL files with line counts
2. Updated list of chart types (now includes 7 new ones)
3. New section: "Phase 2 Changes" summarizing:
   - 7 new infrastructure modules
   - 7 new chart types registered
   - Bug fixes (list them)
   - New features: presets, session persistence, .cplot project files,
     .pzfx import, custom comparisons, statistical wiki, undo/redo,
     keyboard shortcuts, event bus
4. Updated "Adding a new chart type" checklist to include:
   - Add icon to plotter_app_icons.py
   - Add PlotTypeConfig to plotter_registry.py
   - Add function to plotter_functions.py
5. New gotchas section for:
   - Tests must run with xvfb-run on headless systems
   - All new modules use plotter_ prefix
   - Event bus is available but not yet widely used
   - .cplot files are ZIP archives

Update README.md with:
1. New project name: Claude Plotter
2. Updated feature list
3. Supported file formats: .xlsx, .xls, .cplot, .pzfx (import)
4. New chart types listed

=======================================================================
FINAL: Create summary and commit
=======================================================================

Create phase2/PHASE2_SUMMARY.md:

    # Phase 2 Build Summary
    
    ## Test Results
    - Total tests: [number]
    - Passing: [number]
    - Failing: [number]
    
    ## New Files Created
    [list all new .py files]
    
    ## Existing Files Modified
    [list modified files with brief description]
    
    ## Features Added
    [numbered list]
    
    ## Bugs Fixed
    [numbered list]
    
    ## Known Issues
    [list anything from KNOWN_ISSUES.txt]
    
    ## Verification Checks
    - [ ] All tests pass
    - [ ] All modules import
    - [ ] No duplicate definitions
    - [ ] No stale prism_ references
    - [ ] Wiki content complete
    - [ ] Documentation updated

git add -A
git commit -m "docs(agent-g): verification complete, documentation updated

Verification results:
- All tests passing
- All modules import cleanly
- No duplicate definitions
- Documentation updated (CLAUDE.md, README.md)
- Phase 2 summary created

Ready for merge to master."
