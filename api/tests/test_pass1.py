"""
Task 2.7: pass-1 legality solver tests.

Semantics under test (PLAN.md 2.7, D13): scene order and day assignment fixed, scene start
times and each minor's call, dismissal and meal free inside the crew window; every
applicable rule is a named assumption. A rule is in `core_rule_ids` when enforcing it
ALONE makes the day impossible ("individually sufficient"). The checker (task 2.9) stays
the source of truth for `violations`; the solver core must be a subset of what the
crew-window proxy flags, except the timing-only meal rule the proxy cannot see.

Fixtures: data/fixtures/illegal-days/*.json (six illegal, one legal), each carrying
`_check_day_index`, `_day_scene_ids`, `_expected_status`, `_expected_core`.
"""
from __future__ import annotations

import json
from datetime import date, time
from pathlib import Path
from typing import Any

import pytest

from api.hold.legality import Pass1ScopeError, scene_minutes
from api.hold.legality_checker import (
    TIMING_ONLY_RULE_IDS,
    DayTimeline,
    MinorTimeline,
    check_day_legality,
)
from api.hold.registry import RegistryError
from api.hold.schemas import CastMember, Jurisdiction, Scene, ScheduleInput, ShootDay
from api.hold.solve import Pass1Result, pass1_day, pass1_schedule

FIXTURES = Path(__file__).parents[2] / "data" / "fixtures" / "illegal-days"
ILLEGAL = sorted(p for p in FIXTURES.glob("*.json") if p.stem != "legal-day")
LEGAL = FIXTURES / "legal-day.json"
TIME_LIMIT = 10.0

_M = CastMember(id="cM", letter="M", age=14, resident_state="CA", day_rate_cents=81000, rate_tier="low_budget")
_A = CastMember(id="cA", letter="A", age=None, resident_state=None, day_rate_cents=81000, rate_tier="low_budget")


def _load(path: Path) -> tuple[ScheduleInput, dict[str, Any]]:
    raw = json.loads(path.read_text())
    meta = {k: v for k, v in raw.items() if k.startswith("_")}
    schedule = ScheduleInput.model_validate({k: v for k, v in raw.items() if not k.startswith("_")})
    return schedule, meta


def _day_scenes(meta: dict[str, Any], day_index: int) -> list[str]:
    ids: list[str] = meta["_day_scene_ids"].get(str(day_index), [])
    return ids


def _run(path: Path) -> tuple[Pass1Result, dict[str, Any]]:
    schedule, meta = _load(path)
    idx = int(meta["_check_day_index"])
    result = pass1_day(schedule, idx, day_scene_ids=_day_scenes(meta, idx), time_limit_s=TIME_LIMIT)
    return result, meta


def _scene(i: int, eighths: int, cast: list[str]) -> Scene:
    return Scene(id=f"s{i}", number=i, int_ext="EXT", day_night="DAY", set="Set", pages_eighths=eighths, cast_ids=cast, location_id="loc1")


def _day(d: date, call: str, wrap: str, school_day: bool = False) -> ShootDay:
    return ShootDay(date=d, call=time.fromisoformat(call), wrap=time.fromisoformat(wrap), school_day=school_day)


def _timeline_from_witness(witness: dict[str, Any]) -> DayTimeline:
    minors: dict[str, MinorTimeline] = {}
    for cast_id, m in witness["minors"].items():
        meal = m.get("meal")
        minors[cast_id] = MinorTimeline(
            call=time.fromisoformat(m["call"]),
            dismiss=time.fromisoformat(m["dismiss"]),
            work_minutes=int(m["work_minutes"]),
            meal_start=time.fromisoformat(meal["start"]) if meal else None,
            meal_end=time.fromisoformat(meal["end"]) if meal else None,
        )
    return DayTimeline(minors=minors)


# ---------------------------------------------------------------------------
# Fixture set
# ---------------------------------------------------------------------------

def test_fixture_set_is_six_illegal_plus_one_legal() -> None:
    assert len(ILLEGAL) == 6, [p.stem for p in ILLEGAL]
    assert LEGAL.exists()
    for p in [*ILLEGAL, LEGAL]:
        schedule, meta = _load(p)
        assert schedule.constructed is True
        assert meta["_expected_status"] in {"ILLEGAL", "LEGAL"}


