"""Tool 1: search the whole project for files/lines matching a term."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from ..config import Config
from ..context import ToolContext
from ..safety import secrets as secrets_mod
from ..safety.paths import is_excluded_path, is_within_root, relative_to_root

MAX_MATCHES_PER_FILE = 5
MAX_MATCH_SCAN = 50


def _normalize_extensions(extensions: list[str] | None) -> set[str] | None:
    if not extensions:
        return None
    normalized: set[str] = set()
    for ext in extensions:
        cleaned = str(ext).strip().lower()
        if not cleaned:
            continue
        normalized.add(cleaned if cleaned.startswith(".") else f".{cleaned}")
    return normalized or None


def _candidate(path: Path, config: Config) -> bool:
    if is_excluded_path(path, config):
        return False
    if secrets_mod.is_secret_path(path, config.secret_patterns):
        return False
    try:
        if path.is_symlink() and not is_within_root(path.resolve(), config.project_root):
            return False
        if path.stat().st_size > config.max_file_bytes:
            return False
    except OSError:
        return False
    return True


def _find_matches(path: Path, needle: str, config: Config) -> list[dict[str, Any]]:
    try:
        data = path.read_bytes()
    except OSError:
        return []
    if secrets_mod.is_probably_binary(data):
        return []
    text = data.decode("utf-8", errors="replace")
    matches: list[dict[str, Any]] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if needle in line.lower():
            matches.append({"line": number, "text": line.strip()[:200]})
            if len(matches) >= MAX_MATCH_SCAN:
                break
    return matches


def run(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    config = ctx.config
    root = ctx.root
    query = args["query"]
    needle = query.lower()
    extensions = _normalize_extensions(args.get("extensions"))
    limit = min(
        args.get("max_results") or config.max_search_results,
        config.max_search_results,
    )

    results: list[dict[str, Any]] = []
    truncated = False

    for current_dir, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in config.excluded_dirs)
        for filename in filenames:
            if len(results) >= limit:
                truncated = True
                break
            path = Path(current_dir) / filename
            if extensions is not None and path.suffix.lower() not in extensions:
                continue
            if not _candidate(path, config):
                continue
            matches = _find_matches(path, needle, config)
            if matches:
                results.append(
                    {
                        "path": relative_to_root(path, root),
                        "match_count": len(matches),
                        "matches": matches[:MAX_MATCHES_PER_FILE],
                    }
                )
        if truncated:
            break

    return {
        "query": query,
        "file_count": len(results),
        "truncated": truncated,
        "results": results,
        "message": "No matches found."
        if not results
        else f"{len(results)} file(s) matched '{query}'.",
    }
