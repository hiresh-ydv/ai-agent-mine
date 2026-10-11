"""Tool 6: run the project's approved, predefined test command."""

from __future__ import annotations

import subprocess
import sys
import time
from typing import Any

from ..context import ToolContext
from ..errors import ToolError
from ..safety.paths import relative_to_root, resolve_within_root
from ..state import Status

# Only these trusted profiles may be executed. The LLM cannot supply a command.
PROFILES: dict[str, dict[str, Any]] = {
    "default": {
        "description": "Run the project's pytest suite quietly.",
        "args": ["-q"],
    },
}


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _truncate(text: str, limit: int) -> str:
    text = text or ""
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n... [truncated {len(text) - limit} characters]"


def _summary(stdout: str, stderr: str, passed: bool, timed_out: bool) -> str:
    if timed_out:
        return "The test runner timed out."
    for line in reversed((stdout or "").strip().splitlines()):
        stripped = line.strip().strip("= ")
        lowered = stripped.lower()
        if stripped and (
            "passed" in lowered or "failed" in lowered or "error" in lowered
        ):
            return stripped
    return "Tests passed." if passed else "Tests failed."


def run(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    profile_name = (args.get("test_profile") or ctx.config.test_profile or "default").strip()
    profile = PROFILES.get(profile_name)
    if profile is None:
        raise ToolError(
            f"Unknown test profile '{profile_name}'. Allowed profiles: {', '.join(PROFILES)}."
        )

    command = [sys.executable, "-m", "pytest", *profile["args"]]
    display = " ".join([sys.executable, "-m", "pytest", *profile["args"]])

    target = args.get("test_target")
    if target:
        target_path = resolve_within_root(ctx.root, target)
        if not target_path.exists():
            raise ToolError(f"Test target not found: {target}")
        relative_target = relative_to_root(target_path, ctx.root)
        command.append(relative_target)
        display = f"{display} {relative_target}"

    ctx.state.transition(Status.TESTING)
    started = time.monotonic()
    timed_out = False

    try:
        completed = subprocess.run(
            command,
            cwd=str(ctx.root),
            capture_output=True,
            text=True,
            timeout=ctx.config.test_timeout_seconds,
            check=False,
        )
        exit_code = completed.returncode
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        exit_code = -1
        stdout = _as_text(exc.stdout)
        stderr = _as_text(exc.stderr) + (
            f"\nThe test runner timed out after {ctx.config.test_timeout_seconds} seconds."
        )
    except (OSError, ValueError) as exc:
        raise ToolError(f"Could not start the test runner: {exc}") from exc

    duration = round(time.monotonic() - started, 3)
    passed = exit_code == 0 and not timed_out

    result = {
        "profile": profile_name,
        "command": display,
        "exit_code": exit_code,
        "duration_seconds": duration,
        "timed_out": timed_out,
        "passed": passed,
        "stdout": _truncate(stdout, ctx.config.max_output_chars),
        "stderr": _truncate(stderr, ctx.config.max_output_chars),
        "summary": _summary(stdout, stderr, passed, timed_out),
    }
    ctx.state.test_results = result
    return result
