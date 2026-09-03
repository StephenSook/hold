"""
Task 2.7: pass-1 legality model for HOLD (CP-SAT with named rule assumptions).

Semantics (PLAN.md 2.7, private plan section 5): the scene order and the day assignment are
FIXED; scene start times, each minor's call and dismissal, and one crew meal break are FREE
inside the day's crew window. Every applicable rule record becomes a hard constraint gated
by a BoolVar named after the rule id. The solver (api/hold/solve.py) assumes those literals
and asks CP-SAT which of them make the day impossible.

Timing model, in integer minutes since midnight:
- Each scene k on the day gets start_k in [call, wrap - dur_k], end_k = start_k + dur_k,
  and the fixed order end_k <= start_{k+1}.
- Scene minutes come from the page-per-hour heuristic: ceil(pages_eighths * 15 / 2).
  That is PLAN.md D16, a labeled heuristic, never a fact.
- One optional 30-minute crew meal interval that overlaps no scene.
- Per minor with a scene on the day: call = min(own starts), dismiss = max(own ends),
  work = sum(own durations), a constant once the scene list is fixed.

Rule constraints (applicability shared with the checker through its public predicates):
- max_location_hours: dismiss - call <= H * 60
- work caps (school-day and non-school-day key selection): work <= cap, a constant test
- evening curfews: dismiss <= curfew; post-midnight curfews never bind a same-day wrap
- earliest_call: call >= 05:00, on the record matching the night type
- min_turnaround_hours: call >= prev_dismissal - 1440 + H * 60, GA and SAG on school days,
  CA always, and only when the previous shoot day is the previous calendar date
- max_consecutive_days: a constant test on the run of consecutive shoot dates
- max_work_before_meal_hours (CA 11761): a span over the limit requires the meal to be
  present, to start within the limit of the call, and to sit inside the span

Out of scope for pass 1 (stated so nobody assumes them): wraps past midnight (rejected as
UNDETERMINED upstream), more than one meal per day (two minors whose calls differ by more
than six hours can only satisfy the meal rule together if one break fits both), turnaround
measured from the previous day's crew wrap whether or not the minor worked it (the same
assumption the checker makes), the CA 48-hour weekly cap, rate records (no scheduling
params), and the display-only ids (ratios, chaperones, infants).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import time
from pathlib import Path
from typing import Any

from ortools.sat.python import cp_model

from api.hold.legality_checker import (
    age_applies,
    build_day_context,
    curfew_limit_minutes,
    earliest_call_applies,
    rule_applies_to_minor,
    turnaround_applies,
    work_cap_hours,
)
from api.hold.registry import RuleRecord, load_rules
from api.hold.schemas import ScheduleInput

HEURISTIC_NOTE = "scene minutes = ceil(pages_eighths * 15 / 2), one page per hour (PLAN.md D16 heuristic)"


class Pass1ScopeError(ValueError):
    """The input is outside what pass 1 models (not a data error, not a solver error)."""
MEAL_MINUTES_DEFAULT = 30

_RULES_DIR = Path(__file__).parent.parent.parent / "rules"


def scene_minutes(pages_eighths: int) -> int:
    """Page-per-hour heuristic (D16): 8 eighths = 60 minutes; odd eighths round up."""
    return math.ceil(pages_eighths * 15 / 2)


def minutes_of(t: time) -> int:
    return t.hour * 60 + t.minute


@dataclass
class MinorVars:
    cast_id: str
    age: int
    call: Any            # IntVar
    dismiss: Any         # IntVar
    work_minutes: int
    scene_ids: list[str]


@dataclass
class DayModel:
    """One day's CP-SAT model plus the handles the solver needs to read it back."""

    model: cp_model.CpModel
    day_index: int
    call_m: int
    wrap_m: int
    scene_ids: list[str]
    durations: dict[str, int]
    starts: dict[str, Any]                 # scene id -> IntVar
    minors: dict[str, MinorVars]           # cast id -> vars
    literals: dict[str, Any]               # rule id -> BoolVar (one per applicable rule)
    meal_present: Any                      # BoolVar
    meal_start: Any                        # IntVar
    meal_minutes: int
    notes: list[str] = field(default_factory=list)

    def all_literals(self) -> list[Any]:
        return [self.literals[k] for k in sorted(self.literals)]


