"""Tool 2: search within a single project file."""

from __future__ import annotations

import re
from typing import Any

from ..context import ToolContext
from ..errors import ToolError
from ..safety.paths import relative_to_root, resolve_within_root
from ._files import read_source_text

MAX_PATTERN_LENGTH = 500


def _matching_indices(lines: list[str], query: str, use_regex: bool) -> list[int]:
    if use_regex:
        if len(query) > MAX_PATTERN_LENGTH:
            raise ToolError("Regular expression is too long.")
        try:
            pattern = re.compile(query)
        except re.error as exc:
            raise ToolError(f"Invalid regular expression: {exc}") from exc
        return [i for i, line in enumerate(lines) if pattern.search(line)]
    needle = query.lower()
    return [i for i, line in enumerate(lines) if needle in line.lower()]


def run(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    path = resolve_within_root(ctx.root, args["path"])
    text = read_source_text(path, ctx.config)

    lines = text.splitlines()
    context = int(args.get("context_lines") or 0)
    indices = _matching_indices(lines, args["query"], bool(args.get("regex")))

    limit = ctx.config.max_search_results
    truncated = len(indices) > limit
    matches: list[dict[str, Any]] = []
    for index in indices[:limit]:
        start = max(0, index - context)
        end = min(len(lines), index + context + 1)
        matches.append(
            {
                "line": index + 1,
                "text": lines[index],
                "context": [
                    {"line": n + 1, "text": lines[n]} for n in range(start, end)
                ],
            }
        )

    relative = relative_to_root(path, ctx.root)
    return {
        "path": relative,
        "match_count": len(indices),
        "truncated": truncated,
        "matches": matches,
        "message": f"No matches for '{args['query']}' in {relative}."
        if not matches
        else f"{len(indices)} match(es) for '{args['query']}' in {relative}.",
    }
