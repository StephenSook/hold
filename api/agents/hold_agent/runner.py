"""
Running the agent behind our own route (task 3.1, guardrails task 3.3): a Runner with an in-memory
session per request, a hard timeout, and at most one model call per request. The live path exists
only when Vertex AI is configured (GOOGLE_CLOUD_PROJECT); HOLD_FAKE_EXTERNALS=1 never reaches here.
"""
from __future__ import annotations

import asyncio
import os
import uuid

from google.adk.agents.run_config import RunConfig
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types

from api.agents.hold_agent.agent import root_agent
from api.hold.schemas import ExtractResult

APP_NAME = "hold"
MAX_LLM_CALLS = 1
EXTRACT_TIMEOUT_S = 30.0


class ExtractionError(RuntimeError):
    """The model did not return a parseable ExtractResult."""


def is_configured() -> bool:
    return os.environ.get("HOLD_FAKE_EXTERNALS", "0") != "1" and bool(os.environ.get("GOOGLE_CLOUD_PROJECT"))


def build_runner() -> Runner:
    session_service = InMemorySessionService()  # type: ignore[no-untyped-call]  # ADK ships no annotations here
    return Runner(agent=root_agent, app_name=APP_NAME, session_service=session_service)


async def extract(text: str, image: bytes | None = None, mime_type: str = "image/png", timeout_s: float = EXTRACT_TIMEOUT_S) -> ExtractResult:
    """One request, one session, one model call, one ExtractResult; TimeoutError after timeout_s."""
    runner = build_runner()
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
    text_out = "".join(final_text).strip()
    if not text_out:
        raise ExtractionError("the model returned no final text")
    try:
        return ExtractResult.model_validate_json(text_out)
    except ValueError as exc:
        raise ExtractionError(f"the model's final text is not an ExtractResult: {exc}") from exc
