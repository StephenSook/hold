"""
Task 3.2 golden files, live half: each sample document is sent to the deployed /api/extract and
the answer must match the recorded golden on every field the solver reads. Marked network: CI
runs `-m "not network"`; run it by hand with `uv run pytest -m network api/tests/test_extract_live.py`.
"""
from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path
from typing import Any

import pytest

from api.hold.schemas import ExtractResult, ScheduleInput

ROOT = Path(__file__).parents[2]
SAMPLES = ROOT / "data" / "demo" / "samples"
GOLDEN = ROOT / "data" / "fixtures" / "extraction"
URL = os.environ.get("HOLD_URL", "https://hold-fwmdq7fc3q-uc.a.run.app")


def _extract(text: str) -> ExtractResult:
    return ExtractResult.model_validate(_extract_raw(text))


def _extract_raw(text: str) -> dict[str, Any]:
    """The live answer as it arrives. A test that has to tell an absent field from a defaulted one
    must read the body before pydantic fills the schema defaults in."""
    request = urllib.request.Request(f"{URL}/api/extract", data=json.dumps({"text": text}).encode(), headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=120) as response:
        return dict(json.loads(response.read()))


def _golden(name: str) -> ExtractResult:
    raw = json.loads((GOLDEN / f"{name}.expected.json").read_text())
    return ExtractResult.model_validate({k: v for k, v in raw.items() if not k.startswith("_")})


def _undefined_cast_ids(schedule: ScheduleInput) -> set[str]:
    """Ids a scene or a constraint names that no cast record defines. The comparison below maps every
    id to its letter, so a fallback to the raw id would let "A" compare equal to "cA", and pass 1
    refuses such a schedule (Pass1ScopeError). Both sides of the comparison go through this."""
    used = {cid for s in schedule.scenes for cid in s.cast_ids} | {c.cast_id for c in schedule.constraints if c.cast_id}
    return used - {c.id for c in schedule.cast}


@pytest.mark.network
@pytest.mark.parametrize("name", ["callsheet-day3", "constraints-note"])
def test_live_extraction_matches_the_golden_on_solver_fields(name: str) -> None:
    live_raw = _extract_raw((SAMPLES / f"{name}.txt").read_text())
    golden_raw = json.loads((GOLDEN / f"{name}.expected.json").read_text())
    got = ExtractResult.model_validate(live_raw)
    want = _golden(name)
    assert got.status == want.status == "ok", (got.status, got.questions)
    assert got.schedule is not None and want.schedule is not None
    g, w = got.schedule, want.schedule
    # Compare meaning, not naming: a cast member is its letter and a scene is its number, so a change
    # of id convention is never read as an extraction error (round eight, finding 3).
    got_letter = {c.id: c.letter for c in g.cast}
    want_letter = {c.id: c.letter for c in w.cast}
    # Every id a scene or constraint names must be a cast record on both sides: a fallback to the raw
    # id would let "A" compare equal to "cA", and pass 1 refuses that schedule (round nine, finding 2).
    for schedule, side in ((g, "live"), (w, "golden")):
        dangling = _undefined_cast_ids(schedule)
        assert not dangling, f"{side} names cast ids with no cast record: {sorted(dangling)}"
    assert [(s.number, s.int_ext, s.day_night, s.pages_eighths, sorted(got_letter[i] for i in s.cast_ids)) for s in g.scenes] == [
        (s.number, s.int_ext, s.day_night, s.pages_eighths, sorted(want_letter[i] for i in s.cast_ids)) for s in w.scenes
    ]
    assert [(c.letter, c.age, c.resident_state, c.day_rate_cents, c.rate_tier) for c in g.cast] == [(c.letter, c.age, c.resident_state, c.day_rate_cents, c.rate_tier) for c in w.cast]
    assert [(d.date, d.call.hour, d.call.minute, d.wrap.hour, d.wrap.minute, d.school_day) for d in g.days] == [(d.date, d.call.hour, d.call.minute, d.wrap.hour, d.wrap.minute, d.school_day) for d in w.days]
    assert g.jurisdiction == w.jurisdiction and g.constructed is True
    # Pass 2 prices hold days from overnight_location and the schema default is false on both sides,
    # so comparing the parsed values alone passes when an answer omits the key (round ten, finding 4).
    # The golden half of this is asserted offline below, where CI actually runs it.
    assert "overnight_location" in (live_raw.get("schedule") or {}), "the live answer omitted overnight_location"
    assert golden_raw["schedule"]["overnight_location"] == w.overnight_location
    assert g.overnight_location == w.overnight_location
    scene_number = {s.id: s.number for s in g.scenes}
    got_constraints = sorted((c.type, got_letter[c.cast_id] if c.cast_id else None, scene_number.get(c.scene_id_a or ""), scene_number.get(c.scene_id_b or ""), tuple(c.unavailable_day_indices or [])) for c in g.constraints)
    want_number = {s.id: s.number for s in w.scenes}
    want_constraints = sorted((c.type, want_letter[c.cast_id] if c.cast_id else None, want_number.get(c.scene_id_a or ""), want_number.get(c.scene_id_b or ""), tuple(c.unavailable_day_indices or [])) for c in w.constraints)
    assert got_constraints == want_constraints