def _gate(model: cp_model.CpModel, lit: Any, cond: Any) -> None:
    """Add `cond` enforced only when `lit` is true. `cond` may be a Python bool (constant
    test): CpModel.add turns False into an enforced empty clause, which is exactly the
    'this rule alone is impossible' encoding."""
    model.add(cond).only_enforce_if(lit)


def build_day_model(
    schedule: ScheduleInput,
    day_index: int,
    day_scene_ids: list[str],
    prev_dismissal_minutes: int | None,
    rules_dir: Path | None = None,
    tidy_objective: bool = False,
) -> DayModel:
    """
    Build the pass-1 model for one day.

    prev_dismissal_minutes: the previous consecutive calendar day's dismissal (crew wrap by
    default), or None when there is no previous consecutive shoot day.
    tidy_objective: add a small objective (earliest starts, shortest minor spans, no
    unneeded meal) so a FEASIBLE witness reads like a call sheet. The verdict never
    depends on it.
    """
    if rules_dir is None:
        rules_dir = _RULES_DIR
    day = schedule.days[day_index]
    call_m = minutes_of(day.call)
    wrap_m = minutes_of(day.wrap)
    if wrap_m <= call_m:
        raise Pass1ScopeError("wrap at or before call: same-day windows only in pass 1")

    scenes_by_id = {s.id: s for s in schedule.scenes}
    unknown = [sid for sid in day_scene_ids if sid not in scenes_by_id]
    if unknown:
        raise Pass1ScopeError(f"unknown scene ids for day {day_index}: {unknown}")

    model = cp_model.CpModel()
    durations: dict[str, int] = {}
    starts: dict[str, Any] = {}
    intervals: list[Any] = []
    prev_start: Any = None
    prev_dur = 0
    for sid in day_scene_ids:
        dur = scene_minutes(scenes_by_id[sid].pages_eighths)
        durations[sid] = dur
        start = model.new_int_var(call_m, wrap_m, f"start_{sid}")
        model.add(start + dur <= wrap_m)
        if prev_start is not None:
            model.add(prev_start + prev_dur <= start)
        intervals.append(model.new_fixed_size_interval_var(start, dur, f"iv_{sid}"))
        starts[sid] = start
        prev_start, prev_dur = start, dur

    meal_minutes = MEAL_MINUTES_DEFAULT
    meal_present = model.new_bool_var("meal_present")
    meal_start = model.new_int_var(call_m, max(call_m, wrap_m - meal_minutes), "meal_start")
    meal_iv = model.new_optional_fixed_size_interval_var(meal_start, meal_minutes, meal_present, "iv_meal")
    model.add_no_overlap([*intervals, meal_iv])

    # Minor variables
    minors: dict[str, MinorVars] = {}
    for member in schedule.cast:
        if member.age is None:
            continue
        own = [sid for sid in day_scene_ids if member.id in scenes_by_id[sid].cast_ids]
        if not own:
            continue
        call_v = model.new_int_var(call_m, wrap_m, f"call_{member.id}")
        dismiss_v = model.new_int_var(call_m, wrap_m, f"dismiss_{member.id}")
        model.add_min_equality(call_v, [starts[sid] for sid in own])
        model.add_max_equality(dismiss_v, [starts[sid] + durations[sid] for sid in own])
        minors[member.id] = MinorVars(
            cast_id=member.id,
            age=member.age,
            call=call_v,
            dismiss=dismiss_v,
            work_minutes=sum(durations[sid] for sid in own),
            scene_ids=own,
        )

    dm = DayModel(
        model=model,
        day_index=day_index,
        call_m=call_m,
        wrap_m=wrap_m,
        scene_ids=list(day_scene_ids),
        durations=durations,
        starts=starts,
        minors=minors,
        literals={},
        meal_present=meal_present,
        meal_start=meal_start,
        meal_minutes=meal_minutes,
    )

    if minors:
        ctx = build_day_context(schedule, day_index)
        rules = load_rules(rules_dir, shooting_date=day.date)
        shoot_state = schedule.jurisdiction.shoot_state
        cast_by_id = {c.id: c for c in schedule.cast}
        for mv in minors.values():
            member = cast_by_id[mv.cast_id]
            for rule in rules:
                if not rule_applies_to_minor(rule, member, shoot_state):
                    continue
                if not age_applies(rule, mv.age):
                    continue
                _add_rule_constraints(
                    dm,
                    rule,
                    mv,
                    is_school_night=ctx.is_school_night,
                    school_day=day.school_day,
                    consecutive_run=ctx.consecutive_run,
                    prev_dismissal_minutes=prev_dismissal_minutes,
                )

    if tidy_objective:
        terms: list[Any] = [starts[sid] for sid in day_scene_ids]
        terms.extend(mv.dismiss - mv.call for mv in minors.values())
        terms.append(meal_minutes * meal_present)
        if terms:
            model.minimize(cp_model.LinearExpr.sum(terms))
    return dm


