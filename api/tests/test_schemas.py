"""
Task 1.9: Verify all shared contract fixtures validate against their Pydantic models.
These fixtures are what Deem builds the web app against.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from api.hold.schemas import (
    ExtractResult,
    ScheduleInput,
    SolveResult,
    Verdict,
)

FIXTURES = Path(__file__).parent.parent.parent / "data" / "fixtures" / "contracts"


def _load(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text())  # type: ignore[no-any-return]


def test_schedule_input_fixture_validates() -> None:
    data = _load("schedule-input.json")
    obj = ScheduleInput.model_validate(data)
    assert len(obj.scenes) == 3
    assert obj.constructed is True
    assert obj.jurisdiction.shoot_state == "GA"
    # Minor cast member present
    minor = next(c for c in obj.cast if c.letter == "M")
    assert minor.age == 14
    assert minor.resident_state == "CA"


def test_schedule_input_round_trips() -> None:
    data = _load("schedule-input.json")
    obj = ScheduleInput.model_validate(data)
    # Round-trip through JSON
    round_tripped = ScheduleInput.model_validate_json(obj.model_dump_json())
    assert round_tripped == obj


def test_extract_result_fixture_validates() -> None:
    data = _load("extract-result.json")
    obj = ExtractResult.model_validate(data)
    assert obj.status == "ok"
    assert obj.schedule is not None
    assert len(obj.questions) == 0


def test_extract_result_needs_clarification() -> None:
    obj = ExtractResult(
        status="needs_clarification",
        schedule=None,
        questions=["What is the call time for day 2?", "Is scene 5 interior or exterior?"],
        notes="Ambiguous input",
    )
    assert obj.status == "needs_clarification"
    assert len(obj.questions) == 2


def test_verdict_illegal_fixture_validates() -> None:
    data = _load("verdict-illegal.json")
    obj = Verdict.model_validate(data)
    assert obj.status == "ILLEGAL"
    assert len(obj.violations) == 1
    v = obj.violations[0]
    assert v.rule_id == "CA_11760e_work_cap"
    assert v.quote  # non-empty verbatim quote required


def test_solve_result_fixture_validates() -> None:
    data = _load("solve-result.json")
    obj = SolveResult.model_validate(data)
    assert obj.pass2.status == "FEASIBLE"
    assert obj.pass2.hold_days == 0
    assert obj.checker.agrees is True
    assert obj.benchmark is None


@pytest.mark.parametrize("filename,model_cls", [
    ("schedule-input.json", ScheduleInput),
    ("extract-result.json", ExtractResult),
    ("verdict-illegal.json", Verdict),
    ("solve-result.json", SolveResult),
])
def test_all_fixtures_parse(filename: str, model_cls: type[Any]) -> None:
    data = _load(filename)
    obj = model_cls.model_validate(data)
    assert obj is not None


def test_days_must_be_chronological_and_unique() -> None:
    """Checker fallbacks, turnaround and pass-2 hold days read days by list position."""
    raw = _load("schedule-input.json")
    days = raw["days"]
    assert len(days) >= 2
    with pytest.raises(ValidationError, match="chronological"):
        ScheduleInput.model_validate(dict(raw, days=[days[1], days[0], *days[2:]]))
    with pytest.raises(ValidationError, match="chronological"):
        ScheduleInput.model_validate(dict(raw, days=[days[0], days[0], *days[1:]]))


def test_extract_result_status_matches_its_payload() -> None:
    """Round four, finding 6: the confirmation UI trusts these two invariants."""
    with pytest.raises(ValidationError, match="requires a schedule"):
        ExtractResult.model_validate({"status": "ok", "schedule": None, "questions": [], "notes": ""})
    with pytest.raises(ValidationError, match="requires questions"):
        ExtractResult.model_validate({"status": "needs_clarification", "schedule": None, "questions": [], "notes": ""})
    ok = ExtractResult.model_validate({"status": "needs_clarification", "schedule": None, "questions": ["Which day?"], "notes": ""})
    assert ok.questions == ["Which day?"]
