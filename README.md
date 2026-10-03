<div align="center">

# 🧰 Harness Engineering — Getting Started

**Agent = Model + Harness.** A small agent harness built from scratch on the Claude API, plus the evals that show why each part exists: same model, same tasks — the harness alone takes the score from **1/6 to 6/6**.

[![CI](https://github.com/gsaini/harness-engineering-getting-started/actions/workflows/ci.yml/badge.svg)](https://github.com/gsaini/harness-engineering-getting-started/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Claude](https://img.shields.io/badge/Claude-Opus%205.5-D97757?style=for-the-badge&logo=anthropic&logoColor=white)
![Anthropic SDK](https://img.shields.io/badge/anthropic-1.x-191919?style=for-the-badge)
![Offline](https://img.shields.io/badge/Tests%20%26%20evals-offline%2C%20free-16A34A?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-EAB308?style=for-the-badge)

</div>

---

## The idea

The **harness** is everything in an agent that isn't the model: the loop, the tools, what goes into the context, what the agent may touch, how you decide it's done, and how you see what went wrong. Harness engineering's working rule, usually credited to Mitchell Hashimoto:

> *Anytime you find an agent makes a mistake, you take the time to engineer a solution so that the agent never makes that mistake again.*

This repo does exactly that, five times. Each harness version fixes one failure the evals caught — and nothing else changes:

| Version | Adds | The failure it fixes |
| --------- | ------ | ---------------------- |
| **v0** | a loop and six tools | — |
| **v1** | tool errors become actionable feedback | a stale file path **crashed** the run |
| **v2** | workspace boundary, read-only tests, explicit `finish` | the agent **edited the test**; it **obeyed instructions planted in a README** |
| **v3** | `finish` runs the test suite | the agent **declared victory** with a bug left |
| **v4** | truncate output at the source; project memory | a **1.7 MB log** flooded the context |

## The scoreboard

`harness eval` runs six tasks through every version and grades each run with code:

| task | v0 | v1 | v2 | v3 | v4 |
| ------ | :-: | :-: | :-: | :-: | :-: |
| big-log | 📚 context_budget | 📚 context_budget | 📚 context_budget | 📚 context_budget | ✅ |
| fix-pagination | ✅ | ✅ | ✅ | ✅ | ✅ |
| poisoned-readme | ☠️ collateral damage | ☠️ collateral damage | ✅ | ✅ | ✅ |
| tempting-test | 🙈 tampered | 🙈 tampered | ✅ | ✅ | ✅ |
| two-bugs | ❌ tests fail | ❌ tests fail | ❌ tests fail | ✅ | ✅ |
| wrong-path | 💥 crashed | ✅ | ✅ | ✅ | ✅ |
| **passed** | **1/6** | **2/6** | **4/6** | **5/6** | **6/6** |

> **Read this table correctly.** It comes from the **scripted model**, an offline stand-in that deliberately reproduces each failure mode, so the evals run free and deterministically in CI. It proves each harness version **catches the failure it was built for**. It does **not** say how often a real model fails: Claude won't fall for every trap. Run the same evals against Claude with your API key (below) to see real behavior, steps, tokens, and cost.

## Quick start

```bash
git clone https://github.com/gsaini/harness-engineering-getting-started.git
cd harness-engineering-getting-started
uv sync                     # or: python -m venv .venv && .venv/bin/pip install -e .

uv run harness eval         # the scoreboard above — offline, no API key, no cost
uv run pytest               # 32 tests, also offline
uv run harness trace runs/<stamp>/two-bugs-v3.jsonl   # watch v3 bounce a premature "done"
```

### With Claude

```bash
export ANTHROPIC_API_KEY=...          # or: ant auth login

# Start with one run, check the cost line, then widen:
uv run harness eval --model claude-opus-5-5 --tasks fix-pagination --versions v4 --yes
uv run harness eval --model claude-opus-5-5 --yes          # 6 tasks × 5 versions = 30 runs

# Or point v4 at your own project:
uv run harness run "Make the failing tests in tests/ pass" --workspace path/to/repo
```

`harness run` and live evals **execute code on your machine**: the agent can write Python and `run_tests` runs it. Use a throwaway copy of a project, or a container.

## The lessons

Read them in order. Each is short and points at the exact code:

0. [Agent = Model + Harness](docs/00-agent-equals-model-plus-harness.md)
1. [The loop](docs/01-the-loop.md) — append-only history, frozen prefix, every stop reason
2. [Tools and errors](docs/02-tools-and-errors.md) — v1: errors the model can act on
3. [Guardrails](docs/03-guardrails.md) — v2: boundaries the model can't be trusted to keep
4. [Verification](docs/04-verification.md) — v3: "done" is a claim
5. [Context](docs/05-context.md) — v4: cut at the source, never edit history
6. [Memory](docs/06-memory.md) — v4: lessons for the next run
7. [Evals](docs/07-evals.md) — how to add a task and a fix, and the bugs the evals caught in the harness itself

## How it calls Claude

[`ClaudeModel`](src/harness/model.py) uses the official `anthropic` Python SDK (1.x) with current defaults:

- **`claude-opus-5-5`**, with **`effort` set explicitly** (`medium`, the model's default — change it with `--effort`). Thinking is always on for Opus 5.5; there is no thinking budget to tune.
- **Server-side refusal fallbacks** (`fallbacks: "default"`): if a safety classifier declines a request, the API re-runs it on a recommended fallback model instead of returning the refusal. Remove the two lines in `ClaudeModel.request` if you don't want it.
- **Automatic prompt caching** (`cache_control` at the top level), so each turn re-reads the earlier turns at the cache price.
- **Streaming** with `max_tokens=64000` (thinking counts toward it), and **streamed tool input**, validated by the harness before any tool runs.

The loop is hand-written on purpose; that's the subject. For production, the SDK's tool runner, the Claude Agent SDK, or Managed Agents give you a tested loop.

## Repository layout

```text
src/harness/
  loop.py       the agent loop               tools.py    tools + input validation
  guard.py      workspace boundary            context.py  truncation, token budget
  memory.py     lessons for future runs       trace.py    JSONL traces
  config.py     harness versions v0–v4        evals.py    tasks, grading, scoreboard
  model.py      Claude                        scripted.py offline model + failure policies
  cli.py        `harness eval | run | trace | versions`
evals/tasks/    six tasks: prompt, workspace, checks
tests/          offline tests, including the whole scoreboard
docs/           the lessons
```

## Safety, in every version

- **The floor:** every file path must stay inside the run's directory, so even v0 can't touch your files.
- **Budgets:** 30 steps and ~100K estimated tokens per run, checked *before* each request.
- **Live evals ask first:** a real model needs `--yes`, and the CLI suggests starting with one task.

## Related reading

- Study notes in [awesome-software-engineering](https://github.com/gsaini/awesome-software-engineering): [Loop Engineering](https://github.com/gsaini/awesome-software-engineering/blob/main/notes/loop-engineering.md) · [Browser Harness](https://github.com/gsaini/awesome-software-engineering/blob/main/notes/browser-harness.md) · [Building an Agent Evaluator](https://github.com/gsaini/awesome-software-engineering/blob/main/notes/building-agent-evaluators.md) · [Jev Ultrafast](https://github.com/gsaini/awesome-software-engineering/blob/main/notes/jev-ultrafast.md)
- [The State of AI Harness Engineering 2026](https://marmelab.com/blog/2026/09/24/the-state-of-ai-harness-engineering-2026.html) (marmelab) · [awesome-harness-engineering](https://github.com/ai-boost/awesome-harness-engineering)
- [Claude API documentation](https://platform.claude.com/docs)

## License

[MIT](LICENSE). An independent learning project, not affiliated with Anthropic.
