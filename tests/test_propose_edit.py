from __future__ import annotations

import pytest

from helpers import make_context
from mini_codex.errors import PatchError, SecretAccessError
from mini_codex.state import Status
from mini_codex.tools import propose_edit


@pytest.fixture
def repo(config):
    root = config.project_root
    (root / "pkg").mkdir()
    (root / "pkg" / "discount.py").write_text("def apply_discount(price, percent):\n    return price - percent\n")
    (root / ".env").write_text("SECRET=1\n")
    return root


def test_propose_edit_does_not_modify_file(config, repo):
    context = make_context(config)
    original = (repo / "pkg" / "discount.py").read_text()

    result = propose_edit.run(
        {
            "path": "pkg/discount.py",
            "old_text": "return price - percent",
            "new_text": "return price * (1 - percent / 100)",
            "reason": "Convert percentage to a fraction.",
        },
        context,
    )

    assert (repo / "pkg" / "discount.py").read_text() == original
    assert result["status"] == "pending"
    patch = context.state.patches[result["patch_id"]]
    assert patch.source_fingerprint
    assert "+return price * (1 - percent / 100)" in result["unified_diff"]
    assert context.state.status is Status.PATCH_PROPOSED


def test_propose_edit_rejects_ambiguous_text(config, repo):
    (repo / "pkg" / "dup.py").write_text("value = 1\nvalue = 1\n")
    context = make_context(config)
    with pytest.raises(PatchError):
        propose_edit.run(
            {"path": "pkg/dup.py", "old_text": "value = 1", "new_text": "value = 2", "reason": "x"},
            context,
        )


def test_propose_edit_rejects_missing_text(config, repo):
    context = make_context(config)
    with pytest.raises(PatchError):
        propose_edit.run(
            {"path": "pkg/discount.py", "old_text": "not present", "new_text": "x", "reason": "x"},
            context,
        )


def test_propose_edit_rejects_noop(config, repo):
    context = make_context(config)
    with pytest.raises(PatchError):
        propose_edit.run(
            {
                "path": "pkg/discount.py",
                "old_text": "return price - percent",
                "new_text": "return price - percent",
                "reason": "x",
            },
            context,
        )


def test_propose_edit_rejects_secret_file(config, repo):
    context = make_context(config)
    with pytest.raises(SecretAccessError):
        propose_edit.run(
            {"path": ".env", "old_text": "SECRET=1", "new_text": "SECRET=2", "reason": "x"},
            context,
        )
