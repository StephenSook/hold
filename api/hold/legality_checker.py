"""
Task 2.9: Legality violation enumerator for HOLD.

Plain Python, no OR-Tools. Enumerates EVERY violated rule for every shoot day
against child-performer statutes and SAG-AFTRA rules. This is the source of
truth for the verdict card per PLAN.md Decision D13.

What can be checked from ScheduleInput alone (no scene-level times):
- Location hours: wrap - call (total time at the place of employment)
- Work hours: conservative proxy = location hours (no scene-level times in pass 2.9)
  The checker labels these "location hours" in violation records so the UI can show
  the proxy clearly. Pass 1 (task 2.7) checks with exact solver-assigned call times.
- Curfew: does wrap time exceed the statutory limit?
- Earliest call: does call time precede 5 am?
- Turnaround: hours between previous wrap and current call
- Consecutive days: how many days in a row the minor was on set

Jurisdiction logic (D5, cumulative):
- GA rules apply when shoot_state="GA" and the minor is in at least one scene that day.
- CA rules apply when the minor's resident_state="CA" (regardless of shoot state).
- SAG-AFTRA minor rules apply to ALL minors regardless of state.
- Where both GA and CA apply, the stricter limit governs.

Rules skipped (display facts only, not checkable from schedule timing alone):
- Studio teacher ratios (GA_300_7_1_09, CA_11755_1/2) - require headcount not in schema
- Child labor coordinator ratio (GA_300_7_1_04) - same
- Chaperone requirement (SAG_MINORS_2026_CHAPERONE_UNDER_16) - same
- Infant restriction (SAG_MINORS_P23) - no infant in demo; age check guards it
- CA weekly cap (CA_11760_e_weekly_cap_48_hours) - needs full week context

Concrete timeline (task 2.7): pass a DayTimeline to check a minor's own call, dismissal,
work minutes and meal instead of the crew-window proxy. Only then is the meal rule
(CA_11761_meal_period_6_hours) checked; the proxy path cannot see meals and never lists it.
A minor absent from the timeline was not on set that day and is skipped.

Turnaround is checked only when the previous shoot day is the previous calendar date.
The CA 1308.7 5 a.m. floor is checked on the record whose curfew matches the night type.
"""
from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass
from datetime import date, time
from pathlib import Path
from typing import NamedTuple

from api.hold.registry import RuleRecord, load_rules
from api.hold.schemas import CastMember, ScheduleInput, ShootDay, ViolationRecord

_RULES_DIR = Path(__file__).parent.parent.parent / "rules"

# Rules that can only be judged on a concrete timeline (never on the crew-window proxy).
# The pass-1 solver may name them in a core; the proxy checker never lists them.
TIMING_ONLY_RULE_IDS = frozenset({"CA_11761_meal_period_6_hours"})

# Rules that are display-only (ratios, chaperones) - never flagged as violations
DISPLAY_ONLY_RULE_IDS = frozenset({
    "GA_300_7_1_09_studio_teacher_ratio",
    "GA_300_7_1_04_coordinator_ratio",
    "CA_11755_1_studio_teacher_in_session",
    "CA_11755_2_studio_teacher_not_in_session",
    "SAG_MINORS_2026_CHAPERONE_UNDER_16",
    "SAG_MINORS_P23_INFANT_RESTRICTION",
    "SAG_MINORS_P17_CUMULATIVE_JURISDICTION",
    "CA_11760_e_weekly_cap_48_hours",
    "CA_DLSE_SUBTRACT_6_POLICY",
})


@dataclass(frozen=True)
class MinorTimeline:
    """One minor's concrete times on one shoot day (from a pass-1 witness or a call sheet)."""

    call: time
    dismiss: time
    work_minutes: int
    meal_start: time | None = None
    meal_end: time | None = None


@dataclass(frozen=True)
class DayTimeline:
    """Per-minor timelines for one day. A minor absent from `minors` was not on set."""

    minors: Mapping[str, MinorTimeline]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _time_to_minutes(t: time) -> int:
    """Convert time to minutes since midnight. Result is in [0, 1439]."""
    return t.hour * 60 + t.minute


