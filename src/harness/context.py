"""Context hygiene.

The rule that shapes everything here: **history is append-only.** Current Claude
models bind their thinking to the exact conversation that produced it, so editing,
trimming, or deleting an earlier turn invalidates later reasoning (and the prompt
cache). So we shape tool output *before* it enters the history, never after.
For long runs, prefer the API's server-side context editing or compaction over
rewriting history yourself.
"""

from __future__ import annotations

import json


def truncate(text: str, limit: int, hint: str) -> str:
    """Cut `text` to `limit` characters and say how to get the rest."""
    if len(text) <= limit:
        return text
    head = text[:limit]
    return f"{head}\n\n[output truncated: showing {limit:,} of {len(text):,} characters. {hint}]"


def estimate_tokens(*parts: object) -> int:
    """Rough token estimate (~4 characters per token) for the budget check.

    An estimate is enough for a safety stop; use the API's token counting
    endpoint when you need exact numbers.
    """
    return sum(len(json.dumps(p, default=_plain)) for p in parts) // 4


def _plain(obj: object) -> object:
    dump = getattr(obj, "model_dump", None)
    return dump() if callable(dump) else str(obj)
