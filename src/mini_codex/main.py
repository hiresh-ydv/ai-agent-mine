"""Command-line entry point for Mini Codex."""

from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path

from .agent import Agent, TaskReport
from .config import Config
from .console import Console
from .errors import ConfigError, LLMError
from .llm import GroqLLM
from .state import Status

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_FAILED = 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mini-codex",
        description="A local-first, Groq-powered coding agent that proposes, asks for "
        "approval, and applies minimal fixes.",
    )
    parser.add_argument(
        "--project",
        "-p",
        default=".",
        help="Project root the agent is confined to (default: current directory).",
    )
    parser.add_argument(
        "--task",
        "-t",
        default=None,
        help="Natural-language description of the issue. Prompted for if omitted.",
    )
    parser.add_argument("--model", default=None, help="Override GROQ_MODEL.")
    parser.add_argument("--max-turns", type=int, default=None, help="Override MAX_AGENT_TURNS.")
    parser.add_argument(
        "--max-tool-calls", type=int, default=None, help="Override MAX_TOOL_CALLS."
    )
    return parser


def _print_report(console: Console, report: TaskReport) -> None:
    console.write("")
    console.rule("Task report")
    console.write(f"Status:        {report.status}")
    console.write(f"Changed files: {', '.join(report.changed_files) or '(none)'}")
    console.write(f"Turns:         {report.turn_count}")
    console.write(f"Tool calls:    {report.tool_call_count}")
    if report.test_results is not None:
        tests = report.test_results
        console.write(
            f"Tests:         {'PASSED' if tests.get('passed') else 'FAILED'} "
            f"(exit {tests.get('exit_code')}, {tests.get('duration_seconds')}s)"
        )
        console.write(f"Test summary:  {tests.get('summary')}")
    if report.error:
        console.error(f"Error:         {report.error}")
    if report.final_message:
        console.write("")
        console.write(report.final_message.strip())


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    console = Console()

    root = Path(args.project).resolve()
    if not root.is_dir():
        console.error(f"Project directory not found: {root}")
        return EXIT_USAGE

    try:
        config = Config.from_env(root)
    except ConfigError as exc:
        console.error(f"Configuration error: {exc}")
        return EXIT_USAGE

    overrides = {}
    if args.model:
        overrides["groq_model"] = args.model
    if args.max_turns:
        overrides["max_agent_turns"] = args.max_turns
    if args.max_tool_calls:
        overrides["max_tool_calls"] = args.max_tool_calls
    if overrides:
        config = replace(config, **overrides)

    try:
        llm = GroqLLM(
            config.groq_api_key,
            config.groq_model,
            timeout_seconds=config.llm_timeout_seconds,
        )
    except LLMError as exc:
        console.error(str(exc))
        return EXIT_USAGE

    console.write("Mini Codex - Groq-powered coding agent")
    console.write(f"Project: {root}")
    console.write(f"Model:   {config.groq_model}")
    console.write("")

    task = args.task
    if not task:
        try:
            task = console.prompt("Describe the issue: ").strip()
        except (EOFError, KeyboardInterrupt):
            console.error("No task provided.")
            return EXIT_USAGE
    if not task:
        console.error("No task provided.")
        return EXIT_USAGE

    agent = Agent(config, console, llm)
    report = agent.run(task)
    _print_report(console, report)

    if report.status in {Status.COMPLETED.value, Status.REJECTED.value}:
        return EXIT_OK
    return EXIT_FAILED
