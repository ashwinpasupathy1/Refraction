---
name: fix-tests
description: Diagnose and fix failing tests in the Claude Prism test suite
---

You are fixing failing tests in Claude Prism. Run the test suite, diagnose failures, and fix the root cause.

## Step 1 — Run the full suite

```bash
python3 run_all.py
```

Note the exact count of failures and which suite(s) they are in.

## Step 2 — Run the failing suite(s) in isolation

```bash
python3 run_all.py comprehensive
python3 run_all.py canvas_renderer
python3 run_all.py modular
python3 run_all.py p1p2p3
python3 run_all.py control
```

Collect the exact error messages and tracebacks.

## Step 3 — Diagnose

For each failure, determine whether it is:
- **A broken function** — the chart function raises an exception or produces wrong output
- **A broken test** — the test assertion is wrong (e.g. testing stale behavior)
- **A missing fixture** — the test uses data that no longer matches the expected format
- **A regression** — a recent code change broke existing behavior

Prefer fixing the source code over changing tests. Only update a test if the test itself is genuinely wrong.

## Step 4 — Fix

Make the minimal change needed to fix the root cause. Do not refactor surrounding code.

## Step 5 — Verify

Run `python3 run_all.py` again. The final output must show **0 failures** and a test count ≥ 571. Report the before/after counts.
