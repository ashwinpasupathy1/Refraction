#!/bin/bash
set -e
cd "$(dirname "$0")/.."

echo "=== Agent 0: Renaming prism → plotter ==="

BRANCH=$(git branch --show-current)
if [ "$BRANCH" != "master" ]; then
    echo "ERROR: Must be on master branch. Currently on: $BRANCH"
    exit 1
fi

echo "Step 0: Baseline test run..."
BASELINE=$(xvfb-run python3 run_all.py 2>&1 | grep "PASSED:" | tail -1 | grep -oP '\d+')
echo "  Baseline: $BASELINE tests passing"

echo ""
echo "Step 1: Rename files..."
for f in prism_barplot_app.py prism_functions.py prism_widgets.py \
         prism_validators.py prism_results.py prism_registry.py \
         prism_tabs.py; do
    if [ -f "$f" ]; then
        newname=$(echo "$f" | sed 's/^prism_/plotter_/')
        git mv "$f" "$newname"
        echo "  $f → $newname"
    fi
done

echo ""
echo "Step 2: Rename module imports..."
find . -name "*.py" -not -path "./.git/*" -not -path "./phase2/*" | while read pyfile; do
    sed -i \
        -e 's/import prism_functions/import plotter_functions/g' \
        -e 's/import prism_widgets/import plotter_widgets/g' \
        -e 's/import prism_validators/import plotter_validators/g' \
        -e 's/import prism_results/import plotter_results/g' \
        -e 's/import prism_registry/import plotter_registry/g' \
        -e 's/import prism_tabs/import plotter_tabs/g' \
        -e 's/import prism_barplot_app/import plotter_barplot_app/g' \
        -e 's/import prism_test_harness/import plotter_test_harness/g' \
        -e 's/from prism_functions/from plotter_functions/g' \
        -e 's/from prism_widgets/from plotter_widgets/g' \
        -e 's/from prism_validators/from plotter_validators/g' \
        -e 's/from prism_results/from plotter_results/g' \
        -e 's/from prism_registry/from plotter_registry/g' \
        -e 's/from prism_tabs/from plotter_tabs/g' \
        -e 's/from prism_barplot_app/from plotter_barplot_app/g' \
        -e 's/from prism_test_harness/from plotter_test_harness/g' \
        -e 's/from prism_canvas_renderer/from plotter_canvas_renderer/g' \
        "$pyfile"
done

echo ""
echo "Step 3: Rename function definitions..."
find . -name "*.py" -not -path "./.git/*" -not -path "./phase2/*" | while read pyfile; do
    sed -i \
        -e 's/def prism_barplot(/def plotter_barplot(/g' \
        -e 's/def prism_linegraph(/def plotter_linegraph(/g' \
        -e 's/def prism_grouped_barplot(/def plotter_grouped_barplot(/g' \
        -e 's/def prism_boxplot(/def plotter_boxplot(/g' \
        -e 's/def prism_scatterplot(/def plotter_scatterplot(/g' \
        -e 's/def prism_violin(/def plotter_violin(/g' \
        -e 's/def prism_kaplan_meier(/def plotter_kaplan_meier(/g' \
        -e 's/def prism_heatmap(/def plotter_heatmap(/g' \
        -e 's/def prism_two_way_anova(/def plotter_two_way_anova(/g' \
        -e 's/def prism_before_after(/def plotter_before_after(/g' \
        -e 's/def prism_histogram(/def plotter_histogram(/g' \
        -e 's/def prism_subcolumn_scatter(/def plotter_subcolumn_scatter(/g' \
        -e 's/def prism_curve_fit(/def plotter_curve_fit(/g' \
        -e 's/def prism_column_stats(/def plotter_column_stats(/g' \
        -e 's/def prism_contingency(/def plotter_contingency(/g' \
        -e 's/def prism_repeated_measures(/def plotter_repeated_measures(/g' \
        -e 's/def prism_chi_square_gof(/def plotter_chi_square_gof(/g' \
        -e 's/def prism_stacked_bar(/def plotter_stacked_bar(/g' \
        -e 's/def prism_bubble(/def plotter_bubble(/g' \
        -e 's/def prism_dot_plot(/def plotter_dot_plot(/g' \
        -e 's/def prism_bland_altman(/def plotter_bland_altman(/g' \
        -e 's/def prism_forest_plot(/def plotter_forest_plot(/g' \
        -e 's/def prism_area_chart(/def plotter_area_chart(/g' \
        -e 's/def prism_raincloud(/def plotter_raincloud(/g' \
        -e 's/def prism_qq_plot(/def plotter_qq_plot(/g' \
        -e 's/def prism_lollipop(/def plotter_lollipop(/g' \
        -e 's/def prism_waterfall(/def plotter_waterfall(/g' \
        -e 's/def prism_pyramid(/def plotter_pyramid(/g' \
        -e 's/def prism_ecdf(/def plotter_ecdf(/g' \
        -e 's/def _apply_prism_style(/def _apply_plotter_style(/g' \
        -e 's/def prism_link(/def plotter_link(/g' \
        "$pyfile"