def test_scene_minutes_rounds_half_eighths_up() -> None:
    """One page (8 eighths) is 60 minutes; odd eighth counts round up to whole minutes."""
    assert scene_minutes(8) == 60
    assert scene_minutes(16) == 120
    assert scene_minutes(3) == 23
    assert scene_minutes(1) == 8


# ---------------------------------------------------------------------------
# Illegal fixtures: exact core, subset of the checker, non-empty violations
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("path", ILLEGAL, ids=[p.stem for p in ILLEGAL])
def test_illegal_fixture_core_is_exact(path: Path) -> None:
    result, meta = _run(path)
    assert result.solver_status != "UNKNOWN", "time limit hit; raise TIME_LIMIT before judging"
    assert result.verdict.status == "ILLEGAL", (result.verdict.status, result.note)
    assert set(result.verdict.core_rule_ids) == set(meta["_expected_core"]), (
        f"{path.stem}: core {sorted(result.verdict.core_rule_ids)} vs expected {sorted(meta['_expected_core'])}; "
        f"per_rule={result.per_rule}"
    )


@pytest.mark.parametrize("path", ILLEGAL, ids=[p.stem for p in ILLEGAL])
def test_illegal_fixture_core_is_subset_of_checker(path: Path) -> None:
    """D13: the solver explains, the checker enumerates. Every core id is in the checker's list."""
    result, meta = _run(path)
    schedule, _ = _load(path)
    idx = int(meta["_check_day_index"])
    proxy_ids = {v.rule_id for v in check_day_legality(schedule, idx)}
    core = set(result.verdict.core_rule_ids)
    assert core <= proxy_ids | TIMING_ONLY_RULE_IDS, (core - proxy_ids, proxy_ids)
    violation_ids = {v.rule_id for v in result.verdict.violations}
    assert violation_ids, "ILLEGAL verdict must carry the checker's violations"
    assert core <= violation_ids | TIMING_ONLY_RULE_IDS


def test_per_rule_statuses_are_exposed() -> None:
    result, _ = _run(FIXTURES / "curfew-school-night.json")
    assert result.per_rule["GA_300_7_1_03_school_night_curfew"] == "INFEASIBLE"
    assert result.per_rule["CA_1308_7_curfew_school_night"] == "INFEASIBLE"
    assert result.per_rule["GA_300_7_1_03_ages_9_15_location_hours"] == "FEASIBLE"
    assert set(result.individually_sufficient) == set(result.verdict.core_rule_ids)


def test_illegal_verdict_is_deterministic() -> None:
    a, _ = _run(FIXTURES / "curfew-school-night.json")
    b, _ = _run(FIXTURES / "curfew-school-night.json")
    assert a.verdict.core_rule_ids == b.verdict.core_rule_ids
    assert a.per_rule == b.per_rule


# ---------------------------------------------------------------------------
# Legal fixture: witness the checker passes
# ---------------------------------------------------------------------------

def test_legal_fixture_returns_witness_the_checker_passes() -> None:
    result, _ = _run(LEGAL)
    schedule, meta = _load(LEGAL)
    assert result.solver_status != "UNKNOWN"
    v = result.verdict
    assert v.status == "LEGAL", (v.status, result.note)
    assert v.core_rule_ids == []
    assert v.violations == []
    assert v.witness is not None
    w = v.witness
    for key in ("day", "date", "crew_call", "crew_wrap", "scenes", "minors", "heuristic"):
        assert key in w, key
    scenes = w["scenes"]
    assert isinstance(scenes, list)
    assert [s["id"] for s in scenes] == _day_scenes(meta, 0)
    call_m = 7 * 60
    wrap_m = 16 * 60
    prev_end = call_m
    for s in scenes:
        start = _minutes(str(s["start"]))
        end = _minutes(str(s["end"]))
        assert call_m <= start < end <= wrap_m, s
        assert start >= prev_end, "scenes must keep the fixed order"
        prev_end = end
    minors = w["minors"]
    assert isinstance(minors, dict)
    assert _minutes(str(minors["cM"]["call"])) >= 5 * 60
    assert check_day_legality(schedule, 0, timeline=_timeline_from_witness(w)) == []


def test_legal_witness_is_deterministic() -> None:
    a, _ = _run(LEGAL)
    b, _ = _run(LEGAL)
    assert a.verdict.witness == b.verdict.witness


