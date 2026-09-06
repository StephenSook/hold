"""
POST /api/interpret-event: one sentence about what happened on set, one typed event to confirm.

This is the second agent surface, and it is deliberately not a second question answerer. The panel
below the board already has three buttons that publish a typed event; what it did not have was a
way to say "we lost the barn on Thursday" and get to the same place. Interpreting that sentence is
a judgement, so a model does it. Deciding what the change costs is arithmetic over a rule set, so
the solver does it, through the same `apply_set_event` path the buttons use.

Nothing is applied here. The route returns a proposal and a plain-English reading of it; a person
presses publish. Under HOLD_FAKE_EXTERNALS=1 a fixture proposal is returned and says so in its
reading, and when Vertex AI is unconfigured the route refuses with 503 rather than guessing.
"""
from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.agents.hold_agent.runner import EVENT_TIMEOUT_S, ExtractionError, is_configured
from api.agents.hold_agent.runner import interpret_event as run_interpret
from api.hold.schemas import EventProposal, EventProposalOut

router = APIRouter()
log = logging.getLogger(__name__)

# One sentence about one change. A paste of a whole call sheet belongs at /api/extract, and is
# refused here before it costs a model call rather than after.
MAX_SENTENCE_CHARS = 400


class InterpretRequest(BaseModel):
    sentence: str = Field(min_length=1, max_length=MAX_SENTENCE_CHARS)
    #: The board this sentence is about. Its ids are the only ones the proposal may name.
    schedule: dict[str, Any]


_FIXTURE = EventProposal(
    status="ok",
    kind="actor_late",
    cast_id="cC",
    day_index=3,
    reading="Cast member C cannot work on day 4, Thursday 8 October.",
)


@router.post("/api/interpret-event")
async def interpret_event(request: InterpretRequest) -> EventProposalOut:
    if os.environ.get("HOLD_FAKE_EXTERNALS", "0") == "1":
        return EventProposalOut.of(
            _FIXTURE.model_copy(
                update={"reading": f"fixture: HOLD_FAKE_EXTERNALS=1, no model was called. {_FIXTURE.reading}"}
            )
        )
    if not is_configured():
        raise HTTPException(
            status_code=503,
            detail="the agent is not configured: GOOGLE_CLOUD_PROJECT is unset (PLAN.md task 0.1); this route runs the task 3.1 agent and needs Vertex AI credentials",
        )
    try:
        return EventProposalOut.of(await run_interpret(request.sentence, request.schedule, timeout_s=EVENT_TIMEOUT_S))
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail=f"the agent exceeded {EVENT_TIMEOUT_S:.0f} s") from exc
    except ExtractionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # the caller sees the failure class, never a blank 500
        log.exception("interpret-event failed")
        code = getattr(exc, "code", None)
        where = f" (upstream status {code})" if isinstance(code, int) else ""
        raise HTTPException(status_code=502, detail=f"the agent failed: {type(exc).__name__}{where}; details are in the service log") from exc
