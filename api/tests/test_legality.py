"""
Task 2.9: Tests for the legality violation enumerator.

Five fixture day types as specified in PLAN.md task 2.9:
- One legal day (no violations)
- Curfew violation (school night, wrap past 10 PM - GA + CA)
- Work/location hours violation
- Turnaround violation (< 12h between days)
- Consecutive days violation (> 6 consecutive days)

All fixtures use the demo schedule cast (minor M, age 14, CA resident, GA shoot).
D13: checker is source of truth; pass-1 core must be a subset of these lists.
"""
from __future__ import annotations

from datetime import date, time

from api.hold.legality_checker import check_day_legality, check_schedule_legality
from api.hold.schemas import (
    CastMember,
    Jurisdiction,
    Scene,
    ScheduleInput,
    ShootDay,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_MINOR_M = CastMember(
    id="cM",
    letter="M",
    age=14,
    resident_state="CA",
    day_rate_cents=81000,
    rate_tier="low_budget",
)

_ADULT_A = CastMember(
    id="cA",
    letter="A",
    age=None,
    resident_state=None,
    day_rate_cents=81000,
    rate_tier="low_budget",
)

_SCENE_WITH_MINOR = Scene(
    id="s1",
    number=1,
    int_ext="EXT",
    day_night="DAY",
    set="Peach Orchard",
    pages_eighths=16,
    cast_ids=["cM", "cA"],
    location_id="locGA1",
)

_GA_JURISDICTION = Jurisdiction(shoot_state="GA")


def _make_schedule(days: list[ShootDay], minor: CastMember = _MINOR_M) -> ScheduleInput:
    """Build a minimal ScheduleInput with one scene (the minor is in it)."""
    return ScheduleInput(
        scenes=[_SCENE_WITH_MINOR],
        cast=[minor, _ADULT_A],
        days=days,
        constraints=[],
        jurisdiction=_GA_JURISDICTION,
        constructed=True,
    )


def _day(
    d: date,
    call: str,
    wrap: str,
    school_day: bool = False,
) -> ShootDay:
    h_c, m_c = map(int, call.split(":"))
    h_w, m_w = map(int, wrap.split(":"))
    return ShootDay(
        date=d,
        call=time(h_c, m_c),
        wrap=time(h_w, m_w),
        school_day=school_day,
    )


# ---------------------------------------------------------------------------
# Test 1: Legal day - no violations expected
# ---------------------------------------------------------------------------

def test_legal_day_no_violations() -> None:
    """A well-formed non-school day, 4h (within GA 5h work, GA 10h location, CA 8h cap)."""
    # GA work cap: 5h for 9-15, GA location cap: 10h, CA daily cap: 8h.
    # 4h satisfies all three. No curfew issues (wrap 11:00, non-school-night post-midnight curfew).
    days = [_day(date(2026, 10, 5), "07:00", "11:00", school_day=False)]
    schedule = _make_schedule(days)
    violations = check_day_legality(schedule, 0)
    assert violations == [], f"Expected no violations, got: {[v.rule_id for v in violations]}"


# ---------------------------------------------------------------------------
# Test 2: GA + CA school-night curfew violation
# The demo illegal day: 2026-10-08, call 07:00, wrap 21:30, school_day=True
# Minor M (age 14, CA resident, GA shoot)
# GA rule: curfew 22:00 school night (age 9-15) - wrap 21:30 is <= 22:00 -> NO violation
# BUT: next day (day_index+1) school_day flag triggers the curfew, not current day.
# Let us use wrap 22:30 to make it clearly past 22:00.
# ---------------------------------------------------------------------------

def test_ga_school_night_curfew_violation() -> None:
    """Wrap at 22:30 on a night before a school day violates GA 10 PM curfew for minor 9-15."""
    days = [
        _day(date(2026, 10, 7), "07:00", "22:30", school_day=False),  # day 0: next day is school
        _day(date(2026, 10, 8), "07:00", "16:00", school_day=True),   # day 1: school day
    ]
    schedule = _make_schedule(days)
    violations = check_day_legality(schedule, 0)  # check day 0 (preceding the school day)
    rule_ids = [v.rule_id for v in violations]
    assert "GA_300_7_1_03_school_night_curfew" in rule_ids, (
        f"Expected GA school night curfew violation, got: {rule_ids}"
    )


def test_ca_school_night_curfew_violation() -> None:
    """CA-resident minor wrap at 22:30 before school day also violates Cal. Lab. Code 1308.7(a)."""
    days = [
        _day(date(2026, 10, 7), "07:00", "22:30", school_day=False),
        _day(date(2026, 10, 8), "07:00", "16:00", school_day=True),
    ]
    schedule = _make_schedule(days)
    violations = check_day_legality(schedule, 0)
    rule_ids = [v.rule_id for v in violations]
    assert "CA_1308_7_curfew_school_night" in rule_ids, (
        f"Expected CA school night curfew violation, got: {rule_ids}"
    )


def test_curfew_violation_has_correct_fields() -> None:
    """ViolationRecord fields are populated correctly for a GA curfew breach."""
    days = [
        _day(date(2026, 10, 7), "07:00", "23:00", school_day=False),
        _day(date(2026, 10, 8), "07:00", "16:00", school_day=True),
    ]
    schedule = _make_schedule(days)
    violations = check_day_legality(schedule, 0)
    ga_v = next((v for v in violations if v.rule_id == "GA_300_7_1_03_school_night_curfew"), None)
    assert ga_v is not None
    assert ga_v.citation == "Ga. Comp. R. & Regs. 300-7-1-.03(2)(a)"
    assert "22:00" in ga_v.limit
    assert "23:00" in ga_v.computed
    assert ga_v.over_by  # non-empty
    assert ga_v.quote  # verbatim text present
    assert ga_v.source_url.startswith("https://")
    assert ga_v.jurisdiction == "GA"


# ---------------------------------------------------------------------------
# Test 3: Location / work hours violation (GA)
# 10-hour location cap for age 9-15 under GA rules
# ---------------------------------------------------------------------------

def test_ga_location_hours_violation() -> None:
    """11 hours at location violates GA 10-hour cap for minor aged 9-15."""
    days = [_day(date(2026, 10, 5), "07:00", "18:00", school_day=False)]  # 11 hours
    schedule = _make_schedule(days)
    violations = check_day_legality(schedule, 0)
    rule_ids = [v.rule_id for v in violations]
    assert "GA_300_7_1_03_ages_9_15_location_hours" in rule_ids, (
        f"Expected GA location hours violation, got: {rule_ids}"
    )


def test_ga_work_hours_violation() -> None:
    """6 hours at location violates GA 5-hour work cap for minor aged 9-15."""
    days = [_day(date(2026, 10, 5), "07:00", "13:00", school_day=False)]  # 6 hours
    schedule = _make_schedule(days)
    violations = check_day_legality(schedule, 0)
    rule_ids = [v.rule_id for v in violations]
    assert "GA_300_7_1_03_ages_9_15_work_hours" in rule_ids, (
        f"Expected GA work hours violation, got: {rule_ids}"
    )


def test_no_violation_within_limits() -> None:
    """4 hours at location is within both GA work and location limits for age 9-15."""
    days = [_day(date(2026, 10, 5), "07:00", "11:00", school_day=False)]  # 4 hours
    schedule = _make_schedule(days)
    violations = check_day_legality(schedule, 0)
    assert violations == [], f"Unexpected violations: {[v.rule_id for v in violations]}"


# ---------------------------------------------------------------------------
# Test 4: Turnaround violation
# ---------------------------------------------------------------------------

def test_turnaround_violation_school_day() -> None:
    """
    Wrap at 22:00 on day 1, call at 07:00 on day 2 (school_day=True):
    turnaround = 9 hours, violates GA 12h turnaround rule.
    """
    days = [
        _day(date(2026, 10, 7), "07:00", "22:00", school_day=False),
        _day(date(2026, 10, 8), "07:00", "16:00", school_day=True),
    ]
    schedule = _make_schedule(days)
    violations = check_day_legality(schedule, 1)  # check day 1 (the school day)
    rule_ids = [v.rule_id for v in violations]
    assert "GA_300_7_1_03_turnaround_school_hours" in rule_ids, (
        f"Expected GA turnaround violation, got: {rule_ids}"
    )


def test_turnaround_ok_when_sufficient() -> None:
    """Wrap at 18:00, next call at 07:00 = 13h turnaround: no violation."""
    days = [
        _day(date(2026, 10, 7), "07:00", "18:00", school_day=False),
        _day(date(2026, 10, 8), "07:00", "16:00", school_day=True),
    ]
    schedule = _make_schedule(days)
    violations = check_day_legality(schedule, 1)
    rule_ids = [v.rule_id for v in violations]
    assert "GA_300_7_1_03_turnaround_school_hours" not in rule_ids, (
        f"Unexpected turnaround violation: {rule_ids}"
    )


def test_ca_turnaround_violation() -> None:
    """CA 12h turnaround (8 CCR 11760(i)) fires for CA-resident minor with < 12h gap."""
    days = [
        _day(date(2026, 10, 7), "07:00", "22:00", school_day=False),
        _day(date(2026, 10, 8), "07:00", "16:00", school_day=False),  # non-school, but CA checks anyway
    ]
    schedule = _make_schedule(days)
    violations = check_day_legality(schedule, 1)
    rule_ids = [v.rule_id for v in violations]
    assert "CA_11760_i_turnaround_12_hours" in rule_ids, (
        f"Expected CA turnaround violation, got: {rule_ids}"
    )


# ---------------------------------------------------------------------------
# Test 5: Consecutive days violation
# ---------------------------------------------------------------------------

def test_consecutive_days_violation() -> None:
    """7 consecutive shoot days violates GA 6-consecutive-day maximum."""
    start = date(2026, 10, 5)
    days = [
        _day(date.fromordinal(start.toordinal() + i), "07:00", "16:00", school_day=False)
        for i in range(7)
    ]
    schedule = _make_schedule(days)
    # Check the 7th day (index 6)
    violations = check_day_legality(schedule, 6)
    rule_ids = [v.rule_id for v in violations]
    assert "GA_300_7_1_03_consecutive_days" in rule_ids, (
        f"Expected consecutive days violation on day 7, got: {rule_ids}"
    )


def test_sixth_consecutive_day_ok() -> None:
    """6 consecutive days is exactly the limit - no violation."""
    start = date(2026, 10, 5)
    days = [
        _day(date.fromordinal(start.toordinal() + i), "07:00", "16:00", school_day=False)
        for i in range(6)
    ]
    schedule = _make_schedule(days)
    violations = check_day_legality(schedule, 5)
    rule_ids = [v.rule_id for v in violations]
    assert "GA_300_7_1_03_consecutive_days" not in rule_ids, (
        f"Unexpected consecutive days violation: {rule_ids}"
    )


# ---------------------------------------------------------------------------
# Test 6: Adult-only cast - no minor violations
# ---------------------------------------------------------------------------

def test_adult_only_no_violations() -> None:
    """A schedule with only adult cast members should never produce minor violations."""
    adult_scene = Scene(
        id="s1",
        number=1,
        int_ext="EXT",
        day_night="DAY",
        set="Set",
        pages_eighths=16,
        cast_ids=["cA"],
        location_id="locGA1",
    )
    schedule = ScheduleInput(
        scenes=[adult_scene],
        cast=[_ADULT_A],
        days=[_day(date(2026, 10, 5), "07:00", "23:00", school_day=False)],
        constraints=[],
        jurisdiction=_GA_JURISDICTION,
        constructed=True,
    )
    violations = check_day_legality(schedule, 0)
    assert violations == [], f"Adults should have no minor violations: {[v.rule_id for v in violations]}"


# ---------------------------------------------------------------------------
# Test 7: Demo schedule day 4 (the known illegal day)
# 2026-10-08, call 07:00, wrap 21:30, school_day=True, GA shoot, minor M age 14 CA
# Next day (index 4) is 2026-10-09, school_day=False.
# school_night flag: is next day school? No -> is_school_night=False for day 3.
# But current day IS school_day=True, so curfew precedes day 4 (non-school).
# Actually the demo day 4 (index 3) itself is school_day=True.
# The CURFEW rule fires on the preceding night (is_school_night = next day is school).
# Day index 3 has next day index 4 which is school_day=False -> is_school_night=False.
# So the curfew on day 3 is the NON-school-night curfew: CA = 00:30, GA = midnight.
# Wrap 21:30 is before midnight -> no curfew violation.
# BUT: location hours = 14.5h > GA 10h limit for age 9-15 -> violation.
# ---------------------------------------------------------------------------

def test_demo_illegal_day_location_hours() -> None:
    """Demo day 4: 14.5h at location violates GA 10h cap for minor age 14."""
    import json
    from pathlib import Path
    demo_path = Path(__file__).parent.parent.parent / "data" / "demo" / "hold-demo.json"
    raw = json.loads(demo_path.read_text())
    schedule = ScheduleInput.model_validate(raw)
    # Day index 3 is 2026-10-08, call 07:00, wrap 21:30 (14.5 hours), school_day=True
    violations = check_day_legality(schedule, 3)
    rule_ids = [v.rule_id for v in violations]
    assert "GA_300_7_1_03_ages_9_15_location_hours" in rule_ids, (
        f"Expected GA location hours violation on demo day 4, got: {rule_ids}"
    )


def test_demo_school_day_has_strictest_violations() -> None:
    """
    Demo day 3 (2026-10-08, school_day=True, wrap 21:30) is the most-violated day:
    it triggers the 3h school-day work cap (vs 8h on other days) making it strictly worse.
    All other demo days (12h, non-school) also have violations (12h > GA 10h location cap).
    """
    import json
    from pathlib import Path
    demo_path = Path(__file__).parent.parent.parent / "data" / "demo" / "hold-demo.json"
    raw = json.loads(demo_path.read_text())
    schedule = ScheduleInput.model_validate(raw)
    # School day (index 3): must have the school-day work cap violation
    school_violations = check_day_legality(schedule, 3)
    school_ids = {v.rule_id for v in school_violations}
    assert "CA_11760_e_work_hours_9_15_school_day" in school_ids
    assert "GA_300_7_1_03_ages_9_15_location_hours" in school_ids
    # Non-school 12h days also have violations (12h > 10h GA location, > 8h CA daily cap)
    for i in [0, 1, 2, 4, 5, 6]:
        v = check_day_legality(schedule, i)
        ids = {vv.rule_id for vv in v}
        assert "GA_300_7_1_03_ages_9_15_location_hours" in ids, (
            f"Demo day {i} (12h) should violate GA location cap, got: {ids}"
        )


# ---------------------------------------------------------------------------
# Test 8: check_schedule_legality wrapper
# ---------------------------------------------------------------------------

def test_check_schedule_legality_returns_per_day_lists() -> None:
    """check_schedule_legality returns one list per day."""
    days = [
        _day(date(2026, 10, 5), "07:00", "16:00", school_day=False),
        _day(date(2026, 10, 6), "07:00", "16:00", school_day=False),
    ]
    schedule = _make_schedule(days)
    result = check_schedule_legality(schedule)
    assert len(result) == 2


def test_check_schedule_legality_flags_illegal_day() -> None:
    """check_schedule_legality flags day 0 (16h at location) and day 1 (8h turnaround)."""
    days = [
        _day(date(2026, 10, 7), "07:00", "23:00", school_day=False),  # 16h - over location cap
        _day(date(2026, 10, 8), "07:00", "16:00", school_day=False),
    ]
    schedule = _make_schedule(days)
    result = check_schedule_legality(schedule)
    assert len(result[0]) > 0, "Day 0 should have violations (16h location)"
    day1_ids = {v.rule_id for v in result[1]}
    assert "CA_11760_i_turnaround_12_hours" in day1_ids, (
        f"Day 1 follows a 23:00 wrap with a 07:00 call (8h): CA turnaround must fire, got {day1_ids}"
    )


# ---------------------------------------------------------------------------
# Test 9: Multiple violations on one day
# ---------------------------------------------------------------------------

def test_multiple_violations_same_day() -> None:
    """
    Wrap 23:00 on a night before school day, 16h location:
    GA school night curfew + CA school night curfew + GA location hours + GA work hours.
    At minimum three distinct rule ids.
    """
    days = [
        _day(date(2026, 10, 7), "07:00", "23:00", school_day=False),
        _day(date(2026, 10, 8), "07:00", "16:00", school_day=True),
    ]
    schedule = _make_schedule(days)
    violations = check_day_legality(schedule, 0)
    assert len(violations) >= 3, (
        f"Expected >= 3 violations for an extreme day, got {len(violations)}: "
        f"{[v.rule_id for v in violations]}"
    )


# ---------------------------------------------------------------------------
# Test 10: turnaround only across consecutive calendar dates
# ---------------------------------------------------------------------------

def test_turnaround_skipped_when_dates_not_consecutive() -> None:
    """A Friday 22:00 wrap and a Monday 07:00 call is a 57-hour rest, not a 9-hour one."""
    friday = ShootDay(date=date(2026, 10, 9), call=time(7, 0), wrap=time(23, 0), school_day=False, school_night=False)
    days = [friday, _day(date(2026, 10, 12), "07:00", "16:00", school_day=True)]  # Monday
    schedule = _make_schedule(days)
    rule_ids = {v.rule_id for v in check_day_legality(schedule, 1)}
    assert not rule_ids & {
        "GA_300_7_1_03_turnaround_school_hours",
        "SAG_MINORS_P22_TURNAROUND_SCHOOL_DAY",
        "CA_11760_i_turnaround_12_hours",
    }, f"Turnaround must not fire across a weekend gap, got: {rule_ids}"
    friday_ids = {v.rule_id for v in check_day_legality(schedule, 0)}
    assert not friday_ids & {"GA_300_7_1_03_school_night_curfew", "CA_1308_7_curfew_school_night"}, friday_ids


def test_school_night_unknown_across_a_gap_is_assumed_and_labeled() -> None:
    days = [_day(date(2026, 10, 9), "07:00", "23:00", school_day=False), _day(date(2026, 10, 12), "07:00", "16:00", school_day=True)]
    schedule = _make_schedule(days)
    curfew = next(v for v in check_day_legality(schedule, 0) if v.rule_id == "GA_300_7_1_03_school_night_curfew")
    assert "assumed" in curfew.limit


def test_school_night_derived_from_the_next_calendar_day_is_not_labeled() -> None:
    days = [_day(date(2026, 10, 7), "07:00", "23:00", school_day=False), _day(date(2026, 10, 8), "07:00", "16:00", school_day=True)]
    schedule = _make_schedule(days)
    curfew = next(v for v in check_day_legality(schedule, 0) if v.rule_id == "GA_300_7_1_03_school_night_curfew")
    assert "assumed" not in curfew.limit


# ---------------------------------------------------------------------------
# Test 11: Cal. Lab. Code 1308.7 earliest call, gated by night type
# ---------------------------------------------------------------------------

def test_ca_earliest_call_fires_on_school_night_record() -> None:
    """A 04:30 call the day before a school day breaches Lab. Code 1308.7(a), the 5 a.m. floor."""
    days = [
        _day(date(2026, 10, 7), "04:30", "09:00", school_day=False),
        _day(date(2026, 10, 8), "07:00", "16:00", school_day=True),
    ]
    schedule = _make_schedule(days)
    rule_ids = {v.rule_id for v in check_day_legality(schedule, 0)}
    assert "CA_1308_7_curfew_school_night" in rule_ids, rule_ids
    assert "CA_1308_7_curfew_non_school_night" not in rule_ids, rule_ids
    assert "GA_300_7_1_03_earliest_call" in rule_ids, rule_ids


def test_ca_earliest_call_fires_on_non_school_night_record() -> None:
    """A 04:30 call with no school day following breaches Lab. Code 1308.7(b), not (a).
    A lone day says so explicitly; with nothing listed after it the schedule would assume a school night."""
    days = [ShootDay(date=date(2026, 10, 7), call=time(4, 30), wrap=time(9, 0), school_day=False, school_night=False)]
    schedule = _make_schedule(days)
    rule_ids = {v.rule_id for v in check_day_legality(schedule, 0)}
    assert "CA_1308_7_curfew_non_school_night" in rule_ids, rule_ids
    assert "CA_1308_7_curfew_school_night" not in rule_ids, rule_ids


# ---------------------------------------------------------------------------
# Test 12: a concrete per-minor timeline overrides the crew-window proxy
# ---------------------------------------------------------------------------

def test_timeline_overrides_crew_window() -> None:
    """A 12-hour crew day is legal for a minor who is called for two hours of it."""
    from api.hold.legality_checker import DayTimeline, MinorTimeline

    days = [_day(date(2026, 10, 5), "07:00", "19:00", school_day=False)]
    schedule = _make_schedule(days)
    timeline = DayTimeline(
        minors={"cM": MinorTimeline(call=time(9, 0), dismiss=time(11, 0), work_minutes=120)}
    )
    assert check_day_legality(schedule, 0, timeline=timeline) == []


def test_timeline_meal_check() -> None:
    """Eight hours on set with no recorded meal breaches 8 CCR 11761; a 30-minute meal inside six hours clears it."""
    from api.hold.legality_checker import DayTimeline, MinorTimeline

    days = [_day(date(2026, 10, 5), "07:00", "19:00", school_day=False)]
    schedule = _make_schedule(days)
    no_meal = DayTimeline(
        minors={"cM": MinorTimeline(call=time(7, 0), dismiss=time(15, 0), work_minutes=240)}
    )
    ids = {v.rule_id for v in check_day_legality(schedule, 0, timeline=no_meal)}
    assert "CA_11761_meal_period_6_hours" in ids, ids
    with_meal = DayTimeline(
        minors={
            "cM": MinorTimeline(
                call=time(7, 0),
                dismiss=time(15, 0),
                work_minutes=240,
                meal_start=time(12, 0),
                meal_end=time(12, 30),
            )
        }
    )
    ids = {v.rule_id for v in check_day_legality(schedule, 0, timeline=with_meal)}
    assert "CA_11761_meal_period_6_hours" not in ids, ids


def test_timeline_skips_absent_minor() -> None:
    """A minor with no timeline entry was not on set: a 16-hour crew day yields nothing for them."""
    from api.hold.legality_checker import DayTimeline

    days = [_day(date(2026, 10, 5), "07:00", "23:00", school_day=False)]
    schedule = _make_schedule(days)
    assert check_day_legality(schedule, 0, timeline=DayTimeline(minors={})) == []


# ---------------------------------------------------------------------------
# Test 13: who is a minor, and the on-set filter
# ---------------------------------------------------------------------------

def test_recorded_age_eighteen_gets_no_minor_rules() -> None:
    adult = CastMember(id="cX", letter="X", age=18, resident_state="CA", day_rate_cents=81000, rate_tier="low_budget")
    days = [_day(date(2026, 10, 7), "07:00", "23:00", school_day=False), _day(date(2026, 10, 8), "07:00", "16:00", school_day=True)]
    schedule = _make_schedule(days, minor=adult)
    assert check_day_legality(schedule, 0) == []


def test_on_set_filter_skips_minor_without_a_scene() -> None:
    older = CastMember(id="cZ", letter="Z", age=17, resident_state=None, day_rate_cents=81000, rate_tier="low_budget")
    days = [_day(date(2026, 10, 5), "07:00", "20:00", school_day=False)]  # 13h: both brackets breach
    schedule = ScheduleInput(
        scenes=[_SCENE_WITH_MINOR], cast=[_MINOR_M, _ADULT_A, older], days=days, constraints=[],
        jurisdiction=_GA_JURISDICTION, constructed=True,
    )
    all_ids = {v.rule_id for v in check_day_legality(schedule, 0)}
    assert "GA_300_7_1_03_ages_16_17_location_hours" in all_ids
    on_set_ids = {v.rule_id for v in check_day_legality(schedule, 0, on_set={"cM"})}
    assert "GA_300_7_1_03_ages_16_17_location_hours" not in on_set_ids
    assert "GA_300_7_1_03_ages_9_15_location_hours" in on_set_ids


def test_prev_dismissal_override_in_checker() -> None:
    """A caller who knows yesterday's dismissal can supply it across a calendar gap."""
    days = [
        _day(date(2026, 10, 4), "07:00", "22:00", school_day=False),
        _day(date(2026, 10, 8), "07:00", "11:00", school_day=False),
    ]
    schedule = _make_schedule(days)
    assert "CA_11760_i_turnaround_12_hours" not in {v.rule_id for v in check_day_legality(schedule, 1)}
    ids = {v.rule_id for v in check_day_legality(schedule, 1, prev_dismissal=time(22, 0))}
    assert "CA_11760_i_turnaround_12_hours" in ids


def test_timeline_meal_too_early_leaves_a_long_stretch_after_it() -> None:
    """A meal at 06:00 on a 05:00 to 13:30 day leaves seven hours after it: still a breach."""
    from api.hold.legality_checker import DayTimeline, MinorTimeline

    days = [_day(date(2026, 10, 5), "05:00", "13:30", school_day=False)]
    schedule = _make_schedule(days)
    tl = DayTimeline(minors={"cM": MinorTimeline(call=time(5, 0), dismiss=time(13, 30), work_minutes=480,
                                                  meal_start=time(6, 0), meal_end=time(6, 30))})
    ids = {v.rule_id for v in check_day_legality(schedule, 0, timeline=tl)}
    assert "CA_11761_meal_period_6_hours" in ids


def test_consecutive_days_use_worked_dates_when_given() -> None:
    start = date(2026, 10, 5)
    days = [_day(date.fromordinal(start.toordinal() + i), "07:00", "16:00", school_day=False) for i in range(7)]
    schedule = _make_schedule(days)
    worked = {"cM": {date.fromordinal(start.toordinal() + 6)}}
    ids = {v.rule_id for v in check_day_legality(schedule, 6, worked_dates=worked)}
    assert "GA_300_7_1_03_consecutive_days" not in ids
    all_days = {"cM": {d.date for d in days}}
    ids = {v.rule_id for v in check_day_legality(schedule, 6, worked_dates=all_days)}
    assert "GA_300_7_1_03_consecutive_days" in ids