def _minutes(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


# ---------------------------------------------------------------------------
# Constructed cases: adults only, overfull window, timing-only core, joint-only core
# ---------------------------------------------------------------------------

def _schedule(scenes: list[Scene], days: list[ShootDay], cast: list[CastMember], state: str = "GA") -> ScheduleInput:
    return ScheduleInput(scenes=scenes, cast=cast, days=days, constraints=[], jurisdiction=Jurisdiction(shoot_state=state), constructed=True)  # type: ignore[arg-type]


def test_adult_only_day_is_legal_with_empty_core() -> None:
    schedule = _schedule([_scene(1, 16, ["cA"])], [_day(date(2026, 10, 5), "07:00", "16:00")], [_A])
    result = pass1_day(schedule, 0, day_scene_ids=["s1"], time_limit_s=TIME_LIMIT)
    assert result.verdict.status == "LEGAL"
    assert result.verdict.core_rule_ids == []
    assert result.verdict.violations == []
    assert result.verdict.witness is not None


def test_overfull_window_is_undetermined_not_illegal() -> None:
    """Three hours of scenes in a two-hour window is a scheduling impossibility, not a legal one."""
    schedule = _schedule([_scene(1, 24, ["cA"])], [_day(date(2026, 10, 5), "07:00", "09:00")], [_A])
    result = pass1_day(schedule, 0, day_scene_ids=["s1"], time_limit_s=TIME_LIMIT)
    assert result.verdict.status == "UNDETERMINED"
    assert "window" in result.note.lower()
    assert result.verdict.core_rule_ids == []


def test_timing_only_core_is_undetermined_with_named_rule() -> None:
    """
    Non-GA shoot, CA-resident minor bracketing a six-hour adult scene in an eight-hour window
    packed edge to edge: no 30-minute meal can fit, so only the meal rule fails. The crew-window
    checker cannot see meals, so the verdict is UNDETERMINED and names the rule.
    """
    schedule = _schedule(
        [_scene(1, 8, ["cM"]), _scene(2, 48, ["cA"]), _scene(3, 8, ["cM"])],
        [_day(date(2026, 10, 5), "07:00", "15:00")],
        [_M, _A],
        state="other",
    )
    result = pass1_day(schedule, 0, day_scene_ids=["s1", "s2", "s3"], time_limit_s=TIME_LIMIT)
    assert result.individually_sufficient == ["CA_11761_meal_period_6_hours"], result.per_rule
    assert result.verdict.status == "UNDETERMINED"
    assert "CA_11761_meal_period_6_hours" in result.note


def test_joint_only_infeasibility_reports_sufficient_core() -> None:
    """
    Non-GA shoot. Day 1 follows a 22:00 wrap (CA turnaround: call at or after 10:00) and precedes
    a school day (CA 1308.7(a): dismissed by 22:00). M opens and closes a day of exactly twelve
    hours of scenes (1h, 5h, 5h, 1h). Each rule alone is satisfiable: turnaround alone shifts the
    day to 10:00 to 22:00, the curfew alone is met from 07:00, the meal rule alone fits a 30-minute
    break between the two adult scenes. All three together cannot hold: the meal stretches the
    span to 12.5 hours, which no longer fits between a 10:00 call and a 22:00 dismissal.
    """
    scenes = [_scene(1, 8, ["cM"]), _scene(2, 8, ["cM"]), _scene(3, 40, ["cA"]), _scene(4, 40, ["cA"]), _scene(5, 8, ["cM"])]
    days = [
        _day(date(2026, 10, 7), "07:00", "22:00"),
        _day(date(2026, 10, 8), "07:00", "23:30"),
        _day(date(2026, 10, 9), "07:00", "11:00", school_day=True),
    ]
    schedule = _schedule(scenes, days, [_M, _A], state="other")
    result = pass1_day(schedule, 1, day_scene_ids=["s2", "s3", "s4", "s5"], time_limit_s=TIME_LIMIT)
    assert result.solver_status != "UNKNOWN"
    assert result.individually_sufficient == [], result.per_rule
    joint = {"CA_11760_i_turnaround_12_hours", "CA_1308_7_curfew_school_night", "CA_11761_meal_period_6_hours"}
    assert joint <= set(result.sufficient_core), result.sufficient_core
    assert result.verdict.status == "ILLEGAL"
    assert "joint" in result.note.lower()
    assert set(result.verdict.core_rule_ids) == set(result.sufficient_core)
    proxy_ids = {v.rule_id for v in check_day_legality(schedule, 1)}
    assert set(result.verdict.core_rule_ids) <= proxy_ids | TIMING_ONLY_RULE_IDS


def test_turnaround_uses_previous_consecutive_day_only() -> None:
    """The turnaround fixture with a three-day gap before the school day becomes legal."""
    schedule, meta = _load(FIXTURES / "turnaround-school-day.json")
    days = list(schedule.days)
    days[0] = ShootDay(date=date(2026, 10, 4), call=days[0].call, wrap=days[0].wrap, school_day=days[0].school_day)
    shifted = schedule.model_copy(update={"days": days})
    result = pass1_day(shifted, 1, day_scene_ids=_day_scenes(meta, 1), time_limit_s=TIME_LIMIT)
    assert result.verdict.status == "LEGAL", (result.verdict.status, result.per_rule)


# ---------------------------------------------------------------------------
# Whole schedule
# ---------------------------------------------------------------------------

def test_pass1_schedule_returns_one_verdict_per_day() -> None:
    schedule, meta = _load(FIXTURES / "consecutive-days.json")
    day_scene_ids = {int(k): v for k, v in meta["_day_scene_ids"].items()}
    verdicts = pass1_schedule(schedule, day_scene_ids=day_scene_ids, time_limit_s=TIME_LIMIT)
    assert len(verdicts) == len(schedule.days) == 7
    assert verdicts[0].verdict.status == "LEGAL"
    assert verdicts[6].verdict.status == "ILLEGAL"
    assert verdicts[6].verdict.core_rule_ids == ["GA_300_7_1_03_consecutive_days"]


# ---------------------------------------------------------------------------
# Errors are errors: scope problems are UNDETERMINED, data corruption raises
# ---------------------------------------------------------------------------

def test_wrap_before_call_is_out_of_scope_not_a_verdict() -> None:
    schedule = _schedule([_scene(1, 8, ["cM"])], [_day(date(2026, 10, 5), "20:00", "02:00")], [_M, _A])
    result = pass1_day(schedule, 0, day_scene_ids=["s1"], time_limit_s=TIME_LIMIT)
    assert result.verdict.status == "UNDETERMINED"
    assert "out of scope" in result.note
    assert result.solver_status == "NOT_RUN"


def test_unknown_scene_id_is_out_of_scope_not_a_verdict() -> None:
    schedule = _schedule([_scene(1, 8, ["cM"])], [_day(date(2026, 10, 5), "07:00", "16:00")], [_M, _A])
    result = pass1_day(schedule, 0, day_scene_ids=["s1", "s9"], time_limit_s=TIME_LIMIT)
    assert result.verdict.status == "UNDETERMINED"
    assert "s9" in result.note


def test_registry_corruption_raises_instead_of_undetermined(tmp_path: Path) -> None:
    """A rule record missing its citation is a D4 violation: the solver must raise like the checker."""
    src = Path(__file__).parents[2] / "rules"
    for f in src.glob("*.yaml"):
        text = f.read_text()
        if f.name == "ca.yaml":
            text = text.replace("citation: 8 CCR 11761", "citation:", 1)
        (tmp_path / f.name).write_text(text)
    schedule, meta = _load(LEGAL)
    with pytest.raises(RegistryError):
        pass1_day(schedule, 0, day_scene_ids=_day_scenes(meta, 0), time_limit_s=TIME_LIMIT, rules_dir=tmp_path)


def test_scope_error_type_is_distinct_from_registry_error() -> None:
    assert issubclass(Pass1ScopeError, ValueError)
    assert not issubclass(RegistryError, Pass1ScopeError)


# ---------------------------------------------------------------------------
# A day with no scene list is never a verdict
# ---------------------------------------------------------------------------

def test_explicit_empty_scene_list_is_undetermined() -> None:
    schedule, _ = _load(FIXTURES / "curfew-school-night.json")
    result = pass1_day(schedule, 0, day_scene_ids=[], time_limit_s=TIME_LIMIT)
    assert result.verdict.status == "UNDETERMINED"
    assert "no scenes" in result.note
    assert result.verdict.witness is None


def test_pass1_schedule_raises_on_a_missing_day_key() -> None:
    schedule, meta = _load(FIXTURES / "curfew-school-night.json")
    incomplete = {0: _day_scenes(meta, 0)}  # day 1 missing on purpose
    with pytest.raises(KeyError):
        pass1_schedule(schedule, day_scene_ids=incomplete, time_limit_s=TIME_LIMIT)


# ---------------------------------------------------------------------------
# Who is a minor, and which minors were on set
# ---------------------------------------------------------------------------

def _cast(cid: str, age: int | None, state: str | None = None) -> CastMember:
    return CastMember(id=cid, letter=cid[-1], age=age, resident_state=state, day_rate_cents=81000, rate_tier="low_budget")


def test_recorded_age_eighteen_is_an_adult() -> None:
    """An 18-year-old with an age on file is not a minor: a 23:00 school-night wrap is legal."""
    adult = _cast("cX", 18, "CA")
    days = [_day(date(2026, 10, 7), "14:00", "23:00"), _day(date(2026, 10, 8), "07:00", "11:00", school_day=True)]
    schedule = _schedule([_scene(1, 24, ["cA"]), _scene(2, 24, ["cA"]), _scene(3, 24, ["cX"])], days, [adult, _A])
    result = pass1_day(schedule, 0, day_scene_ids=["s1", "s2", "s3"], time_limit_s=TIME_LIMIT)
    assert result.verdict.status == "LEGAL", (result.verdict.status, result.per_rule)
    assert result.per_rule == {}
    assert check_day_legality(schedule, 0) == []


def _bracket_day(age: int) -> tuple[ScheduleInput, list[str]]:
    """Minor opens and closes a 13-hour GA day around an 11-hour adult block (span 12.5 h)."""
    minor = _cast("cY", age)
    days = [_day(date(2026, 10, 5), "07:00", "20:00")]
    scenes = [_scene(1, 6, ["cY"]), _scene(2, 88, ["cA"]), _scene(3, 6, ["cY"])]
    return _schedule(scenes, days, [minor, _A]), ["s1", "s2", "s3"]


def test_fifteen_is_in_the_nine_to_fifteen_bracket() -> None:
    schedule, ids = _bracket_day(15)
    result = pass1_day(schedule, 0, day_scene_ids=ids, time_limit_s=TIME_LIMIT)
    assert set(result.verdict.core_rule_ids) == {"GA_300_7_1_03_ages_9_15_location_hours"}


def test_sixteen_is_in_the_sixteen_to_seventeen_bracket() -> None:
    schedule, ids = _bracket_day(16)
    result = pass1_day(schedule, 0, day_scene_ids=ids, time_limit_s=TIME_LIMIT)
    assert set(result.verdict.core_rule_ids) == {"GA_300_7_1_03_ages_16_17_location_hours"}
    assert "GA_300_7_1_03_ages_9_15_location_hours" not in result.per_rule


def test_seventeen_is_still_covered() -> None:
    schedule, ids = _bracket_day(17)
    result = pass1_day(schedule, 0, day_scene_ids=ids, time_limit_s=TIME_LIMIT)
    assert result.verdict.status == "ILLEGAL"
    assert "GA_300_7_1_03_ages_16_17_location_hours" in result.verdict.core_rule_ids


def test_illegal_violations_exclude_minors_with_no_scene_that_day() -> None:
    """A 17-year-old in the cast but not on set must not put 16-17 rules on the verdict card."""
    older = _cast("cZ", 17)
    days = [_day(date(2026, 10, 5), "07:00", "20:00")]
    scenes = [_scene(1, 6, ["cM"]), _scene(2, 88, ["cA"]), _scene(3, 6, ["cM"])]
    schedule = _schedule(scenes, days, [_M, _A, older])
    result = pass1_day(schedule, 0, day_scene_ids=["s1", "s2", "s3"], time_limit_s=TIME_LIMIT)
    assert result.verdict.status == "ILLEGAL"
    assert result.verdict.witness is None
    ids = {v.rule_id for v in result.verdict.violations}
    assert not {r for r in ids if "16_17" in r}, ids


# ---------------------------------------------------------------------------
# The previous-dismissal override reaches the checker; the CA school-day cap binds
# ---------------------------------------------------------------------------

def test_prev_dismissal_override_reaches_the_checker() -> None:
    """With a three-day gap the schedule implies no turnaround; the override says 22:00 yesterday."""
    schedule, meta = _load(FIXTURES / "turnaround-school-day.json")
    days = list(schedule.days)
    days[0] = ShootDay(date=date(2026, 10, 4), call=days[0].call, wrap=days[0].wrap, school_day=days[0].school_day)
    shifted = schedule.model_copy(update={"days": days})
    result = pass1_day(shifted, 1, day_scene_ids=_day_scenes(meta, 1), prev_dismissal=time(22, 0), time_limit_s=TIME_LIMIT)
    assert result.verdict.status == "ILLEGAL"
    core = set(result.verdict.core_rule_ids)
    assert "CA_11760_i_turnaround_12_hours" in core
    violation_ids = {v.rule_id for v in result.verdict.violations}
    assert core <= violation_ids, (core - violation_ids, violation_ids)


def test_school_day_three_hour_cap_binds_in_the_solver() -> None:
    days = [_day(date(2026, 10, 5), "07:00", "16:00", school_day=True)]
    schedule = _schedule([_scene(1, 32, ["cM", "cA"])], days, [_M, _A])
    result = pass1_day(schedule, 0, day_scene_ids=["s1"], time_limit_s=TIME_LIMIT)
    assert set(result.verdict.core_rule_ids) == {"CA_11760_e_work_hours_9_15_school_day"}, result.per_rule
    assert result.per_rule["GA_300_7_1_03_ages_9_15_work_hours"] == "FEASIBLE"


# ---------------------------------------------------------------------------
# Meal rule: no stretch over the limit on either side of the meal
# ---------------------------------------------------------------------------

def test_seven_hours_after_the_meal_is_not_legal() -> None:
    """Second-model finding: 05:00 to 13:30, a 1h minor scene, then a 7h minor scene. One 30-minute
    meal at 06:00 satisfied "within six hours of call" and left seven uninterrupted hours after it."""
    days = [_day(date(2026, 10, 5), "05:00", "13:30")]
    schedule = _schedule([_scene(1, 8, ["cM"]), _scene(2, 56, ["cM"])], days, [_M, _A], state="other")
    result = pass1_day(schedule, 0, day_scene_ids=["s1", "s2"], time_limit_s=TIME_LIMIT)
    assert result.verdict.status != "LEGAL", (result.verdict.status, result.verdict.witness)
    assert "CA_11761_meal_period_6_hours" in result.per_rule
    assert result.per_rule["CA_11761_meal_period_6_hours"] == "INFEASIBLE"


# ---------------------------------------------------------------------------
# Dangling or duplicate cast references are not a verdict
# ---------------------------------------------------------------------------

def test_scene_referencing_unknown_cast_id_is_undetermined() -> None:
    """Second-model finding: cast=[] with a scene naming a missing minor solved as LEGAL."""
    schedule = _schedule([_scene(1, 8, ["ghost"])], [_day(date(2026, 10, 5), "07:00", "16:00")], [])
    result = pass1_day(schedule, 0, day_scene_ids=["s1"], time_limit_s=TIME_LIMIT)
    assert result.verdict.status == "UNDETERMINED"
    assert "ghost" in result.note
    assert result.solver_status == "NOT_RUN"


def test_duplicate_cast_ids_are_undetermined() -> None:
    twin = _cast("cM", 17)
    schedule = _schedule([_scene(1, 8, ["cM"])], [_day(date(2026, 10, 5), "07:00", "16:00")], [_M, twin])
    result = pass1_day(schedule, 0, day_scene_ids=["s1"], time_limit_s=TIME_LIMIT)
    assert result.verdict.status == "UNDETERMINED"
    assert "duplicate" in result.note


def test_duplicate_scene_ids_are_undetermined() -> None:
    schedule = _schedule([_scene(1, 8, ["cM"]), _scene(1, 8, ["cA"])], [_day(date(2026, 10, 5), "07:00", "16:00")], [_M, _A])
    result = pass1_day(schedule, 0, day_scene_ids=["s1"], time_limit_s=TIME_LIMIT)
    assert result.verdict.status == "UNDETERMINED"
    assert "duplicate" in result.note
