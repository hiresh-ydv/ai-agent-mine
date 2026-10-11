from __future__ import annotations

import pytest

from helpers import FakeConsole, make_context
from mini_codex.errors import ToolError
from mini_codex.state import Status
from mini_codex.tools import approval, propose_edit

EDIT = {
    "path": "app.py",
    "old_text": "return 1",
    "new_text": "return 2",
    "reason": "Bump the return value.",
}


def _prepare(config, answers):
    root = config.project_root
    (root / "app.py").write_text("def f():\n    return 1\n")
    console = FakeConsole(answers)
    context = make_context(config, console=console)
    result = propose_edit.run(dict(EDIT), context)
    return context, result["patch_id"], root / "app.py"


def test_approval_applies_patch(config):
    context, patch_id, path = _prepare(config, ["y"])

    result = approval.run({"patch_id": patch_id}, context)

    assert result["approved"] is True
    assert result["applied"] is True
    assert "return 2" in path.read_text()
    assert context.state.changed_files == ["app.py"]
    assert context.state.status is Status.PATCH_APPLIED
    assert (context.backups_root / patch_id / "app.py").exists()


def test_rejection_leaves_file_unchanged(config):
    context, patch_id, path = _prepare(config, ["n"])
    before = path.read_bytes()

    result = approval.run({"patch_id": patch_id}, context)

    assert result["approved"] is False
    assert result["applied"] is False
    assert result["stop"] is True
    assert path.read_bytes() == before
    assert context.state.status is Status.REJECTED


def test_empty_input_is_rejection(config):
    context, patch_id, path = _prepare(config, [""])
    before = path.read_bytes()

    result = approval.run({"patch_id": patch_id}, context)

    assert result["approved"] is False
    assert path.read_bytes() == before


def test_unknown_patch_id_is_rejected(config):
    context, _, _ = _prepare(config, ["y"])
    with pytest.raises(ToolError):
        approval.run({"patch_id": "does-not-exist"}, context)


def test_stale_patch_is_refused(config):
    context, patch_id, path = _prepare(config, ["y"])
    path.write_text("def f():\n    return 999\n")
    externally_written = path.read_text()

    with pytest.raises(ToolError):
        approval.run({"patch_id": patch_id}, context)

    assert path.read_text() == externally_written
    assert context.state.patches[patch_id].status == "failed"


def test_already_applied_patch_cannot_reapply(config):
    context, patch_id, _ = _prepare(config, ["y"])
    approval.run({"patch_id": patch_id}, context)

    with pytest.raises(ToolError):
        approval.run({"patch_id": patch_id}, context)
