"""Patch construction, validation, and safe application.

The rules here are deliberately conservative: a patch must match exactly one
region of the current file, the file must not have changed since the patch was
prepared, and writes are atomic with an on-disk recovery copy.
"""

from __future__ import annotations

import difflib
import hashlib
import os
import shutil
import tempfile
from pathlib import Path

from ..errors import PatchError


def fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def detect_newline(content: str) -> str:
    if "\r\n" in content:
        return "\r\n"
    if "\r" in content and "\n" not in content:
        return "\r"
    return "\n"


def read_text_raw(path: str | Path) -> str:
    with open(path, "r", encoding="utf-8", errors="replace", newline="") as handle:
        return handle.read()


def find_unique_match(content: str, old_text: str) -> int:
    if old_text == "":
        raise PatchError("The original text to replace must not be empty.")
    count = content.count(old_text)
    if count == 0:
        raise PatchError(
            "The original text was not found in the file. Provide the exact current text, "
            "including surrounding context, so it can be located."
        )
    if count > 1:
        raise PatchError(
            f"The original text appears {count} times; the edit is ambiguous. Include more "
            "surrounding context so the match is unique."
        )
    return content.index(old_text)


def build_unified_diff(relative_path: str, old_text: str, new_text: str, context: int = 3) -> str:
    old_lines = normalize_newlines(old_text).splitlines(keepends=True)
    new_lines = normalize_newlines(new_text).splitlines(keepends=True)
    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=f"a/{relative_path}",
        tofile=f"b/{relative_path}",
        n=context,
    )
    return "".join(diff)


def atomic_write_text(path: str | Path, text: str, encoding: str = "utf-8") -> None:
    target = Path(path)
    directory = target.parent
    fd, tmp_name = tempfile.mkstemp(dir=str(directory), prefix=".mini_codex_", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding=encoding, newline="") as handle:
            handle.write(text)
        os.replace(tmp_name, target)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def create_backup(path: str | Path, backup_root: str | Path, subdir: str) -> Path:
    source = Path(path)
    destination = Path(backup_root) / subdir / source.name
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return destination