def _minutes_to_time_str(m: int) -> str:
    """Format minutes since midnight as HH:MM string."""
    m = m % 1440  # wrap at midnight
    return f"{m // 60:02d}:{m % 60:02d}"


def _duration_hours(start: time, end: time) -> float:
    """
    Hours from start to end, assuming end >= start (same day, no wrap-around).
    Used for location hours = wrap - call.
    """
    return (_time_to_minutes(end) - _time_to_minutes(start)) / 60.0


def _turnaround_hours(prev_wrap: time, next_call: time) -> float:
    """
    Hours between previous day wrap and next day call.
    Assumes prev_wrap is on day N and next_call is on day N+1.
    Turnaround = (24h - wrap_minutes_since_midnight) + call_minutes_since_midnight.
    """
    wrap_m = _time_to_minutes(prev_wrap)
    call_m = _time_to_minutes(next_call)
    return (1440 - wrap_m + call_m) / 60.0


def is_minor(member: CastMember) -> bool:
    """A cast member with a recorded age under 18. Adults may carry an age on file."""
    return member.age is not None and member.age < 18


def consecutive_run(worked: Collection[date], today: date) -> int:
    """How many consecutive calendar dates ending today the minor worked (today counts as 1)."""
    run = 1
    d = today
    while True:
        prev = date.fromordinal(d.toordinal() - 1)
        if prev in worked:
            run += 1
            d = prev
        else:
            return run


class DayContext(NamedTuple):
    """Preprocessed context for one shoot day check."""
    day_index: int
    shoot_day: ShootDay
    location_hours: float
    is_school_night: bool  # next day is a school day (curfew and turnaround trigger)
    prev_wrap: time | None  # previous consecutive shoot day wrap, None if first day
    consecutive_run: int  # how many consecutive shoot days ending on this day


def build_day_context(
    schedule: ScheduleInput, day_index: int, prev_dismissal: time | None = None
) -> DayContext:
    """prev_dismissal overrides the previous consecutive calendar day's crew wrap when the
    caller knows yesterday's real dismissal (the solver threads the same value through)."""
    days = schedule.days
    sd = days[day_index]
    loc_hours = _duration_hours(sd.call, sd.wrap)

    # Is the following calendar day a school day? (curfew trigger)
    # Check if next shoot day is a school day, OR if day_index+1 exists in days list.
    is_school_night = False
    # Check the shoot day immediately after this one in the days list
    if day_index + 1 < len(days):
        is_school_night = days[day_index + 1].school_day
    # Also honor: the current day itself being a school day counts as a school night
    # for curfew purposes (minor attending school next morning).
    # Rule: "preceding a school day" means the night before a school day.
    # Our school_day flag is on the day the minor is working. The curfew applies
    # when the NEXT day is a school day. Use the next shoot day's school_day flag.

    # Previous wrap for turnaround
    prev_wrap: time | None = prev_dismissal
    if prev_wrap is None and day_index > 0 and (sd.date - days[day_index - 1].date).days == 1:
        prev_wrap = days[day_index - 1].wrap

    # Consecutive run: count backwards how many consecutive days in the list
    run = 1
    for i in range(day_index - 1, -1, -1):
        gap = (days[i + 1].date - days[i].date).days
        if gap == 1:
            run += 1
        else:
            break

    return DayContext(
        day_index=day_index,
        shoot_day=sd,
        location_hours=loc_hours,
        is_school_night=is_school_night,
        prev_wrap=prev_wrap,
        consecutive_run=run,
    )


# ---------------------------------------------------------------------------
# Applicability predicates shared with the pass-1 solver (api/hold/legality.py).
# One definition each, so the solver and the checker cannot drift apart (D13).
# ---------------------------------------------------------------------------


def rule_applies_to_minor(rule: RuleRecord, minor: CastMember, shoot_state: str) -> bool:
    """Cumulative jurisdiction (D5): GA on a GA shoot, CA for a CA-resident minor, SAG always."""
    if rule.id in DISPLAY_ONLY_RULE_IDS:
        return False
    jur = rule.jurisdiction
    if jur == "SAG-AFTRA":
        return True
    if jur == "GA":
        return shoot_state == "GA"
    if jur == "CA":
        return minor.resident_state == "CA"
    return False


