"""A small, readable agent harness: Agent = Model + Harness."""

from harness.config import VERSIONS, HarnessConfig
from harness.loop import RunResult, run_agent

__all__ = ["VERSIONS", "HarnessConfig", "RunResult", "run_agent"]
