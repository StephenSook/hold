"""
Task 2.8: pass 2, the cost pass. Order and day assignment free, rules as hard constraints,
hold-day cents minimized. Every returned schedule is re-judged by pass 1 (D2: the solver
structurally cannot emit an illegal schedule) and recounted by plain Python (D13).
"""
from __future__ import annotations

import json
from datetime import date, time
from pathlib import Path

from api.hold.pass2 import (
    Pass2Outcome,
    pack_order_into_days,
    pass2,
    recount_hold_days,
    to_solve_result,
)
from api.hold.schemas import CastMember, Constraint, Jurisdiction, Scene, ScheduleInput, ShootDay

ROOT = Path(__file__).parents[2]
DEMO = ROOT / "data" / "demo" / "hold-demo.json"
BEFORE = ROOT / "data" / "demo" / "before-order.json"
TIME_LIMIT = 30.0


def _demo() -> ScheduleInput:
    raw = json.loads(DEMO.read_text())
    return ScheduleInput.model_validate({k: v for k, v in raw.items() if not k.startswith("_")})


def _scene(i: int, eighths: int, cast: list[str]) -> Scene:
    return Scene(id=f"s{i}", number=i, int_ext="EXT", day_night="DAY", set="Set", pages_eighths=eighths, cast_ids=cast, location_id="loc1")


def _day(d: date, call: str, wrap: str, school_day: bool = False) -> ShootDay:
    return ShootDay(date=d, call=time.fromisoformat(call), wrap=time.fromisoformat(wrap), school_day=school_day, school_night=False)


_M = CastMember(id="cM", letter="M", age=14, resident_state="CA", day_rate_cents=83400, rate_tier="low_budget")
_A = CastMember(id="cA", letter="A", age=None, resident_state=None, day_rate_cents=83400, rate_tier="low_budget")
_B = CastMember(id="cB", letter="B", age=None, resident_state=None, day_rate_cents=83400, rate_tier="low_budget")


def _schedule(scenes: list[Scene], days: list[ShootDay], cast: list[CastMember], overnight: bool = True, constraints: list[Constraint] | None = None) -> ScheduleInput:
    return ScheduleInput(scenes=scenes, cast=cast, days=days, constraints=constraints or [], jurisdiction=Jurisdiction(shoot_state="GA"), constructed=True, overnight_location=overnight)


def _run(schedule: ScheduleInput, workers: int = 8) -> Pass2Outcome:
    return pass2(schedule, time_limit_s=TIME_LIMIT, num_workers=workers)


# ---------------------------------------------------------------------------
# The demo: zero hold days, zero illegal days, two separate panels
# ---------------------------------------------------------------------------

def test_demo_returns_zero_hold_days_and_zero_illegal_days() -> None:
    outcome = _run(_demo())
    r = outcome.result
    assert r.status == "OPTIMAL", (r.status, r.reasons, outcome.note)
    assert r.hold_days == 0
    assert r.holding_cents == 0
    assert r.total_cents > 0
    assert sorted(r.order) == list(range(10))
    used = [p for p in outcome.pass1 if outcome.day_scene_ids.get(p.verdict.day)]
    assert used and all(p.verdict.status == "LEGAL" for p in used), [(p.verdict.day, p.verdict.status, p.verdict.reason) for p in used]
    assert outcome.checker.agrees, outcome.checker.note
    assert sum(len(v) for v in outcome.day_scene_ids.values()) == 10


def test_demo_before_plan_recounts_the_fixture_hold_days() -> None:
    """The before plan's hold-day figure is computed from its day map, never typed (D7)."""
    schedule = _demo()
    before = json.loads(BEFORE.read_text())
    day_map = {int(k): v for k, v in before["day_scene_ids"].items()}
    assert sorted(sid for ids in day_map.values() for sid in ids) == sorted(before["scene_order"])
    held = recount_hold_days(schedule, day_map)
    assert sum(len(v) for v in held.values()) == before["hold_days"], held


def test_demo_before_plan_is_illegal_on_the_school_day() -> None:
    from api.hold.solve import pass1_schedule

    schedule = _demo()
    before = json.loads(BEFORE.read_text())
    day_map = {int(k): v for k, v in before["day_scene_ids"].items()}
    full = {d: day_map.get(d, []) for d in range(len(schedule.days))}
    verdicts = pass1_schedule(schedule, day_scene_ids=full, time_limit_s=TIME_LIMIT)
    illegal = [v for v in verdicts if v.verdict.status == "ILLEGAL"]
    assert [v.verdict.day for v in illegal] == [before["illegal_day_index"]], [(v.verdict.day, v.verdict.status, v.verdict.reason) for v in verdicts]
    assert len(illegal) == before["illegal_days"]
    core = set(illegal[0].verdict.core_rule_ids)
    assert "CA_11760_e_location_hours_9_15" in core, core
    used = [v for v in verdicts if day_map.get(v.verdict.day)]
    assert all(v.verdict.status == "LEGAL" for v in used if v.verdict.day != before["illegal_day_index"])


