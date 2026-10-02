import itertools

import pytest
from anthropic.types import Message

_ids = itertools.count(1)


def message(*blocks: dict, stop: str = "tool_use", **extra) -> Message:
    """A real SDK Message, for fake models."""
    return Message.model_validate(
        {
            "id": f"msg_{next(_ids)}",
            "type": "message",
            "role": "assistant",
            "model": "fake",
            "content": list(blocks),
            "stop_reason": stop,
            "stop_sequence": None,
            "usage": {"input_tokens": 10, "output_tokens": 5},
            **extra,
        }
    )


def tool_use(name: str, **args) -> dict:
    return {"type": "tool_use", "id": f"toolu_{next(_ids)}", "name": name, "input": args}


def text(value: str) -> dict:
    return {"type": "text", "text": value}


class FakeModel:
    """Returns the given responses in order and records every request it receives."""

    name = "fake"

    def __init__(self, *responses: Message):
        self.responses = list(responses)
        self.requests: list[dict] = []

    def create(self, *, system, tools, messages):
        self.requests.append({"system": system, "tools": tools, "messages": [dict(m) for m in messages]})
        return self.responses.pop(0)


@pytest.fixture
def workspace(tmp_path):
    ws = tmp_path / "ws"
    (ws / "src").mkdir(parents=True)
    (ws / "tests").mkdir()
    (ws / "src" / "app.py").write_text("VALUE = 1\n")
    (ws / "tests" / "test_app.py").write_text("def test_ok():\n    assert True\n")
    (ws / "pytest.ini").write_text("[pytest]\ntestpaths = tests\n")
    return ws
