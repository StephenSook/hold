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


# One request gets this many tool calls in total. Live diagnosis (2026-09-03): the model retried
# check_legality with an empty schedule against the same refusal until the ADK call ceiling; a
# refusal alone does not end a loop, a budget does.
MAX_TOOL_CALLS_PER_REQUEST = 4
_BUDGET_KEY = "temp:hold_tool_calls"  # temp: state is scoped to the invocation


def _spend(tool_context: ToolContext | None) -> int:
    """Count this call against the request's budget; returns the count after this call."""
    state = getattr(tool_context, "state", None)
    if state is None:
        return 1
    count = int(state.get(_BUDGET_KEY, 0)) + 1
    state[_BUDGET_KEY] = count
    return count


def guard_tool_call(tool: BaseTool, args: dict[str, Any], tool_context: ToolContext) -> dict[str, Any] | None:
    """None lets the call through; a dict is returned to the model instead of running the tool.
    Past the per-request budget every call is answered with a terminal instruction."""
    if _spend(tool_context) > MAX_TOOL_CALLS_PER_REQUEST:
        return {
            "error": f"no more tool calls: this request used its budget of {MAX_TOOL_CALLS_PER_REQUEST}",
            "stop": True,
            "instruction": "Answer the user now without tools. If the document does not state what you need, return status needs_clarification with the questions.",
        }
    model = ALLOWED_TOOLS.get(tool.name)
    if model is None:
        return {"error": f"tool {tool.name!r} is not allowed", "allowed": sorted(ALLOWED_TOOLS)}
    try:
        model.model_validate(args)
    except ValidationError as exc:
        first = exc.errors()[0]
        return {"error": "invalid argument", "field": ".".join(str(p) for p in first["loc"]) or "<root>", "detail": first["msg"]}
    return None
