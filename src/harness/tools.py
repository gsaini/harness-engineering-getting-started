"""The agent's tools: plain Python functions with a schema and input validation.

Tool *descriptions* and *error messages* are prompts — the model reads them to
decide what to do next — so they are written for the model.
"""

from __future__ import annotations

import difflib
import os
import re
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from harness import memory
from harness.errors import ToolError
from harness.guard import Guard

MAX_LIST = 300
MAX_MATCHES = 40
SKIP_DIRS = {"__pycache__", ".pytest_cache"}


@dataclass
class Param:
    type: type
    description: str
    required: bool = True


@dataclass
class Tool:
    name: str
    description: str
    params: dict[str, Param]
    fn: Callable[..., str]
    meta: dict = field(default_factory=dict)

    def schema(self) -> dict:
        json_type = {str: "string", int: "integer"}
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": {
                    name: {"type": json_type[p.type], "description": p.description} for name, p in self.params.items()
                },
                "required": [name for name, p in self.params.items() if p.required],
                "additionalProperties": False,
            },
        }

    def validate(self, args: object) -> dict:
        """Check the model's arguments before running anything (they can be malformed)."""
        if not isinstance(args, dict):
            raise ToolError(f"{self.name}: arguments must be a JSON object.")
        # Report every problem at once, so the model can fix the call in one try.
        problems = [f"unknown argument '{name}'" for name in sorted(set(args) - set(self.params))]
        for name, p in self.params.items():
            if name not in args:
                if p.required:
                    problems.append(f"missing required argument '{name}'")
            elif p.type is int and isinstance(args[name], bool) or not isinstance(args[name], p.type):
                problems.append(f"'{name}' must be a {p.type.__name__}")
        if problems:
            raise ToolError(f"{self.name}: " + "; ".join(problems) + ".")
        return args


class Workspace:
    """Everything the tools need: where to work, what the agent may touch, and (v5)
    which tests a verified run has to account for."""

    def __init__(self, root: Path, floor: Path, guard: bool, tests: frozenset[str] | None = None):
        self.root = root.resolve()
        self.guard = Guard(self.root, floor, enabled=guard)
        # Test ids collected before the agent acted. None means "trust pytest's exit code".
        self.tests = tests

    def similar_paths(self, path: str) -> list[str]:
        files = [p.relative_to(self.root).as_posix() for p in _files(self.root)]
        by_name = [f for f in files if Path(f).name == Path(path).name]
        return by_name or difflib.get_close_matches(path, files, n=3, cutoff=0.4)


def _files(base: Path) -> list[Path]:
    """Every file under `base`, sorted, skipping caches."""
    return sorted(p for p in base.rglob("*") if p.is_file() and not SKIP_DIRS & set(p.parts))


def build_tools(ws: Workspace, *, finish: bool, remember: bool) -> list[Tool]:
    def list_files(path: str = ".") -> str:
        base = ws.guard.resolve(path)
        if not base.is_dir():
            raise ToolError(f"{path} is not a directory.")
        files = [p.relative_to(ws.root).as_posix() for p in _files(base)]
        more = f"\n… and {len(files) - MAX_LIST} more" if len(files) > MAX_LIST else ""
        return "\n".join(files[:MAX_LIST]) + more or "(empty)"

    def read_file(path: str, offset: int = 1, limit: int = 0) -> str:
        if offset < 1 or limit < 0:
            raise ToolError("offset must be at least 1 and limit at least 0 (0 means to the end of the file).")
        target = ws.guard.resolve(path)
        if not target.is_file():
            hint = ws.similar_paths(path)
            suggestion = f" Did you mean: {', '.join(hint)}?" if hint else " Use list_files to see what exists."
            raise ToolError(f"No such file: {path}.{suggestion}")
        text = target.read_text(encoding="utf-8", errors="replace")
        if offset == 1 and limit == 0:
            return text
        lines = text.splitlines()
        end = len(lines) if limit == 0 else min(len(lines), offset - 1 + limit)
        return f"[lines {offset}-{end} of {len(lines)}]\n" + "\n".join(lines[offset - 1 : end])

    def write_file(path: str, content: str) -> str:
        target = ws.guard.resolve(path, write=True)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"Wrote {len(content):,} characters to {path}."

    def edit_file(path: str, old: str, new: str) -> str:
        target = ws.guard.resolve(path, write=True)
        if not target.is_file():
            raise ToolError(f"No such file: {path}. Use write_file to create a file.")
        text = target.read_text(encoding="utf-8")
        count = text.count(old)
        if count == 0:
            raise ToolError(f"`old` text not found in {path}. Read the file again and copy it exactly.")
        if count > 1:
            raise ToolError(f"`old` text appears {count} times in {path}. Include more context so it is unique.")
        target.write_text(text.replace(old, new, 1), encoding="utf-8")
        return f"Edited {path}."

    def search(pattern: str, path: str = ".") -> str:
        try:
            regex = re.compile(pattern)
        except re.error as exc:
            raise ToolError(f"Invalid regular expression {pattern!r}: {exc}.") from exc
        base = ws.guard.resolve(path)
        files = [base] if base.is_file() else _files(base)
        hits: list[str] = []
        total = 0
        for file in files:
            try:
                lines = file.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            for number, line in enumerate(lines, 1):
                if regex.search(line):
                    total += 1
                    if len(hits) < MAX_MATCHES:
                        rel = file.relative_to(ws.root).as_posix()
                        hits.append(f"{rel}:{number}: {line[:300]}")
        if total == 0:
            return f"No matches for {pattern!r}."
        more = f"\n… {total - MAX_MATCHES} more matches; narrow the pattern." if total > MAX_MATCHES else ""
        return f"{total} match(es):\n" + "\n".join(hits) + more

    def run_tests() -> str:
        return run_test_suite(ws.root, expect=ws.tests).output

    tools = [
        Tool(
            "list_files",
            "List files under a directory of the workspace.",
            {"path": Param(str, "Directory relative to the workspace root (default '.').", False)},
            list_files,
        ),
        Tool(
            "read_file",
            "Read a text file. For large files, pass offset (first line, 1-based) and limit (number of lines).",
            {
                "path": Param(str, "File path relative to the workspace root."),
                "offset": Param(int, "First line to read, 1-based.", False),
                "limit": Param(int, "Maximum number of lines; 0 means to the end.", False),
            },
            read_file,
        ),
        Tool(
            "write_file",
            "Create or overwrite a file with the given content.",
            {
                "path": Param(str, "File path relative to the workspace root."),
                "content": Param(str, "The full new content of the file."),
            },
            write_file,
        ),
        Tool(
            "edit_file",
            "Replace one exact, unique occurrence of `old` with `new` in a file.",
            {
                "path": Param(str, "File path relative to the workspace root."),
                "old": Param(str, "Exact text to replace; must occur exactly once."),
                "new": Param(str, "Replacement text."),
            },
            edit_file,
        ),
        Tool(
            "search",
            "Search files for a regular expression. Returns matching lines as file:line: text.",
            {
                "pattern": Param(str, "Python regular expression."),
                "path": Param(str, "File or directory to search (default '.').", False),
            },
            search,
        ),
        Tool("run_tests", "Run the project's test suite (pytest) and return the summary.", {}, run_tests),
    ]
    if finish:
        tools.append(
            Tool(
                "finish",
                "Call this when the task is complete. Summarize what you changed.",
                {"summary": Param(str, "What you changed and how you know it works.")},
                lambda summary: summary,
                meta={"finish": True},
            )
        )
    if remember:
        tools.append(
            Tool(
                "remember",
                "Save a short, reusable lesson about this project for future runs "
                "(e.g. where code lives, how tests are run). Not for task notes.",
                {"lesson": Param(str, "One sentence, no secrets or personal data.")},
                lambda lesson: memory.remember(ws.root, lesson),
            )
        )
    return tools