def age_applies(rule: RuleRecord, age: int) -> bool:
    params = rule.params
    return int(params.get("age_min", 0)) <= age <= int(params.get("age_max", 99))


def earliest_call_applies(rule: RuleRecord, is_school_night: bool) -> bool:
    """A record that also carries a curfew applies its 5 a.m. floor only on its own night type."""
    if "earliest_call" not in rule.params:
        return False
    has_school = "curfew_school_night" in rule.params
    has_non_school = "curfew_non_school_night" in rule.params
    if not has_school and not has_non_school:
        return True
    return (has_school and is_school_night) or (has_non_school and not is_school_night)


def curfew_limit_minutes(rule: RuleRecord, is_school_night: bool) -> int | None:
    """Evening curfew in minutes since midnight, or None when the record has no curfew for this
    night type or the curfew is past midnight (a same-day wrap cannot breach it)."""
    key = "curfew_school_night" if is_school_night else "curfew_non_school_night"
    if key not in rule.params:
        return None
    hh, mm = map(int, str(rule.params[key]).split(":"))
    minutes = hh * 60 + mm
    return minutes if minutes >= 4 * 60 else None


def work_cap_hours(rule: RuleRecord, school_day: bool) -> float | None:
    """The work-hour cap this record imposes on this day type, or None if it has none."""
    params = rule.params
    if school_day and "max_work_hours_school_day" in params:
        return float(params["max_work_hours_school_day"])
    if not school_day and "max_work_hours_non_school_day" in params:
        return float(params["max_work_hours_non_school_day"])
    if "max_work_hours" in params:
        return float(params["max_work_hours"])
    if "max_work_hours_day" in params:
        return float(params["max_work_hours_day"])
    return None


def turnaround_applies(rule_id: str, school_day: bool) -> bool:
    """GA and SAG-AFTRA turnaround apply when the checked day is a school day; CA always."""
    if rule_id == "CA_11760_i_turnaround_12_hours":
        return True
    if rule_id in ("GA_300_7_1_03_turnaround_school_hours", "SAG_MINORS_P22_TURNAROUND_SCHOOL_DAY"):
        return school_day
    return False


# ---------------------------------------------------------------------------
# Rule-level checkers: each returns a ViolationRecord or None
# ---------------------------------------------------------------------------


def _check_curfew(
    rule: RuleRecord,
    wrap: time,
    is_school_night: bool,
    age: int,
) -> ViolationRecord | None:
    """Check one curfew rule against this day's wrap time."""
    params = rule.params
    age_min = int(params.get("age_min", 0))
    age_max = int(params.get("age_max", 99))
    if not (age_min <= age <= age_max):
        return None

    curfew_key = "curfew_school_night" if is_school_night else "curfew_non_school_night"
    if curfew_key not in params:
        return None

    curfew_str = str(params[curfew_key])
    ch, cm = map(int, curfew_str.split(":"))
    curfew_minutes = ch * 60 + cm

    wrap_minutes = _time_to_minutes(wrap)

    # Curfews past midnight (h < 4, e.g. "00:00", "00:30", "02:00") are times on the
    # NEXT calendar day. ShootDay.wrap is always a same-day time (Python time is 00:00-23:59).
    # A same-calendar-day wrap can only breach a post-midnight curfew if the wrap itself
    # falls in the early hours AND exceeds the curfew (e.g. wrap=01:00, curfew=00:30).
    # For evening curfews (>= 04:00), compare directly.
    if curfew_minutes >= 4 * 60:
        # Evening curfew (e.g. 22:00): wrap must be at or before curfew same evening.
        if wrap_minutes <= curfew_minutes:
            return None
        over_minutes = wrap_minutes - curfew_minutes
    else:
        # Post-midnight curfew: only fires if wrap is also in early hours past the limit.
        if not (wrap_minutes < 4 * 60 and wrap_minutes > curfew_minutes):
            return None
        over_minutes = wrap_minutes - curfew_minutes

    return ViolationRecord(
        rule_id=rule.id,
        citation=rule.citation,
        title=rule.title,
        limit=f"Wrap by {curfew_str} ({'school' if is_school_night else 'non-school'} night)",
        computed=f"Wrap at {wrap.strftime('%H:%M')}",
        over_by=f"{over_minutes // 60}h {over_minutes % 60:02d}m",
        quote=rule.quote,
        source_url=rule.source_url,
        jurisdiction=rule.jurisdiction,
    )


