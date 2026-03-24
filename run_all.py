"""
run_all.py
==========
Unified test runner for all Refraction test suites.

Runs pytest on the test structure:
    tests/engine/       -- Pure computational tests (stats, validators, helpers)
    tests/integration/  -- API and pipeline integration tests
    tests/              -- Top-level analysis, stats, validators, QA tests

Usage:
    python3 run_all.py                       # run all pytest tests
    python3 run_all.py stats                 # legacy: old test_stats.py
    python3 run_all.py validators            # legacy: old test_validators.py
    python3 run_all.py api                   # pytest: test_api.py
    python3 run_all.py engine                # pytest: tests/engine/ only
    python3 run_all.py integration           # pytest: tests/integration/ only
"""

import sys
import os
import argparse

_HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    parser = argparse.ArgumentParser(description="Refraction unified test runner")
    parser.add_argument("suites", nargs="*",
                        help="Suite name(s): engine / integration / stats / validators / "
                             "api / analysis / qa (default: run all)")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Verbose pytest output")
    args = parser.parse_args()

    # New pytest-based suites
    NEW_SUITES = {
        "engine": os.path.join(_HERE, "tests", "engine"),
        "integration": os.path.join(_HERE, "tests", "integration"),
        "api": os.path.join(_HERE, "tests", "test_api.py"),
        "qa": os.path.join(_HERE, "tests", "test_phase6_qa.py"),
    }

    # Legacy suites (old harness-based tests, kept for backward compat)
    LEGACY_SUITES = {
        "stats": "test_stats",
        "stats_exhaustive": "test_stats_exhaustive",
        "validators": "test_validators",
        "analysis": "test_analysis",
    }

    requested = args.suites if args.suites else list(NEW_SUITES.keys())

    # Check for legacy suite names
    legacy_requested = [s for s in requested if s in LEGACY_SUITES]
    new_requested = [s for s in requested if s in NEW_SUITES]
    unknown = [s for s in requested if s not in LEGACY_SUITES and s not in NEW_SUITES]

    if unknown:
        all_available = sorted(set(list(NEW_SUITES.keys()) + list(LEGACY_SUITES.keys())))
        print(f"Unknown suite(s): {unknown}  |  available: {all_available}")
        sys.exit(1)

    exit_code = 0

    # Run new pytest suites
    if new_requested:
        import pytest
        pytest_args = []
        for suite_name in new_requested:
            pytest_args.append(NEW_SUITES[suite_name])
        pytest_args.append("-v")
        result = pytest.main(pytest_args)
        if result != 0:
            exit_code = 1

    # Run legacy suites if explicitly requested
    if legacy_requested:
        import time
        import importlib

        sys.path.insert(0, os.path.join(_HERE, "tests"))
        import plotter_test_harness as _h

        LINE = "\u2501" * 64
        total_p = total_f = 0
        all_errors = []

        for key in legacy_requested:
            module_name = LEGACY_SUITES[key]
            _h.PASS = 0
            _h.FAIL = 0
            _h.ERRORS = []

            print(f"\n{LINE}")
            print(f"  SUITE: {key}  ->  {module_name}.py")
            print(LINE)

            t0 = time.perf_counter()
            sys.modules.pop(module_name, None)
            try:
                importlib.import_module(module_name)
            except SystemExit:
                pass
            except Exception as exc:
                import traceback
                print(f"\n  X  Suite crashed:\n     {exc}")
                traceback.print_exc()

            elapsed = time.perf_counter() - t0
            p, f = _h.PASS, _h.FAIL
            errs = list(_h.ERRORS)
            total_p += p
            total_f += f
            all_errors.extend(errs)

            status = "all passed" if f == 0 else f"{f} failed"
            print(f"\n  {status} ({p} passed, {p+f} total, {elapsed:.1f}s)")

        print(f"\n{LINE}")
        print("  LEGACY SUITE RESULTS")
        print(LINE)
        print(f"  PASSED:  {total_p}")
        print(f"  FAILED:  {total_f}")
        print(f"  TOTAL:   {total_p + total_f}")

        if total_f > 0:
            exit_code = 1

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