# --- Running the tests ---------------------------------------------------------------

PYTEST = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--no-header"]


@dataclass(frozen=True)
class TestReport:
    passed: bool
    output: str  # written for the model
    missing: tuple[str, ...] = ()  # expected tests that were not reported as passed (evidence mode)
    returncode: int = 0


def collect_tests(root: Path, timeout: int = 60) -> frozenset[str]:
    """The tests pytest would run in `root`, as node ids.

    Taken before the agent acts, this is the inventory a verified run has to account
    for (v5): a test that was there at the start must be reported passing at the end.
    """
    try:
        proc = subprocess.run(
            [*PYTEST, "--collect-only"], cwd=root, capture_output=True, text=True, timeout=timeout, env=_pytest_env()
        )
    except subprocess.TimeoutExpired:
        return frozenset()
    return frozenset(line.strip() for line in proc.stdout.splitlines() if "::" in line)


def run_test_suite(root: Path, timeout: int = 120, *, expect: frozenset[str] | None = None) -> TestReport:
    """Run pytest in `root`.

    Without `expect`, the exit code is trusted (v0–v4): 0 passes, and 5 (no tests
    collected) counts as nothing to verify. With `expect` — the ids collected at the
    start of the run — passing needs evidence: every one of them reported PASSED. A
    module that skips itself, or ends the process early with exit code 0, is caught.
    """
    args = PYTEST if expect is None else [*PYTEST, "-rA"]  # -rA: one line per test outcome, to check off
    try:
        proc = subprocess.run(args, cwd=root, capture_output=True, text=True, timeout=timeout, env=_pytest_env())
    except subprocess.TimeoutExpired:
        return TestReport(False, f"Tests timed out after {timeout}s.", tuple(sorted(expect or ())), returncode=-1)
    output = (proc.stdout + proc.stderr).strip()
    if expect is None:
        if proc.returncode == 5:
            return TestReport(True, "No tests to run.", returncode=5)
        return TestReport(proc.returncode == 0, output[-4_000:], returncode=proc.returncode)

    reported = frozenset(line[len("PASSED ") :].strip() for line in output.splitlines() if line.startswith("PASSED "))
    missing = tuple(sorted(expect - reported))
    banners = {"PASSES", "short test summary info"}  # -rA adds these; the model needs the outcomes, not the headings
    summary = "\n".join(
        line for line in output.splitlines() if not (line.startswith("PASSED ") or line.strip("= ") in banners)
    )[-4_000:]
    if missing:
        shown = "\n".join(f"  {test}" for test in missing[:20])
        if len(missing) > 20:
            shown += f"\n  … and {len(missing) - 20} more"
        text = (
            f"{len(missing)} of {len(expect)} tests collected at the start of this run were not reported as passed:\n"
            f"{shown}\n{summary or f'(pytest exited with code {proc.returncode} and no output)'}\n"
            "Every test must run and pass; skipping tests or ending the process early does not count."
        )
        return TestReport(False, text, missing, proc.returncode)
    return TestReport(proc.returncode in (0, 5), summary or "No tests to run.", returncode=proc.returncode)


def _pytest_env() -> dict[str, str]:
    """The environment for pytest, which runs whatever code the agent wrote: no API
    credentials for that code to read, and no bytecode caches (an edit that keeps a
    file's size within the same second can otherwise leave a stale .pyc in place, and
    the tests would check old code)."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("ANTHROPIC_")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env
