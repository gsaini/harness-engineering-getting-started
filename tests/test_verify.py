"""Verification needs evidence: exit code 0 is a claim the code under test can fake."""

from conftest import FakeModel, message, tool_use

from harness.config import VERSIONS
from harness.loop import run_agent
from harness.tools import collect_tests, run_test_suite


def _needs_value_2(workspace):
    (workspace / "tests" / "test_app.py").write_text(
        "from src.app import VALUE\n\ndef test_value():\n    assert VALUE == 2\n"
    )
    (workspace / "pytest.ini").write_text("[pytest]\npythonpath = .\ntestpaths = tests\n")


def test_collect_tests_lists_node_ids(workspace):
    _needs_value_2(workspace)
    assert collect_tests(workspace) == {"tests/test_app.py::test_value"}


def test_exit_code_zero_is_not_evidence(workspace):
    """The module under test ends the process before pytest reports anything."""
    _needs_value_2(workspace)
    inventory = collect_tests(workspace)
    (workspace / "src" / "app.py").write_text("import os\nos._exit(0)\n")
    assert run_test_suite(workspace).passed is True  # v0–v4 trust the exit code — this is the hole
    report = run_test_suite(workspace, expect=inventory)
    assert report.passed is False and report.missing == ("tests/test_app.py::test_value",)
    assert "not reported as passed" in report.output and "no output" in report.output


def test_skipped_tests_are_not_evidence(workspace):
    """The module under test skips itself at import time; pytest collects nothing and exits 5."""
    _needs_value_2(workspace)
    inventory = collect_tests(workspace)
    (workspace / "src" / "app.py").write_text("import pytest\npytest.skip('flaky', allow_module_level=True)\n")
    assert run_test_suite(workspace).passed is True
    report = run_test_suite(workspace, expect=inventory)
    assert report.passed is False and report.returncode == 5 and "test_value" in report.output


def test_evidence_mode_passes_honest_work_and_empty_suites(workspace):
    _needs_value_2(workspace)
    inventory = collect_tests(workspace)
    (workspace / "src" / "app.py").write_text("VALUE = 2\n")
    report = run_test_suite(workspace, expect=inventory)
    assert report.passed and report.missing == () and "1 passed" in report.output
    assert "PASSED" not in report.output  # the check-off lines stay out of the model's context
    (workspace / "tests" / "test_app.py").unlink()
    assert run_test_suite(workspace, expect=frozenset()).passed is True  # nothing was expected


def test_credentials_are_kept_from_the_code_under_test(workspace, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    (workspace / "tests" / "test_app.py").write_text(
        "import os\n\ndef test_no_key():\n    assert not any(k.startswith('ANTHROPIC_') for k in os.environ)\n"
    )
    assert run_test_suite(workspace).passed is True


def test_v5_finish_refuses_a_run_whose_tests_vanished(workspace):
    _needs_value_2(workspace)
    skip = "import pytest\npytest.skip('flaky', allow_module_level=True)\n"
    model = FakeModel(
        message(tool_use("write_file", path="src/app.py", content=skip)),
        message(tool_use("finish", summary="green")),  # v4 would accept this
        message(tool_use("write_file", path="src/app.py", content="VALUE = 2\n")),
        message(tool_use("finish", summary="green for real")),
    )
    result = run_agent("make the tests pass", workspace, model, VERSIONS["v5"])
    bounced = result.messages[4]["content"][0]
    assert bounced["is_error"] and "tests/test_app.py::test_value" in bounced["content"]
    assert result.status == "done" and result.final_text == "green for real"
