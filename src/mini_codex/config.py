"""Configuration loading and validation.

The loader looks for a ``.env`` file in the current working directory first and
then walks up through parent directories, so a shared key at the repository
root works even when the agent is launched from a nested folder. Values already
present in the real environment always win over values found in ``.env`` files.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import dotenv_values

from .errors import ConfigError

DEFAULT_MODEL = "openai/gpt-oss-120b"

DEFAULT_EXCLUDED_DIRS: tuple[str, ...] = (
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "build",
    "dist",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".idea",
    ".vscode",
    ".mini_codex_backups",
)

DEFAULT_EXCLUDED_FILE_PATTERNS: tuple[str, ...] = (
    "*.pyc",
    "*.pyo",
    "*.so",
    "*.dll",
    "*.dylib",
    "*.exe",
    "*.bin",
    "*.png",
    "*.jpg",
    "*.jpeg",
    "*.gif",
    "*.ico",
    "*.pdf",
    "*.zip",
    "*.tar",
    "*.gz",
    "*.whl",
    "*.egg",
    "uv.lock",
    "poetry.lock",
    "package-lock.json",
    "*.db",
    "*.sqlite",
    "*.sqlite3",
)

# Files that must never be read, searched, diffed, or sent to the model.
DEFAULT_SECRET_PATTERNS: tuple[str, ...] = (
    ".env",
    ".env.*",
    "*.env",
    "*.pem",
    "*.key",
    "*.p12",
    "*.pfx",
    "*.keystore",
    "*.jks",
    "id_rsa",
    "id_rsa.*",
    "id_dsa*",
    "id_ecdsa*",
    "id_ed25519*",
    ".git-credentials",
    ".netrc",
    "credentials",
    "credentials.*",
    "secrets",
    "secrets.*",
    "*.secret",
    "*.secrets",
    ".npmrc",
    ".pypirc",
    "service-account*.json",
)


def find_env_files(start: Path) -> list[Path]:
    """Return every ``.env`` file from ``start`` up to the filesystem root."""

    resolved = Path(start).resolve()
    found: list[Path] = []
    for directory in [resolved, *resolved.parents]:
        candidate = directory / ".env"
        if candidate.is_file():
            found.append(candidate)
    return found


def load_environment(start: Path | None = None, override: bool = False) -> dict[str, str]:
    """Load ``.env`` files into ``os.environ``.

    Files nearest to ``start`` take precedence over ancestors. Existing real
    environment variables are preserved unless ``override`` is true.
    """

    start = Path(start) if start is not None else Path.cwd()
    collected: dict[str, str] = {}
    for env_file in reversed(find_env_files(start)):
        for key, value in dotenv_values(env_file).items():
            if value is not None:
                collected[key] = value
    for key, value in collected.items():
        if override or key not in os.environ:
            os.environ[key] = value
    return collected


def _env_int(raw: str | None, default: int, name: str) -> int:
    if raw is None or str(raw).strip() == "":
        return default
    try:
        value = int(str(raw).strip())
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer, got {raw!r}.") from exc
    if value <= 0:
        raise ConfigError(f"{name} must be a positive integer, got {value}.")
    return value


@dataclass(frozen=True)
class Config:
    """Immutable runtime configuration for a single agent task."""

    project_root: Path
    groq_api_key: str
    groq_model: str = DEFAULT_MODEL
    max_agent_turns: int = 20
    max_tool_calls: int = 40
    tool_timeout_seconds: int = 30
    test_timeout_seconds: int = 120
    llm_timeout_seconds: int = 60
    max_file_bytes: int = 1_000_000
    max_search_results: int = 50
    max_output_chars: int = 20_000
    max_read_lines: int = 400
    test_profile: str = "default"
    excluded_dirs: tuple[str, ...] = field(default=DEFAULT_EXCLUDED_DIRS)
    excluded_file_patterns: tuple[str, ...] = field(default=DEFAULT_EXCLUDED_FILE_PATTERNS)
    secret_patterns: tuple[str, ...] = field(default=DEFAULT_SECRET_PATTERNS)

    @classmethod
    def from_env(cls, project_root: str | Path, env_start: str | Path | None = None) -> "Config":
        load_environment(Path(env_start) if env_start is not None else Path.cwd())

        root = Path(project_root).resolve()

        api_key = os.environ.get("GROQ_API_KEY", "").strip()
        if not api_key or api_key.lower().startswith("replace"):
            raise ConfigError(
                "GROQ_API_KEY is not set. Add it to a .env file or the environment "
                "before running Mini Codex."
            )

        model = os.environ.get("GROQ_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL

        return cls(
            project_root=root,
            groq_api_key=api_key,
            groq_model=model,
            max_agent_turns=_env_int(os.environ.get("MAX_AGENT_TURNS"), 20, "MAX_AGENT_TURNS"),
            max_tool_calls=_env_int(os.environ.get("MAX_TOOL_CALLS"), 40, "MAX_TOOL_CALLS"),
            tool_timeout_seconds=_env_int(
                os.environ.get("TOOL_TIMEOUT_SECONDS"), 30, "TOOL_TIMEOUT_SECONDS"
            ),
            test_timeout_seconds=_env_int(
                os.environ.get("TEST_TIMEOUT_SECONDS"), 120, "TEST_TIMEOUT_SECONDS"
            ),
            llm_timeout_seconds=_env_int(
                os.environ.get("LLM_TIMEOUT_SECONDS"), 60, "LLM_TIMEOUT_SECONDS"
            ),
            test_profile=os.environ.get("TEST_PROFILE", "default").strip() or "default",
        )
