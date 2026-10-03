import json

from conftest import FakeModel, message, text, tool_use

from harness.config import VERSIONS
from harness.loop import run_agent


def _plain(messages):
    return json.loads(json.dumps(messages, default=lambda o: o.model_dump(mode="json")))


def test_history_is_append_only_and_prefix_is_frozen(workspace):
    model = FakeModel(
        message(tool_use("read_file", path="src/app.py")),
        message(tool_use("edit_file", path="src/app.py", old="VALUE = 1", new="VALUE = 2")),
        message(tool_use("finish", summary="done")),
    )
    result = run_agent("bump VALUE", workspace, model, VERSIONS["v4"])
    assert result.status == "done"
    requests = model.requests
    # The system prompt and tool set never change during a run (caching, and the
    # model's reasoning is bound to the exact conversation that produced it).
    assert len({r["system"] for r in requests}) == 1
    assert len({json.dumps(r["tools"], sort_keys=True) for r in requests}) == 1
    # Every request's history starts with the previous request's history, unedited.
    for earlier, later in zip(requests, requests[1:], strict=False):
        before, after = _plain(earlier["messages"]), _plain(later["messages"])
        assert after[: len(before)] == before


def test_parallel_tool_calls_return_in_one_turn(workspace):
    model = FakeModel(
        message(tool_use("read_file", path="src/app.py"), tool_use("list_files")),
        message(text("All good."), stop="end_turn"),
    )
    result = run_agent("look around", workspace, model, VERSIONS["v1"])
    results_turn = result.messages[2]
    assert results_turn["role"] == "user"
    assert [b["type"] for b in results_turn["content"]] == ["tool_result", "tool_result"]


def test_naive_harness_crashes_on_a_tool_error_v1_feeds_it_back(workspace):
    bad = message(tool_use("read_file", path="nope.py"))
    crashed = run_agent("read", workspace, FakeModel(bad), VERSIONS["v0"])
    assert crashed.status == "crashed" and "No such file" in crashed.error

    recovered = run_agent("read", workspace, FakeModel(bad, message(text("ok"), stop="end_turn")), VERSIONS["v1"])
    error_result = recovered.messages[2]["content"][0]
    assert recovered.status == "done"
    assert error_result["is_error"] is True and "No such file" in error_result["content"]


def test_invalid_tool_input_becomes_feedback(workspace):
    model = FakeModel(message(tool_use("read_file", file="src/app.py")), message(text("ok"), stop="end_turn"))
    result = run_agent("read", workspace, model, VERSIONS["v1"])
    assert "missing required argument 'path'" in result.messages[2]["content"][0]["content"]


def test_refusal_stops_without_running_tools(workspace):
    model = FakeModel(
        message(text(""), stop="refusal", stop_details={"type": "refusal", "category": None, "explanation": None})
    )
    result = run_agent("x", workspace, model, VERSIONS["v4"])
    assert result.status == "refused" and len(model.requests) == 1


def test_max_tokens_is_reported_not_executed(workspace):
    model = FakeModel(message(text("partial"), stop="max_tokens"))
    assert run_agent("x", workspace, model, VERSIONS["v4"]).status == "max_tokens"


def test_pause_turn_resumes_by_appending(workspace):
    model = FakeModel(message(text("working"), stop="pause_turn"), message(text("done"), stop="end_turn"))
    result = run_agent("x", workspace, model, VERSIONS["v1"])
    assert result.status == "done" and len(model.requests) == 2
    assert len(model.requests[1]["messages"]) == 2  # paused turn kept, nothing rebuilt


def test_finish_is_required_once_the_harness_offers_it(workspace):
    chatty = FakeModel(
        message(text("I think I'm done."), stop="end_turn"), message(text("Really done."), stop="end_turn")
    )
    result = run_agent("x", workspace, chatty, VERSIONS["v2"])
    assert result.status == "stalled" and len(chatty.requests) == 2


def test_tests_see_same_size_edits_made_within_one_second(workspace):
    """Regression: a stale .pyc made verification check the old code."""
    (workspace / "tests" / "test_app.py").write_text(
        "from src.app import VALUE\n\ndef test_value():\n    assert VALUE == 2\n"
    )
    (workspace / "pytest.ini").write_text("[pytest]\npythonpath = .\ntestpaths = tests\n")
    from harness.tools import run_test_suite

    assert run_test_suite(workspace).passed is False
    (workspace / "src" / "app.py").write_text("VALUE = 2\n")  # same size, same second
    assert run_test_suite(workspace).passed is True


def test_verify_on_finish_bounces_failing_work(workspace):
    (workspace / "tests" / "test_app.py").write_text(
        "from src.app import VALUE\n\ndef test_value():\n    assert VALUE == 2\n"
    )
    (workspace / "pytest.ini").write_text("[pytest]\npythonpath = .\ntestpaths = tests\n")
    model = FakeModel(
        message(tool_use("finish", summary="done")),  # premature
        message(tool_use("edit_file", path="src/app.py", old="VALUE = 1", new="VALUE = 2")),
        message(tool_use("finish", summary="done for real")),
    )
    result = run_agent("make the test pass", workspace, model, VERSIONS["v3"])
    first_finish = result.messages[2]["content"][0]
    assert first_finish["is_error"] and "test suite fails" in first_finish["content"]
    assert result.status == "done" and result.final_text == "done for real"


def test_context_budget_stops_before_sending(workspace):
    (workspace / "huge.txt").write_text("x" * 600_000)
    model = FakeModel(message(tool_use("read_file", path="huge.txt")), message(text("never sent"), stop="end_turn"))
    result = run_agent("read it", workspace, model, VERSIONS["v1"])
    assert result.status == "context_budget" and len(model.requests) == 1


def test_v4_truncates_large_output_at_the_source(workspace):
    (workspace / "huge.txt").write_text("x" * 600_000)
    model = FakeModel(message(tool_use("read_file", path="huge.txt")), message(tool_use("finish", summary="ok")))
    result = run_agent("read it", workspace, model, VERSIONS["v4"])
    output = result.messages[2]["content"][0]["content"]
    assert result.status == "done" and len(output) < 7_000 and "offset and limit" in output


def test_step_limit(workspace):
    model = FakeModel(*[message(tool_use("list_files")) for _ in range(40)])
    assert run_agent("loop forever", workspace, model, VERSIONS["v1"]).status == "step_limit"


def test_finish_runs_after_the_other_calls_in_its_turn(workspace):
    """Regression: `finish` verified the state *before* an edit requested in the same turn."""
    (workspace / "tests" / "test_app.py").write_text(
        "from src.app import VALUE\n\ndef test_value():\n    assert VALUE == 2\n"
    )
    (workspace / "pytest.ini").write_text("[pytest]\npythonpath = .\ntestpaths = tests\n")
    model = FakeModel(
        message(
            tool_use("finish", summary="done"),
            tool_use("edit_file", path="src/app.py", old="VALUE = 1", new="VALUE = 2"),
        )
    )
    result = run_agent("bump VALUE", workspace, model, VERSIONS["v3"])
    assert result.status == "done" and len(model.requests) == 1  # the edit was verified, not skipped
    results_turn = result.messages[2]["content"]
    calls = result.messages[1]["content"]
    assert [r["tool_use_id"] for r in results_turn] == [c.id for c in calls]  # results keep the call order
