"""OpenAI adapter tests against a fake client: no network, no key, no cost."""

import json
from types import SimpleNamespace as NS
from typing import Any

from committee.llm.openai_provider import OpenAIProvider, to_openai_input
from committee.llm.types import Message, ToolCall, ToolSpec


class FakeResponse(NS):
    pass


def item(**fields: Any) -> NS:
    """Mimics an SDK output item: attribute access plus model_dump()."""
    obj = NS(**fields)
    obj.model_dump = lambda exclude_none=True: {k: v for k, v in fields.items() if not callable(v)}
    return obj


class FakeClient:
    def __init__(self, response: NS) -> None:
        self.calls: list[dict[str, Any]] = []
        self.responses = NS(create=self._create)
        self._response = response

    def _create(self, **kwargs: Any) -> NS:
        self.calls.append(kwargs)
        return self._response


def test_complete_translates_request_and_function_call_response() -> None:
    response = FakeResponse(
        status="completed",
        usage=NS(input_tokens=120, output_tokens=30),
        output=[
            item(type="reasoning", id="rs_1", summary=[]),
            item(type="message", content=[NS(type="output_text", text="Checking prices.")]),
            item(
                type="function_call",
                call_id="call_1",
                name="get_price_stats",
                arguments='{"tickers": ["AAPL"]}',
            ),
        ],
    )
    client = FakeClient(response)
    provider = OpenAIProvider("sk-test", "gpt-6-luna", client=client)
    tool = ToolSpec(name="get_price_stats", description="d", input_schema={"type": "object"})

    result = provider.complete(
        [Message(role="system", content="be careful"), Message(role="user", content="go")], [tool]
    )

    sent = client.calls[0]
    assert sent["instructions"] == "be careful"
    assert sent["input"] == [{"role": "user", "content": "go"}]
    assert sent["tools"][0]["name"] == "get_price_stats"
    assert result.stop_reason == "tool_use"
    assert result.message.content == "Checking prices."
    assert result.message.tool_calls == [
        ToolCall(id="call_1", name="get_price_stats", arguments={"tickers": ["AAPL"]})
    ]
    assert result.usage.input_tokens == 120
    assert [r["type"] for r in result.message.raw] == ["reasoning", "message", "function_call"]


def test_openai_turns_replay_raw_items_and_other_providers_are_rebuilt() -> None:
    own = Message(role="assistant", provider="openai", raw=[{"type": "reasoning", "id": "rs_1"}])
    foreign = Message(
        role="assistant",
        content="from claude",
        provider="anthropic",
        tool_calls=[ToolCall(id="t1", name="x", arguments={"a": 1})],
    )
    failed = Message(role="tool", tool_call_id="t1", content="bad input", is_error=True)

    items = to_openai_input([own, foreign, failed])

    assert items[0] == {"type": "reasoning", "id": "rs_1"}
    assert items[1] == {"role": "assistant", "content": "from claude"}
    assert items[2] == {
        "type": "function_call",
        "call_id": "t1",
        "name": "x",
        "arguments": json.dumps({"a": 1}),
    }
    assert items[3] == {
        "type": "function_call_output",
        "call_id": "t1",
        "output": "ERROR: bad input",
    }


def test_malformed_arguments_do_not_crash() -> None:
    response = FakeResponse(
        status="completed",
        usage=NS(input_tokens=1, output_tokens=1),
        output=[item(type="function_call", call_id="c", name="t", arguments="{not json")],
    )
    provider = OpenAIProvider("sk-test", "m", client=FakeClient(response))
    result = provider.complete([Message(role="user", content="go")], [])
    assert result.message.tool_calls[0].arguments == {"_unparseable_arguments": "{not json"}
