from __future__ import annotations

import pytest

from helpers import make_config, make_context
from mini_codex.errors import MiniCodexError, ToolError
from mini_codex.state import Status
from mini_codex.tools import run_tests


def _write_passing_repo(root):
    (root / "pytest.ini").write_text("[pytest]\n")
    (root / "test_ok.py").write_text("def test_ok():\n    assert 1 == 1\n")


def test_passing_tests_reported(config):
    root = config.project_root
    _write_passing_repo(root)
    context = make_context(config, status=Status.PATCH_APPLIED)

    result = run_tests.run({}, context)

    assert result["passed"] is True
    assert result["exit_code"] == 0
    assert result["timed_out"] is False
    assert context.state.status is Status.TESTING


def test_failing_tests_reported(config):
    root = config.project_root
    (root / "pytest.ini").write_text("[pytest]\n")
    (root / "test_bad.py").write_text("def test_bad():\n    assert 1 == 2\n")
    context = make_context(config, status=Status.PATCH_APPLIED)

    result = run_tests.run({}, context)

    assert result["passed"] is False
    assert result["exit_code"] != 0
    assert "fail" in result["summary"].lower() or "error" in result["summary"].lower()


def test_target_outside_root_is_rejected(config):
    root = config.project_root
    _write_passing_repo(root)
    context = make_context(config, status=Status.PATCH_APPLIED)

    with pytest.raises(MiniCodexError):
        run_tests.run({"test_target": "../outside.py"}, context)


def test_missing_target_is_rejected(config):
    root = config.project_root
    _write_passing_repo(root)
    context = make_context(config, status=Status.PATCH_APPLIED)

    with pytest.raises(ToolError):
        run_tests.run({"test_target": "missing_test.py"}, context)


def test_unknown_profile_is_rejected(config):
    root = config.project_root
    _write_passing_repo(root)
    context = make_context(config, status=Status.PATCH_APPLIED)

    with pytest.raises(ToolError):
        run_tests.run({"test_profile": "rm -rf"}, context)


def test_tests_require_applied_patch(config):
    root = config.project_root
    _write_passing_repo(root)
    context = make_context(config)  # INVESTIGATING, no patch applied

    with pytest.raises(MiniCodexError):
        run_tests.run({"test_target": "test_ok.py"}, context)


def test_timeout_is_reported(config):
    root = config.project_root
    (root / "pytest.ini").write_text("[pytest]\n")
    (root / "test_slow.py").write_text("import time\n\ndef test_slow():\n    time.sleep(5)\n")
    slow_config = make_config(root, test_timeout_seconds=1)
    context = make_context(slow_config, status=Status.PATCH_APPLIED)

    result = run_tests.run({"test_target": "test_slow.py"}, context)

    assert result["timed_out"] is True
    assert result["passed"] is False
