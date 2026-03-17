#!/usr/bin/env python3
"""
update_docs.py
==============
SessionStart hook for Claude Prism.
Runs once at the start of each new session to refresh README.md and CLAUDE.md
with current file line counts and registered chart type counts.

Outputs a brief status summary to stdout (added to Claude's session context).
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent  # .claude/hooks/ -> project root

# ── Source files tracked in the File Map ─────────────────────────────────────
SOURCE_FILES = [
    "prism_barplot_app.py",
    "prism_functions.py",
    "prism_canvas_renderer.py",
    "prism_widgets.py",
    "prism_validators.py",
    "prism_results.py",
    "prism_test_harness.py",
    "run_all.py",
]

# ── Test suites ───────────────────────────────────────────────────────────────
TEST_FILES = {
    "comprehensive":   "test_comprehensive.py",
    "canvas_renderer": "test_canvas_renderer.py",
    "modular":         "test_modular.py",
    "p1p2p3":          "test_p1_p2_p3.py",
    "control":         "test_control.py",
}


def line_count(filename: str) -> int:
    path = ROOT / filename
    if not path.exists():
        return 0
    with open(path, "rb") as f:
        return sum(1 for _ in f)


def test_count(filename: str) -> int:
    path = ROOT / filename
    if not path.exists():
        return 0
    content = path.read_text(errors="replace")
    return len(re.findall(r"\brun\(", content))


def registered_chart_count() -> int:
    path = ROOT / "prism_barplot_app.py"
    if not path.exists():
        return 0
    content = path.read_text(errors="replace")
    return len(re.findall(r"^\s+PlotTypeConfig\(", content, re.MULTILINE))


def round_approx(n: int, base: int = 50) -> str:
    """Round n to nearest `base` and format with ~."""
    return f"~{round(n / base) * base:,}"


# ── CLAUDE.md update ──────────────────────────────────────────────────────────
def update_test_counts(
    suite_counts: dict[str, int],
    total: int,
    readme_path: Path,
    claude_path: Path,
) -> tuple[bool, bool]:
    """Update test count numbers in both docs."""
    readme_changed = False
    claude_changed = False

    for path, flag_ref in [(readme_path, readme_changed), (claude_path, claude_changed)]:
        if not path.exists():
            continue
        content = path.read_text()
        original = content

        # Total: "571 tests across 5 suites" or "571/571"
        content = re.sub(r"\b\d{3,}(?:/\d{3,})? tests\b", f"{total} tests", content)
        # "must print 571/571" style
        content = re.sub(
            r"(print\s+)(\d{3,})/(\d{3,})\b",
            rf"\g<1>{total}/{total}",
            content,
        )
        # README badge: tests-571%20passing
        content = re.sub(
            r"(tests-)\d{3,}(%20passing)",
            rf"\g<1>{total}\2",
            content,
        )

        # Per-suite comments: "# 309 tests —" or "#  80 tests —"
        suite_map = {
            "comprehensive":   suite_counts.get("comprehensive", 0),
            "canvas_renderer": suite_counts.get("canvas_renderer", 0),
            "modular":         suite_counts.get("modular", 0),
            "p1p2p3":          suite_counts.get("p1p2p3", 0),
            "control":         suite_counts.get("control", 0),
        }
        label_map = {
            "comprehensive":   "comprehensive",
            "canvas_renderer": "canvas_renderer",
            "modular":         "modular",
            "p1p2p3":          "p1p2p3",
            "control":         "control",
        }
        for key, count in suite_map.items():
            suite_label = label_map[key]
            # Match "run_all.py comprehensive      # 309 tests"
            content = re.sub(
                r"(run_all\.py\s+" + re.escape(suite_label) + r"\s+#\s*)[\d,]+( tests)",
                rf"\g<1>{count}\2",
                content,
            )
            # Also match "# 309 tests —" anywhere on a line with the suite name
            content = re.sub(
                r"(" + re.escape(suite_label) + r".*?#\s*)[\d,]+([ \t]+tests\b)",
                rf"\g<1>{count}\2",
                content,
            )

        if content != original:
            path.write_text(content)
            if path == readme_path:
                readme_changed = True
            else:
                claude_changed = True

    return readme_changed, claude_changed


def update_claude_md(counts: dict[str, int]) -> bool:
    path = ROOT / "CLAUDE.md"
    if not path.exists():
        return False

    content = path.read_text()
    original = content

    for fname, count in counts.items():
        # Match:  filename    <digits with optional comma>  lines   <description>
        # e.g.:   prism_barplot_app.py      7,834 lines   App class...
        pattern = (
            r"((?:^|\n)(?:[ \t]*)"
            + re.escape(fname)
            + r"[ \t]+)[\d,]+([ \t]+lines)"
        )
        replacement = rf"\g<1>{count:,}\2"
        content = re.sub(pattern, replacement, content)

    if content != original:
        path.write_text(content)
        return True
    return False


# ── README.md update ──────────────────────────────────────────────────────────
def update_readme(counts: dict[str, int], n_charts: int) -> bool:
    path = ROOT / "README.md"
    if not path.exists():
        return False

    content = path.read_text()
    original = content

    # Update approximate line counts in Architecture section
    readme_bases = {
        "prism_barplot_app.py":   200,
        "prism_functions.py":     200,
        "prism_canvas_renderer.py": 100,
        "prism_widgets.py":       50,
        "prism_validators.py":    10,
        "prism_results.py":       10,
    }

    for fname, base in readme_bases.items():
        if fname not in counts:
            continue
        approx = round_approx(counts[fname], base)
        pattern = (
            r"((?:^|\n)(?:[ \t]*)"
            + re.escape(fname)
            + r"[ \t]+)~[\d,]+([ \t]+lines)"
        )
        replacement = rf"\g<1>{approx}\2"
        content = re.sub(pattern, replacement, content)

    # Update chart count badge and headings
    # Badge: ![Charts](https://img.shields.io/badge/chart%20types-29-orange)
    content = re.sub(
        r"(chart%20types-)\d+(-orange)",
        rf"\g<1>{n_charts}\2",
        content,
    )
    # "29 chart types" in prose
    content = re.sub(
        r"\b\d+ chart types\b",
        f"{n_charts} chart types",
        content,
    )
    # Badge text: ![Charts](... "29 chart types" ...)
    content = re.sub(
        r"(!\[Charts\].*?chart.types.)(\d+)",
        rf"\g<1>{n_charts}",
        content,
    )

    if content != original:
        path.write_text(content)
        return True
    return False


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    counts = {f: line_count(f) for f in SOURCE_FILES}
    suite_counts = {k: test_count(v) for k, v in TEST_FILES.items()}
    total_tests = sum(suite_counts.values())
    n_charts = registered_chart_count()

    claude_path = ROOT / "CLAUDE.md"
    readme_path = ROOT / "README.md"

    claude_updated = update_claude_md(counts)
    readme_updated = update_readme(counts, n_charts)
    readme_tests_updated, claude_tests_updated = update_test_counts(
        suite_counts, total_tests, readme_path, claude_path
    )
    claude_updated = claude_updated or claude_tests_updated
    readme_updated = readme_updated or readme_tests_updated

    # Output goes into Claude's session context
    print("=== Claude Prism — session context ===")
    print(f"Charts registered in sidebar: {n_charts}")
    print(f"Test registrations (run() calls): {total_tests}")
    print("  " + "  ".join(f"{k}={v}" for k, v in suite_counts.items()))
    print("File line counts:")
    for fname, count in counts.items():
        print(f"  {fname}: {count:,}")
    if claude_updated:
        print("CLAUDE.md: updated")
    if readme_updated:
        print("README.md: updated")
    print("=====================================")


if __name__ == "__main__":
    main()