done

echo ""
echo "Step 4: Rename function CALLS and string references..."
find . -name "*.py" -not -path "./.git/*" -not -path "./phase2/*" | while read pyfile; do
    sed -i \
        -e 's/prism_barplot(/plotter_barplot(/g' \
        -e 's/prism_linegraph(/plotter_linegraph(/g' \
        -e 's/prism_grouped_barplot(/plotter_grouped_barplot(/g' \
        -e 's/prism_boxplot(/plotter_boxplot(/g' \
        -e 's/prism_scatterplot(/plotter_scatterplot(/g' \
        -e 's/prism_violin(/plotter_violin(/g' \
        -e 's/prism_kaplan_meier(/plotter_kaplan_meier(/g' \
        -e 's/prism_heatmap(/plotter_heatmap(/g' \
        -e 's/prism_two_way_anova(/plotter_two_way_anova(/g' \
        -e 's/prism_before_after(/plotter_before_after(/g' \
        -e 's/prism_histogram(/plotter_histogram(/g' \
        -e 's/prism_subcolumn_scatter(/plotter_subcolumn_scatter(/g' \
        -e 's/prism_curve_fit(/plotter_curve_fit(/g' \
        -e 's/prism_column_stats(/plotter_column_stats(/g' \
        -e 's/prism_contingency(/plotter_contingency(/g' \
        -e 's/prism_repeated_measures(/plotter_repeated_measures(/g' \
        -e 's/prism_chi_square_gof(/plotter_chi_square_gof(/g' \
        -e 's/prism_stacked_bar(/plotter_stacked_bar(/g' \
        -e 's/prism_bubble(/plotter_bubble(/g' \
        -e 's/prism_dot_plot(/plotter_dot_plot(/g' \
        -e 's/prism_bland_altman(/plotter_bland_altman(/g' \
        -e 's/prism_forest_plot(/plotter_forest_plot(/g' \
        -e 's/prism_area_chart(/plotter_area_chart(/g' \
        -e 's/prism_raincloud(/plotter_raincloud(/g' \
        -e 's/prism_qq_plot(/plotter_qq_plot(/g' \
        -e 's/prism_lollipop(/plotter_lollipop(/g' \
        -e 's/prism_waterfall(/plotter_waterfall(/g' \
        -e 's/prism_pyramid(/plotter_pyramid(/g' \
        -e 's/prism_ecdf(/plotter_ecdf(/g' \
        -e 's/_apply_prism_style(/_apply_plotter_style(/g' \
        -e 's/_prism_palette_n/_plotter_palette_n/g' \
        -e 's/prism_link(/plotter_link(/g' \
        "$pyfile"
done

