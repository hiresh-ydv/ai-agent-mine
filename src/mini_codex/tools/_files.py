"""Shared file-access helpers used by the read/search/edit tools."""

from __future__ import annotations

from pathlib import Path

from ..config import Config
from ..errors import SecretAccessError, ToolError
from ..safety import secrets as secrets_mod
from ..safety.paths import is_excluded_path


def check_readable(path: Path, config: Config) -> None:
    """Validate that a resolved path may be read by the agent."""

    if secrets_mod.is_secret_path(path, config.secret_patterns):
        raise SecretAccessError("Access to secret-like files is blocked.")
    if is_excluded_path(path, config):
        raise ToolError("This file is excluded from agent access.")
    if not path.exists():
        raise ToolError("File not found inside the project root.")
    if not path.is_file():
        raise ToolError("The given path is not a regular file.")


def read_source_text(path: Path, config: Config) -> str:
    check_readable(path, config)
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise ToolError(f"Could not inspect the file: {exc}") from exc
    if size > config.max_file_bytes:
        raise ToolError(
            f"File is too large to read ({size} bytes > {config.max_file_bytes})."
        )
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise ToolError(f"Could not read the file: {exc}") from exc
    if secrets_mod.is_probably_binary(data):
        raise ToolError("File appears to be binary and cannot be read as text.")
    return data.decode("utf-8", errors="replace")
