"""OpenAI adapter, using the official SDK's Responses API.

Translation between our neutral types and OpenAI's:

    system message         -> `instructions`
    user message           -> {"role": "user", "content": ...}
    assistant message      -> its raw output items, replayed (message, reasoning, function_call)
    tool message           -> {"type": "function_call_output", "call_id": ..., "output": ...}
    ToolSpec               -> {"type": "function", "name", "description", "parameters"}
"""

import json
from typing import Any

from openai import OpenAI

from committee.llm.types import Message, ModelResponse, ToolCall, ToolSpec, Usage

MAX_OUTPUT_TOKENS = 4_000


class OpenAIProvider:
    name = "openai"

    def __init__(self, api_key: str, model: str, client: Any = None) -> None:
        self.model = model
        self.name = f"openai:{model}"
        # `client` is injectable so tests can pass a fake and never hit the network.
        # Typed as Any: we build request dicts ourselves rather than the SDK's TypedDicts.
        self._client: Any = client or OpenAI(api_key=api_key, max_retries=3, timeout=120)

    def complete(self, messages: list[Message], tools: list[ToolSpec]) -> ModelResponse:
        instructions = "\n\n".join(m.content for m in messages if m.role == "system")
        response = self._client.responses.create(
            model=self.model,
            instructions=instructions or None,
            input=to_openai_input(messages),
            tools=[to_openai_tool(t) for t in tools],
            max_output_tokens=MAX_OUTPUT_TOKENS,
        )
        return from_openai_response(response)


def to_openai_tool(tool: ToolSpec) -> dict[str, Any]:
    return {
        "type": "function",
        "name": tool.name,
        "description": tool.description,
        "parameters": tool.input_schema,
        "strict": False,  # our Pydantic schemas use optional fields/$defs that strict mode rejects
    }


def to_openai_input(messages: list[Message]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for m in messages:
        match m.role:
            case "system":
                continue  # sent as `instructions`
            case "user":
                items.append({"role": "user", "content": m.content})
            case "assistant" if m.provider == "openai" and m.raw:
                items.extend(m.raw)
            case "assistant":
                # Came from another provider (e.g. in a mixed-model debate): rebuild it.
                if m.content:
                    items.append({"role": "assistant", "content": m.content})
                items.extend(
                    {
                        "type": "function_call",
                        "call_id": c.id,
                        "name": c.name,
                        "arguments": json.dumps(c.arguments),
                    }
                    for c in m.tool_calls
                )
            case "tool":
                output = f"ERROR: {m.content}" if m.is_error else m.content
                items.append(
                    {"type": "function_call_output", "call_id": m.tool_call_id, "output": output}
                )
    return items


def from_openai_response(response: Any) -> ModelResponse:
    text_parts: list[str] = []
    tool_calls: list[ToolCall] = []
    for item in response.output:
        if item.type == "message":
            text_parts.extend(c.text for c in item.content if c.type == "output_text")
        elif item.type == "function_call":
            try:
                arguments = json.loads(item.arguments or "{}")
            except json.JSONDecodeError:
                # Malformed JSON from the model: pass it through so the tool layer rejects it
                # and the model sees the error, instead of crashing the run.
                arguments = {"_unparseable_arguments": item.arguments}
            tool_calls.append(ToolCall(id=item.call_id, name=item.name, arguments=arguments))

    if tool_calls:
        stop_reason = "tool_use"
    elif response.status == "incomplete":
        stop_reason = "max_tokens"
    else:
        stop_reason = "end_turn"

    return ModelResponse(
        message=Message(
            role="assistant",
            content="\n".join(text_parts),
            tool_calls=tool_calls,
            provider="openai",
            raw=[item.model_dump(exclude_none=True) for item in response.output],
        ),
        usage=Usage(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        ),
        stop_reason=stop_reason,
    )
