"""
Running the agent behind our own route (task 3.1, guardrails task 3.3): a Runner with an in-memory
session per request, a hard timeout, and at most three model calls per request. The live path exists
only when Vertex AI is configured (GOOGLE_CLOUD_PROJECT); HOLD_FAKE_EXTERNALS=1 never reaches here.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from datetime import date
from typing import Any

from google.adk.agents import LlmAgent
from google.adk.agents.run_config import RunConfig
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types
from pydantic import BaseModel

from api.agents.hold_agent.agent import event_agent, extract_agent, root_agent
from api.hold.schemas import EventProposal, ExtractResult

log = logging.getLogger(__name__)

APP_NAME = "hold"
# With tools and an output schema the ADK loop needs more than one model call per request (a
# thought turn, an optional tool turn, the structured final answer); one call raised
# LlmCallsLimitExceededError on the first live extraction. Three is the hard cap.
MAX_LLM_CALLS = 3
EXTRACT_TIMEOUT_S = 30.0


class ExtractionError(RuntimeError):
    """The model did not return a parseable ExtractResult."""


def is_configured() -> bool:
    return os.environ.get("HOLD_FAKE_EXTERNALS", "0") != "1" and bool(os.environ.get("GOOGLE_CLOUD_PROJECT"))


def build_runner(agent: LlmAgent = root_agent) -> Runner:
    session_service = InMemorySessionService()  # type: ignore[no-untyped-call]  # ADK ships no annotations here
    return Runner(agent=agent, app_name=APP_NAME, session_service=session_service)


async def extract(text: str, image: bytes | None = None, mime_type: str = "image/png", timeout_s: float = EXTRACT_TIMEOUT_S) -> ExtractResult:
    """One request, one session, at most MAX_LLM_CALLS model calls, one ExtractResult; TimeoutError after timeout_s."""
    runner = build_runner(extract_agent)  # tool-less: extraction is one structured answer
    session = await runner.session_service.create_session(app_name=APP_NAME, user_id="api", session_id=uuid.uuid4().hex)
    parts = [types.Part.from_text(text=text)]
    if image is not None:
        parts.append(types.Part.from_bytes(data=image, mime_type=mime_type))
    message = types.Content(role="user", parts=parts)
    final_text: list[str] = []

    async def run() -> None:
        async for event in runner.run_async(
            user_id="api", session_id=session.id, new_message=message, run_config=RunConfig(max_llm_calls=MAX_LLM_CALLS)
        ):
            if event.is_final_response() and event.content and event.content.parts:
                final_text.append("".join(p.text or "" for p in event.content.parts))

    await asyncio.wait_for(run(), timeout=timeout_s)
    return parse_extract_result("".join(final_text))


ASK_TIMEOUT_S = 45.0
# An answer may need a thought turn, a tool turn, a second tool turn and a final turn. Extraction
# is capped at three because it calls nothing; asking is capped higher because calling is the point.
MAX_ASK_LLM_CALLS = 6


class ToolCall(BaseModel):
    """One tool the agent chose to call, and whether the guard let it through."""

    name: str
    args: dict[str, Any]
    refused: bool = False
    detail: str = ""


class AskResult(BaseModel):
    """The agent's answer and the trajectory it took to get there.

    The trajectory is returned, not just logged. An agent that says a day is illegal is worth
    exactly as much as the reader's ability to see which rule it looked up to decide that, and
    the tools it called are the difference between an answer and an assertion.
    """

    answer: str
    tool_calls: list[ToolCall] = []
    fixture: bool = False


async def ask(question: str, schedule: dict[str, Any] | None = None, timeout_s: float = ASK_TIMEOUT_S) -> AskResult:
    """Put a question to the tool-bearing agent and report what it called on the way to answering.

    This runs `root_agent`, which until now existed and was never invoked: every route ran the
    tool-less extraction twin, so `check_legality`, `optimize_schedule` and `lookup_rule` were
    defined, tested, and unreachable in production, and the `before_tool_callback` allowlist that
    guards them had never once executed on the deployed service.
    """
    runner = build_runner(root_agent)
    session = await runner.session_service.create_session(app_name=APP_NAME, user_id="api", session_id=uuid.uuid4().hex)

    prompt = question if schedule is None else (
        f"{question}\n\nThe schedule to use, as JSON:\n{json.dumps(schedule)}"
    )
    message = types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
    final_text: list[str] = []
    calls: list[ToolCall] = []

    async def run() -> None:
        async for event in runner.run_async(
            user_id="api", session_id=session.id, new_message=message,
            run_config=RunConfig(max_llm_calls=MAX_ASK_LLM_CALLS),
        ):
            for call in event.get_function_calls():
                calls.append(ToolCall(name=call.name or "?", args=dict(call.args or {})))
            for response in event.get_function_responses():
                # The guard refuses by returning an error object rather than raising, so a refusal
                # arrives here as a normal response and would otherwise look like a successful call.
                body = response.response if isinstance(response.response, dict) else {}
                result = body.get("result", body)
                if isinstance(result, dict) and "error" in result:
                    for recorded in reversed(calls):
                        if recorded.name == response.name and not recorded.refused:
                            recorded.refused = True
                            recorded.detail = str(result.get("error", ""))[:200]
                            break
            if event.is_final_response() and event.content and event.content.parts:
                final_text.append("".join(p.text or "" for p in event.content.parts))

    await asyncio.wait_for(run(), timeout=timeout_s)
    answer = "".join(final_text).strip()
    if not answer:
        raise ExtractionError("the agent returned no final text")
    return AskResult(answer=answer, tool_calls=calls)


def parse_extract_result(text_out: str) -> ExtractResult:
    """The model's final text as an ExtractResult. The error names the failing fields only; the
    text itself (which may be a private document echoed back) stays in the log."""
    text_out = text_out.strip()
    if not text_out:
        raise ExtractionError("the model returned no final text")
    try:
        return ExtractResult.model_validate_json(text_out)
    except ValueError as exc:
        fields = sorted({".".join(str(p) for p in e.get("loc", ())) or "<root>" for e in getattr(exc, "errors", lambda: [])()}) or ["<json>"]
        log.warning("extraction: final text is not an ExtractResult (%s)", exc)
        raise ExtractionError(f"the model's final text is not an ExtractResult (fields: {', '.join(fields)})") from exc


EVENT_TIMEOUT_S = 35.0
# One structured answer over a short sentence, with no tools. Two calls, not three: the
# extraction cap allows a thought turn over a long document, and this input is one line.
MAX_EVENT_LLM_CALLS = 2
# The sentence is short and the timeout is not, because the first call of a process pays for the
# client as well as the answer: at 20 s the very first live run timed out and every later one
# returned in a few seconds. A cap tuned on a warm client is a cap that only fails in production.


def _event_context(schedule: dict[str, Any]) -> str:
    """The ids the sentence is allowed to name, each beside the words a person would use for it.

    The model is given the ids rather than asked to invent them, which is the whole reason the
    proposal can be checked: `apply_set_event` refuses an id that does not exist, so a hallucinated
    cast member fails loudly at the boundary instead of quietly rescheduling the wrong performer.

    What travels with each id is the handle a sentence actually uses. Cast are letters on this
    board, so "B is out" has to reach `cB`. Scenes are said by number or by set, so "the orchard
    scene" has to reach `s1`. Days are said by weekday, so the weekday is spelled out beside the
    0-based index the payload wants. Nothing else goes over the wire: no page counts, no day rates,
    no contract terms, because none of them can help decide which of three events this is.
    """
    cast = ", ".join(f"{c.get('id')} (letter {c.get('letter', '?')})" for c in schedule.get("cast", []))
    scenes = ", ".join(
        f"{s.get('id')} (scene {s.get('number', '?')}, {s.get('int_ext', '')} {s.get('set', '')})".strip()
        for s in schedule.get("scenes", [])
    )
    days = ", ".join(
        f"day_index {i} = {d.get('date')} ({_weekday(str(d.get('date', '')))})"
        for i, d in enumerate(schedule.get("days", []))
    )
    return f"Cast: {cast}\nScenes: {scenes}\nDays: {days}"


def _weekday(iso_date: str) -> str:
    """The weekday name for an ISO date, or an empty label when the date is unreadable. A sentence
    says Thursday and a payload wants an index, and this is the only bridge between them."""
    try:
        return date.fromisoformat(iso_date[:10]).strftime("%A")
    except ValueError:
        return "unknown day"


async def interpret_event(
    sentence: str, schedule: dict[str, Any], timeout_s: float = EVENT_TIMEOUT_S
) -> EventProposal:
    """One sentence about what happened on set, one typed proposal, no tools and no action.

    Nothing is applied here. The proposal goes back to the person who wrote the sentence, who
    confirms it before the deterministic `apply_set_event` path touches the plan. That split is
    deliberate: interpreting English is the model's job and deciding what a change costs is the
    solver's, and putting a model on the second half would make the number unprovable.
    """
    runner = build_runner(event_agent)
    session = await runner.session_service.create_session(
        app_name=APP_NAME, user_id="api", session_id=uuid.uuid4().hex
    )
    prompt = f"{_event_context(schedule)}\n\nWhat happened: {sentence}"
    message = types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
    final_text: list[str] = []

    async def run() -> None:
        async for event in runner.run_async(
            user_id="api", session_id=session.id, new_message=message,
            run_config=RunConfig(max_llm_calls=MAX_EVENT_LLM_CALLS),
        ):
            if event.is_final_response() and event.content and event.content.parts:
                final_text.append("".join(p.text or "" for p in event.content.parts))

    await asyncio.wait_for(run(), timeout=timeout_s)
    return parse_event_proposal("".join(final_text))


def parse_event_proposal(text_out: str) -> EventProposal:
    """The model's final text as an EventProposal, with the same field-naming discipline as
    extraction: the error says which fields failed and the text itself stays in the log."""
    text_out = text_out.strip()
    if not text_out:
        raise ExtractionError("the model returned no final text")
    try:
        return EventProposal.model_validate_json(text_out)
    except ValueError as exc:
        fields = sorted({".".join(str(p) for p in e.get("loc", ())) or "<root>" for e in getattr(exc, "errors", lambda: [])()}) or ["<json>"]
        log.warning("event: final text is not an EventProposal (%s)", exc)
        raise ExtractionError(f"the model's final text is not an EventProposal (fields: {', '.join(fields)})") from exc
