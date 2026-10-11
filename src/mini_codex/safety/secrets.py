"""Secret-file detection and binary-content sniffing."""

from __future__ import annotations

import fnmatch
from pathlib import Path

from ..config import DEFAULT_SECRET_PATTERNS


def is_secret_path(path: str | Path, patterns: tuple[str, ...] = DEFAULT_SECRET_PATTERNS) -> bool:
    name = Path(path).name.lower()
    lowered = tuple(pattern.lower() for pattern in patterns)
    return any(fnmatch.fnmatch(name, pattern) for pattern in lowered)


def is_probably_binary(data: bytes) -> bool:
    """Heuristically detect binary content without decoding the whole file."""

    if b"\x00" in data:
        return True
    if not data:
        return False
    sample = data[:4096]
    printable = set(range(0x20, 0x7F)) | {0x09, 0x0A, 0x0C, 0x0D}
    non_text = sum(1 for byte in sample if byte not in printable)
    if non_text / len(sample) > 0.30:
        return True
    try:
        sample.decode("utf-8")
    except UnicodeDecodeError:
        return True
    return False
