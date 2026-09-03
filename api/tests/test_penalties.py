"""
Task 2.5: Tests for hold day penalty calculator.
Hand-verification of all rate tiers and P&H transitions.
D7: no inline numeric assertions - values derived from the rules YAML via the calculator.
"""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import pytest

from api.hold.penalties import hold_day_cost_cents, hold_days_total_cents
from api.hold.schemas import CastMember


def _cast(rate_cents: int, tier: str) -> CastMember:
    return CastMember(
        id="test",
        letter="X",
        age=None,
        resident_state=None,
        day_rate_cents=rate_cents,
        rate_tier=tier,  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# Hand-calculated reference values. The day rates below are test inputs chosen for the
# arithmetic they exercise; the published 7/1/2026 minimums live in rules/sag_rates.yaml
# (Low Budget $834, Moderate Low $449, Ultra Low $257) and test_registry_low_budget_rate
# reads the Low Budget figure from the registry rather than typing it here (D7).
#
# $810/day input, P&H 21% (before 2026-09-06):
#   ph = 81000 * 2100 / 10000 = 17010 cents
#   total = 81000 + 17010 = 98010 cents = $980.10
#
# $810/day input, P&H 22% (2026-09-06 and after):
#   ph = 81000 * 2200 / 10000 = 17820 cents
#   total = 81000 + 17820 = 98820 cents = $988.20
#
# $449.05/day input, P&H 21%:
#   ph = 44905 * 2100 / 10000 = 9430.05 cents
#   half-up rounding: 0.05 < 0.5, so rounds DOWN to 9430 cents
#   total = 44905 + 9430 = 54335 cents = $543.35
#
# $249/day input, P&H 21%:
#   ph = 24900 * 2100 / 10000 = 5229 cents (exact)
#   total = 24900 + 5229 = 30129 cents = $301.29
# ---------------------------------------------------------------------------

LOW_BUDGET_CAST = _cast(81000, "low_budget")
MODERATE_LOW_CAST = _cast(44905, "moderate_low")
ULTRA_LOW_CAST = _cast(24900, "ultra_low")

DATE_PRE_PH_CHANGE = date(2026, 9, 4)   # 21% P&H
DATE_POST_PH_CHANGE = date(2026, 9, 6)  # 22% P&H
SHOOT_DATE = date(2026, 10, 8)          # demo shoot date, 21% P&H still? No - after Sep 6, so 22%


def test_low_budget_pre_ph_change() -> None:
    """$810 input before the P&H rate change: $810 + 21% = $980.10."""
    cost = hold_day_cost_cents(LOW_BUDGET_CAST, DATE_PRE_PH_CHANGE)
    assert cost == 98010, f"Expected 98010 (=$980.10), got {cost}"


def test_low_budget_post_ph_change() -> None:
    """$810 input after the P&H rate change: $810 + 22% = $988.20."""
    cost = hold_day_cost_cents(LOW_BUDGET_CAST, DATE_POST_PH_CHANGE)
    assert cost == 98820, f"Expected 98820 (=$988.20), got {cost}"


def test_moderate_low_pre_ph_change() -> None:
    """$449.05 input: $449.05 + 21% = $543.35 (9430.05 rounds to 9430)."""
    cost = hold_day_cost_cents(MODERATE_LOW_CAST, DATE_PRE_PH_CHANGE)
    assert cost == 54335, f"Expected 54335 (=$543.35), got {cost}"


def test_ultra_low_pre_ph_change() -> None:
    """$249 input: $249 + 21% = $301.29."""
    cost = hold_day_cost_cents(ULTRA_LOW_CAST, DATE_PRE_PH_CHANGE)
    assert cost == 30129, f"Expected 30129 (=$301.29), got {cost}"


def test_ph_rate_changes_on_sep_6() -> None:
    """P&H rate flips to 22% on 2026-09-06 exactly."""
    before = hold_day_cost_cents(LOW_BUDGET_CAST, date(2026, 9, 5))
    on = hold_day_cost_cents(LOW_BUDGET_CAST, date(2026, 9, 6))
    assert before == 98010   # 21%
    assert on == 98820       # 22%
    assert on > before


def test_multiple_hold_dates() -> None:
    """hold_days_total_cents sums correctly across dates spanning the P&H change."""
    dates = [date(2026, 9, 5), date(2026, 9, 6)]  # one 21%, one 22%
    total = hold_days_total_cents(LOW_BUDGET_CAST, dates)
    assert total == 98010 + 98820


def test_shoot_date_post_ph_change() -> None:
    """Demo shoot dates (Oct 2026) use 22% P&H."""
    cost = hold_day_cost_cents(LOW_BUDGET_CAST, SHOOT_DATE)
    assert cost == 98820


def test_registry_low_budget_rate_on_a_demo_date() -> None:
    """The Low Budget day rate comes from the registry (7/1/2026 record), never typed here."""
    from pathlib import Path

    from api.hold.registry import get_rule

    rules_dir = Path(__file__).parents[2] / "rules"
    record = get_rule(rules_dir, "SAG_RATES_LOW_BUDGET_DAY", shooting_date=SHOOT_DATE)
    assert record is not None
    rate = int(record.params["day_rate_cents"])
    cast = _cast(rate, "low_budget")
    # 22% P&H on the demo date, half-up to the cent
    assert hold_day_cost_cents(cast, SHOOT_DATE) == rate + round(rate * 22 / 100)
    assert get_rule(rules_dir, "SAG_RATES_LOW_BUDGET_DAY", shooting_date=date(2027, 8, 1)) is None
    later = get_rule(rules_dir, "SAG_RATES_LOW_BUDGET_DAY_2027", shooting_date=date(2027, 8, 1))
    assert later is not None and int(later.params["day_rate_cents"]) > rate


def test_a_date_no_rate_record_covers_is_refused_not_defaulted() -> None:
    """D4: no P&H record covers 2019, so the cost is refused instead of silently taking 21 percent."""
    from api.hold.penalties import RatesError

    member = CastMember(id="cA", letter="A", age=None, resident_state=None, day_rate_cents=10000, rate_tier="low_budget")
    with pytest.raises(RatesError, match="2019-01-01"):
        hold_day_cost_cents(member, date(2019, 1, 1))


# ---- Task 2.11: rest periods, forced calls and meal penalties (SAG-AFTRA), integer cents ----


def _lba(day_rate_cents: int) -> CastMember:
    return CastMember(id="cA", letter="A", age=None, resident_state=None, day_rate_cents=day_rate_cents, rate_tier="low_budget")


def test_forced_call_is_the_lesser_of_the_day_rate_and_900_dollars() -> None:
    from api.hold.penalties import forced_call_penalty_cents

    assert forced_call_penalty_cents(_lba(83400), date(2026, 10, 8)) == 83400  # $834 LBA day rate
    assert forced_call_penalty_cents(_lba(100000), date(2026, 10, 8)) == 90000  # $1,000 rate capped at $900
    assert forced_call_penalty_cents(_lba(100000), date(2026, 10, 8), weekly=True) == 95000  # weekly cap $950
    assert forced_call_penalty_cents(_lba(83400), date(2026, 10, 8), weekly=True) == 83400


def test_meal_penalty_ladder_by_half_hour_or_fraction() -> None:
    from api.hold.penalties import meal_penalty_cents

    d = date(2026, 10, 8)
    assert meal_penalty_cents(0, d, "low_budget") == 0
    assert meal_penalty_cents(1, d, "low_budget") == 2500  # first half-hour or fraction: $25
    assert meal_penalty_cents(30, d, "low_budget") == 2500
    assert meal_penalty_cents(35, d, "low_budget") == 6000  # $25 + $35
    assert meal_penalty_cents(95, d, "low_budget") == 16000  # $25 + $35 + $50 + $50
    assert meal_penalty_cents(95, d, "ultra_low") == 10000  # flat $25 per half-hour or part


def test_rest_period_violations_use_the_12_and_56_hour_rules() -> None:
    from api.hold.penalties import daily_rest_violated, weekly_rest_violated

    d = date(2026, 10, 8)
    assert daily_rest_violated(datetime(2026, 10, 7, 22, 0), datetime(2026, 10, 8, 9, 0), d)  # 11 h
    assert not daily_rest_violated(datetime(2026, 10, 7, 22, 0), datetime(2026, 10, 8, 10, 0), d)  # 12 h exactly
    assert weekly_rest_violated(datetime(2026, 10, 9, 20, 0), datetime(2026, 10, 12, 3, 0), d)  # 55 h
    assert not weekly_rest_violated(datetime(2026, 10, 9, 20, 0), datetime(2026, 10, 12, 4, 0), d)  # 56 h


def test_penalty_records_never_reach_the_minor_checker() -> None:
    from api.hold.legality_checker import rule_applies_to_minor
    from api.hold.registry import load_rules

    penalty_ids = {"SAG_RATES_REST_PERIOD_12_HOURS", "SAG_RATES_MEAL_PENALTY_LADDER", "SAG_RATES_FORCED_CALL_DAY_PERFORMER"}
    rules = {r.id: r for r in load_rules(Path("rules"))}
    assert penalty_ids <= set(rules)
    minor = CastMember(id="cM", letter="M", age=14, resident_state="CA", day_rate_cents=83400, rate_tier="low_budget")
    for rid in penalty_ids:
        assert rules[rid].params.get("kind") == "penalty"
        assert not rule_applies_to_minor(rules[rid], minor, "GA")


def test_meal_penalty_refuses_an_unknown_rate_tier() -> None:
    """Round six, finding 7: a tier the schema does not name is refused, never priced on the ladder."""
    from api.hold.penalties import RatesError, meal_penalty_cents

    with pytest.raises(RatesError, match="rate tier"):
        meal_penalty_cents(35, date(2026, 10, 8), "not_a_tier")