def _literal(dm: DayModel, rule_id: str) -> Any:
    lit = dm.literals.get(rule_id)
    if lit is None:
        lit = dm.model.new_bool_var(rule_id)
        dm.literals[rule_id] = lit
    return lit


def _add_rule_constraints(
    dm: DayModel,
    rule: RuleRecord,
    mv: MinorVars,
    *,
    is_school_night: bool,
    school_day: bool,
    consecutive_run: int,
    prev_dismissal_minutes: int | None,
) -> None:
    """Every constraint one rule record imposes on one minor, gated by the rule's literal."""
    model = dm.model
    params = rule.params

    curfew = curfew_limit_minutes(rule, is_school_night)
    if curfew is not None:
        _gate(model, _literal(dm, rule.id), mv.dismiss <= curfew)

    if earliest_call_applies(rule, is_school_night):
        hh, mm = map(int, str(params["earliest_call"]).split(":"))
        _gate(model, _literal(dm, rule.id), mv.call >= hh * 60 + mm)

    if "max_location_hours" in params:
        _gate(model, _literal(dm, rule.id), mv.dismiss - mv.call <= int(float(params["max_location_hours"]) * 60))

    cap = work_cap_hours(rule, school_day)
    if cap is not None:
        _gate(model, _literal(dm, rule.id), mv.work_minutes <= int(cap * 60))

    if (
        "min_turnaround_hours" in params
        and turnaround_applies(rule.id, school_day)
        and prev_dismissal_minutes is not None
    ):
        required = int(float(params["min_turnaround_hours"]) * 60)
        _gate(model, _literal(dm, rule.id), mv.call >= prev_dismissal_minutes - 1440 + required)

    if "max_consecutive_days" in params:
        _gate(model, _literal(dm, rule.id), consecutive_run <= int(params["max_consecutive_days"]))

    if "max_work_before_meal_hours" in params:
        limit = int(float(params["max_work_before_meal_hours"]) * 60)
        lit = _literal(dm, rule.id)
        needs_meal = model.new_bool_var(f"needs_meal_{mv.cast_id}")
        model.add(mv.dismiss - mv.call > limit).only_enforce_if(needs_meal)
        model.add(mv.dismiss - mv.call <= limit).only_enforce_if(needs_meal.negated())
        model.add_implication(needs_meal, dm.meal_present).only_enforce_if(lit)
        model.add(dm.meal_start >= mv.call).only_enforce_if([lit, needs_meal])
        model.add(dm.meal_start <= mv.call + limit).only_enforce_if([lit, needs_meal])
        model.add(dm.meal_start + dm.meal_minutes <= mv.dismiss).only_enforce_if([lit, needs_meal])
