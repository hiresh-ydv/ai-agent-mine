"""Shared test doubles and helpers."""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

from mini_codex.config import Config
from mini_codex.console import Console
from mini_codex.context import ToolContext
from mini_codex.llm import ChatResponse, ToolCall
from mini_codex.state import Status, TaskState


def make_config(root: str | Path, **overrides: Any) -> Config:
    values: dict[str, Any] = {
        "project_root": Path(root).resolve(),
        "groq_api_key": "test-key",
        "groq_model": "test-model",
    }
    values.update(overrides)
    return Config(**values)


class FakeConsole(Console):
    def __init__(self, answers: list[str] | None = None) -> None:
        self._buffer = io.StringIO()
        super().__init__(stream=self._buffer, input_fn=self._answer, color=False)
        self.answers = list(answers or [])

    def _answer(self, prompt: str) -> str:
        self.write(prompt)
        if not self.answers:
            return "n"
        return self.answers.pop(0)

    def text(self) -> str:
        return self._buffer.getvalue()


class FakeLLM:
    def __init__(self, responder) -> None:
        self.responder = responder
        self.messages_seen: list[list[dict[str, Any]]] = []

    def complete(self, messages, tools=None) -> ChatResponse:
        self.messages_seen.append(messages)
        return self.responder(messages, tools)


def tool_response(*calls: tuple[str, dict[str, Any]]) -> ChatResponse:
    tool_calls = [
        ToolCall(id=f"call_{index}", name=name, arguments=json.dumps(args))
        for index, (name, args) in enumerate(calls)
    ]
    return ChatResponse(content=None, tool_calls=tool_calls)


def raw_tool_response(name: str, arguments: str, call_id: str = "call_raw") -> ChatResponse:
    return ChatResponse(content=None, tool_calls=[ToolCall(id=call_id, name=name, arguments=arguments)])


def text_response(text: str) -> ChatResponse:
    return ChatResponse(content=text, tool_calls=[])


def last_tool_result(messages: list[dict[str, Any]]) -> dict[str, Any] | None:
    for message in reversed(messages):
        if message.get("role") == "tool":
            return json.loads(message["content"])
    return None


def make_context(
    config: Config,
    *,
    console: FakeConsole | None = None,
    query: str = "task",
    status: Status = Status.INVESTIGATING,
) -> ToolContext:
    state = TaskState.new(query, config.project_root)
    if status is not Status.IDLE:
        state.status = status
    return ToolContext(
        config=config,
        state=state,
        console=console or FakeConsole(),
        root=config.project_root,
        interactive=False,
    )
