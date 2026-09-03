"""
Task 2.8: pass 2, the cost pass (PLAN.md D2, D3, D13).

Order and day assignment are free; scene starts and each minor's call and dismissal are
free inside each day's crew window; every child-performer rule is a plain hard constraint,
so the solver structurally cannot emit an illegal schedule; the objective is hold-day cost
in integer cents. The result is re-judged day by day by pass 1 and recounted by plain Python.

Hold days, as this model defines them: shoot days listed in the schedule that fall between a
cast member's first and last working day on which that member does not work. A hold day is
PAID (and therefore minimized) when the production is on an overnight location (the
low-budget agreements pay consecutive employment only there, rules/sag_rates.yaml
SAG_RATES_CONSECUTIVE_EMPLOYMENT_LOW_BUDGET) or the member's rate tier is "other", which
HOLD reads as the Basic Agreement. Otherwise hold days are counted but cost nothing, and the
outcome says so. Cost per paid hold day is the tier's day rate plus P&H for that date
(api/hold/penalties.py). total_cents = working days plus paid hold days at the same rate.

Optimality is reported as CP-SAT reports it (OPTIMAL, or FEASIBLE with the bound); D3 keeps
that separate from the benchmark residual. INFEASIBLE re-solves with rule literals as
assumptions and returns UNDETERMINED with the rule ids as reasons.
"""
from __future__ import annotations

import os
import time as _time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from ortools.sat.python import cp_model

from api.hold.legality import MEAL_MINUTES_DEFAULT, minutes_of, scene_minutes
from api.hold.legality_checker import (
    age_applies,
    curfew_limit_minutes,
    earliest_call_applies,
    is_minor,
    rule_applies_to_minor,
    school_night,
    turnaround_applies,
    work_cap_hours,
)
from api.hold.penalties import hold_day_cost_cents
from api.hold.registry import RuleRecord, load_rules
from api.hold.schemas import CheckerResult, Pass2Result, ScheduleInput, SolveResult
from api.hold.solve import Pass1Result, pass1_schedule

_RULES_DIR = Path(__file__).parent.parent.parent / "rules"
_BIG = 1440


@dataclass
class Pass2Outcome:
    result: Pass2Result
    day_scene_ids: dict[int, list[str]]
    pass1: list[Pass1Result]
    checker: CheckerResult
    paid_hold_days: bool
    solve_ms: float
    note: str


# ---------------------------------------------------------------------------
# Plain-Python helpers (also the independent recount, D13)
# ---------------------------------------------------------------------------


def hold_days_paid(schedule: ScheduleInput) -> dict[str, bool]:
    """Per cast member: are intervening days compensable under their agreement?"""
    return {c.id: bool(schedule.overnight_location or c.rate_tier == "other") for c in schedule.cast}


def pack_order_into_days(schedule: ScheduleInput, order: list[str]) -> dict[int, list[str]]:
    """Greedy day packing of a fixed scene order by the page-per-hour heuristic: fill each day's
    window in turn; a scene that does not fit opens the next day; the last day takes the rest."""
    durations = {s.id: scene_minutes(s.pages_eighths) for s in schedule.scenes}
    packed: dict[int, list[str]] = {}
    d, used, last = 0, 0, len(schedule.days) - 1
    for sid in order:
        dur = durations[sid]
        window = minutes_of(schedule.days[d].wrap) - minutes_of(schedule.days[d].call)
        while d < last and used > 0 and used + dur > window:
            d, used = d + 1, 0
            window = minutes_of(schedule.days[d].wrap) - minutes_of(schedule.days[d].call)
        packed.setdefault(d, []).append(sid)
        used += dur
    return packed


def recount_hold_days(schedule: ScheduleInput, day_scene_ids: dict[int, list[str]]) -> dict[str, list[date]]:
    """Per cast member, the scheduled shoot dates between their first and last working date on
    which they do not work. Plain Python, no solver."""
    scenes_by_id = {s.id: s for s in schedule.scenes}
    out: dict[str, list[date]] = {}
    for c in schedule.cast:
        worked = sorted({
            schedule.days[d].date
            for d, ids in day_scene_ids.items()
            for sid in ids
            if c.id in scenes_by_id[sid].cast_ids
        })
        if len(worked) < 2:
            out[c.id] = []
            continue
        first, last = worked[0], worked[-1]
        worked_set = set(worked)
        out[c.id] = [day.date for day in schedule.days if first < day.date < last and day.date not in worked_set]
    return out


