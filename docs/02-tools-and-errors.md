# 2 · Tools and errors (v1)

**Eval failure:** `wrong-path` — the task names `utils/strings.py`; the file moved to `src/textkit/strings.py`. In v0, `read_file` raises, the exception escapes the loop, and the run dies.

**Fix:** tool failures become `tool_result` blocks with `is_error: true` and a message the model can act on:

```text
No such file: utils/strings.py. Did you mean: src/textkit/strings.py?
```

The model reads the hint, opens the right file, and finishes the task. Same model, same tools — the only change is what the harness does with an exception.

## Tool descriptions and errors are prompts

The model decides what to do next from your tool's name, description, and output. Write them for it:

- **Say what to do instead.** "`old` text appears 2 times — include more context so it is unique" beats "ValueError".
- **Report every problem at once.** A call with a wrong argument name gets *"unknown argument 'file'; missing required argument 'path'"* in one message, not two round trips.
- **Validate inputs yourself.** [`Tool.validate`](../src/harness/tools.py) checks types, required and unknown arguments before anything runs. With streamed tool input (`eager_input_streaming`), the API no longer validates arguments for you, and a cut-off stream can produce partial JSON.
- **Close the schema.** `additionalProperties: false` tells the model exactly which arguments exist.

## Dedicated tools beat one big shell

This harness has `read_file`, `edit_file`, `search`, and `run_tests` instead of a single `bash` tool. A dedicated tool gives the harness typed arguments it can **check, gate, and audit** — the guard in [03](03-guardrails.md) can refuse a write to `tests/` only because a write is a `write_file` call, not an opaque shell string. Start broad if you must; promote an action to its own tool when you need to control it.