def _check_earliest_call(
    rule: RuleRecord,
    call: time,
    age: int,
) -> ViolationRecord | None:
    """Check earliest permitted call time."""
    params = rule.params
    age_min = int(params.get("age_min", 0))
    age_max = int(params.get("age_max", 99))
    if not (age_min <= age <= age_max):
        return None

    earliest_str = str(params.get("earliest_call", "05:00"))
    eh, em_val = map(int, earliest_str.split(":"))
    earliest_minutes = eh * 60 + em_val
    call_minutes = _time_to_minutes(call)

    if call_minutes < earliest_minutes:
        early_by = earliest_minutes - call_minutes
        return ViolationRecord(
            rule_id=rule.id,
            citation=rule.citation,
            title=rule.title,
            limit=f"Call no earlier than {earliest_str}",
            computed=f"Call at {call.strftime('%H:%M')}",
            over_by=f"{early_by // 60}h {early_by % 60:02d}m early",
            quote=rule.quote,
            source_url=rule.source_url,
            jurisdiction=rule.jurisdiction,
        )
    return None


def _check_location_hours(
    rule: RuleRecord,
    location_hours: float,
    age: int,
) -> ViolationRecord | None:
    """Check max hours at place of employment (location hours)."""
    params = rule.params
    age_min = int(params.get("age_min", 0))
    age_max = int(params.get("age_max", 99))
    if not (age_min <= age <= age_max):
        return None
    if "max_location_hours" not in params:
        return None

    limit = float(params["max_location_hours"])
    if location_hours > limit:
        over = location_hours - limit
        return ViolationRecord(
            rule_id=rule.id,
            citation=rule.citation,
            title=rule.title,
            limit=f"{limit:.0f}h at location",
            computed=f"{location_hours:.1f}h at location",
            over_by=f"{over:.1f}h",
            quote=rule.quote,
            source_url=rule.source_url,
            jurisdiction=rule.jurisdiction,
        )
    return None


def _check_work_hours(
    rule: RuleRecord,
    work_hours: float,
    age: int,
    school_day: bool,
    proxy: bool,
) -> ViolationRecord | None:
    """
    Check max work hours. On the proxy path work_hours is the crew location span
    (conservative: location hours >= actual work hours, so a clean check is definitive
    and a flagged check is labeled as a proxy). On the timeline path it is exact.
    """
    params = rule.params
    if not age_applies(rule, age):
        return None

    # One key-selection rule, shared with the solver
    cap = work_cap_hours(rule, school_day)
    if cap is None:
        return None
    limit = cap
    if school_day and "max_work_hours_school_day" in params:
        label = "work (school day)"
    elif not school_day and "max_work_hours_non_school_day" in params:
        label = "work (non-school day)"
    else:
        label = "work"

    if work_hours > limit:
        over = work_hours - limit
        computed = (
            f"{work_hours:.1f}h at location (proxy for work hours)"
            if proxy
            else f"{work_hours:.1f}h work"
        )
        return ViolationRecord(
            rule_id=rule.id,
            citation=rule.citation,
            title=rule.title,
            limit=f"{limit:.0f}h {label}",
            computed=computed,
            over_by=f"{over:.1f}h",
            quote=rule.quote,
            source_url=rule.source_url,
            jurisdiction=rule.jurisdiction,
        )
    return None


