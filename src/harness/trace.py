"""Traces: one JSON line per event, so every run can be replayed and diffed.

You can't improve a harness you can't see. Each failure you fix starts as a
line in a trace.
"""

from __future__ import annotations

import json
import time
from pathlib import Path


class Tracer:
    def __init__(self, path: Path | None):
        self.path = path
        if path:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("", encoding="utf-8")

    def log(self, event: str, **data: object) -> None:
        if not self.path:
            return
        record = {"t": round(time.time(), 3), "event": event, **data}
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=_plain) + "\n")


def _plain(obj: object) -> object:
    dump = getattr(obj, "model_dump", None)
    return dump(mode="json") if callable(dump) else str(obj)


def show(path: Path) -> str:
    """A human-readable view of a trace file."""
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        e = json.loads(line)
        kind = e["event"]
        if kind == "model":
            out.append(
                f"#{e['step']:>2} model  stop={e['stop_reason']}  in~{e.get('input_tokens', '?')} out={e.get('output_tokens', '?')}"
            )
        elif kind == "tool":
            flag = " ERROR" if e.get("is_error") else ""
            out.append(f"    tool  {e['name']}({_short(e.get('input'))}){flag} → {_short(e.get('output'), 90)}")
        else:
            out.append(f"    {kind}  {_short({k: v for k, v in e.items() if k not in ('t', 'event')}, 120)}")
    return "\n".join(out)


def _short(value: object, n: int = 60) -> str:
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    text = " ".join(text.split())
    return text if len(text) <= n else text[: n - 1] + "…"
