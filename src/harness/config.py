"""Harness versions. Each one adds a single fix for a failure the evals caught.

Same model, same tools, same tasks — only the harness changes between versions.
"""

from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class HarnessConfig:
    name: str
    description: str
    # v1: tool failures go back to the model as actionable `is_error` results
    #     instead of crashing the run.
    errors_as_feedback: bool = False
    # v2: the agent may only touch files inside its workspace, tests are
    #     read-only, and "done" becomes an explicit `finish` tool call.
    guard: bool = False
    finish_tool: bool = False
    # v3: `finish` runs the test suite; failures are sent back instead of accepted.
    verify_on_finish: bool = False
    # v4: large tool outputs are cut at the source with a hint on how to read
    #     more, and the agent can save lessons for future runs.
    truncate_outputs: bool = False
    memory: bool = False
    # v5: a passing test run needs evidence — every test collected at the start of
    #     the run reported as passed — not just an exit code of zero.
    require_evidence: bool = False

    # Lab safety, on in every version (not a lesson — it keeps experiments cheap):
    max_steps: int = 30
    max_context_tokens: int = 100_000  # estimated; the run stops before sending more
    output_limit_chars: int = 6_000  # used when truncate_outputs is on


_V0 = HarnessConfig(name="v0", description="naive: a loop and some tools")
_V1 = replace(_V0, name="v1", description="+ tool errors become feedback", errors_as_feedback=True)
_V2 = replace(
    _V1,
    name="v2",
    description="+ guardrails: workspace boundary, read-only tests, explicit finish",
    guard=True,
    finish_tool=True,
)
_V3 = replace(_V2, name="v3", description="+ verify before done: finish runs the tests", verify_on_finish=True)
_V4 = replace(
    _V3,
    name="v4",
    description="+ context hygiene and memory: truncate at the source, keep lessons",
    truncate_outputs=True,
    memory=True,
)
_V5 = replace(
    _V4,
    name="v5",
    description="+ evidence: every test seen at the start must be seen passing, not just exit code 0",
    require_evidence=True,
)

VERSIONS: dict[str, HarnessConfig] = {c.name: c for c in (_V0, _V1, _V2, _V3, _V4, _V5)}