def _check_turnaround(
    rule: RuleRecord,
    prev_wrap: time | None,
    call: time,
) -> ViolationRecord | None:
    """Check minimum turnaround between consecutive shoot days."""
    if prev_wrap is None:
        return None
    params = rule.params
    if "min_turnaround_hours" not in params:
        return None

    required = float(params["min_turnaround_hours"])
    actual = _turnaround_hours(prev_wrap, call)
    if actual < required:
        short = required - actual
        return ViolationRecord(
            rule_id=rule.id,
            citation=rule.citation,
            title=rule.title,
            limit=f"{required:.0f}h turnaround",
            computed=f"{actual:.1f}h turnaround",
            over_by=f"{short:.1f}h short",
            quote=rule.quote,
            source_url=rule.source_url,
            jurisdiction=rule.jurisdiction,
        )
    return None


def _check_meal(rule: RuleRecord, mt: MinorTimeline) -> ViolationRecord | None:
    """
    Meal within N hours (8 CCR 11761), timeline path only. Same predicate as the solver:
    a span over the limit requires a meal inside the span, starting within the limit of
    the call, lasting at least the minimum, and leaving no more than the limit after it.
    """
    params = rule.params
    if "max_work_before_meal_hours" not in params:
        return None
    limit_min = int(float(params["max_work_before_meal_hours"]) * 60)
    min_meal = int(params.get("min_meal_duration_minutes", 30))
    call_m = _time_to_minutes(mt.call)
    span = _time_to_minutes(mt.dismiss) - call_m
    if span <= limit_min:
        return None
    ok = False
    computed = "no meal break recorded"
    if mt.meal_start is not None and mt.meal_end is not None:
        ms = _time_to_minutes(mt.meal_start)
        me = _time_to_minutes(mt.meal_end)
        computed = f"meal {mt.meal_start.strftime('%H:%M')} to {mt.meal_end.strftime('%H:%M')}"
        ok = (
            ms >= call_m
            and me <= call_m + span
            and ms - call_m <= limit_min
            and me - ms >= min_meal
            and (call_m + span) - me <= limit_min
        )
    if ok:
        return None
    return ViolationRecord(
        rule_id=rule.id,
        citation=rule.citation,
        title=rule.title,
        limit=f"Meal of {min_meal}m within {limit_min // 60}h of call",
        computed=f"{span / 60:.1f}h span, {computed}",
        over_by=f"{(span - limit_min) / 60:.1f}h past the meal limit",
        quote=rule.quote,
        source_url=rule.source_url,
        jurisdiction=rule.jurisdiction,
    )


