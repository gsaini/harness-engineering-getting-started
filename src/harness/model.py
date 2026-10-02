"""The model side of `Agent = Model + Harness`.

`ClaudeModel` calls the Claude API. `ScriptedModel` (see scripted.py) replays a
fixed policy offline so the harness can be tested for free.
"""

from __future__ import annotations

from typing import Any, Protocol

import anthropic

DEFAULT_MODEL = "claude-opus-5-5"

# Models that accept `output_config.effort`, and that support server-side
# refusal fallbacks with `fallbacks: "default"` on the Claude API.
_EFFORT = {"claude-opus-5-5", "claude-opus-5", "claude-fable-5-1", "claude-sonnet-5-5", "claude-sonnet-5"}
_FALLBACKS = {"claude-opus-5-5", "claude-opus-5", "claude-fable-5-1", "claude-sonnet-5-5"}

# $ per million tokens: (input, output, cache read, cache write). For cost estimates only.
PRICES = {
    "claude-opus-5-5": (4.00, 20.00, 0.20, 5.00),
    "claude-sonnet-5-5": (2.00, 10.00, 0.20, 2.50),
    "claude-haiku-4-5": (1.00, 5.00, 0.10, 1.25),
}


class Model(Protocol):
    name: str

    def create(self, *, system: str, tools: list[dict], messages: list[dict]) -> Any:
        """Return an Anthropic `Message` (or `BetaMessage`) for the conversation so far."""


class ClaudeModel:
    def __init__(
        self,
        name: str = DEFAULT_MODEL,
        *,
        effort: str = "medium",
        max_tokens: int = 64_000,
        client: anthropic.Anthropic | None = None,
    ):
        self.name = name
        self.effort = effort
        # Thinking counts toward max_tokens (even when its text isn't returned), so
        # leave room; streaming keeps a large value safe from HTTP timeouts.
        self.max_tokens = max_tokens
        self.client = client or anthropic.Anthropic(max_retries=4)  # retries 429/5xx with backoff

    def request(self, *, system: str, tools: list[dict], messages: list[dict]) -> dict:
        """Build the request. Kept separate so tests can check it without a network call."""
        kwargs: dict[str, Any] = {
            "model": self.name,
            "max_tokens": self.max_tokens,
            "system": system,
            # Stream tool inputs as they're generated; the harness validates them
            # (tools.Tool.validate) because streamed input isn't validated by the API.
            "tools": [{**tool, "eager_input_streaming": True} for tool in tools],
            "messages": messages,
            # Cache the whole stable prefix (tools + system + history so far) each turn.
            "cache_control": {"type": "ephemeral"},
        }
        betas = []
        if self.name in _EFFORT:
            kwargs["output_config"] = {"effort": self.effort}  # set explicitly: Opus 5.5 defaults to medium
        if self.name in _FALLBACKS:
            # If a safety classifier declines a request, the API re-runs it on a
            # recommended fallback model instead of returning the refusal.
            betas.append("server-side-fallback-2026-07-01")
            kwargs["fallbacks"] = "default"
        if betas:
            kwargs["betas"] = betas
        return kwargs

    def create(self, *, system: str, tools: list[dict], messages: list[dict]) -> Any:
        with self.client.beta.messages.stream(**self.request(system=system, tools=tools, messages=messages)) as stream:
            return stream.get_final_message()
