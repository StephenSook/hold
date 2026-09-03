"""
Task 2.7: pass 1, the legality verdict for one shoot day.

Three solves per day, all single worker, no objective (PLAN.md 2.7):
1. Base solve with every rule literal free. INFEASIBLE means the scenes do not fit the crew
   window under the page-per-hour heuristic: UNDETERMINED, a scheduling impossibility, not a
   legal one.
2. Full solve with every applicable rule literal assumed. FEASIBLE means a legal timing
   exists: LEGAL, with a witness call sheet the checker re-reads. INFEASIBLE yields CP-SAT's
   sufficient core through sufficient_assumptions_for_infeasibility().
3. Per-literal solves, one rule assumed at a time. A rule whose enforcement ALONE makes the
   day impossible is "individually sufficient". core_rule_ids is that set; when it is empty
   (rules that bind only together) it is the sufficient core, labeled joint.

D13: the checker enumerates, the solver explains. `violations` always come from the checker:
on ILLEGAL from the crew-window proxy, on LEGAL from the witness timeline (expected empty; if
the checker still finds something the day is UNDETERMINED, never a silent LEGAL).

Witness keys (documented in PLAN.md Shared Contracts, Verdict row):
  day, date, crew_call, crew_wrap, heuristic,
  scenes: [{id, start, end, cast_ids}],
  minors: {cast_id: {call, dismiss, work_minutes, location_minutes, meal: {start, end} | null}}
Times are "HH:MM" strings.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import time
from pathlib import Path
from typing import Any

from ortools.sat.python import cp_model

from api.hold.legality import HEURISTIC_NOTE, DayModel, Pass1ScopeError, build_day_model, minutes_of
from api.hold.legality_checker import (
    TIMING_ONLY_RULE_IDS,
    DayTimeline,
    MinorTimeline,
    check_day_legality,
)
from api.hold.schemas import ScheduleInput, Verdict

_KNOWN_STATUSES = frozenset({"OPTIMAL", "FEASIBLE", "INFEASIBLE", "UNKNOWN", "MODEL_INVALID"})


@dataclass
class Pass1Result:
    verdict: Verdict
    solver_status: str
    individually_sufficient: list[str] = field(default_factory=list)
    sufficient_core: list[str] = field(default_factory=list)
    per_rule: dict[str, str] = field(default_factory=dict)
    note: str = ""


def _hhmm(minutes: int) -> str:
    minutes %= 1440
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _solver(time_limit_s: float) -> cp_model.CpSolver:
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_s
    solver.parameters.num_workers = 1
    return solver


def _solve_with(dm: DayModel, assumptions: list[Any], time_limit_s: float) -> tuple[str, cp_model.CpSolver]:
    dm.model.clear_assumptions()
    if assumptions:
        dm.model.add_assumptions(assumptions)
    solver = _solver(time_limit_s)
    status = solver.status_name(solver.solve(dm.model))
    if status not in _KNOWN_STATUSES:
        raise RuntimeError(f"CP-SAT returned an unexpected status {status!r}")
    return status, solver


def _prev_dismissal_minutes(schedule: ScheduleInput, day_index: int) -> int | None:
    """Previous consecutive calendar day's crew wrap; days are independent (never a witness)."""
    if day_index == 0:
        return None
    prev, cur = schedule.days[day_index - 1], schedule.days[day_index]
    if (cur.date - prev.date).days != 1:
        return None
    return minutes_of(prev.wrap)


def _witness(dm: DayModel, solver: cp_model.CpSolver, schedule: ScheduleInput) -> dict[str, object]:
    day = schedule.days[dm.day_index]
    scenes_by_id = {s.id: s for s in schedule.scenes}
    scenes: list[dict[str, object]] = []
    for sid in dm.scene_ids:
        start = int(solver.value(dm.starts[sid]))
        scenes.append({
            "id": sid,
            "start": _hhmm(start),
            "end": _hhmm(start + dm.durations[sid]),
            "cast_ids": list(scenes_by_id[sid].cast_ids),
        })
    meal: dict[str, str] | None = None
    if int(solver.value(dm.meal_present)) == 1:
        ms = int(solver.value(dm.meal_start))
        meal = {"start": _hhmm(ms), "end": _hhmm(ms + dm.meal_minutes)}
    minors: dict[str, object] = {}
    for cast_id, mv in dm.minors.items():
        call = int(solver.value(mv.call))
        dismiss = int(solver.value(mv.dismiss))
        minors[cast_id] = {
            "call": _hhmm(call),
            "dismiss": _hhmm(dismiss),
            "work_minutes": mv.work_minutes,
            "location_minutes": dismiss - call,
            "meal": meal,
        }
    return {
        "day": dm.day_index,
        "date": day.date.isoformat(),
        "crew_call": _hhmm(dm.call_m),
        "crew_wrap": _hhmm(dm.wrap_m),
        "heuristic": HEURISTIC_NOTE,
        "scenes": scenes,
        "minors": minors,
    }


