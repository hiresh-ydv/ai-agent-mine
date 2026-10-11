from __future__ import annotations

import pytest

from helpers import make_context
from mini_codex.errors import PathSecurityError, SecretAccessError, ToolError
from mini_codex.tools import read_file, search_codebase, search_in_file


@pytest.fixture
def tree(config):
    root = config.project_root
    (root / "pkg").mkdir()
    (root / "pkg" / "module.py").write_text(
        "def compute_discount(price, percent):\n    return price - percent\n"
    )
    (root / "README.md").write_text("# Docs about discount handling\n")
    (root / "notes.txt").write_text("no relevant words here\n")
    (root / ".env").write_text("DISCOUNT_SECRET=discount\n")
    (root / ".git").mkdir()
    (root / ".git" / "config").write_text("discount = true\n")
    (root / "__pycache__").mkdir()
    (root / "__pycache__" / "module.py").write_text("discount cache\n")
    return root


def test_search_finds_and_excludes(config, tree):
    context = make_context(config)
    result = search_codebase.run({"query": "discount"}, context)

    paths = {entry["path"] for entry in result["results"]}
    assert "pkg/module.py" in paths
    assert "README.md" in paths
    assert ".env" not in paths
    assert not any(path.startswith(".git") for path in paths)
    assert not any(path.startswith("__pycache__") for path in paths)


def test_search_extension_filter(config, tree):
    context = make_context(config)
    result = search_codebase.run({"query": "discount", "extensions": ["md"]}, context)

    paths = {entry["path"] for entry in result["results"]}
    assert paths == {"README.md"}


def test_search_no_matches_returns_message(config, tree):
    context = make_context(config)
    result = search_codebase.run({"query": "nonexistent-token"}, context)

    assert result["file_count"] == 0
    assert result["message"] == "No matches found."


def test_search_in_file_literal_with_context(config, tree):
    context = make_context(config)
    result = search_in_file.run(
        {"path": "pkg/module.py", "query": "return", "context_lines": 1}, context
    )

    assert result["match_count"] == 1
    assert result["matches"][0]["line"] == 2
    assert len(result["matches"][0]["context"]) == 2


def test_search_in_file_regex(config, tree):
    context = make_context(config)
    result = search_in_file.run(
        {"path": "pkg/module.py", "query": r"def \w+\(", "regex": True}, context
    )
    assert result["match_count"] == 1


def test_search_in_file_rejects_secret(config, tree):
    context = make_context(config)
    with pytest.raises(SecretAccessError):
        search_in_file.run({"path": ".env", "query": "discount"}, context)


def test_search_in_file_rejects_traversal(config, tree):
    context = make_context(config)
    with pytest.raises(PathSecurityError):
        search_in_file.run({"path": "../outside.txt", "query": "x"}, context)


def test_search_in_file_invalid_regex(config, tree):
    context = make_context(config)
    with pytest.raises(ToolError):
        search_in_file.run({"path": "pkg/module.py", "query": "(", "regex": True}, context)


def test_read_file_returns_exact_lines(config, tree):
    context = make_context(config)
    result = read_file.run({"path": "pkg/module.py", "start_line": 1, "end_line": 2}, context)

    assert result["lines"][0] == {"line": 1, "text": "def compute_discount(price, percent):"}
    assert result["lines"][1] == {"line": 2, "text": "    return price - percent"}
    assert result["total_lines"] == 2


def test_read_file_invalid_range(config, tree):
    context = make_context(config)
    with pytest.raises(ToolError):
        read_file.run({"path": "pkg/module.py", "start_line": 3, "end_line": 1}, context)


def test_read_file_beyond_eof(config, tree):
    context = make_context(config)
    with pytest.raises(ToolError):
        read_file.run({"path": "pkg/module.py", "start_line": 99, "end_line": 100}, context)


def test_read_file_missing(config, tree):
    context = make_context(config)
    with pytest.raises(ToolError):
        read_file.run({"path": "pkg/missing.py", "start_line": 1, "end_line": 2}, context)
