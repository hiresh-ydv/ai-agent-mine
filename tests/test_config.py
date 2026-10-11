from __future__ import annotations

import pytest

from mini_codex.config import Config, load_environment
from mini_codex.errors import ConfigError


def test_missing_api_key_raises(tmp_path, monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(ConfigError):
        Config.from_env(tmp_path, env_start=tmp_path)


def test_placeholder_key_raises(tmp_path, monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "replace_with_your_key")
    with pytest.raises(ConfigError):
        Config.from_env(tmp_path, env_start=tmp_path)


def test_loads_env_from_parent_directory(tmp_path, monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_MODEL", raising=False)
    (tmp_path / ".env").write_text("GROQ_API_KEY=abc123\nGROQ_MODEL=parent-model\n")
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)

    config = Config.from_env(nested, env_start=nested)

    assert config.groq_api_key == "abc123"
    assert config.groq_model == "parent-model"
    assert config.project_root == nested.resolve()


def test_nearest_env_wins(tmp_path, monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    (tmp_path / ".env").write_text("GROQ_API_KEY=outer\n")
    nested = tmp_path / "inner"
    nested.mkdir()
    (nested / ".env").write_text("GROQ_API_KEY=inner\n")

    load_environment(nested, override=True)
    config = Config.from_env(nested, env_start=nested)

    assert config.groq_api_key == "inner"


def test_invalid_int_env_reports_config_error(tmp_path, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "abc123")
    monkeypatch.setenv("MAX_AGENT_TURNS", "not-a-number")
    with pytest.raises(ConfigError):
        Config.from_env(tmp_path, env_start=tmp_path)


def test_defaults_are_applied(tmp_path, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "abc123")
    monkeypatch.delenv("MAX_AGENT_TURNS", raising=False)
    monkeypatch.delenv("GROQ_MODEL", raising=False)

    config = Config.from_env(tmp_path, env_start=tmp_path)

    assert config.max_agent_turns == 20
    assert config.max_tool_calls == 40
    assert config.groq_model
