"""
run_all.py
==========
Unified test runner for all Refraction test suites.

Runs all five suites in a single Python process sharing the already-loaded
plotter_functions module (saves ~3–5 s vs running each file separately).

Suites:
    stats           — statistical verification + control-group logic
    validators      — spreadsheet validators
    specs           — Plotly spec builders + server
    api             — FastAPI endpoint tests

Usage:
    python3 run_all.py                       # run all suites
    python3 run_all.py comprehensive         # one suite only
    python3 run_all.py stats validators      # two suites
"""

import sys, os, time, importlib, argparse

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "tests"))

import plotter_test_harness as _h   # pre-loads pf

LINE = "━" * 64

SUITES = {
    "stats":         "test_stats",
    "validators":    "test_validators",
    "specs":         "test_phase3_plotly",
    "api":           "test_api",
    "analysis":      "test_analysis",
    "spec_correctness": "test_spec_correctness",
    "edge_cases":    "test_edge_cases",
    "api_integration": "test_api_integration",
    "invariants":    "test_invariants",
}


def run_suite(module_name: str, label: str) -> tuple[int, int, list]:
    """Execute one test suite module. Returns (passed, failed, errors)."""
    # Reset harness counters so this suite starts fresh
    _h.PASS = 0; _h.FAIL = 0; _h.ERRORS = []

    print(f"\n{LINE}")
    print(f"  SUITE: {label}  →  {module_name}.py")
    print(LINE)

    t0 = time.perf_counter()

    # Force re-execution even if previously imported
    sys.modules.pop(module_name, None)
    try:
        importlib.import_module(module_name)
    except SystemExit:
        pass    # test files call sys.exit at the end — absorb it
    except Exception as exc:
        import traceback
        print(f"\n  ✗  Suite import/execution crashed:\n     {exc}")
        traceback.print_exc()

    elapsed = time.perf_counter() - t0
    p, f = _h.PASS, _h.FAIL
    errs  = list(_h.ERRORS)  # copy before next reset

    status = "✓ all passed" if f == 0 else f"✗ {f} failed"
    print(f"\n  {status} ({p} passed, {p+f} total, {elapsed:.1f}s)")
    return p, f, errs


def main():
    parser = argparse.ArgumentParser(description="Refraction unified test runner")
    parser.add_argument("suites", nargs="*",
                        help="Suite name(s): comprehensive / stats / validators / "
                             "specs / api "
                             "(default: all)")
    args = parser.parse_args()

    requested = args.suites if args.suites else list(SUITES.keys())
    unknown   = [s for s in requested if s not in SUITES]
    if unknown:
        print(f"Unknown suite(s): {unknown}  |  available: {list(SUITES.keys())}")
        sys.exit(1)

    total_p = total_f = 0
    all_errors: list[str] = []
    wall_t0 = time.perf_counter()

    for key in requested:
        p, f, errs = run_suite(SUITES[key], key)
        total_p += p; total_f += f
        all_errors.extend(errs)

    wall = time.perf_counter() - wall_t0

    print(f"\n{LINE}")
    print("  AGGREGATED RESULTS")
    print(LINE)
    print(f"  Suites:    {len(requested)}")
    print(f"  ✓ PASSED:  {total_p}")
    print(f"  ✗ FAILED:  {total_f}")
    print(f"  TOTAL:     {total_p + total_f}")
    print(f"  Wall time: {wall:.1f}s")

    if all_errors:
        print(f"\n{LINE}")
        print("  ALL FAILURES:")
        print(LINE)
        for e in all_errors:
            print(e)

    sys.exit(0 if total_f == 0 else 1)


if __name__ == "__main__":
    main()
