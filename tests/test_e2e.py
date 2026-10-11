"""End-to-end scenarios driven by a scripted (fake) model."""

from __future__ import annotations

from helpers import FakeConsole, FakeLLM, last_tool_result, make_config, text_response, tool_response
from mini_codex.agent import Agent

DISCOUNT_PATH = "buggy_discount.py"
DISCOUNT_FIX = "return price * (1 - discount_percent / 100)"


def _step(messages) -> int:
    return sum(1 for message in messages if message.get("role") == "assistant")


def test_successful_repair_end_to_end(sample_repo):
    config = make_config(sample_repo)
    console = FakeConsole(["y"])

    def responder(messages, tools):
        step = _step(messages)
        if step == 0:
            return tool_response(("search_codebase", {"query": "apply_discount"}))
        if step == 1:
            return tool_response(
                ("read_file", {"path": DISCOUNT_PATH, "start_line": 1, "end_line": 20})
            )
        if step == 2:
            return tool_response(
                (
                    "propose_edit",
                    {
                        "path": DISCOUNT_PATH,
                        "old_text": "return price - discount_percent",
                        "new_text": DISCOUNT_FIX,
                        "reason": "Convert the percentage to a fraction before subtracting.",
                    },
                )
            )
        if step == 3:
            return tool_response(
                (
                    "request_approval_and_apply",
                    {"patch_id": last_tool_result(messages)["patch_id"]},
                )
            )
        if step == 4:
            return tool_response(("run_tests", {"test_target": "test_buggy_discount.py"}))
        return text_response("Fixed apply_discount; the discount tests now pass.")

    report = Agent(config, console, FakeLLM(responder)).run(
        "The discount calculation is incorrect. Find and fix it."
    )

    assert report.status == "COMPLETED"
    assert report.changed_files == [DISCOUNT_PATH]
    assert report.test_results is not None
    assert report.test_results["passed"] is True
    assert DISCOUNT_FIX in (sample_repo / DISCOUNT_PATH).read_text()


def test_rejected_repair_leaves_file_unchanged(sample_repo):
    config = make_config(sample_repo)
    console = FakeConsole(["n"])
    original = (sample_repo / DISCOUNT_PATH).read_bytes()

    def responder(messages, tools):
        step = _step(messages)
        if step == 0:
            return tool_response(("search_codebase", {"query": "apply_discount"}))
        if step == 1:
            return tool_response(
                ("read_file", {"path": DISCOUNT_PATH, "start_line": 1, "end_line": 20})
            )
        if step == 2:
            return tool_response(
                (
                    "propose_edit",
                    {
                        "path": DISCOUNT_PATH,
                        "old_text": "return price - discount_percent",
                        "new_text": DISCOUNT_FIX,
                        "reason": "Convert the percentage to a fraction.",
                    },
                )
            )
        return tool_response(
            ("request_approval_and_apply", {"patch_id": last_tool_result(messages)["patch_id"]})
        )

    report = Agent(config, console, FakeLLM(responder)).run("Fix the discount calculation.")

    assert report.status == "REJECTED"
    assert report.changed_files == []
    assert report.test_results is None
    assert (sample_repo / DISCOUNT_PATH).read_bytes() == original


def test_stale_patch_is_refused_end_to_end(sample_repo):
    config = make_config(sample_repo)
    console = FakeConsole(["y"])
    external = "def apply_discount(price, discount_percent):\n    return 0\n"

    def responder(messages, tools):
        step = _step(messages)
        if step == 0:
            return tool_response(("search_codebase", {"query": "apply_discount"}))
        if step == 1:
            return tool_response(
                ("read_file", {"path": DISCOUNT_PATH, "start_line": 1, "end_line": 20})
            )
        if step == 2:
            return tool_response(
                (
                    "propose_edit",
                    {
                        "path": DISCOUNT_PATH,
                        "old_text": "return price - discount_percent",
                        "new_text": DISCOUNT_FIX,
                        "reason": "Convert the percentage to a fraction.",
                    },
                )
            )
        if step == 3:
            (sample_repo / DISCOUNT_PATH).write_text(external)
            return tool_response(
                (
                    "request_approval_and_apply",
                    {"patch_id": last_tool_result(messages)["patch_id"]},
                )
            )
        return text_response("Stopping: the file changed underneath me.")

    report = Agent(config, console, FakeLLM(responder)).run("Fix the discount calculation.")

    assert report.status == "FAILED"
    assert report.changed_files == []
    assert (sample_repo / DISCOUNT_PATH).read_text() == external


def test_max_turns_stops_runaway_loop(sample_repo):
    config = make_config(sample_repo, max_agent_turns=3)
    llm = FakeLLM(lambda messages, tools: tool_response(("search_codebase", {"query": "discount"})))

    report = Agent(config, FakeConsole(), llm).run("Investigate forever.")

    assert report.status == "FAILED"
    assert "turns" in report.error.lower()
