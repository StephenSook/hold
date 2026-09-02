"""
Task 1.9: Verify all shared contract fixtures validate against their Pydantic models.
These fixtures are what Deem builds the web app against.
"""
import json
from pathlib import Path

import pytest

from api.hold.schemas import (
    ExtractResult,
    ScheduleInput,
    SolveResult,
    Verdict,
)

FIXTURES = Path(__file__).parent.parent.parent / "data" / "fixtures" / "contracts"


def _load(name: str) -> dict:  # type: ignore[type-arg]
    return json.loads((FIXTURES / name).read_text())


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
def test_all_fixtures_parse(filename: str, model_cls: type) -> None:  # type: ignore[type-arg]
    data = _load(filename)
    obj = model_cls.model_validate(data)
    assert obj is not None
