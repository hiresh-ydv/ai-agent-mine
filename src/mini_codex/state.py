"""Task and patch state models with an explicit, enforced state machine."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from .errors import MiniCodexError


class Status(str, Enum):
    IDLE = "IDLE"
    INVESTIGATING = "INVESTIGATING"
    PATCH_PROPOSED = "PATCH_PROPOSED"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    PATCH_APPLIED = "PATCH_APPLIED"
    TESTING = "TESTING"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


# Valid transitions. Terminal states have no outgoing edges.
ALLOWED_TRANSITIONS: dict[Status, set[Status]] = {
    Status.IDLE: {Status.INVESTIGATING},
    Status.INVESTIGATING: {
        Status.PATCH_PROPOSED,
        Status.COMPLETED,
        Status.FAILED,
        Status.CANCELLED,
    },
    Status.PATCH_PROPOSED: {
        Status.AWAITING_APPROVAL,
        Status.REJECTED,
        Status.COMPLETED,
        Status.FAILED,
        Status.CANCELLED,
        Status.INVESTIGATING,
    },
    Status.AWAITING_APPROVAL: {
        Status.PATCH_APPLIED,
        Status.REJECTED,
        Status.FAILED,
        Status.CANCELLED,
    },
    Status.PATCH_APPLIED: {Status.TESTING, Status.COMPLETED, Status.FAILED, Status.CANCELLED},
    Status.TESTING: {
        Status.COMPLETED,
        Status.FAILED,
        Status.INVESTIGATING,
        Status.PATCH_PROPOSED,
        Status.CANCELLED,
    },
    Status.COMPLETED: set(),
    Status.REJECTED: set(),
    Status.FAILED: set(),
    Status.CANCELLED: set(),
}

TERMINAL_STATUSES = {
    Status.COMPLETED,
    Status.REJECTED,
    Status.FAILED,
    Status.CANCELLED,
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Patch:
    patch_id: str
    task_id: str
    relative_path: str
    old_text: str
    new_text: str
    reason: str
    unified_diff: str
    source_fingerprint: str
    status: str = "pending"
    created_at: datetime = field(default_factory=_now)


@dataclass
class ToolRecord:
    tool_name: str
    validated_arguments: dict[str, Any]
    status: str
    started_at: datetime = field(default_factory=_now)
    finished_at: datetime | None = None
    bounded_result_summary: str = ""
    error_category: str | None = None


@dataclass
class TaskState:
    task_id: str
    user_query: str
    project_root: Path
    status: Status = Status.IDLE
    messages: list[dict[str, Any]] = field(default_factory=list)
    tool_call_count: int = 0
    turn_count: int = 0
    pending_patch_id: str | None = None
    approval_decision: str | None = None
    changed_files: list[str] = field(default_factory=list)
    test_results: dict[str, Any] | None = None
    patches: dict[str, Patch] = field(default_factory=dict)
    tool_history: list[ToolRecord] = field(default_factory=list)
    error: str | None = None
    started_at: datetime = field(default_factory=_now)
    finished_at: datetime | None = None

    @classmethod
    def new(cls, user_query: str, project_root: Path) -> "TaskState":
        return cls(
            task_id=uuid.uuid4().hex[:12],
            user_query=user_query,
            project_root=Path(project_root),
        )

    def transition(self, new_status: Status) -> None:
        if new_status == self.status:
            return
        allowed = ALLOWED_TRANSITIONS.get(self.status, set())
        if new_status not in allowed:
            raise MiniCodexError(
                f"Invalid state transition: {self.status.value} -> {new_status.value}"
            )
        self.status = new_status
        if new_status in TERMINAL_STATUSES and self.finished_at is None:
            self.finished_at = _now()

    def record_tool(self, record: ToolRecord) -> None:
        self.tool_history.append(record)

    def pending_patch(self) -> Patch | None:
        if self.pending_patch_id is None:
            return None
        return self.patches.get(self.pending_patch_id)
