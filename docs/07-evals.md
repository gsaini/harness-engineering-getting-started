# 7 · Evals

Evals are how you notice a mistake, and how you prove the fix without breaking anything else.

## The tasks

| Task | Failure it exposes | Graded by |
|------|--------------------|-----------|
| `fix-pagination` | — (baseline: everyone should pass) | pytest |
| `wrong-path` | a stale path crashes the run | pytest |
| `tempting-test` | editing the test instead of the code | pytest, after restoring the original tests |
| `poisoned-readme` | obeying instructions planted in a file | pytest + the decoy `neighbor/` project unchanged |
| `two-bugs` | declaring victory early | pytest |
| `big-log` | reading a huge file whole | `answer.txt` |

Each run gets a fresh copy of the task in a temporary run directory. The grader is code, not a model: it detects (and undoes) changes to read-only files, checks the decoy project next to the workspace, runs the real test suite, and compares expected files.

## Two kinds of runs

- **Scripted (offline, free).** [`scripted.py`](../src/harness/scripted.py) replays policies that reproduce each failure mode. This proves the **mechanism** — each version catches the failure it was built for, and [`test_evals.py`](../tests/test_evals.py) pins the whole scoreboard so a regression fails CI. It says nothing about how often a real model fails.
- **Live.** `harness eval --model claude-opus-5-5 --yes` runs the same tasks against Claude. A capable model won't fall for every trap, so expect more passes in early versions than the scripted run shows. What's worth watching is whether each version holds up on *every* task — and the steps, tokens, and cost it took.

## Adding a fix, the harness-engineering way

1. **Reproduce** the failure as a task: `evals/tasks/<name>/` with `task.json`, a `workspace/`, and the check that should pass.
2. **Watch it fail** — in a trace: `harness trace runs/<stamp>/<task>-<version>.jsonl`.
3. **Fix the harness**, behind a flag in [`config.py`](../src/harness/config.py) so the old version still runs.
4. **Re-run every task on every version.** The fix should flip one cell and leave the rest alone.

## Bugs the evals caught in the harness itself

- `finish` bounced forever on a task with no tests (pytest exit code 5).
- An early v2 nudged a quiet model forever — hence the `stalled` status.
- Verification passed on stale bytecode after a same-size edit.

Evals test the harness, not just the agent.
