---
name: test-and-commit
description: Run the full test suite and commit if all tests pass
disable-model-invocation: true
---

1. Run `python3 run_all.py`
2. If any tests fail, stop and report which tests failed and why
3. If all tests pass, stage all changes with `git add -A`
4. Write a descriptive commit message based on what changed
5. Commit and push to the current branch