def _timeline(witness: dict[str, object]) -> DayTimeline:
    minors_raw = witness["minors"]
    assert isinstance(minors_raw, dict)
    minors: dict[str, MinorTimeline] = {}
    for cast_id, m in minors_raw.items():
        meal = m.get("meal")
        minors[cast_id] = MinorTimeline(
            call=time.fromisoformat(m["call"]),
            dismiss=time.fromisoformat(m["dismiss"]),
            work_minutes=int(m["work_minutes"]),
            meal_start=time.fromisoformat(meal["start"]) if meal else None,
            meal_end=time.fromisoformat(meal["end"]) if meal else None,
        )
    return DayTimeline(minors=minors)


def pass1_day(
    schedule: ScheduleInput,
    day_index: int,
    day_scene_ids: list[str] | None = None,
    prev_dismissal: time | None = None,
    time_limit_s: float = 10.0,
    rules_dir: Path | None = None,
) -> Pass1Result:
    """
    Pass-1 verdict for one day. See the module docstring for the three-step solve.

    day_scene_ids: the scenes shot that day, in shooting order. None means every scene in
    the production, in listed order (only sensible for a one-day schedule); an explicit
    empty list is UNDETERMINED, never a verdict. prev_dismissal: override for the previous
    day's dismissal; by default the previous consecutive calendar day's crew wrap.
    """
    if day_scene_ids is None:
        day_scene_ids = [s.id for s in schedule.scenes]
    prev_m = minutes_of(prev_dismissal) if prev_dismissal is not None else _prev_dismissal_minutes(schedule, day_index)

    def undetermined(note: str, status: str, **extra: Any) -> Pass1Result:
        return Pass1Result(
            verdict=Verdict(status="UNDETERMINED", day=day_index, violations=[], core_rule_ids=[], witness=None),
            solver_status=status,
            note=note,
            **extra,
        )

    if not day_scene_ids:
        return undetermined("no scenes assigned to this day; nothing to judge", "NOT_RUN")

    try:
        dm = build_day_model(schedule, day_index, day_scene_ids, prev_m, rules_dir=rules_dir)
    except Pass1ScopeError as exc:
        # Only the two documented scope cases land here. Registry corruption and parse
        # errors propagate, exactly as they do from the checker.
        return undetermined(f"out of scope for pass 1: {exc}", "NOT_RUN")

    # 1. base feasibility: rules unenforced
    base_status, _ = _solve_with(dm, [], time_limit_s)
    if base_status == "MODEL_INVALID":
        raise RuntimeError(f"pass 1 built an invalid CP-SAT model for day {day_index}: {dm.model.validate()}")
    if base_status == "UNKNOWN":
        return undetermined("time limit reached before the base model was decided", base_status)
    if base_status == "INFEASIBLE":
        return undetermined(
            "the scenes do not fit the crew window under the page-per-hour heuristic; "
            "no rule was consulted",
            base_status,
        )

    literals = dm.all_literals()
    rule_ids = sorted(dm.literals)

    # 2. full solve: every applicable rule assumed
    full_status, solver = _solve_with(dm, literals, time_limit_s)
    if full_status == "UNKNOWN":
        return undetermined("time limit reached before the legality model was decided", full_status)

    if full_status in ("OPTIMAL", "FEASIBLE"):
        tidy = build_day_model(schedule, day_index, day_scene_ids, prev_m, rules_dir=rules_dir, tidy_objective=True)
        tidy_status, tidy_solver = _solve_with(tidy, tidy.all_literals(), time_limit_s)
        if tidy_status in ("OPTIMAL", "FEASIBLE"):
            witness = _witness(tidy, tidy_solver, schedule)
        else:
            witness = _witness(dm, solver, schedule)
        feasible_table: dict[str, str] = dict.fromkeys(rule_ids, "FEASIBLE")
        leftovers = check_day_legality(schedule, day_index, rules_dir=rules_dir, timeline=_timeline(witness))
        if leftovers:
            return Pass1Result(
                verdict=Verdict(status="UNDETERMINED", day=day_index, violations=leftovers, core_rule_ids=[], witness=witness),
                solver_status=full_status,
                per_rule=feasible_table,
                note="solver found a timing the checker still flags: " + ", ".join(v.rule_id for v in leftovers),
            )
        return Pass1Result(
            verdict=Verdict(status="LEGAL", day=day_index, violations=[], core_rule_ids=[], witness=witness),
            solver_status=full_status,
            per_rule=feasible_table,
            note="a legal timing exists; witness checked by the independent checker",
        )

    # INFEASIBLE: CP-SAT's sufficient core, then one solve per rule
    if full_status != "INFEASIBLE":
        raise RuntimeError(f"unexpected full-solve status {full_status!r} for day {day_index}")
    index_to_id = {dm.literals[rid].index: rid for rid in rule_ids}
    raw_core = list(solver.sufficient_assumptions_for_infeasibility())
    unmapped = [i for i in raw_core if i not in index_to_id]
    if unmapped:
        raise RuntimeError(f"core indices are not rule literals: {unmapped}")
    sufficient_core = sorted(index_to_id[i] for i in raw_core)
    if not sufficient_core:
        raise RuntimeError(f"INFEASIBLE with a feasible base but an empty core on day {day_index}")

    per_rule: dict[str, str] = {}
    for rid in rule_ids:
        status, _ = _solve_with(dm, [dm.literals[rid]], time_limit_s)
        if status == "MODEL_INVALID":
            raise RuntimeError(f"per-rule solve for {rid} reports an invalid model")
        per_rule[rid] = "FEASIBLE" if status in ("OPTIMAL", "FEASIBLE") else status
    if any(s == "UNKNOWN" for s in per_rule.values()):
        return undetermined("time limit reached during per-rule solves", "UNKNOWN", per_rule=per_rule, sufficient_core=sufficient_core)

    individually = [rid for rid in rule_ids if per_rule[rid] == "INFEASIBLE"]
    if individually:
        core = individually
        note = "each listed rule alone makes this day impossible"
    else:
        core = sufficient_core
        note = "joint: no single rule makes this day impossible, these rules do together"

    if core and set(core) <= TIMING_ONLY_RULE_IDS:
        return Pass1Result(
            verdict=Verdict(status="UNDETERMINED", day=day_index, violations=[], core_rule_ids=list(core), witness=None),
            solver_status=full_status,
            individually_sufficient=individually,
            sufficient_core=sufficient_core,
            per_rule=per_rule,
            note="only timing-only rules fail (" + ", ".join(core) + "): no meal break fits; "
            "the crew-window checker cannot judge this, so the day is not proven either way",
        )

    violations = check_day_legality(schedule, day_index, rules_dir=rules_dir)
    return Pass1Result(
        verdict=Verdict(status="ILLEGAL", day=day_index, violations=violations, core_rule_ids=list(core), witness=None),
        solver_status=full_status,
        individually_sufficient=individually,
        sufficient_core=sufficient_core,
        per_rule=per_rule,
        note=note,
    )


def pass1_schedule(
    schedule: ScheduleInput,
    day_scene_ids: dict[int, list[str]] | None = None,
    time_limit_s: float = 10.0,
    rules_dir: Path | None = None,
) -> list[Pass1Result]:
    """Pass 1 over every day. Days are independent: turnaround uses the previous day's crew wrap."""
    results: list[Pass1Result] = []
    for i in range(len(schedule.days)):
        if day_scene_ids is None:
            ids = None
        elif i in day_scene_ids:
            ids = day_scene_ids[i]
        else:
            raise KeyError(f"pass1_schedule: no scene list for day {i}; an empty list must be explicit")
        results.append(pass1_day(schedule, i, day_scene_ids=ids, time_limit_s=time_limit_s, rules_dir=rules_dir))
    return results
