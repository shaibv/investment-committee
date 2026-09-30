"""A tool = a name, a description, a Pydantic model for its arguments, and a function.

The Pydantic model does double duty: its JSON Schema is what the model sees, and it
validates whatever arguments the model sends back.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ValidationError

from committee.llm.types import ToolSpec


class ToolError(Exception):
    """An error the model should see and can react to (bad input, rule violation)."""


@dataclass
class ToolResult:
    content: str
    is_error: bool = False
    # A tool can end the agent's run by returning a final value (e.g. an accepted proposal).
    final: BaseModel | None = None


@dataclass
class Tool:
    name: str
    description: str
    args_model: type[BaseModel]
    fn: Callable[[Any], Any]

    def spec(self) -> ToolSpec:
        return ToolSpec(
            name=self.name,
            description=self.description,
            input_schema=self.args_model.model_json_schema(),
        )

    def run(self, arguments: dict[str, Any]) -> ToolResult:
        try:
            args = self.args_model.model_validate(arguments)
            output = self.fn(args)
        except ValidationError as e:
            return ToolResult(f"Invalid arguments: {e}", is_error=True)
        except ToolError as e:
            return ToolResult(str(e), is_error=True)
        if isinstance(output, ToolResult):
            return output
        return ToolResult(json.dumps(output, indent=2))
