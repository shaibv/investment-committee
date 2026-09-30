"""The agent loop, written by hand (no framework).

send messages + tool specs to the model
-> model replies with text and/or tool calls
-> run each tool, append results as messages
-> repeat until a tool returns a final value, or we run out of turns
"""

from dataclasses import dataclass, field

from pydantic import BaseModel

from committee.events import Event, EventHandler, EventType
from committee.llm.types import Message, ModelProvider, Usage
from committee.tools.base import Tool, ToolResult

NUDGE = (
    "You replied without calling a tool. You must finish by calling submit_allocation "
    "with your final allocation."
)


class AgentError(Exception):
    pass


@dataclass
class AgentResult:
    final: BaseModel
    turns: int
    usage: Usage
    transcript: list[Message] = field(default_factory=list)


class Agent:
    def __init__(
        self,
        name: str,
        system_prompt: str,
        provider: ModelProvider,
        tools: list[Tool],
        max_turns: int = 10,
        on_event: EventHandler | None = None,
    ) -> None:
        self.name = name
        self.system_prompt = system_prompt
        self.provider = provider
        self.tools = {t.name: t for t in tools}
        self.max_turns = max_turns
        self.on_event = on_event

    def _emit(self, type_: EventType, **data: object) -> None:
        if self.on_event:
            self.on_event(Event(type=type_, agent=self.name, data=data))

    def _run_tool(self, name: str, arguments: dict[str, object]) -> ToolResult:
        tool = self.tools.get(name)
        if tool is None:
            return ToolResult(f"Unknown tool '{name}'.", is_error=True)
        return tool.run(arguments)

    def run(self, task: str) -> AgentResult:
        messages = [
            Message(role="system", content=self.system_prompt),
            Message(role="user", content=task),
        ]
        specs = [t.spec() for t in self.tools.values()]
        usage = Usage()
        nudged = False
        self._emit("agent_started", provider=self.provider.name, task=task)

        for turn in range(1, self.max_turns + 1):
            response = self.provider.complete(messages, specs)
            usage += response.usage
            reply = response.message
            messages.append(reply)
            self._emit(
                "model_response",
                turn=turn,
                text=reply.content,
                tool_calls=len(reply.tool_calls),
                usage=response.usage.model_dump(),
            )

            if not reply.tool_calls:
                # Models sometimes "answer in prose" instead of calling the tool. One nudge.
                if nudged:
                    break
                nudged = True
                messages.append(Message(role="user", content=NUDGE))
                self._emit("agent_nudged", turn=turn)
                continue

            for call in reply.tool_calls:
                self._emit("tool_call", turn=turn, tool=call.name, arguments=call.arguments)
                result = self._run_tool(call.name, call.arguments)
                self._emit(
                    "tool_result",
                    turn=turn,
                    tool=call.name,
                    is_error=result.is_error,
                    content=result.content,
                )
                messages.append(
                    Message(
                        role="tool",
                        content=result.content,
                        tool_call_id=call.id,
                        is_error=result.is_error,
                    )
                )
                if result.final is not None:
                    self._emit("agent_submitted", turn=turn, usage=usage.model_dump())
                    return AgentResult(result.final, turn, usage, messages)

        self._emit("agent_failed", reason="no accepted submission", turns=self.max_turns)
        raise AgentError(f"{self.name} did not submit an accepted result.")
