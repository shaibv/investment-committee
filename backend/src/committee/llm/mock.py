"""A deterministic stand-in for a real LLM (ADR 0002).

It speaks the exact same protocol as a real provider (reads messages, emits tool calls),
so the agent loop, tools, validation and UI can all be built and tested with no API keys.
Its "reasoning" is a fixed strategy: rank by Sharpe, weight by inverse volatility.
"""

import json
import math
import re
from typing import Any

from committee.llm.types import Message, ModelResponse, ToolCall, ToolSpec, Usage

CONTEXT_BLOCK = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _cap_weights(raw: dict[str, float], cap: float) -> dict[str, float]:
    """Normalize to 1, then clip anything above `cap` and spread the excess over the rest."""
    weights = {t: w / sum(raw.values()) for t, w in raw.items()}
    for _ in range(len(weights)):
        over = {t for t, w in weights.items() if w > cap}
        if not over:
            break
        excess = sum(weights[t] - cap for t in over)
        under = {t: w for t, w in weights.items() if t not in over and w < cap}
        for t in over:
            weights[t] = cap
        under_total = sum(under.values())
        for t, w in under.items():
            weights[t] = w + excess * w / under_total
    return {t: round(w, 4) for t, w in weights.items()}


class MockProvider:
    name = "mock"

    def __init__(self) -> None:
        self._call_counter = 0

    def complete(self, messages: list[Message], tools: list[ToolSpec]) -> ModelResponse:
        context = self._context(messages)
        called = self._tool_outputs(messages)

        if "get_price_stats" not in called:
            reply = self._tool_reply(
                "Let me look at the trailing-year statistics for every candidate.",
                "get_price_stats",
                {"tickers": context["candidates"]},
            )
        elif "analyze_portfolio" not in called:
            weights = self._draft_weights(called["get_price_stats"], context["profile"])
            reply = self._tool_reply(
                f"I'll pick the {len(weights)} best risk-adjusted names and weight them by "
                "inverse volatility. Checking the draft before submitting.",
                "analyze_portfolio",
                {"weights": weights},
            )
        elif "submit_allocation" not in called:
            stats = called["get_price_stats"]["stats"]
            draft = self._last_call_args(messages, "analyze_portfolio")["weights"]
            analysis = called["analyze_portfolio"]
            reply = self._tool_reply(
                "The draft looks balanced. Submitting.",
                "submit_allocation",
                {
                    "positions": [
                        {
                            "ticker": t,
                            "weight": w,
                            "rationale": (
                                f"Sharpe {stats[t]['sharpe']}, volatility "
                                f"{stats[t]['annual_volatility']:.0%}; sized inversely to risk."
                            ),
                        }
                        for t, w in draft.items()
                    ],
                    "summary": (
                        f"Risk-parity-style basket of {len(draft)} stocks. Backtested "
                        f"annual return {analysis['annual_return']:.1%}, volatility "
                        f"{analysis['annual_volatility']:.1%}, max drawdown "
                        f"{analysis['max_drawdown']:.1%}."
                    ),
                },
            )
        else:
            reply = Message(role="assistant", content="I have nothing further to add.")

        prompt_text = "".join(m.content for m in messages)
        return ModelResponse(
            message=reply,
            usage=Usage(
                input_tokens=_estimate_tokens(prompt_text),
                output_tokens=_estimate_tokens(reply.model_dump_json()),
            ),
            stop_reason="tool_use" if reply.tool_calls else "end_turn",
        )

    # --- helpers -------------------------------------------------------------------------

    def _context(self, messages: list[Message]) -> dict[str, Any]:
        task = next(m.content for m in messages if m.role == "user")
        match = CONTEXT_BLOCK.search(task)
        if not match:
            raise ValueError("Mock provider expects a ```json context block in the task.")
        return dict(json.loads(match.group(1)))

    def _tool_outputs(self, messages: list[Message]) -> dict[str, Any]:
        """Latest successful output of each tool, keyed by tool name."""
        names = {c.id: c.name for m in messages for c in m.tool_calls}
        outputs: dict[str, Any] = {}
        for m in messages:
            if m.role == "tool" and not m.is_error and m.tool_call_id in names:
                outputs[names[m.tool_call_id]] = json.loads(m.content)
        return outputs

    def _last_call_args(self, messages: list[Message], tool: str) -> dict[str, Any]:
        calls = [c for m in messages for c in m.tool_calls if c.name == tool]
        return calls[-1].arguments

    def _draft_weights(
        self, price_stats: dict[str, Any], profile: dict[str, Any]
    ) -> dict[str, float]:
        stats: dict[str, dict[str, float]] = price_stats["stats"]
        excluded = {t.upper() for t in profile["excluded_tickers"]}
        ranked = sorted(
            (t for t in stats if t not in excluded),
            key=lambda t: stats[t]["sharpe"],
            reverse=True,
        )
        cap = profile["max_weight"]
        count = max(profile["min_holdings"], math.ceil(1 / cap))
        count = min(count, profile["max_holdings"], len(ranked))
        chosen = ranked[:count]
        return _cap_weights({t: 1 / stats[t]["annual_volatility"] for t in chosen}, cap)

    def _tool_reply(self, text: str, tool: str, arguments: dict[str, Any]) -> Message:
        self._call_counter += 1
        return Message(
            role="assistant",
            content=text,
            tool_calls=[ToolCall(id=f"mock_{self._call_counter}", name=tool, arguments=arguments)],
        )
