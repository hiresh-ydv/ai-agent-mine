from __future__ import annotations

import os

import pytest

from helpers import make_config
from mini_codex.errors import PathSecurityError
from mini_codex.safety.paths import is_excluded_path, resolve_within_root


def test_resolves_file_inside_root(tmp_path):
    (tmp_path / "pkg").mkdir()
    target = tmp_path / "pkg" / "mod.py"
    target.write_text("x = 1\n")

    resolved = resolve_within_root(tmp_path, "pkg/mod.py")
    assert resolved == target.resolve()


def test_absolute_path_is_rejected(tmp_path):
    with pytest.raises(PathSecurityError):
        resolve_within_root(tmp_path, str(tmp_path / "x.py"))


def test_traversal_is_rejected(tmp_path):
    with pytest.raises(PathSecurityError):
        resolve_within_root(tmp_path, "../secret.txt")


def test_empty_path_is_rejected(tmp_path):
    with pytest.raises(PathSecurityError):
        resolve_within_root(tmp_path, "   ")


def test_symlink_escape_is_rejected(tmp_path):
    outside = tmp_path.parent / "outside_target.txt"
    outside.write_text("secret\n")
    link = tmp_path / "link.txt"
    try:
        os.symlink(outside, link)
    except (OSError, NotImplementedError):
        pytest.skip("Symlinks are not supported in this environment.")

    with pytest.raises(PathSecurityError):
        resolve_within_root(tmp_path, "link.txt")


def test_excluded_dir_is_detected(tmp_path):
    config = make_config(tmp_path)
    assert is_excluded_path(tmp_path / ".git" / "config", config)
    assert is_excluded_path(tmp_path / "__pycache__" / "x.pyc", config)
    assert not is_excluded_path(tmp_path / "src" / "app.py", config)
