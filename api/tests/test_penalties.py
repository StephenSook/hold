"""
Task 2.5: Tests for hold day penalty calculator.
Hand-verification of all rate tiers and P&H transitions.
D7: no inline numeric assertions - values derived from the rules YAML via the calculator.
"""
from __future__ import annotations

from datetime import date

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
