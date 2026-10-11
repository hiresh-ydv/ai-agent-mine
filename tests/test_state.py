from __future__ import annotations

import pytest

from mini_codex.errors import MiniCodexError
from mini_codex.state import Status, TaskState


def test_valid_transition_sequence():
    state = TaskState.new("fix it", ".")
    state.transition(Status.INVESTIGATING)
    state.transition(Status.PATCH_PROPOSED)
    state.transition(Status.AWAITING_APPROVAL)
    state.transition(Status.PATCH_APPLIED)
    state.transition(Status.TESTING)
    state.transition(Status.COMPLETED)

    assert state.status is Status.COMPLETED
    assert state.finished_at is not None


def test_patch_cannot_apply_without_approval():
    state = TaskState.new("fix it", ".")
    state.transition(Status.INVESTIGATING)
    state.transition(Status.PATCH_PROPOSED)

    with pytest.raises(MiniCodexError):
        state.transition(Status.PATCH_APPLIED)


def test_terminal_state_is_final():
    state = TaskState.new("fix it", ".")
    state.transition(Status.INVESTIGATING)
    state.transition(Status.COMPLETED)

    with pytest.raises(MiniCodexError):
        state.transition(Status.INVESTIGATING)


def test_repeated_transition_is_noop():
    state = TaskState.new("fix it", ".")
    state.transition(Status.INVESTIGATING)
    state.transition(Status.INVESTIGATING)
    assert state.status is Status.INVESTIGATING
