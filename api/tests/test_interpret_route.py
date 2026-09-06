"""
The event interpreter: a sentence in, a typed event out, and a person between it and the plan.

The tests that matter here are the two ends. At the model end, a proposal that is not an
EventProposal is refused by name rather than half-parsed. At the engine end, a proposal the model
could actually emit is fed to the deterministic `apply_set_event` path unchanged, which is the only
thing that proves the two halves fit: a schema both sides merely import is not a wire.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from hypothesis import given, settings
from hypothesis import strategies as st

from api.agents.hold_agent.runner import _event_context, parse_event_proposal
from api.hold.schemas import EventProposal, EventProposalOut, ScheduleInput, SetEvent
from api.hold.set_events import SetEventError, apply_set_event
from api.main import app

ROOT = Path(__file__).parents[2]
DEMO = ROOT / "data" / "demo" / "hold-demo.json"


def _demo() -> dict[str, Any]:
    raw = json.loads(DEMO.read_text())
    return {k: v for k, v in raw.items() if not k.startswith("_")}


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("HOLD_FAKE_EXTERNALS", "1")
    return TestClient(app)


def test_fixture_says_it_is_a_fixture(client: TestClient) -> None:
    body = client.post(
        "/api/interpret-event", json={"sentence": "C is out Thursday", "schedule": _demo()}
    ).json()
    assert body["status"] == "ok"
    assert body["kind"] == "actor_late"
    assert body["payload"] == {"cast_id": "cC", "day_index": 3}
    assert "fixture" in body["reading"], "a fixture answer that does not say so is a lie on the wire"


def test_live_mode_refuses_when_the_model_is_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOLD_FAKE_EXTERNALS", "0")
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    with TestClient(app) as live:
        answer = live.post("/api/interpret-event", json={"sentence": "x", "schedule": _demo()})
    assert answer.status_code == 503
    assert "GOOGLE_CLOUD_PROJECT" in answer.json()["detail"]


def test_a_pasted_document_is_refused_before_it_costs_a_model_call(client: TestClient) -> None:
    answer = client.post("/api/interpret-event", json={"sentence": "x" * 401, "schedule": _demo()})
    assert answer.status_code == 422


def test_the_context_names_the_ids_and_the_day_numbering(client: TestClient) -> None:
    context = _event_context(_demo())
    schedule = ScheduleInput.model_validate(_demo())
    # Every id the model is allowed to use is in front of it, and the 0-based day index is spelled
    # out beside its date, because "Thursday" is the form a sentence actually arrives in.
    for cast in schedule.cast:
        assert cast.id in context
    for scene in schedule.scenes:
        assert scene.id in context
    assert "day_index 0 = " in context
    assert f"day_index {len(schedule.days) - 1} = " in context
    # The handles a sentence actually uses: the letter, the set name, and the weekday.
    assert f"letter {schedule.cast[0].letter}" in context
    assert schedule.scenes[0].set in context
    assert "Monday" in context, "a sentence says Thursday, and only the weekday bridges to an index"
    # Nothing else travels: no page counts, no day rates, no contract terms.
    assert "pages_eighths" not in context
    assert "rate" not in context


@pytest.mark.parametrize(
    "proposal",
    [
        EventProposal(status="ok", kind="actor_late", cast_id="cC", day_index=3),
        EventProposal(status="ok", kind="weather_cover", day_index=2),
    ],
)
def test_a_proposal_is_accepted_by_the_deterministic_path(proposal: EventProposal) -> None:
    """The whole design rests on this: the model proposes, the engine acts, and the object that
    crosses between them is one the engine already refuses to misread."""
    schedule = ScheduleInput.model_validate(_demo())
    assert proposal.kind is not None
    edited, description = apply_set_event(
        schedule,
        SetEvent(kind=proposal.kind, payload=proposal.event_payload(), source="agent"),
    )
    assert description
    assert len(edited.constraints) > len(schedule.constraints)


def test_an_invented_id_is_refused_at_the_boundary() -> None:
    """A model that invents a performer does not quietly reschedule the wrong one. This is why the
    proposal is allowed to be wrong: the next step checks it, and the person before that does too."""
    schedule = ScheduleInput.model_validate(_demo())
    with pytest.raises(SetEventError, match="not in the schedule"):
        apply_set_event(
            schedule,
            SetEvent(kind="actor_late", payload={"cast_id": "ZZ", "day_index": 0}, source="agent"),
        )


def test_a_reply_that_is_not_a_proposal_names_the_failing_fields() -> None:
    with pytest.raises(Exception, match="kind"):
        parse_event_proposal('{"status": "ok", "kind": "reshoot", "payload": {}}')


def test_an_ok_proposal_missing_its_fields_becomes_the_question_it_actually_is() -> None:
    """The defect the first live run produced, pinned.

    Gemini answered "Rained out Wednesday, nothing exterior is happening" with status ok, a reading
    that correctly named day_index 2, and nothing in the payload, because the payload was a
    free-form dict and the response schema gave it nowhere to write. The fields are named now, and
    this is the backstop for the day a model still leaves one out: a proposal that cannot be
    applied is a question, never a publish button that 422s when pressed.
    """
    for text, missing in [
        ('{"status":"ok","kind":"weather_cover"}', "day_index"),
        ('{"status":"ok","kind":"actor_late","cast_id":"cC"}', "day_index"),
        ('{"status":"ok","kind":"scene_dropped"}', "scene_id"),
    ]:
        proposal = parse_event_proposal(text)
        assert proposal.status == "needs_clarification", text
        assert any(missing in q for q in proposal.questions), proposal.questions
    # And a complete one is left alone, or the backstop would swallow every real answer.
    whole = parse_event_proposal('{"status":"ok","kind":"weather_cover","day_index":2}')
    assert whole.status == "ok"
    assert whole.event_payload() == {"day_index": 2}


def test_the_browser_gets_the_payload_assembled_on_this_side() -> None:
    """One mapping from named fields to event payload, on the side that owns the engine."""
    out = EventProposalOut.of(EventProposal(status="ok", kind="actor_late", cast_id="cC", day_index=3))
    assert out.payload == {"cast_id": "cC", "day_index": 3}
    assert EventProposalOut.of(EventProposal(status="needs_clarification")).payload == {}


def test_needs_clarification_carries_questions_and_no_kind() -> None:
    proposal = parse_event_proposal(
        '{"status": "needs_clarification", "questions": ["Which day is Thursday?"], "reading": "unclear"}'
    )
    assert proposal.kind is None
    assert proposal.day_index is None
    assert proposal.questions


# ---------------------------------------------------------------------------
# The deterministic attack on the proposal, run instead of a second model pass.
# ---------------------------------------------------------------------------

@given(
    status=st.sampled_from(["ok", "needs_clarification"]),
    kind=st.sampled_from([None, "actor_late", "scene_dropped", "weather_cover"]),
    cast_id=st.sampled_from([None, "cA", "cB", "cC", "cM", "cZZ"]),
    scene_id=st.sampled_from([None, "s1", "s6", "s99"]),
    day_index=st.sampled_from([None, -1, 0, 3, 6, 7, 10 ** 9]),
    questions=st.lists(st.text(min_size=1, max_size=20), max_size=3),
    reading=st.text(max_size=40),
)
@settings(max_examples=400, deadline=None)
def test_a_proposal_is_either_publishable_or_says_what_it_needs(
    status: str, kind: str | None, cast_id: str | None, scene_id: str | None,
    day_index: int | None, questions: list[str], reading: str,
) -> None:
    """Two invariants over every shape the wire can carry, whatever a model puts on it.

    A proposal that reaches the browser as `ok` must produce a payload the engine's own argument
    reader accepts, and a proposal that is not `ok` must say something rather than rendering a
    heading over an empty list. Ids that do not exist are still the engine's business, not this
    schema's: the point here is that the SHAPE is never unusable and never silent.
    """
    proposal = EventProposal(
        status=status, kind=kind, cast_id=cast_id, scene_id=scene_id,
        day_index=day_index, questions=questions, reading=reading,
    )
    out = EventProposalOut.of(proposal)
    if proposal.status == "ok":
        assert proposal.kind is not None
        payload = proposal.event_payload()
        assert payload and out.payload == payload
        # Every field the engine reads for this kind is present and of the type it reads.
        for field in EventProposal.REQUIRED[proposal.kind]:
            assert payload[field] is not None
            assert isinstance(payload[field], int if field == "day_index" else str)
    else:
        assert out.payload == {}
        assert proposal.questions or proposal.reading, "a refusal that says nothing is an empty box"
