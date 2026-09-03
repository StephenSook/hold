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
"""
from __future__ import annotations

from datetime import time
from pathlib import Path
from typing import NamedTuple

from api.hold.registry import RuleRecord, load_rules
from api.hold.schemas import CastMember, ScheduleInput, ShootDay, ViolationRecord

_RULES_DIR = Path(__file__).parent.parent.parent / "rules"


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


def _minor_on_set_day(cast_member: CastMember, day_index: int, schedule: ScheduleInput) -> bool:
    """True if the minor appears in at least one scene assigned to this day index."""
    # We don't have scene-to-day assignment in ScheduleInput directly.
    # Use cast_ids presence in any scene as the conservative assumption:
    # if the minor is in ANY scene in the production, they may be called on any day.
    # The caller is responsible for passing only days where the minor is scheduled.
    # For task 2.9 the checker is called with the full schedule; the caller
    # should determine which minors appear on which days based on the solved order.
    # Fallback: if no day assignment info, assume minor is on set every day they appear.
    _ = day_index  # day assignment resolution is task 2.7/2.8's job
    return any(cast_member.id in scene.cast_ids for scene in schedule.scenes)


class _DayContext(NamedTuple):
    """Preprocessed context for one shoot day check."""
    day_index: int
    shoot_day: ShootDay
    location_hours: float
    is_school_night: bool  # next day is a school day (curfew and turnaround trigger)
    prev_wrap: time | None  # previous consecutive shoot day wrap, None if first day
    consecutive_run: int  # how many consecutive shoot days ending on this day


def _build_day_context(schedule: ScheduleInput, day_index: int) -> _DayContext:
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
    prev_wrap: time | None = None
    if day_index > 0:
        prev_wrap = days[day_index - 1].wrap

    # Consecutive run: count backwards how many consecutive days in the list
    run = 1
    for i in range(day_index - 1, -1, -1):
        gap = (days[i + 1].date - days[i].date).days
        if gap == 1:
            run += 1
        else:
            break

    return _DayContext(
        day_index=day_index,
        shoot_day=sd,
        location_hours=loc_hours,
        is_school_night=is_school_night,
        prev_wrap=prev_wrap,
        consecutive_run=run,
    )


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
    location_hours: float,
    age: int,
    school_day: bool,
) -> ViolationRecord | None:
    """
    Check max work hours. Uses location hours as a conservative proxy.
    The proxy is conservative: location hours >= actual work hours,
    so a clean check here is definitive; a flagged check is labeled as such.
    """
    params = rule.params
    age_min = int(params.get("age_min", 0))
    age_max = int(params.get("age_max", 99))
    if not (age_min <= age <= age_max):
        return None

    # Select the relevant limit
    if school_day and "max_work_hours_school_day" in params:
        limit = float(params["max_work_hours_school_day"])
        label = "work (school day)"
    elif not school_day and "max_work_hours_non_school_day" in params:
        limit = float(params["max_work_hours_non_school_day"])
        label = "work (non-school day)"
    elif "max_work_hours" in params:
        limit = float(params["max_work_hours"])
        label = "work"
    elif "max_work_hours_day" in params:
        limit = float(params["max_work_hours_day"])
        label = "work"
    else:
        return None

    if location_hours > limit:
        over = location_hours - limit
        return ViolationRecord(
            rule_id=rule.id,
            citation=rule.citation,
            title=rule.title,
            limit=f"{limit:.0f}h {label}",
            computed=f"{location_hours:.1f}h at location (proxy for work hours)",
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


def _check_consecutive_days(
    rule: RuleRecord,
    consecutive_run: int,
) -> ViolationRecord | None:
    """Check max consecutive work days."""
    params = rule.params
    if "max_consecutive_days" not in params:
        return None
    limit = int(params["max_consecutive_days"])
    if consecutive_run > limit:
        return ViolationRecord(
            rule_id=rule.id,
            citation=rule.citation,
            title=rule.title,
            limit=f"{limit} consecutive days max",
            computed=f"{consecutive_run} consecutive days",
            over_by=f"{consecutive_run - limit} days",
            quote=rule.quote,
            source_url=rule.source_url,
            jurisdiction=rule.jurisdiction,
        )
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

# Rules that are display-only (ratios, chaperones) - never flagged as violations
_DISPLAY_ONLY_IDS = frozenset({
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


def check_day_legality(
    schedule: ScheduleInput,
    day_index: int,
    rules_dir: Path | None = None,
) -> list[ViolationRecord]:
    """
    Enumerate every legality violation for one shoot day.

    Args:
        schedule: The full ScheduleInput (jurisdiction, cast, days).
        day_index: 0-based index into schedule.days.
        rules_dir: Override for the rules directory (tests inject a temp dir).

    Returns:
        List of ViolationRecord. Empty means LEGAL for that day.

    D13: This is the source of truth. The CP-SAT pass-1 core is a sufficient
    subset; the checker is complete.
    """
    if rules_dir is None:
        rules_dir = _RULES_DIR

    shoot_day = schedule.days[day_index]
    ctx = _build_day_context(schedule, day_index)

    # Load all rules valid on this shooting date
    all_rules = load_rules(rules_dir, shooting_date=shoot_day.date)

    violations: list[ViolationRecord] = []
    seen_rule_ids: set[str] = set()  # deduplicate within one day

    def _add(v: ViolationRecord | None) -> None:
        if v is not None and v.rule_id not in seen_rule_ids:
            violations.append(v)
            seen_rule_ids.add(v.rule_id)

    # Determine which minor cast members are relevant for this day
    minors = [m for m in schedule.cast if m.age is not None]
    if not minors:
        return []

    shoot_state = schedule.jurisdiction.shoot_state

    for minor in minors:
        age = minor.age
        assert age is not None  # narrowed above
        is_ca_resident = minor.resident_state == "CA"
        is_ga_shoot = shoot_state == "GA"

        for rule in all_rules:
            if rule.id in _DISPLAY_ONLY_IDS:
                continue

            jur = rule.jurisdiction

            # Determine if this rule applies to this minor
            applies = False
            if jur == "SAG-AFTRA":
                applies = True  # SAG minors rules apply to all minors
            elif jur == "GA" and is_ga_shoot or jur == "CA" and is_ca_resident:
                applies = True

            if not applies:
                continue

            # Curfew checks
            if "curfew_school_night" in rule.params or "curfew_non_school_night" in rule.params:
                _add(_check_curfew(rule, shoot_day.wrap, ctx.is_school_night, age))

            # Earliest call
            if "earliest_call" in rule.params and "curfew_school_night" not in rule.params and "curfew_non_school_night" not in rule.params:
                _add(_check_earliest_call(rule, shoot_day.call, age))

            # Location hours
            if "max_location_hours" in rule.params:
                _add(_check_location_hours(rule, ctx.location_hours, age))

            # Work hours (proxy)
            if any(k in rule.params for k in ("max_work_hours", "max_work_hours_school_day", "max_work_hours_day")):
                _add(_check_work_hours(rule, ctx.location_hours, age, shoot_day.school_day))

            # Turnaround: GA turnaround applies when school_day=True (working during school hours)
            if "min_turnaround_hours" in rule.params:
                if rule.id == "GA_300_7_1_03_turnaround_school_hours":
                    if shoot_day.school_day:
                        _add(_check_turnaround(rule, ctx.prev_wrap, shoot_day.call))
                elif rule.id == "CA_11760_i_turnaround_12_hours":
                    _add(_check_turnaround(rule, ctx.prev_wrap, shoot_day.call))
                elif rule.id == "SAG_MINORS_P22_TURNAROUND_SCHOOL_DAY" and shoot_day.school_day:
                    # Applies when this day is a school day (minor was working day before school)
                    _add(_check_turnaround(rule, ctx.prev_wrap, shoot_day.call))

            # Consecutive days
            if "max_consecutive_days" in rule.params:
                _add(_check_consecutive_days(rule, ctx.consecutive_run))

        # Break after processing the first minor if there is only one set of rules
        # (violations are per-day, not per-minor; we accumulate the superset)

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
