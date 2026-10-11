"""Thin terminal abstraction.

Every user-facing message and every interactive prompt goes through a
``Console`` instance. Tests inject a fake console so the approval flow can be
exercised deterministically without a real terminal.
"""

from __future__ import annotations

import os
import sys
from typing import Callable, Iterable, TextIO


class Console:
    def __init__(
        self,
        stream: TextIO | None = None,
        input_fn: Callable[[str], str] | None = None,
        color: bool | None = None,
    ) -> None:
        self.stream = stream if stream is not None else sys.stdout
        self._input = input_fn if input_fn is not None else input
        if color is None:
            color = bool(getattr(self.stream, "isatty", lambda: False)()) and os.environ.get(
                "NO_COLOR"
            ) is None
        self.color = color

    def _paint(self, text: str, code: str) -> str:
        if not self.color:
            return text
        return f"\x1b[{code}m{text}\x1b[0m"

    def write(self, message: str = "") -> None:
        print(message, file=self.stream)

    def info(self, message: str) -> None:
        self.write(f"[agent] {message}")

    def success(self, message: str) -> None:
        self.write(self._paint(message, "32"))

    def warn(self, message: str) -> None:
        self.write(self._paint(message, "33"))

    def error(self, message: str) -> None:
        self.write(self._paint(message, "31"))

    def rule(self, title: str = "") -> None:
        line = "-" * max(4, 60 - len(title))
        self.write(f"{title} {line}" if title else "-" * 60)

    def block(self, lines: Iterable[str]) -> None:
        for line in lines:
            self.write(line)

    def prompt(self, text: str) -> str:
        return self._input(text)


def confirm(text: str, console: "Console") -> bool:
    """Return True only for an explicit yes. Empty/other input counts as no."""

    try:
        answer = console.prompt(text)
    except (EOFError, KeyboardInterrupt):
        return False
    return answer.strip().lower() in {"y", "yes"}
