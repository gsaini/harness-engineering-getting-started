# 4 · Verification (v3)

**Eval failure:** `two-bugs` — `mean()` and `median()` are both wrong. The scripted model fixes `mean()` and calls `finish` without running the tests. v0–v2 believe it; the grader finds `test_median_even_count` still failing.

**Fix:** `finish` runs the test suite. If anything fails, the call is refused and the failures go back to the model:

```text
Not done yet: the test suite fails.
FAILED tests/test_stats.py::test_median_even_count - assert 3 == 2.5
Fix the failures, then call finish again.
```

The model fixes `median()` and finishes for real.

## Principles

- **"Done" is a claim; verification is evidence.** The agent saying it finished tells you it stopped, not that it succeeded.
- **The verifier must not be the implementer.** The check is code the agent can't edit (tests are read-only since v2), not the model grading itself.
- **Make verification hard to fool.** The evals caught a real bug here: after an edit that kept a file's size the same within one second, Python reused a stale `.pyc` and the tests checked the *old* code. The harness now runs tests with `PYTHONDONTWRITEBYTECODE=1`, and a regression test pins it.
- **"No tests" isn't failure.** pytest exits with code 5 when nothing is collected; an early version treated that as a failing suite and bounced `finish` forever on a task with no tests.
- **Verify the state the turn leaves behind.** `finish` runs after any other tool calls in its turn. An early version verified first, and an edit requested alongside `finish` went through unchecked.
- **An exit code is a claim too.** v3 trusts pytest's exit code, and the code under test can buy one: a module that skips itself, or ends the process with `os._exit(0)`, is green here. [08 · Evidence](08-evidence.md) is the fix.