# ---------------------------------------------------------------------------
# Constraints and cost semantics
# ---------------------------------------------------------------------------

def _two_day_days() -> list[ShootDay]:
    return [_day(date(2026, 10, 5), "07:00", "19:00"), _day(date(2026, 10, 6), "07:00", "19:00"), _day(date(2026, 10, 7), "07:00", "19:00")]


def test_precedence_and_availability_are_honored() -> None:
    scenes = [_scene(1, 16, ["cA"]), _scene(2, 16, ["cB"]), _scene(3, 16, ["cA", "cB"])]
    constraints = [
        Constraint(type="precedence", scene_id_a="s3", scene_id_b="s1"),
        Constraint(type="availability", cast_id="cB", unavailable_day_indices=[0]),
    ]
    outcome = _run(_schedule(scenes, _two_day_days(), [_A, _B], constraints=constraints))
    r = outcome.result
    assert r.status in ("OPTIMAL", "FEASIBLE"), (r.status, r.reasons)
    assert r.order.index(2) < r.order.index(0), "s3 must shoot before s1"
    assert all("cB" not in s for s in [next(sc for sc in scenes if sc.id == sid).cast_ids for sid in outcome.day_scene_ids.get(0, [])])


def test_the_cheapest_legal_order_keeps_the_minor_scenes_together() -> None:
    """One 12-hour day: M in s1 and s3 around a 9-hour adult scene would put M 11 hours on set.
    The legal optimum still has zero hold days because the solver reorders, not because it pays."""
    scenes = [_scene(1, 8, ["cM", "cA"]), _scene(2, 72, ["cA"]), _scene(3, 8, ["cM", "cA"])]
    outcome = _run(_schedule(scenes, [_day(date(2026, 10, 5), "07:00", "19:00")], [_M, _A]))
    r = outcome.result
    assert r.status == "OPTIMAL", (r.status, r.reasons)
    assert r.hold_days == 0
    used = [p for p in outcome.pass1 if outcome.day_scene_ids.get(p.verdict.day)]
    assert used and all(p.verdict.status == "LEGAL" for p in used), [(p.verdict.day, p.verdict.reason) for p in used]
    positions = {r.order[p]: p for p in range(3)}
    assert abs(positions[0] - positions[2]) == 1, r.order


def test_unpaid_hold_days_when_not_on_an_overnight_location() -> None:
    """Low-budget tiers off an overnight location: intervening days cost nothing, and the result says so."""
    scenes = [_scene(1, 16, ["cA"]), _scene(2, 16, ["cB"]), _scene(3, 16, ["cA"])]
    days = _two_day_days()
    constraints = [Constraint(type="availability", cast_id="cA", unavailable_day_indices=[1])]
    outcome = _run(_schedule(scenes, days, [_A, _B], overnight=False, constraints=constraints))
    assert outcome.paid_hold_days is False
    assert outcome.result.holding_cents == 0
    assert "not paid" in outcome.note


def test_a_minor_who_cannot_fit_any_window_is_undetermined_with_reasons() -> None:
    scenes = [_scene(1, 56, ["cM"])]  # 7 hours of work for a 14-year-old: over every work cap
    outcome = _run(_schedule(scenes, _two_day_days(), [_M, _A]))
    assert outcome.result.status == "UNDETERMINED"
    assert outcome.result.reasons, outcome.note
    assert any("work" in rid.lower() or "WORK" in rid for rid in outcome.result.reasons), outcome.result.reasons


def test_single_worker_is_deterministic() -> None:
    schedule = _demo()
    a = _run(schedule, workers=1)
    b = _run(schedule, workers=1)
    assert a.result.order == b.result.order
    assert a.day_scene_ids == b.day_scene_ids
    assert a.result.holding_cents == b.result.holding_cents


def test_pack_order_into_days_fills_windows_in_order() -> None:
    schedule = _demo()
    order = [s.id for s in schedule.scenes]
    packed = pack_order_into_days(schedule, order)
    flat = [sid for d in sorted(packed) for sid in packed[d]]
    assert flat == order
    assert min(packed) == 0


def test_to_solve_result_carries_two_separate_panels() -> None:
    outcome = _run(_demo())
    sr = to_solve_result(outcome)
    assert sr.pass2.status == "OPTIMAL" and sr.pass2.hold_days == 0
    assert len(sr.pass1) == len(outcome.pass1)
    assert sr.checker.agrees
    assert sr.benchmark is None
    assert sr.model_dump()["pass2"]["holding_cents"] == 0


def test_shoot_dates_outside_every_rate_record_are_undetermined_with_a_rates_reason() -> None:
    days = [_day(date(2019, 10, 5), "07:00", "19:00"), _day(date(2019, 10, 6), "07:00", "19:00")]
    outcome = _run(_schedule([_scene(1, 8, ["cA"]), _scene(2, 8, ["cA"])], days, [_A]))
    assert outcome.result.status == "UNDETERMINED"
    assert outcome.result.reasons == ["rates"], outcome.result.reasons
    assert "2019" in outcome.note
