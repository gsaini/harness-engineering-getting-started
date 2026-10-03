# 1 · The loop

[`run_agent`](../src/harness/loop.py) is the whole agent: ask the model, run the tools it asks for, append the results, repeat.

```text
messages = [task]
loop:
    response = model(system, tools, messages)     # system + tools are frozen for the run
    messages += response                           # verbatim — never edited later
    stop_reason?  refusal → stop · max_tokens → stop · pause_turn → resume
    no tool calls → done (v0–v1) · nudge to call `finish` (v2+)
    run every tool call, `finish` last → messages += all results, in one turn
```

## Four rules that look small and aren't

1. **History is append-only.** Current Claude models bind their thinking to the exact conversation that produced it. Edit, reorder, or delete an earlier turn — even "just trimming an old tool result" — and the model's earlier reasoning is invalidated (newer accounts get a 400) and the prompt cache restarts. So the loop only ever appends, and shaping output happens *before* it enters the history ([05 · Context](05-context.md)). A test checks every request's history is an unedited prefix of the next.
2. **System prompt and tools are frozen for the run.** Same reason, plus caching: the prefix `tools → system → messages` is what gets cached, and any byte change invalidates it. Lessons the agent learns take effect on the *next* run ([06 · Memory](06-memory.md)).
3. **Append the response as returned.** `response.content` can contain `thinking` blocks (often with empty text) and `fallback` blocks. Pass them back unchanged; don't rebuild the assistant turn from its text.
4. **Return all tool results in one turn.** One assistant turn can request several tools. Send every result back in a single user message, including errors; splitting them teaches the model to stop calling tools in parallel.

## Every stop reason has a branch

| `stop_reason` | What the harness does |
|---------------|-----------------------|
| `tool_use` | run the tools, append the results, continue |
| `end_turn` | done (v0–v1) or nudge once to call `finish`, then `stalled` (v2+) |
| `refusal` | stop and report. With `fallbacks: "default"` the API has already retried on a fallback model, so a refusal here means the whole chain declined |
| `max_tokens` | stop and report — a cut-off tool call can't be run. Thinking counts toward `max_tokens`, hence the 64K default |
| `pause_turn` | append and resume (only server-side tools pause) |

## Lab safety, in every version

These aren't lessons; they keep experiments safe and cheap even for the deliberately naive v0:

- **The floor** — every path must stay inside the run directory, so no version can touch your real files.
- **Step limit** (30) and a **context budget** (~100K estimated tokens, checked *before* each request) — a runaway loop stops before it spends.
