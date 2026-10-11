"""Tool 3: read an exact line range from a project file."""

from __future__ import annotations

from typing import Any

from ..context import ToolContext
from ..errors import ToolError
from ..safety.paths import relative_to_root, resolve_within_root
from ._files import read_source_text


def run(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    start = int(args["start_line"])
    end = int(args["end_line"])
    if end < start:
        raise ToolError("end_line must be greater than or equal to start_line.")

    path = resolve_within_root(ctx.root, args["path"])
    text = read_source_text(path, ctx.config)
    lines = text.splitlines()
    total = len(lines)

    if total == 0:
        return {
            "path": relative_to_root(path, ctx.root),
            "start_line": start,
            "end_line": start,
            "total_lines": 0,
            "truncated": False,
            "lines": [],
            "message": "The file is empty.",
        }

    if start > total:
        raise ToolError(f"start_line {start} is beyond the end of the file ({total} lines).")

    effective_end = min(end, total)
    truncated = effective_end < end
    if effective_end - start + 1 > ctx.config.max_read_lines:
        effective_end = start + ctx.config.max_read_lines - 1
        truncated = True

    window = [{"line": number, "text": lines[number - 1]} for number in range(start, effective_end + 1)]
    return {
        "path": relative_to_root(path, ctx.root),
        "start_line": start,
        "end_line": effective_end,
        "total_lines": total,
        "truncated": truncated,
        "lines": window,
    }
