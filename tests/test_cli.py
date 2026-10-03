from harness.cli import main
from harness.config import VERSIONS


def test_versions_lists_every_harness(capsys):
    assert main(["versions"]) == 0
    out = capsys.readouterr().out
    assert all(name in out for name in VERSIONS)


def test_eval_rejects_bad_arguments_with_a_message(capsys, tmp_path):
    assert main(["eval", "--versions", "v9", "--out", str(tmp_path)]) == 2
    assert "Unknown version(s): v9" in capsys.readouterr().out
    assert main(["eval", "--tasks", "no-such-task", "--out", str(tmp_path)]) == 2
    assert "Unknown task(s): no-such-task" in capsys.readouterr().out
    assert main(["eval", "--repeat", "0", "--out", str(tmp_path)]) == 2
    assert "--repeat" in capsys.readouterr().out
