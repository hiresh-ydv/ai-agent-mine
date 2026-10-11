"""Project-root confinement and file-exclusion rules.

Every path that comes from the model is treated as untrusted. These helpers are
the single place where a path is converted into a concrete file on disk, so the
whole codebase shares one definition of "inside the project".
"""

from __future__ import annotations

import fnmatch
from pathlib import Path

from ..config import Config
from ..errors import PathSecurityError


def is_within_root(candidate: str | Path, root: str | Path) -> bool:
    resolved_root = Path(root).resolve()
    try:
        Path(candidate).resolve().relative_to(resolved_root)
        return True
    except ValueError:
        return False


def resolve_within_root(root: str | Path, relative_path: str) -> Path:
    """Return an absolute path guaranteed to live inside ``root``.

    Raises :class:`PathSecurityError` for empty paths, absolute paths, traversal
    attempts, and symlinks that escape the project root.
    """

    if relative_path is None:
        raise PathSecurityError("A file path is required.")
    text = str(relative_path).strip()
    if not text:
        raise PathSecurityError("A file path is required.")

    root_path = Path(root).resolve()
    candidate = Path(text)

    if candidate.is_absolute():
        raise PathSecurityError(f"Absolute paths are not allowed: {relative_path!r}")

    if any(part == ".." for part in candidate.parts):
        raise PathSecurityError(f"Path traversal is not allowed: {relative_path!r}")

    resolved = (root_path / candidate).resolve()
    if resolved != root_path and root_path not in resolved.parents:
        raise PathSecurityError(f"Path escapes the project root: {relative_path!r}")
    return resolved


def relative_to_root(path: str | Path, root: str | Path) -> str:
    return Path(path).resolve().relative_to(Path(root).resolve()).as_posix()


def is_excluded_path(path: str | Path, config: Config) -> bool:
    """True if the path sits in an excluded directory or matches a skip pattern."""

    candidate = Path(path)
    for part in candidate.parts:
        if part in config.excluded_dirs:
            return True
    name = candidate.name
    for pattern in config.excluded_file_patterns:
        if fnmatch.fnmatch(name, pattern):
            return True
    return False
