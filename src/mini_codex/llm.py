"""Groq client wrapper.

This module is the only place that talks to the network. It converts Groq's
response objects into small, provider-agnostic dataclasses and applies bounded
retries for transient failures.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Protocol

from .errors import LLMError

_RETRYABLE_NAMES = {
    "RateLimitError",
    "APIConnectionError",
    "APITimeoutError",
    "InternalServerError",
}


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: str


@dataclass
class ChatResponse:
    content: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)


class LLMClient(Protocol):
    def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None) -> ChatResponse:
        ...


def _is_retryable(exc: Exception) -> bool:
    if type(exc).__name__ in _RETRYABLE_NAMES:
        return True
    status = getattr(exc, "status_code", None)
    return isinstance(status, int) and status >= 500


def _parse_response(response: Any) -> ChatResponse:
    try:
        message = response.choices[0].message
    except (AttributeError, IndexError, TypeError) as exc:
        raise LLMError("Malformed response from the model provider.") from exc

    content = getattr(message, "content", None)
    tool_calls: list[ToolCall] = []
    for call in getattr(message, "tool_calls", None) or []:
        function = getattr(call, "function", None)
        if function is None:
            continue
        tool_calls.append(
            ToolCall(
                id=getattr(call, "id", "") or "",
                name=getattr(function, "name", "") or "",
                arguments=getattr(function, "arguments", "") or "",
            )
        )
    return ChatResponse(content=content, tool_calls=tool_calls)


class GroqLLM:
    def __init__(
        self,
        api_key: str,
        model: str,
        max_retries: int = 2,
        timeout_seconds: int = 60,
    ) -> None:
        try:
            from groq import Groq
        except ImportError as exc:  # pragma: no cover - depends on environment
            raise LLMError(
                "The 'groq' package is required. Install project dependencies first."
            ) from exc

        self.model = model
        self.max_retries = max_retries
        self._client = Groq(api_key=api_key, timeout=timeout_seconds)

    def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> ChatResponse:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        attempt = 0
        while True:
            try:
                response = self._client.chat.completions.create(**kwargs)
                return _parse_response(response)
            except Exception as exc:  # noqa: BLE001 - provider raises many types
                if _is_retryable(exc) and attempt < self.max_retries:
                    attempt += 1
                    time.sleep(min(2 ** attempt, 8))
                    continue
                raise LLMError(f"Groq request failed: {exc}") from exc
