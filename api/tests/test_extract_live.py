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

import pytest

from api.hold.schemas import ExtractResult

ROOT = Path(__file__).parents[2]
SAMPLES = ROOT / "data" / "demo" / "samples"
GOLDEN = ROOT / "data" / "fixtures" / "extraction"
URL = os.environ.get("HOLD_URL", "https://hold-fwmdq7fc3q-uc.a.run.app")


def _extract(text: str) -> ExtractResult:
    request = urllib.request.Request(f"{URL}/api/extract", data=json.dumps({"text": text}).encode(), headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=120) as response:
        return ExtractResult.model_validate_json(response.read())


def _golden(name: str) -> ExtractResult:
    raw = json.loads((GOLDEN / f"{name}.expected.json").read_text())
    return ExtractResult.model_validate({k: v for k, v in raw.items() if not k.startswith("_")})


@pytest.mark.network
@pytest.mark.parametrize("name", ["callsheet-day3", "constraints-note"])
def test_live_extraction_matches_the_golden_on_solver_fields(name: str) -> None:
    got = _extract((SAMPLES / f"{name}.txt").read_text())
    want = _golden(name)
    assert got.status == want.status == "ok", (got.status, got.questions)
    assert got.schedule is not None and want.schedule is not None
    g, w = got.schedule, want.schedule
    assert [(s.number, s.int_ext, s.day_night, s.pages_eighths, sorted(s.cast_ids)) for s in g.scenes] == [(s.number, s.int_ext, s.day_night, s.pages_eighths, sorted(s.cast_ids)) for s in w.scenes]
    assert [(c.letter, c.age, c.resident_state, c.day_rate_cents, c.rate_tier) for c in g.cast] == [(c.letter, c.age, c.resident_state, c.day_rate_cents, c.rate_tier) for c in w.cast]
    assert [(d.date, d.call.hour, d.call.minute, d.wrap.hour, d.wrap.minute, d.school_day) for d in g.days] == [(d.date, d.call.hour, d.call.minute, d.wrap.hour, d.wrap.minute, d.school_day) for d in w.days]
    assert g.jurisdiction == w.jurisdiction and g.constructed is True
    scene_number = {s.id: s.number for s in g.scenes}
    got_constraints = sorted((c.type, c.cast_id, scene_number.get(c.scene_id_a or ""), scene_number.get(c.scene_id_b or ""), tuple(c.unavailable_day_indices or [])) for c in g.constraints)
    want_number = {s.id: s.number for s in w.scenes}
    want_constraints = sorted((c.type, c.cast_id, want_number.get(c.scene_id_a or ""), want_number.get(c.scene_id_b or ""), tuple(c.unavailable_day_indices or [])) for c in w.constraints)
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
        else:
            assert result.status == "needs_clarification" and result.schedule is None and result.questions
