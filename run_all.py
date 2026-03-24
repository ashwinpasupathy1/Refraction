"""
run_all.py
==========
Unified test runner for all Refraction test suites.

Delegates to pytest. Run with:
    python3 run_all.py                       # run all suites
    python3 run_all.py stats                 # one suite only
    python3 run_all.py stats validators      # two suites

Suites map to test files:
    stats           -> tests/test_stats.py
    validators      -> tests/test_validators.py
    specs           -> tests/test_phase3_plotly.py
    api             -> tests/test_api.py
"""

import sys
import os

# Ensure project root is on sys.path
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

SUITES = {
    "stats":      "tests/test_stats.py",
    "validators": "tests/test_validators.py",
    "specs":      "tests/test_phase3_plotly.py",
    "api":        "tests/test_api.py",
}


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Refraction unified test runner")
    parser.add_argument("suites", nargs="*",
                        help="Suite name(s): stats / validators / specs / api "
                             "(default: all)")
    args = parser.parse_args()

    requested = args.suites if args.suites else list(SUITES.keys())
    unknown = [s for s in requested if s not in SUITES]
    if unknown:
        print(f"Unknown suite(s): {unknown}  |  available: {list(SUITES.keys())}")
        sys.exit(1)

    # Build pytest args
    test_files = [SUITES[key] for key in requested]
    pytest_args = ["-v", "--tb=short"] + test_files

    try:
        import pytest
        exit_code = pytest.main(pytest_args)
    except ImportError:
        print("pytest not installed. Install with: pip install pytest")
        sys.exit(1)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
