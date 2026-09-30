"""Events emitted while an agent runs (ADR 0004).

Phase 1 prints them to the terminal; later phases store them and stream them to the UI.
"""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

EventType = Literal[
    "agent_started",
    "model_response",
    "tool_call",
    "tool_result",
    "agent_nudged",
    "agent_submitted",
    "agent_failed",
]


class Event(BaseModel):
    type: EventType
    agent: str
    data: dict[str, Any] = Field(default_factory=dict)
    at: datetime = Field(default_factory=lambda: datetime.now(UTC))


EventHandler = Callable[[Event], None]
