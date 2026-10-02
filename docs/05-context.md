# 5 · Context (v4)

**Eval failure:** `big-log` — the answer is one line in a 1.7 MB log. The scripted model calls `read_file` on the whole file. In v0–v3 roughly 437K estimated tokens land in the history, and the run stops at the context budget before the next request is even sent.

**Fix:** cut large tool output **at the source**, and say how to get the rest:

```text
[output truncated: showing 6,000 of 1,746,335 characters. Use read_file with offset and limit to read a range, or search to find specific lines.]
```

The model switches to `search("FATAL")`, gets one line back, and answers.

## Why "at the source"

The tempting alternative is to let output in and trim old turns later. Don't:

- **History is append-only.** Current Claude models bind their thinking to the exact conversation that produced it; editing or deleting earlier turns invalidates that reasoning (newer accounts get a 400 error) and restarts the prompt cache. Shape output *before* it's appended.
- When a long run genuinely outgrows its context, use the API's **server-side** tools for it — *context editing* (clears old tool results) or *compaction* (summarizes earlier turns). They don't count as edits to your history, because the API works on its own copy.

## Cheap context is cached context

[`ClaudeModel`](../src/harness/model.py) sends `cache_control: {"type": "ephemeral"}` at the top level, so each request caches the whole prefix up to the last block. In an agent loop that means every turn re-reads the earlier turns at the cache-read price (a tenth of the input price or less). Two things silently break it: changing the system prompt or tools mid-run, and editing history — both forbidden above for other reasons too.
