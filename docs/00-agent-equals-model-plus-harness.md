# 0 · Agent = Model + Harness

The **harness** is everything in an agent that isn't the model: the loop that calls it, the tools it can use, what goes into its context, what it's allowed to touch, how you decide it's done, and how you find out what went wrong.

Harness engineering became a named discipline in 2026, and its working rule is usually credited to Mitchell Hashimoto:

> *Anytime you find an agent makes a mistake, you take the time to engineer a solution so that the agent never makes that mistake again.*

Most of the time that solution is a harness change, not a model change. Teams report large gains with the *same model* — LangChain, for example, moved its coding agent from 30th to 5th on Terminal-Bench 2.0 by changing only the harness ([State of AI Harness Engineering 2026](https://marmelab.com/blog/2026/09/24/the-state-of-ai-harness-engineering-2026.html)).

This repo makes that concrete. The model, the tools, and the six eval tasks stay fixed; only the harness changes:

| Version | Adds | Fixes | Lesson |
|---------|------|-------|--------|
| v0 | a loop and six tools | — | [01 · The loop](01-the-loop.md) |
| v1 | tool errors become feedback | a stale path crashed the run | [02 · Tools and errors](02-tools-and-errors.md) |
| v2 | workspace boundary, read-only tests, explicit `finish` | test tampering; obeying instructions planted in a file | [03 · Guardrails](03-guardrails.md) |
| v3 | `finish` runs the tests | declaring victory early | [04 · Verification](04-verification.md) |
| v4 | truncate at the source; project memory | a 1.7 MB file flooding the context | [05 · Context](05-context.md) · [06 · Memory](06-memory.md) |

The evals behind each row, and how to add your own: [07 · Evals](07-evals.md).

## Where each part lives

| Component | File | ~Lines |
|-----------|------|-------:|
| The loop | [`loop.py`](../src/harness/loop.py) | 185 |
| Tools, input validation | [`tools.py`](../src/harness/tools.py) | 250 |
| Boundaries | [`guard.py`](../src/harness/guard.py) | 50 |
| Context hygiene | [`context.py`](../src/harness/context.py) | 35 |
| Memory | [`memory.py`](../src/harness/memory.py) | 40 |
| Traces | [`trace.py`](../src/harness/trace.py) | 55 |
| Versions | [`config.py`](../src/harness/config.py) | 50 |
| Models (Claude, scripted) | [`model.py`](../src/harness/model.py), [`scripted.py`](../src/harness/scripted.py) | 285 |
| Evals and grading | [`evals.py`](../src/harness/evals.py) | 165 |
