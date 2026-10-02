from conftest import message

from harness.model import ClaudeModel


class FakeStream:
    def __init__(self, response):
        self.response = response

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get_final_message(self):
        return self.response


class FakeClient:
    def __init__(self):
        self.calls = []
        outer = self

        class Messages:
            def stream(self, **kwargs):
                outer.calls.append(kwargs)
                return FakeStream(message({"type": "text", "text": "hi"}, stop="end_turn"))

        class Beta:
            messages = Messages()

        self.beta = Beta()


TOOLS = [{"name": "read_file", "description": "d", "input_schema": {"type": "object", "properties": {}}}]


def test_request_shape_for_opus_5_5():
    req = ClaudeModel(client=FakeClient()).request(
        system="sys", tools=TOOLS, messages=[{"role": "user", "content": "hi"}]
    )
    assert req["model"] == "claude-opus-5-5"
    assert req["output_config"] == {"effort": "medium"}  # explicit: Opus 5.5 defaults to medium anyway
    assert req["fallbacks"] == "default" and req["betas"] == ["server-side-fallback-2026-07-01"]
    assert req["cache_control"] == {"type": "ephemeral"}
    assert req["max_tokens"] == 64_000
    assert req["tools"][0]["eager_input_streaming"] is True
    assert "thinking" not in req  # adaptive thinking is always on for Opus 5.5
    assert not {"temperature", "top_p", "top_k"} & set(req)
    assert "eager_input_streaming" not in TOOLS[0]  # the caller's tool list is not mutated


def test_models_without_effort_or_fallbacks():
    req = ClaudeModel("claude-haiku-4-5", client=FakeClient()).request(system="s", tools=[], messages=[])
    assert not {"output_config", "fallbacks", "betas"} & set(req)


def test_create_streams_and_returns_the_final_message():
    client = FakeClient()
    response = ClaudeModel(client=client).create(system="s", tools=TOOLS, messages=[{"role": "user", "content": "hi"}])
    assert response.content[0].text == "hi" and len(client.calls) == 1