@pytest.mark.network
def test_live_extraction_refuses_to_guess_on_an_ambiguous_note() -> None:
    got = _extract((SAMPLES / "ambiguous-note.txt").read_text())
    assert got.status == "needs_clarification" and got.schedule is None
    assert len(got.questions) >= 3, got.questions


def test_golden_files_are_valid_extract_results() -> None:
    """Offline half: every golden parses as an ExtractResult, records its live run, and either
    carries a constructed schedule or refuses with questions."""
    names = {p.name for p in GOLDEN.glob("*.expected.json")}
    assert names == {"callsheet-day3.expected.json", "constraints-note.expected.json", "ambiguous-note.expected.json"}
    for path in sorted(GOLDEN.glob("*.expected.json")):
        raw = json.loads(path.read_text())
        assert raw["_live_run"]["url"].startswith("https://") and raw["_live_run"]["model"]
        result = ExtractResult.model_validate({k: v for k, v in raw.items() if not k.startswith("_")})
        if result.status == "ok":
            assert result.schedule is not None and result.schedule.constructed is True
            # Stated, not defaulted: pass 2 prices hold days from it, and pydantic would put the
            # default back before anything downstream could notice the golden had dropped the key.
            assert "overnight_location" in raw["schedule"], f"{path.name} does not state overnight_location"
        else:
            assert result.status == "needs_clarification" and result.schedule is None and result.questions


@pytest.mark.network
@pytest.mark.parametrize("name", ["callsheet-day3", "constraints-note"])
def test_every_cast_id_the_live_answer_uses_is_defined(name: str) -> None:
    """Round nine, finding 2: a scene that names a cast id with no cast record is refused by pass 1
    (Pass1ScopeError), so a live answer must never carry one."""
    got = _extract((SAMPLES / f"{name}.txt").read_text())
    assert got.schedule is not None
    assert not _undefined_cast_ids(got.schedule)


def test_the_dangling_id_check_rejects_a_golden_that_names_a_letter() -> None:
    """Round ten, finding 5: the guard above reads only the live answer, while the defect it exists
    for is a golden whose scene names "A" where the cast record is "cA". Feed it exactly that."""
    raw = json.loads((GOLDEN / "callsheet-day3.expected.json").read_text())
    body = {k: v for k, v in raw.items() if not k.startswith("_")}
    schedule = ExtractResult.model_validate(body).schedule
    assert schedule is not None and not _undefined_cast_ids(schedule)
    letter = {c.id: c.letter for c in schedule.cast}
    scene = next(s for s in body["schedule"]["scenes"] if s["cast_ids"])
    scene["cast_ids"] = [letter[cid] for cid in scene["cast_ids"]]
    broken = ExtractResult.model_validate(body).schedule
    assert broken is not None
    assert _undefined_cast_ids(broken) == set(scene["cast_ids"]), "a scene naming a letter must be refused"
