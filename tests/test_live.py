"""Optional live test against the real Groq API.

Skipped unless ``MINI_CODEX_LIVE=1`` and a valid ``GROQ_API_KEY`` are present,
because it makes real network calls and is non-deterministic.
"""

from __future__ import annotations

import os
import shutil

import pytest

from helpers import FakeConsole, make_config
from mini_codex.agent import Agent
from mini_codex.llm import GroqLLM

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        os.environ.get("MINI_CODEX_LIVE") != "1",
        reason="Set MINI_CODEX_LIVE=1 to run live Groq tests.",
    ),
]


def test_live_repair_of_discount_bug(sample_repo):
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        pytest.skip("GROQ_API_KEY is not set.")

    config = make_config(
        sample_repo,
        groq_api_key=api_key,
        groq_model=os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b"),
        max_agent_turns=12,
    )
    console = FakeConsole(["y"] * 5)
    llm = GroqLLM(api_key, config.groq_model, timeout_seconds=60)

    report = Agent(config, console, llm).run(
        "The discount calculation in this project is incorrect. Find the bug and fix it, "
        "then run the tests for the discount module."
    )

    assert report.status in {"COMPLETED", "REJECTED"}