def _day_cost_table(schedule: ScheduleInput, rules_dir: Path) -> dict[str, list[int]]:
    """cents per cast member per day index: day rate plus P&H for that date."""
    return {c.id: [hold_day_cost_cents(c, day.date, rules_dir) for day in schedule.days] for c in schedule.cast}


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


@dataclass
class _Model:
    model: cp_model.CpModel
    pos: list[Any]
    scene_at: list[Any]
    x: list[list[Any]]
    start: list[Any]
    pres: dict[str, list[Any]]
    hold: dict[str, list[Any]]
    literals: dict[str, Any]
    cost: dict[str, list[int]]
    paid: dict[str, bool]


def _build(schedule: ScheduleInput, rules: list[RuleRecord], rules_dir: Path, explain: bool) -> _Model:
    m = cp_model.CpModel()
    scenes = schedule.scenes
    days = schedule.days
    n, D = len(scenes), len(days)
    idx = {s.id: i for i, s in enumerate(scenes)}
    dur = [scene_minutes(s.pages_eighths) for s in scenes]
    win = [(minutes_of(day.call), minutes_of(day.wrap)) for day in days]
    for d, (call_m, wrap_m) in enumerate(win):
        if wrap_m <= call_m:
            raise ValueError(f"day {d}: wrap at or before call; same-day windows only")

    pos = [m.new_int_var(0, n - 1, f"pos_{i}") for i in range(n)]
    scene_at = [m.new_int_var(0, n - 1, f"sat_{p}") for p in range(n)]
    m.add_inverse(pos, scene_at)
    m.add_all_different(pos)

    x = [[m.new_bool_var(f"x_{i}_{d}") for d in range(D)] for i in range(n)]
    day_of = [m.new_int_var(0, D - 1, f"day_{i}") for i in range(n)]
    start = [m.new_int_var(0, _BIG - 1, f"start_{i}") for i in range(n)]
    iv: list[list[Any]] = []
    for i in range(n):
        m.add_exactly_one(x[i])
        m.add(day_of[i] == sum(d * x[i][d] for d in range(D)))
        ivrow: list[Any] = []
        for d in range(D):
            m.add(start[i] >= win[d][0]).only_enforce_if(x[i][d])
            m.add(start[i] + dur[i] <= win[d][1]).only_enforce_if(x[i][d])
            ivrow.append(m.new_optional_fixed_size_interval_var(start[i], dur[i], x[i][d], f"iv_{i}_{d}"))
        iv.append(ivrow)

    meal_minutes = max(
        [int(r.params.get("min_meal_duration_minutes", MEAL_MINUTES_DEFAULT)) for r in rules if "max_work_before_meal_hours" in r.params]
        or [MEAL_MINUTES_DEFAULT]
    )
    meal_present = [m.new_bool_var(f"meal_{d}") for d in range(D)]
    meal_start = [m.new_int_var(0, _BIG - 1, f"meal_start_{d}") for d in range(D)]
    for d in range(D):
        m.add(meal_start[d] >= win[d][0])
        m.add(meal_start[d] + meal_minutes <= win[d][1])
        meal_iv = m.new_optional_fixed_size_interval_var(meal_start[d], meal_minutes, meal_present[d], f"meal_iv_{d}")
        m.add_no_overlap([iv[i][d] for i in range(n)] + [meal_iv])

    # Position order and day order agree; same-day scenes keep position order in time.
    for i in range(n):
        for k in range(i + 1, n):
            before = m.new_bool_var(f"before_{i}_{k}")
            m.add(pos[i] < pos[k]).only_enforce_if(before)
            m.add(pos[i] > pos[k]).only_enforce_if(before.negated())
            m.add(day_of[i] <= day_of[k]).only_enforce_if(before)
            m.add(day_of[k] <= day_of[i]).only_enforce_if(before.negated())
            same = m.new_bool_var(f"same_{i}_{k}")
            m.add(day_of[i] == day_of[k]).only_enforce_if(same)
            m.add(day_of[i] != day_of[k]).only_enforce_if(same.negated())
            m.add(start[i] + dur[i] <= start[k]).only_enforce_if([same, before])
            m.add(start[k] + dur[k] <= start[i]).only_enforce_if([same, before.negated()])

    # Declared constraints
    for cons in schedule.constraints:
        if cons.type == "precedence" and cons.scene_id_a and cons.scene_id_b:
            m.add(pos[idx[cons.scene_id_a]] < pos[idx[cons.scene_id_b]])
        elif cons.type == "availability" and cons.scene_id_a and cons.unavailable_day_indices and not cons.cast_id:
            for d in cons.unavailable_day_indices:
                m.add(x[idx[cons.scene_id_a]][d] == 0)
        elif cons.type == "availability" and cons.cast_id and cons.unavailable_day_indices:
            for i, s in enumerate(scenes):
                if cons.cast_id in s.cast_ids:
                    for d in cons.unavailable_day_indices:
                        m.add(x[i][d] == 0)

    # Presence per cast member per day
    pres: dict[str, list[Any]] = {}
    for member in schedule.cast:
        own = [i for i, s in enumerate(scenes) if member.id in s.cast_ids]
        prow: list[Any] = [m.new_bool_var(f"p_{member.id}_{d}") for d in range(D)]
        for d in range(D):
            if own:
                m.add_max_equality(prow[d], [x[i][d] for i in own])
            else:
                m.add(prow[d] == 0)
        pres[member.id] = prow

    # Rules, gated by presence (and by a rule literal when explaining)
    literals: dict[str, Any] = {}

    def lit(rule_id: str) -> Any:
        if rule_id not in literals:
            literals[rule_id] = m.new_bool_var(rule_id)
        return literals[rule_id]

    def gate(conds: list[Any], rule_id: str, ct: Any) -> None:
        enforce = list(conds) + ([lit(rule_id)] if explain else [])
        c = m.add(ct)
        if enforce:
            c.only_enforce_if(enforce)

    shoot_state = schedule.jurisdiction.shoot_state
    runs: list[list[int]] = []
    for d in range(D):
        if runs and (days[d].date - days[runs[-1][-1]].date).days == 1:
            runs[-1].append(d)
        else:
            runs.append([d])

    for member in schedule.cast:
        if not is_minor(member):
            continue
        own = [i for i, s in enumerate(scenes) if member.id in s.cast_ids]
        if not own:
            continue
        assert member.age is not None
        call = [m.new_int_var(0, 2 * _BIG, f"call_{member.id}_{d}") for d in range(D)]
        dismiss = [m.new_int_var(-_BIG, _BIG, f"dismiss_{member.id}_{d}") for d in range(D)]
        work = [sum(dur[i] * x[i][d] for i in own) for d in range(D)]
        for d in range(D):
            m.add_min_equality(call[d], [start[i] + _BIG - _BIG * x[i][d] for i in own])
            m.add_max_equality(dismiss[d], [start[i] + dur[i] - _BIG + _BIG * x[i][d] for i in own])
        applicable = [r for r in rules if rule_applies_to_minor(r, member, shoot_state) and age_applies(r, member.age)]
        for r in applicable:
            params = r.params
            if "max_consecutive_days" in params:
                limit = int(params["max_consecutive_days"])
                for run in runs:
                    for s0 in range(0, len(run) - limit):
                        window = run[s0 : s0 + limit + 1]
                        gate([], r.id, sum(pres[member.id][d] for d in window) <= limit)
        for d in range(D):
            sd = days[d]
            isn, _assumed = school_night(schedule, d)
            p = pres[member.id][d]
            consecutive_prev = d > 0 and (sd.date - days[d - 1].date).days == 1
            for r in applicable:
                params = r.params
                curfew = curfew_limit_minutes(r, isn)
                if curfew is not None:
                    gate([p], r.id, dismiss[d] <= curfew)
                if earliest_call_applies(r, isn):
                    hh, mm = map(int, str(params["earliest_call"]).split(":"))
                    gate([p], r.id, call[d] >= hh * 60 + mm)
                if "max_location_hours" in params:
                    gate([p], r.id, dismiss[d] - call[d] <= int(float(params["max_location_hours"]) * 60))
                cap = work_cap_hours(r, sd.school_day)
                if cap is not None:
                    gate([], r.id, work[d] <= int(cap * 60))
                if "min_turnaround_hours" in params and turnaround_applies(r.id, sd.school_day) and consecutive_prev:
                    req = int(float(params["min_turnaround_hours"]) * 60)
                    gate([p, pres[member.id][d - 1]], r.id, call[d] >= dismiss[d - 1] - _BIG + req)
                if "max_work_before_meal_hours" in params:
                    limit = int(float(params["max_work_before_meal_hours"]) * 60)
                    next_from_start = params.get("next_meal_within_hours_of_previous_start")
                    needs = m.new_bool_var(f"needs_meal_{member.id}_{d}")
                    m.add(dismiss[d] - call[d] > limit).only_enforce_if(needs)
                    m.add(dismiss[d] - call[d] <= limit).only_enforce_if(needs.negated())
                    gate([needs], r.id, meal_present[d] == 1)
                    gate([needs], r.id, meal_start[d] >= call[d])
                    gate([needs], r.id, meal_start[d] <= call[d] + limit)
                    gate([needs], r.id, meal_start[d] + meal_minutes <= dismiss[d])
                    if next_from_start is not None:
                        gate([needs], r.id, dismiss[d] - meal_start[d] <= int(float(next_from_start) * 60))
                    else:
                        gate([needs], r.id, dismiss[d] - (meal_start[d] + meal_minutes) <= limit)

    # Hold days and cost
    paid = hold_days_paid(schedule)
    cost = _day_cost_table(schedule, rules_dir)
    hold: dict[str, list[Any]] = {}
    obj_terms: list[Any] = []
    for member in schedule.cast:
        present: list[Any] = pres[member.id]
        first_seen: list[Any] = [m.new_bool_var(f"seen_{member.id}_{d}") for d in range(D)]   # worked on or before d
        last_seen: list[Any] = [m.new_bool_var(f"ahead_{member.id}_{d}") for d in range(D)]   # works on or after d
        for d in range(D):
            m.add_max_equality(first_seen[d], present[: d + 1])
            m.add_max_equality(last_seen[d], present[d:])
        holds: list[Any] = []
        for d in range(D):
            h = m.new_bool_var(f"hold_{member.id}_{d}")
            m.add_bool_and([first_seen[d], last_seen[d], present[d].negated()]).only_enforce_if(h)
            m.add_bool_or([first_seen[d].negated(), last_seen[d].negated(), present[d]]).only_enforce_if(h.negated())
            holds.append(h)
            if paid[member.id] and cost[member.id][d] > 0:
                obj_terms.append(cost[member.id][d] * h)
        hold[member.id] = holds
    m.minimize(cp_model.LinearExpr.sum(obj_terms) if obj_terms else 0)
    return _Model(model=m, pos=pos, scene_at=scene_at, x=x, start=start, pres=pres, hold=hold, literals=literals, cost=cost, paid=paid)