echo ""
echo "Step 5: Rename string references (fn_name= and quoted names)..."
find . -name "*.py" -not -path "./.git/*" -not -path "./phase2/*" | while read pyfile; do
    sed -i \
        -e 's/"prism_barplot"/"plotter_barplot"/g' \
        -e 's/"prism_linegraph"/"plotter_linegraph"/g' \
        -e 's/"prism_grouped_barplot"/"plotter_grouped_barplot"/g' \
        -e 's/"prism_boxplot"/"plotter_boxplot"/g' \
        -e 's/"prism_scatterplot"/"plotter_scatterplot"/g' \
        -e 's/"prism_violin"/"plotter_violin"/g' \
        -e 's/"prism_kaplan_meier"/"plotter_kaplan_meier"/g' \
        -e 's/"prism_heatmap"/"plotter_heatmap"/g' \
        -e 's/"prism_two_way_anova"/"plotter_two_way_anova"/g' \
        -e 's/"prism_before_after"/"plotter_before_after"/g' \
        -e 's/"prism_histogram"/"plotter_histogram"/g' \
        -e 's/"prism_subcolumn_scatter"/"plotter_subcolumn_scatter"/g' \
        -e 's/"prism_curve_fit"/"plotter_curve_fit"/g' \
        -e 's/"prism_column_stats"/"plotter_column_stats"/g' \
        -e 's/"prism_contingency"/"plotter_contingency"/g' \
        -e 's/"prism_repeated_measures"/"plotter_repeated_measures"/g' \
        -e 's/"prism_chi_square_gof"/"plotter_chi_square_gof"/g' \
        -e 's/"prism_stacked_bar"/"plotter_stacked_bar"/g' \
        -e 's/"prism_bubble"/"plotter_bubble"/g' \
        -e 's/"prism_dot_plot"/"plotter_dot_plot"/g' \
        -e 's/"prism_bland_altman"/"plotter_bland_altman"/g' \
        -e 's/"prism_forest_plot"/"plotter_forest_plot"/g' \
        -e 's/"prism_area_chart"/"plotter_area_chart"/g' \
        -e 's/"prism_raincloud"/"plotter_raincloud"/g' \
        -e 's/"prism_qq_plot"/"plotter_qq_plot"/g' \
        -e 's/"prism_lollipop"/"plotter_lollipop"/g' \
        -e 's/"prism_waterfall"/"plotter_waterfall"/g' \
        -e 's/"prism_pyramid"/"plotter_pyramid"/g' \
        -e 's/"prism_ecdf"/"plotter_ecdf"/g' \
        -e "s/'prism_barplot'/'plotter_barplot'/g" \
        -e "s/'prism_linegraph'/'plotter_linegraph'/g" \
        -e "s/'prism_grouped_barplot'/'plotter_grouped_barplot'/g" \
        -e "s/'prism_boxplot'/'plotter_boxplot'/g" \
        -e "s/'prism_scatterplot'/'plotter_scatterplot'/g" \
        -e "s/'prism_violin'/'plotter_violin'/g" \
        -e "s/'prism_kaplan_meier'/'plotter_kaplan_meier'/g" \
        -e "s/'prism_heatmap'/'plotter_heatmap'/g" \
        -e "s/'prism_two_way_anova'/'plotter_two_way_anova'/g" \
        -e "s/'prism_before_after'/'plotter_before_after'/g" \
        -e "s/'prism_histogram'/'plotter_histogram'/g" \
        -e "s/'prism_subcolumn_scatter'/'plotter_subcolumn_scatter'/g" \
        -e "s/'prism_curve_fit'/'plotter_curve_fit'/g" \
        -e "s/'prism_column_stats'/'plotter_column_stats'/g" \
        -e "s/'prism_contingency'/'plotter_contingency'/g" \
        -e "s/'prism_repeated_measures'/'plotter_repeated_measures'/g" \
        -e "s/'prism_chi_square_gof'/'plotter_chi_square_gof'/g" \
        -e "s/'prism_stacked_bar'/'plotter_stacked_bar'/g" \
        -e "s/'prism_bubble'/'plotter_bubble'/g" \
        -e "s/'prism_dot_plot'/'plotter_dot_plot'/g" \
        -e "s/'prism_bland_altman'/'plotter_bland_altman'/g" \
        -e "s/'prism_forest_plot'/'plotter_forest_plot'/g" \
        "$pyfile"
done

echo ""
echo "Step 6: Rename test harness file..."
if [ -f "tests/prism_test_harness.py" ]; then
    git mv tests/prism_test_harness.py tests/plotter_test_harness.py
    echo "  tests/prism_test_harness.py → tests/plotter_test_harness.py"
fi

echo ""
echo "Step 7: Rename branding strings..."
find . -name "*.py" -not -path "./.git/*" -not -path "./phase2/*" | while read pyfile; do
    sed -i \
        -e 's/Claude Prism/Claude Plotter/g' \
        -e 's/claude_prism/claude_plotter/g' \
        -e 's/"Default (Prism)"/"Default"/g' \
        -e "s/'Default (Prism)'/'Default'/g" \
        -e 's/Open (Prism default)/Open (default)/g' \
        -e 's/claude_prism_showcase/claude_plotter_showcase/g' \
        -e 's/claude_prism_template/claude_plotter_template/g' \
        "$pyfile"
