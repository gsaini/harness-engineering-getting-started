"""`harness` command line: run a task, run the evals, read a trace."""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

from harness import trace
from harness.config import VERSIONS
from harness.evals import load_tasks, run_eval, scoreboard
from harness.loop import run_agent
from harness.model import DEFAULT_MODEL, ClaudeModel
from harness.scripted import POLICIES, ScriptedModel


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="harness", description="A small agent harness, built to be read.")
    sub = parser.add_subparsers(dest="command", required=True)

    ev = sub.add_parser("eval", help="run every task through every harness version and print a scoreboard")
    ev.add_argument(
        "--model", default="scripted", help="'scripted' (offline, free) or a Claude model id, e.g. claude-opus-5-5"
    )
    ev.add_argument("--versions", default=",".join(VERSIONS), help="comma-separated, e.g. v0,v4")
    ev.add_argument("--tasks", help="comma-separated task ids (default: all)")
    ev.add_argument("--effort", default="medium", help="low | medium | high | xhigh | max")
    ev.add_argument("--out", type=Path, default=Path("runs"), help="where traces and the scoreboard go")
    ev.add_argument("--yes", action="store_true", help="confirm real API calls for a Claude model")

    run = sub.add_parser("run", help="run one task on a workspace directory")
    run.add_argument("task", help="what to do, in plain English")
    run.add_argument("--workspace", type=Path, required=True)
    run.add_argument("--version", default="v4", choices=list(VERSIONS))
    run.add_argument("--model", default=DEFAULT_MODEL)
    run.add_argument("--effort", default="medium")
    run.add_argument("--trace", type=Path, default=Path("runs/run.jsonl"))

    tr = sub.add_parser("trace", help="pretty-print a trace file")
    tr.add_argument("file", type=Path)

    sub.add_parser("versions", help="list harness versions")

    args = parser.parse_args(argv)
    if args.command == "versions":
        for config in VERSIONS.values():
            print(f"{config.name}  {config.description}")
        return 0
    if args.command == "trace":
        print(trace.show(args.file))
        return 0
    if args.command == "run":
        if not _has_credentials():
            print(NO_CREDENTIALS)
            return 2
        model = ClaudeModel(args.model, effort=args.effort)
        result = run_agent(args.task, args.workspace, model, VERSIONS[args.version], tracer=trace.Tracer(args.trace))
        print(f"{result.status} after {result.steps} steps. {result.final_text or result.error}")
        print(f"trace: {args.trace}  (harness trace {args.trace})")
        return 0 if result.status == "done" else 1
    return _eval(args)


def _has_credentials() -> bool:
    """API key, auth token, or an `ant auth login` profile (which the SDK reads automatically)."""
    if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        return True
    config_home = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return (config_home / "anthropic").is_dir()


NO_CREDENTIALS = "No Anthropic credentials found. Set ANTHROPIC_API_KEY (or run `ant auth login`), then try again."


def _eval(args: argparse.Namespace) -> int:
    versions = [VERSIONS[v.strip()] for v in args.versions.split(",")]
    tasks = load_tasks(args.tasks.split(",") if args.tasks else None)
    if args.model == "scripted":

        def make_model(task_id: str):
            return ScriptedModel(POLICIES[task_id])
    else:
        runs = len(tasks) * len(versions)
        if not _has_credentials():
            print(NO_CREDENTIALS)
            return 2
        if not args.yes:
            print(
                f"This makes real API calls with {args.model}: {runs} agent runs. "
                "Start small (e.g. --tasks fix-pagination --versions v4), then re-run with --yes."
            )
            return 2

        def make_model(task_id: str):
            return ClaudeModel(args.model, effort=args.effort)

    out = args.out / time.strftime("%Y%m%d-%H%M%S")
    grades = run_eval(tasks, versions, make_model, out_dir=out)
    board = scoreboard(grades, args.model)
    header = f"Model: `{args.model}`" + ("" if args.model == "scripted" else f" · effort `{args.effort}`")
    out.mkdir(parents=True, exist_ok=True)
    (out / "scoreboard.md").write_text(f"{header}\n\n{board}\n", encoding="utf-8")
    print(f"{header}\n\n{board}\n\nTraces and scoreboard: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
