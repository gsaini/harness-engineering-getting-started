# 6 · Memory (v4)

A harness can get better with every task by remembering what it learned about a project — the same idea as Browser Harness's domain skills or a `CLAUDE.md`, but written by the agent.

v4 adds a `remember` tool. In `wrong-path`, after finding the moved file, the scripted model saves:

```text
- Text utilities live in src/textkit/strings.py, not utils/strings.py.
```

## Rules

- **Lessons take effect on the next run.** They're loaded into the system prompt when a run starts and never change during it — the system prompt is part of the conversation the model's reasoning is bound to, and part of the cached prefix.
- **Memory is an attack surface.** Anything written there is injected into every future prompt. So: one short sentence per lesson, a cap on the number, deduplication, and the file (`.harness/lessons.md`) is **read-only to the agent's file tools** — the only way in is the `remember` tool. A test checks that `write_file` can't plant a lesson.
- **Humans review it.** The lessons live in the repository, in plain Markdown, where they show up in code review.
