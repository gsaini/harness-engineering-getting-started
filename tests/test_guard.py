import pytest

from harness.errors import ToolError
from harness.guard import Guard, is_read_only


def test_floor_holds_even_without_the_guard(tmp_path):
    run = tmp_path / "run"
    (run / "ws").mkdir(parents=True)
    naive = Guard(run / "ws", floor=run, enabled=False)
    assert naive.resolve("../neighbor/x") == (run / "neighbor" / "x").resolve()  # inside the run dir: allowed in v0
    for escape in ("../../outside.txt", "/etc/passwd"):
        with pytest.raises(ToolError, match="outside the run directory"):
            naive.resolve(escape)


def test_guard_keeps_the_agent_in_its_workspace(tmp_path):
    run = tmp_path / "run"
    (run / "ws").mkdir(parents=True)
    guard = Guard(run / "ws", floor=run, enabled=True)
    with pytest.raises(ToolError, match="outside your workspace"):
        guard.resolve("../neighbor/settings.ini", write=True)


def test_tests_are_readable_but_not_writable(workspace):
    guard = Guard(workspace, workspace, enabled=True)
    assert guard.resolve("tests/test_app.py").is_file()
    for path in ("tests/test_app.py", "tests/deep/new_test.py", "pytest.ini", "conftest.py", ".harness/lessons.md"):
        with pytest.raises(ToolError, match="read-only"):
            guard.resolve(path, write=True)
    assert guard.resolve("src/app.py", write=True)


def test_read_only_rule():
    assert is_read_only("tests/a/b.py") and is_read_only("pytest.ini")
    assert not is_read_only("src/tests_helper.py")
