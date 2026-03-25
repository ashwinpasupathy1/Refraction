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
    python3 run_all.py stats                 # test_stats.py
    python3 run_all.py validators            # test_validators.py
    python3 run_all.py api                   # test_api.py
    python3 run_all.py engine                # tests/engine/ only
    python3 run_all.py integration           # tests/integration/ only
    python3 run_all.py stats_exhaustive      # test_stats_exhaustive.py
    python3 run_all.py analysis              # test_analysis.py
"""

import sys
import os
import argparse

_HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    parser = argparse.ArgumentParser(description="Refraction unified test runner")
    parser.add_argument("suites", nargs="*",
                        help="Suite name(s): engine / integration / stats / validators / "
                             "api / analysis / qa / stats_exhaustive (default: run all)")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Verbose pytest output")
    args = parser.parse_args()

    SUITES = {
        "engine": os.path.join(_HERE, "tests", "engine"),
        "integration": os.path.join(_HERE, "tests", "integration"),
        "api": os.path.join(_HERE, "tests", "test_api.py"),
        "qa": os.path.join(_HERE, "tests", "test_phase6_qa.py"),
        "stats": os.path.join(_HERE, "tests", "test_stats.py"),
        "stats_exhaustive": os.path.join(_HERE, "tests", "test_stats_exhaustive.py"),
        "validators": os.path.join(_HERE, "tests", "test_validators.py"),
        "analysis": os.path.join(_HERE, "tests", "test_analysis.py"),
        "deficiency": os.path.join(_HERE, "tests", "test_deficiency_fixes.py"),
    }

    requested = args.suites if args.suites else list(SUITES.keys())

    unknown = [s for s in requested if s not in SUITES]
    if unknown:
        all_available = sorted(SUITES.keys())
        print(f"Unknown suite(s): {unknown}  |  available: {all_available}")
        sys.exit(1)

    import pytest
    pytest_args = []
    for suite_name in requested:
        path = SUITES[suite_name]
        if os.path.exists(path):
            pytest_args.append(path)
        else:
            print(f"Warning: suite path does not exist: {path}")
    pytest_args.append("-v")

    result = pytest.main(pytest_args)
    sys.exit(result)


if __name__ == "__main__":
    main()
