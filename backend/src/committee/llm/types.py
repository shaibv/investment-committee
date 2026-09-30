"""Provider-neutral chat types.

Every model adapter (mock, Anthropic, OpenAI, Gemini, Ollama) translates to and from
these types, so the agent loop never depends on a specific vendor SDK.
"""

from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field

Role = Literal["system", "user", "assistant", "tool"]
StopReason = Literal["end_turn", "tool_use", "max_tokens"]


class ToolSpec(BaseModel):
    """What the model sees about a tool: name, purpose, and a JSON Schema for its input."""

    name: str
    description: str
    input_schema: dict[str, Any]


class ToolCall(BaseModel):
    id: str
    name: str
    arguments: dict[str, Any]


class Message(BaseModel):
    role: Role
    content: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
    # Set only on role="tool" messages: which call this is the result of.
    tool_call_id: str | None = None
    is_error: bool = False
    # The provider's own output items (e.g. OpenAI reasoning items), replayed verbatim on the
    # next turn by that same provider. Other providers ignore it. A deliberate leak in the
    # abstraction: some state only makes sense to the vendor that produced it.
    provider: str | None = None
    raw: list[dict[str, Any]] = Field(default_factory=list)


class Usage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0

    def __add__(self, other: "Usage") -> "Usage":
        return Usage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
        )


class ModelResponse(BaseModel):
    message: Message
    usage: Usage
    stop_reason: StopReason


class ModelProvider(Protocol):
    """The one interface every model backend implements."""

    name: str

    def complete(self, messages: list[Message], tools: list[ToolSpec]) -> ModelResponse: ...
