"""The runtime context passed to every tool."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import Config
from .console import Console
from .state import TaskState


@dataclass
class ToolContext:
    config: Config
    state: TaskState
    console: Console
    root: Path
    interactive: bool = True

    @property
    def backups_root(self) -> Path:
        return self.root / ".mini_codex_backups" / self.state.task_id
