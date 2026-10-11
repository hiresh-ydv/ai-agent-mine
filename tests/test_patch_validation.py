from __future__ import annotations

import pytest

from mini_codex.errors import PatchError
from mini_codex.safety.patch_validation import (
    atomic_write_text,
    build_unified_diff,
    create_backup,
    detect_newline,
    fingerprint,
    find_unique_match,
    normalize_newlines,
)


def test_fingerprint_is_stable_and_sensitive():
    assert fingerprint("hello") == fingerprint("hello")
    assert fingerprint("hello") != fingerprint("hello ")


def test_find_unique_match_returns_index():
    content = "a = 1\nb = 2\nc = 3\n"
    assert find_unique_match(content, "b = 2") == content.index("b = 2")


def test_missing_text_is_rejected():
    with pytest.raises(PatchError):
        find_unique_match("a = 1\n", "z = 9")


def test_ambiguous_text_is_rejected():
    content = "return x\nreturn x\n"
    with pytest.raises(PatchError):
        find_unique_match(content, "return x")


def test_empty_old_text_is_rejected():
    with pytest.raises(PatchError):
        find_unique_match("abc", "")


def test_unified_diff_contains_changes():
    diff = build_unified_diff("m.py", "return price - percent\n", "return price * (1 - percent / 100)\n")
    assert "--- a/m.py" in diff
    assert "+++ b/m.py" in diff
    assert "-return price - percent" in diff
    assert "+return price * (1 - percent / 100)" in diff


def test_newline_detection_and_normalization():
    assert detect_newline("a\r\nb\r\n") == "\r\n"
    assert detect_newline("a\nb\n") == "\n"
    assert normalize_newlines("a\r\nb\rc") == "a\nb\nc"


def test_atomic_write_replaces_content(tmp_path):
    target = tmp_path / "file.txt"
    target.write_text("old")
    atomic_write_text(target, "new")
    assert target.read_text() == "new"


def test_backup_creates_copy(tmp_path):
    source = tmp_path / "file.txt"
    source.write_text("content")
    backup = create_backup(source, tmp_path / "backups", "patch1")
    assert backup.exists()
    assert backup.read_text() == "content"
