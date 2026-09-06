"""
POST /api/ask: put a question to the tool-bearing agent.

This is the route `root_agent` was written for and never got. Every other path ran the tool-less
extraction twin, so the three tools and the allowlist that guards them were defined, tested and
unreachable on the deployed service. Asking is what makes them run.

Under HOLD_FAKE_EXTERNALS=1 a fixture answer is returned and says so in the payload, the same way
extraction does, so the golden path and the e2e suite need no key. When Vertex AI is not
configured the route refuses with 503 rather than pretending to have asked anything.
"""
from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.agents.hold_agent.runner import (
    ASK_TIMEOUT_S,
    AskResult,
    ExtractionError,
    ToolCall,
    is_configured,
)
from api.agents.hold_agent.runner import ask as run_ask

router = APIRouter()
log = logging.getLogger(__name__)

# Long enough for a real question, short enough that a paste of a whole script is refused here
# rather than spending a model call to find out.
MAX_QUESTION_CHARS = 2000


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=MAX_QUESTION_CHARS)
    # Optional: a question about a specific board rather than about the rules in general.
    schedule: dict[str, Any] | None = None


_FIXTURE = AskResult(
    answer=(
        "Day 4 cannot be shot as arranged. The minor is called at 07:00 and wrapped at 21:30, "
        "which is 14 hours 30 minutes at the location, and Georgia caps a minor's presence at 10 "
        "hours. Ga. Comp. R. & Regs. 300-7-1-.03(2)(d) also forbids a work day starting before "
        "5:00 A.M., which this one does not breach."
    ),
    tool_calls=[
        ToolCall(name="check_legality", args={"day_index": 3}),
        ToolCall(name="lookup_rule", args={"rule_id": "GA_300_7_1_03_earliest_call"}),
    ],
    fixture=True,
)


@router.post("/api/ask")
async def ask(request: AskRequest) -> AskResult:
    if os.environ.get("HOLD_FAKE_EXTERNALS", "0") == "1":
        return _FIXTURE
    if not is_configured():
        raise HTTPException(
            status_code=503,
            detail="the agent is not configured: GOOGLE_CLOUD_PROJECT is unset (PLAN.md task 0.1); this route runs the task 3.1 agent and needs Vertex AI credentials",
        )
    try:
        return await run_ask(request.question, request.schedule, timeout_s=ASK_TIMEOUT_S)
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail=f"the agent exceeded {ASK_TIMEOUT_S:.0f} s") from exc
    except ExtractionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # the caller sees the failure class, never a blank 500
        log.exception("ask failed")
        code = getattr(exc, "code", None)
        where = f" (upstream status {code})" if isinstance(code, int) else ""
        raise HTTPException(status_code=502, detail=f"the agent failed: {type(exc).__name__}{where}; details are in the service log") from exc
