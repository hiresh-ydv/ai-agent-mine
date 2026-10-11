"""Project-wide exception hierarchy.

Keeping every custom exception in one module makes it easy for the agent loop
to distinguish expected, safely-handled failures from unexpected bugs.
"""

from __future__ import annotations


class MiniCodexError(Exception):
    """Base class for all Mini Codex errors."""


class ConfigError(MiniCodexError):
    """Raised when configuration or environment variables are invalid."""


class SafetyError(MiniCodexError):
    """Base class for safety violations."""


class PathSecurityError(SafetyError):
    """Raised when a path escapes the project root or is otherwise unsafe."""


class SecretAccessError(SafetyError):
    """Raised when a tool tries to read a secret-like file."""


class PatchError(MiniCodexError):
    """Raised when a proposed patch cannot be validated or applied."""


class ToolError(MiniCodexError):
    """Raised for recoverable tool-level errors reported back to the model."""


class LLMError(MiniCodexError):
    """Raised when the LLM provider request fails irrecoverably."""
