"""
Guardrails (task 3.3): before any tool runs, the call must name one of the three allowed tools
and its arguments must validate against the tool's Pydantic model. A refusal is returned as the
tool's response, naming the field, so the model can correct itself; nothing else executes.
"""
from __future__ import annotations

from typing import Any

from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from pydantic import BaseModel, Field, ValidationError

from api.hold.schemas import ScheduleInput


class CheckLegalityArgs(BaseModel):
    schedule: ScheduleInput
    day_index: int = Field(ge=0)


class OptimizeScheduleArgs(BaseModel):
    schedule: ScheduleInput


class LookupRuleArgs(BaseModel):
    rule_id: str = Field(min_length=1)


ALLOWED_TOOLS: dict[str, type[BaseModel]] = {
    "check_legality": CheckLegalityArgs,
    "optimize_schedule": OptimizeScheduleArgs,
    "lookup_rule": LookupRuleArgs,
}


def guard_tool_call(tool: BaseTool, args: dict[str, Any], tool_context: ToolContext) -> dict[str, Any] | None:
    """None lets the call through; a dict is returned to the model instead of running the tool."""
    model = ALLOWED_TOOLS.get(tool.name)
    if model is None:
        return {"error": f"tool {tool.name!r} is not allowed", "allowed": sorted(ALLOWED_TOOLS)}
    try:
        model.model_validate(args)
    except ValidationError as exc:
        first = exc.errors()[0]
        return {"error": "invalid argument", "field": ".".join(str(p) for p in first["loc"]) or "<root>", "detail": first["msg"]}
    return None
