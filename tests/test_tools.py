import pytest

from harness.context import truncate
from harness.errors import ToolError
from harness.tools import Workspace, build_tools


@pytest.fixture
def tools(workspace):
    return {t.name: t for t in build_tools(Workspace(workspace, workspace, guard=True), finish=True, remember=True)}


def test_validation_rejects_bad_arguments(tools):
    read = tools["read_file"]
    with pytest.raises(ToolError, match="missing required argument 'path'"):
        read.validate({})
    with pytest.raises(ToolError, match="unknown argument 'file'; missing required argument 'path'"):
        read.validate({"file": "a"})  # every problem reported at once
    with pytest.raises(ToolError, match="must be a int"):
        read.validate({"path": "a", "offset": "3"})
    with pytest.raises(ToolError, match="must be a int"):
        read.validate({"path": "a", "offset": True})  # bool is not an int here
    with pytest.raises(ToolError, match="JSON object"):
        read.validate("src/app.py")


def test_schema_is_closed(tools):
    schema = tools["edit_file"].schema()["input_schema"]
    assert schema["additionalProperties"] is False
    assert schema["required"] == ["path", "old", "new"]


def test_missing_file_suggests_where_it_is(tools):
    with pytest.raises(ToolError, match="Did you mean: src/app.py"):
        tools["read_file"].fn(path="lib/app.py")


def test_read_a_line_range(tools, workspace):
    (workspace / "big.txt").write_text("\n".join(f"line {i}" for i in range(1, 101)))
    out = tools["read_file"].fn(path="big.txt", offset=10, limit=3)
    assert out.splitlines() == ["[lines 10-12 of 100]", "line 10", "line 11", "line 12"]


def test_edit_needs_a_unique_match(tools, workspace):
    (workspace / "src" / "dup.py").write_text("x = 1\nx = 1\n")
    with pytest.raises(ToolError, match="appears 2 times"):
        tools["edit_file"].fn(path="src/dup.py", old="x = 1", new="x = 2")
    with pytest.raises(ToolError, match="not found"):
        tools["edit_file"].fn(path="src/dup.py", old="y = 1", new="y = 2")
    assert tools["edit_file"].fn(path="src/app.py", old="VALUE = 1", new="VALUE = 2") == "Edited src/app.py."


def test_search_counts_and_caps(tools, workspace):
    (workspace / "log.txt").write_text("\n".join(["ok"] * 5 + ["boom"] * 50))
    out = tools["search"].fn(pattern="boom", path="log.txt")
    assert out.startswith("50 match(es):") and "10 more matches" in out
    with pytest.raises(ToolError, match="Invalid regular expression"):
        tools["search"].fn(pattern="(")


def test_run_tests_reports_pass(tools):
    assert "passed" in tools["run_tests"].fn()


def test_truncate_says_how_to_get_the_rest():
    assert truncate("short", 100, "hint") == "short"
    out = truncate("x" * 1000, 100, "Use offset.")
    assert out.startswith("x" * 100) and "showing 100 of 1,000 characters. Use offset." in out
