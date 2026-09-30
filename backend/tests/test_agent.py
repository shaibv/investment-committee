from collections.abc import Iterator

import pytest

from committee.agent import Agent, AgentError
from committee.domain import AllocationProposal, InvestorProfile
from committee.events import Event
from committee.llm.mock import MockProvider
from committee.llm.types import Message, ModelResponse, ToolCall, ToolSpec, Usage
from committee.market.data import SyntheticMarketData
from committee.portfolio.validation import validate_proposal
from committee.prompts import build_task
from committee.tools.portfolio_tools import build_tools

CANDIDATES = ["AAA", "BBB", "CCC", "DDD", "EEE", "FFF", "GGG", "HHH", "III", "JJJ", "MISSING"]
PROFILE = InvestorProfile(min_holdings=8, max_holdings=10, max_weight=0.15)


def make_agent(provider: object, events: list[Event] | None = None) -> Agent:
    market = SyntheticMarketData(unknown={"MISSING"})
    tools = build_tools(market, PROFILE, CANDIDATES)
    on_event = events.append if events is not None else None
    return Agent("test", "sys", provider, tools, on_event=on_event)  # type: ignore[arg-type]


def test_mock_agent_end_to_end_produces_a_valid_proposal() -> None:
    events: list[Event] = []
    result = make_agent(MockProvider(), events).run(build_task(PROFILE, CANDIDATES))

    assert isinstance(result.final, AllocationProposal)
    known = set(CANDIDATES) - {"MISSING"}
    assert validate_proposal(result.final, PROFILE, known) == []
    tools_called = [e.data["tool"] for e in events if e.type == "tool_call"]
    assert tools_called == ["get_price_stats", "analyze_portfolio", "submit_allocation"]
    assert result.usage.input_tokens > 0


class ScriptedProvider:
    """Replays canned replies, so we can test how the loop handles misbehaving models."""

    name = "scripted"

    def __init__(self, replies: list[Message]) -> None:
        self._replies: Iterator[Message] = iter(replies)

    def complete(self, messages: list[Message], tools: list[ToolSpec]) -> ModelResponse:
        reply = next(self._replies)
        return ModelResponse(message=reply, usage=Usage(), stop_reason="end_turn")


def submit(weights: dict[str, float], call_id: str) -> Message:
    positions = [{"ticker": t, "weight": w, "rationale": "r"} for t, w in weights.items()]
    return Message(
        role="assistant",
        tool_calls=[
            ToolCall(
                id=call_id,
                name="submit_allocation",
                arguments={"positions": positions, "summary": "s"},
            )
        ],
    )


def test_rejected_submission_is_fed_back_and_agent_can_fix_it() -> None:
    bad = {"AAA": 0.5, "BBB": 0.5}  # too few holdings, weights over the cap
    good = {t: 0.125 for t in CANDIDATES[:8]}
    events: list[Event] = []
    agent = make_agent(ScriptedProvider([submit(bad, "1"), submit(good, "2")]), events)

    result = agent.run("task")

    assert result.turns == 2
    rejection = next(e for e in events if e.type == "tool_result" and e.data["is_error"])
    assert "must be between 8 and 10" in rejection.data["content"]


def test_prose_answer_gets_one_nudge_then_fails() -> None:
    prose = Message(role="assistant", content="I think you should buy AAA.")
    agent = make_agent(ScriptedProvider([prose, prose]))
    with pytest.raises(AgentError):
        agent.run("task")