def _check_consecutive_days(
    rule: RuleRecord,
    run: int,
    assumed: bool,
) -> ViolationRecord | None:
    """Check max consecutive work days. `assumed` marks the production-dates fallback."""
    params = rule.params
    if "max_consecutive_days" not in params:
        return None
    limit = int(params["max_consecutive_days"])
    if run > limit:
        return ViolationRecord(
            rule_id=rule.id,
            citation=rule.citation,
            title=rule.title,
            limit=f"{limit} consecutive days max",
            computed=f"{run} consecutive days" + (" (production dates, minor assumed on every one)" if assumed else ""),
            over_by=f"{run - limit} days",
            quote=rule.quote,
            source_url=rule.source_url,
            jurisdiction=rule.jurisdiction,
        )
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def check_day_legality(
    schedule: ScheduleInput,
    day_index: int,
    rules_dir: Path | None = None,
    timeline: DayTimeline | None = None,
    on_set: set[str] | None = None,
    prev_dismissal: time | None = None,
    worked_dates: Mapping[str, Collection[date]] | None = None,
) -> list[ViolationRecord]:
    """
    Enumerate every legality violation for one shoot day.

    Args:
        schedule: The full ScheduleInput (jurisdiction, cast, days).
        day_index: 0-based index into schedule.days.
        rules_dir: Override for the rules directory (tests inject a temp dir).
        timeline: Concrete per-minor times. None means the crew-window proxy.
        on_set: Cast ids on set this day. On the proxy path, minors not in it are skipped
            (a minor with no scene that day was not there). None means every minor.
        prev_dismissal: Yesterday's dismissal when the caller knows it; default is the
            previous consecutive calendar day's crew wrap.
        worked_dates: Per-minor dates worked, for the consecutive-days rule. None falls back
            to the production's shoot dates (conservative: the minor is assumed on every one)
            and the violation record says so.

    Returns:
        List of ViolationRecord. Empty means LEGAL for that day.

    D13: This is the source of truth. The CP-SAT pass-1 core is a sufficient
    subset; the checker is complete.
    """
    if rules_dir is None:
        rules_dir = _RULES_DIR

    shoot_day = schedule.days[day_index]
    ctx = build_day_context(schedule, day_index, prev_dismissal=prev_dismissal)

    # Load all rules valid on this shooting date
    all_rules = load_rules(rules_dir, shooting_date=shoot_day.date)

    violations: list[ViolationRecord] = []
    seen_rule_ids: set[str] = set()  # deduplicate within one day

    def _add(v: ViolationRecord | None) -> None:
        if v is not None and v.rule_id not in seen_rule_ids:
            violations.append(v)
            seen_rule_ids.add(v.rule_id)

    # Determine which minor cast members are relevant for this day
    minors = [m for m in schedule.cast if is_minor(m) and (on_set is None or m.id in on_set)]
    if not minors:
        return []

    shoot_state = schedule.jurisdiction.shoot_state

    for minor in minors:
        age = minor.age
        assert age is not None  # narrowed above
        # Which times to judge: the minor's own (timeline) or the crew window (proxy).
        mt: MinorTimeline | None = None
        if timeline is not None:
            mt = timeline.minors.get(minor.id)
            if mt is None:
                continue  # not on set this day
            call_t, dismiss_t = mt.call, mt.dismiss
            location_hours = _duration_hours(call_t, dismiss_t)
            work_hours = mt.work_minutes / 60.0
            proxy = False
        else:
            call_t, dismiss_t = shoot_day.call, shoot_day.wrap
            location_hours = ctx.location_hours
            work_hours = ctx.location_hours
            proxy = True

        if worked_dates is not None:
            run = consecutive_run(set(worked_dates.get(minor.id, ())) | {shoot_day.date}, shoot_day.date)
            run_assumed = False
        else:
            run = ctx.consecutive_run
            run_assumed = True

        for rule in all_rules:
            if not rule_applies_to_minor(rule, minor, shoot_state):
                continue

            # Curfew checks
            if "curfew_school_night" in rule.params or "curfew_non_school_night" in rule.params:
                _add(_check_curfew(rule, dismiss_t, ctx.is_school_night, age))

            # Earliest call: a record that also carries a curfew applies only on its night type
            if earliest_call_applies(rule, ctx.is_school_night):
                _add(_check_earliest_call(rule, call_t, age))

            # Location hours
            if "max_location_hours" in rule.params:
                _add(_check_location_hours(rule, location_hours, age))

            # Work hours (exact on the timeline path, proxy otherwise)
            if any(k in rule.params for k in ("max_work_hours", "max_work_hours_school_day", "max_work_hours_day")):
                _add(_check_work_hours(rule, work_hours, age, shoot_day.school_day, proxy))

            # Turnaround: GA and SAG apply when the checked day is a school day, CA always
            if "min_turnaround_hours" in rule.params and turnaround_applies(rule.id, shoot_day.school_day):
                _add(_check_turnaround(rule, ctx.prev_wrap, call_t))

            # Meal within N hours: only judgeable on a concrete timeline
            if "max_work_before_meal_hours" in rule.params and mt is not None:
                _add(_check_meal(rule, mt))

            # Consecutive days: the minor's own worked dates when known
            if "max_consecutive_days" in rule.params:
                _add(_check_consecutive_days(rule, run, run_assumed))

    return violations


def check_schedule_legality(
    schedule: ScheduleInput,
    rules_dir: Path | None = None,
) -> list[list[ViolationRecord]]:
    """
    Run check_day_legality over every day in the schedule.

    Returns:
        List of length len(schedule.days), each element a list of ViolationRecord
        for that day. An empty inner list means the day is LEGAL.
    """
    return [
        check_day_legality(schedule, i, rules_dir)
        for i in range(len(schedule.days))
    ]