OnSolution = Callable[[int, int, float], None]


class _Progress(cp_model.CpSolverSolutionCallback):
    """Reports each improving solution: objective value, best bound, wall time in ms."""

    def __init__(self, on_solution: OnSolution) -> None:
        super().__init__()
        self._on_solution = on_solution

    def on_solution_callback(self) -> None:
        self._on_solution(int(self.objective_value), int(self.best_objective_bound), self.wall_time * 1000.0)


def _solve(
    mm: _Model, time_limit_s: float, num_workers: int, assumptions: list[Any] | None = None, on_solution: OnSolution | None = None
) -> tuple[str, cp_model.CpSolver]:
    mm.model.clear_assumptions()
    if assumptions:
        mm.model.add_assumptions(assumptions)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_s
    solver.parameters.num_workers = num_workers
    callback = _Progress(on_solution) if on_solution is not None else None
    return solver.status_name(solver.solve(mm.model, callback)), solver


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def pass2(
    schedule: ScheduleInput,
    rules_dir: Path | None = None,
    time_limit_s: float = 60.0,
    num_workers: int | None = None,
    on_solution: OnSolution | None = None,
) -> Pass2Outcome:
    """Solve pass 2, then re-judge every used day with pass 1 and recount the hold days.
    on_solution, when given, hears every improving solution (value, bound, ms) from the solver thread."""
    rules_dir = rules_dir or _RULES_DIR
    workers = num_workers or (os.cpu_count() or 8)
    rules = load_rules(rules_dir)
    D = len(schedule.days)
    paid_any = any(hold_days_paid(schedule).values())
    t0 = _time.perf_counter()

    def undetermined(reasons: list[str], note: str) -> Pass2Outcome:
        return Pass2Outcome(
            result=Pass2Result(order=[], status="UNDETERMINED", holding_cents=0, total_cents=0, bound=0, hold_days=0, penalties_cents=0, reasons=reasons),
            day_scene_ids={},
            pass1=[],
            checker=CheckerResult(agrees=False, note=note),
            paid_hold_days=paid_any,
            solve_ms=(_time.perf_counter() - t0) * 1000.0,
            note=note,
        )

    try:
        mm = _build(schedule, rules, rules_dir, explain=False)
    except ValueError as exc:
        return undetermined(["window"], f"out of scope: {exc}")
    status, solver = _solve(mm, time_limit_s, workers, on_solution=on_solution)

    if status == "UNKNOWN":
        return undetermined(["time limit"], "time limit reached before a schedule was decided")
    if status == "MODEL_INVALID":
        raise RuntimeError(f"pass 2 built an invalid model: {mm.model.validate()}")
    if status == "INFEASIBLE":
        # explain: rules as assumptions, one literal per rule id
        mx = _build(schedule, rules, rules_dir, explain=True)
        base_status, _ = _solve(mx, time_limit_s, workers)
        if base_status == "INFEASIBLE":
            return undetermined(["window"], "the scenes do not fit the available day windows under the page-per-hour heuristic; no rule was consulted")
        lits = [mx.literals[k] for k in sorted(mx.literals)]
        full_status, sx = _solve(mx, time_limit_s, workers, assumptions=lits)
        if full_status != "INFEASIBLE":
            return undetermined(["time limit"], "the explanation solve did not finish")
        index_to_id = {v.index: k for k, v in mx.literals.items()}
        core = sorted(index_to_id[i] for i in sx.sufficient_assumptions_for_infeasibility() if i in index_to_id)
        return undetermined(core, "no legal schedule exists on these days; the listed rules are a sufficient reason")

    n = len(schedule.scenes)
    order = [int(solver.value(mm.scene_at[p])) for p in range(n)]
    day_scene_ids: dict[int, list[str]] = {}
    for d in range(D):
        on_day = [i for i in range(n) if int(solver.value(mm.x[i][d])) == 1]
        on_day.sort(key=lambda i: int(solver.value(mm.start[i])))
        if on_day:
            day_scene_ids[d] = [schedule.scenes[i].id for i in on_day]

    hold_days = 0
    holding = 0
    fixed = 0
    for member in schedule.cast:
        for d in range(D):
            if int(solver.value(mm.hold[member.id][d])) == 1:
                hold_days += 1
                if mm.paid[member.id]:
                    holding += mm.cost[member.id][d]
            if int(solver.value(mm.pres[member.id][d])) == 1:
                fixed += mm.cost[member.id][d]
    result = Pass2Result(
        order=order,
        status="OPTIMAL" if status == "OPTIMAL" else "FEASIBLE",
        holding_cents=holding,
        total_cents=holding + fixed,
        bound=int(round(solver.best_objective_bound)),
        hold_days=hold_days,
        penalties_cents=0,
        reasons=[],
    )

    full_map = {d: day_scene_ids.get(d, []) for d in range(D)}
    verdicts = pass1_schedule(schedule, day_scene_ids=full_map, time_limit_s=max(10.0, time_limit_s / 4), rules_dir=rules_dir)
    used = [v for v in verdicts if day_scene_ids.get(v.verdict.day)]
    all_legal = all(v.verdict.status == "LEGAL" for v in used)
    recount = recount_hold_days(schedule, day_scene_ids)
    recount_days = sum(len(v) for v in recount.values())
    recount_cents = 0
    for cid, dates in recount.items():
        if mm.paid[cid]:
            by_date = {schedule.days[d].date: mm.cost[cid][d] for d in range(D)}
            recount_cents += sum(by_date[dt] for dt in dates)
    agrees = all_legal and recount_days == hold_days and recount_cents == holding
    notes = []
    if not all_legal:
        notes.append("pass 1 does not confirm every used day: " + ", ".join(f"day {v.verdict.day} {v.verdict.status}" for v in used if v.verdict.status != "LEGAL"))
    if recount_days != hold_days or recount_cents != holding:
        notes.append(f"recount {recount_days} hold days / {recount_cents} cents vs solver {hold_days} / {holding}")
    if not paid_any:
        notes.append("hold days are not paid on this schedule (no overnight location, low-budget tiers), so they are counted but cost nothing")
    note = "; ".join(notes) if notes else "pass 1 confirms every used day and the recount matches"
    return Pass2Outcome(
        result=result,
        day_scene_ids=day_scene_ids,
        pass1=verdicts,
        checker=CheckerResult(agrees=agrees, note=note),
        paid_hold_days=paid_any,
        solve_ms=(_time.perf_counter() - t0) * 1000.0,
        note=note,
    )


def to_solve_result(outcome: Pass2Outcome) -> SolveResult:
    """The contract object Deem renders: per-day pass-1 verdicts, the pass-2 panel, the agreement flag."""
    return SolveResult(pass1=[p.verdict for p in outcome.pass1], pass2=outcome.result, checker=outcome.checker, benchmark=None)
