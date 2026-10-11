from __future__ import annotations

import json

from helpers import FakeConsole, FakeLLM, make_config, raw_tool_response, text_response, tool_response
from mini_codex.agent import Agent
from mini_codex.errors import LLMError
from mini_codex.state import TaskState


def _tool_results(state: TaskState):
    return [
        json.loads(message["content"])
        for message in state.messages
        if message.get("role") == "tool"
    ]


def test_unknown_tool_reports_error_then_finishes(config):
    responses = [tool_response(("not_a_tool", {})), text_response("finished")]
    llm = FakeLLM(lambda messages, tools: responses.pop(0))
    state = TaskState.new("task", config.project_root)

    report = Agent(config, FakeConsole(), llm).run("task", state)

    results = _tool_results(state)
    assert results[0]["ok"] is False
    assert "Unknown tool" in results[0]["error"]
    assert report.status == "COMPLETED"


def test_malformed_arguments_reported(config):
    responses = [raw_tool_response("read_file", "{not valid json"), text_response("ok")]
    llm = FakeLLM(lambda messages, tools: responses.pop(0))
    state = TaskState.new("task", config.project_root)

    Agent(config, FakeConsole(), llm).run("task", state)

    assert "Malformed JSON" in _tool_results(state)[0]["error"]


def test_invalid_arguments_reported(config):
    responses = [tool_response(("read_file", {"path": "x.py"})), text_response("ok")]
    llm = FakeLLM(lambda messages, tools: responses.pop(0))
    state = TaskState.new("task", config.project_root)

    Agent(config, FakeConsole(), llm).run("task", state)

    assert "Invalid arguments" in _tool_results(state)[0]["error"]


def test_tool_results_correlate_with_tool_call_ids(config):
    responses = [tool_response(("search_codebase", {"query": "x"})), text_response("done")]
    llm = FakeLLM(lambda messages, tools: responses.pop(0))
    state = TaskState.new("task", config.project_root)

    Agent(config, FakeConsole(), llm).run("task", state)

    assistant_ids = {
        call["id"]
        for message in state.messages
        if message.get("role") == "assistant"
        for call in message.get("tool_calls", [])
    }
    tool_ids = {message["tool_call_id"] for message in state.messages if message.get("role") == "tool"}
    assert assistant_ids == tool_ids
    assert assistant_ids  # sanity: at least one call happened


def test_turn_limit_is_enforced(config):
    limited = make_config(config.project_root, max_agent_turns=3)
    llm = FakeLLM(lambda messages, tools: tool_response(("search_codebase", {"query": "x"})))

    report = Agent(limited, FakeConsole(), llm).run("task")

    assert report.status == "FAILED"
    assert "turns" in report.error.lower()


def test_tool_call_limit_is_enforced(config):
    limited = make_config(config.project_root, max_tool_calls=2)
    llm = FakeLLM(lambda messages, tools: tool_response(("search_codebase", {"query": "x"})))

    report = Agent(limited, FakeConsole(), llm).run("task")

    assert report.status == "FAILED"
    assert "tool calls" in report.error.lower()


def test_patch_is_not_applied_without_approval(config):
    root = config.project_root
    (root / "app.py").write_text("def f():\n    return 1\n")
    responses = [
        tool_response(
            (
                "propose_edit",
                {"path": "app.py", "old_text": "return 1", "new_text": "return 2", "reason": "x"},
            )
        ),
        text_response("Stopping without applying."),
    ]
    llm = FakeLLM(lambda messages, tools: responses.pop(0))

    report = Agent(config, FakeConsole(), llm).run("task")

    assert "return 1" in (root / "app.py").read_text()
    assert report.changed_files == []


def test_llm_error_fails_safely(config):
    def responder(messages, tools):
        raise LLMError("provider exploded")

    report = Agent(config, FakeConsole(), FakeLLM(responder)).run("task")

    assert report.status == "FAILED"
    assert "provider exploded" in report.error


def test_unsafe_path_error_is_returned_to_model(config):
    responses = [
        tool_response(("read_file", {"path": "../secret.txt", "start_line": 1, "end_line": 2})),
        text_response("stopped"),
    ]
    llm = FakeLLM(lambda messages, tools: responses.pop(0))
    state = TaskState.new("task", config.project_root)

    report = Agent(config, FakeConsole(), llm).run("task", state)

    error = _tool_results(state)[0]["error"].lower()
    assert "traversal" in error or "escapes" in error
    assert report.status == "COMPLETED"