done

echo ""
echo "Step 8: Rename in hooks and config..."
if [ -f ".claude/hooks/update_docs.py" ]; then
    sed -i \
        -e 's/prism_canvas_renderer/plotter_canvas_renderer/g' \
        -e 's/prism_barplot_app/plotter_barplot_app/g' \
        -e 's/prism_functions/plotter_functions/g' \
        .claude/hooks/update_docs.py
    echo "  Updated .claude/hooks/update_docs.py"
fi

echo ""
echo "Step 9: Update markdown docs..."
for f in CLAUDE.md README.md; do
    if [ -f "$f" ]; then
        sed -i \
            -e 's/prism_barplot_app/plotter_barplot_app/g' \
            -e 's/prism_functions/plotter_functions/g' \
            -e 's/prism_widgets/plotter_widgets/g' \
            -e 's/prism_validators/plotter_validators/g' \
            -e 's/prism_results/plotter_results/g' \
            -e 's/prism_registry/plotter_registry/g' \
            -e 's/prism_tabs/plotter_tabs/g' \
            -e 's/prism_test_harness/plotter_test_harness/g' \
            -e 's/prism_canvas_renderer/plotter_canvas_renderer/g' \
            -e 's/prism_linegraph/plotter_linegraph/g' \
            -e 's/prism_grouped_barplot/plotter_grouped_barplot/g' \
            -e 's/prism_barplot/plotter_barplot/g' \
            -e 's/Claude Prism/Claude Plotter/g' \
            "$f"
        echo "  Updated $f"
    fi
done

echo ""
echo "Step 10: Fix run_all.py import..."
if [ -f "run_all.py" ]; then
    sed -i 's/import prism_test_harness/import plotter_test_harness/g' run_all.py
    echo "  Updated run_all.py"
fi

echo ""
echo "Step 11: Clean __pycache__..."
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

echo ""
echo "Step 12: Check for remaining prism_ references that need fixing..."
REMAINING=$(grep -rn "prism_barplot\|prism_functions\|prism_widgets\|prism_validators\|prism_results\|prism_registry\|prism_tabs\b" \
    --include="*.py" --exclude-dir=.git --exclude-dir=phase2 . 2>/dev/null | \
    grep -v "GraphPad Prism" | grep -v "# .*prism" | grep -v "Extracted from prism_barplot_final" | wc -l)
if [ "$REMAINING" -gt 0 ]; then
    echo "  ⚠️  $REMAINING remaining prism_ module references found:"
    grep -rn "prism_barplot\|prism_functions\|prism_widgets\|prism_validators\|prism_results\|prism_registry\|prism_tabs\b" \
        --include="*.py" --exclude-dir=.git --exclude-dir=phase2 . 2>/dev/null | \
        grep -v "GraphPad Prism" | grep -v "# .*prism" | grep -v "Extracted from prism_barplot_final" | head -20
fi

echo ""
echo "Step 13: Verify tests..."
RESULT=$(xvfb-run python3 run_all.py 2>&1 | grep "PASSED:" | tail -1 | grep -oP '\d+')
echo "  After rename: $RESULT tests passing (was $BASELINE)"

if [ "$RESULT" -ge "$BASELINE" ]; then
    echo "  ✅ Rename successful — no regressions"
    git add -A
    git commit -m "refactor: rename prism → plotter throughout codebase

Mechanical rename to distinguish from GraphPad Prism.
References TO GraphPad Prism in wiki/docs preserved.
All $RESULT tests passing."
    echo "  Committed. Ready for Phase 2 agents."
else
    echo "  ❌ REGRESSION. Was $BASELINE, now $RESULT"
    echo "  Checking what failed..."
    xvfb-run python3 run_all.py 2>&1 | grep -E "(FAILED|Error|Module)" | head -20
    echo ""
    echo "  To revert: git reset --hard HEAD && find . -type d -name __pycache__ -exec rm -rf {} +"
    exit 1
fi
