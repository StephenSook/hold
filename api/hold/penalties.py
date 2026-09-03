"""
Task 2.5: SAG-AFTRA hold day penalty calculator.

Computes the integer-cent cost of hold days for each cast member.
All figures from rules/sag_rates.yaml. No hand-typed numbers here.

D7: Headline numbers come from docs/FACTS.json only (written by scripts/facts.py).
This module computes the raw values; facts.py writes the headline.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from api.hold.registry import RuleRecord, load_rules
from api.hold.schemas import CastMember

_RULES_DIR = Path(__file__).parent.parent.parent / "rules"


class RatesError(ValueError):
    """No rate record covers the shooting date (D4: cite or refuse, never a default)."""


def _get_ph_rate_bps(shooting_date: date, rules: list[RuleRecord]) -> int:
    """The P&H rate in basis points for a shooting date, from the record valid on that date."""
    for rule in rules:
        if rule.id in ("SAG_RATES_PH_21_PCT", "SAG_RATES_PH_22_PCT") and rule.params and "ph_rate_bps" in rule.params:
            return int(rule.params["ph_rate_bps"])
    raise RatesError(f"no P&H record covers {shooting_date.isoformat()}; the registry starts at the 7/1/2026 rate sheets")


def hold_day_cost_cents(
    cast_member: CastMember,
    shooting_date: date,
    rules_dir: Path | None = None,
) -> int:
    """
    Compute the total cost (integer cents) of one hold day for one cast member.

    Cost = day_rate_cents + ph_contribution
    ph_contribution = round_half_up(day_rate_cents * ph_rate_bps / 10000)

    Rounding: standard round-half-up (math.ceil for .5 case) to nearest cent.
    """
    if rules_dir is None:
        rules_dir = _RULES_DIR

    rules = load_rules(rules_dir, shooting_date=shooting_date, jurisdictions={"SAG-AFTRA"})

    day_rate = cast_member.day_rate_cents
    ph_bps = _get_ph_rate_bps(shooting_date, rules)

    # Half-up rounding (SAG-AFTRA standard): use Decimal to avoid banker's rounding.
    # Python's built-in round() uses banker's rounding (round-half-to-even).
    # Example: 44905 * 2100 / 10000 = 9430.05 -> half-up = 9431, banker = 9430.
    ph_exact = Decimal(day_rate * ph_bps) / Decimal(10000)
    ph_cents = int(ph_exact.quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    return day_rate + ph_cents


def _record(rule_id: str, shooting_date: date, rules_dir: Path | None) -> RuleRecord:
    rules = load_rules(rules_dir or _RULES_DIR, shooting_date=shooting_date, jurisdictions={"SAG-AFTRA"})
    for rule in rules:
        if rule.id == rule_id:
            return rule
    raise RatesError(f"no {rule_id} record covers {shooting_date.isoformat()}")


def forced_call_penalty_cents(cast_member: CastMember, shooting_date: date, weekly: bool = False, rules_dir: Path | None = None) -> int:
    """Task 2.11: a forced call (a daily or weekly rest period invaded) costs the lesser of the day
    rate and the record's cap ($900 day performer, $950 weekly performer), per violation."""
    rule_id = "SAG_RATES_FORCED_CALL_WEEKLY_PERFORMER" if weekly else "SAG_RATES_FORCED_CALL_DAY_PERFORMER"
    cap = int(_record(rule_id, shooting_date, rules_dir).params["forced_call_cap_cents"])
    return min(cast_member.day_rate_cents, cap)


def meal_penalty_cents(late_minutes: int, shooting_date: date, rate_tier: str, rules_dir: Path | None = None) -> int:
    """Task 2.11: meal penalty for a meal called `late_minutes` past its due time, per performer.
    Ladder $25, $35, then $50 per half-hour or fraction; Ultra Low Budget pays a flat $25 per half-hour or part."""
    if late_minutes <= 0:
        return 0
    blocks = -(-late_minutes // 30)  # ceiling: any fraction of a half-hour counts
    if rate_tier == "ultra_low":
        flat = int(_record("SAG_RATES_MEAL_PENALTY_ULTRA_LOW_FLAT", shooting_date, rules_dir).params["meal_penalty_per_half_hour_cents"])
        return blocks * flat
    params = _record("SAG_RATES_MEAL_PENALTY_LADDER", shooting_date, rules_dir).params
    first, second, further = (int(params[k]) for k in ("meal_penalty_first_half_hour_cents", "meal_penalty_second_half_hour_cents", "meal_penalty_each_further_half_hour_cents"))
    return sum(first if i == 0 else second if i == 1 else further for i in range(blocks))


def daily_rest_violated(dismissal: datetime, next_call: datetime, shooting_date: date, rules_dir: Path | None = None) -> bool:
    """True when the gap from dismissal to the next call is shorter than the daily rest period (12 hours).
    The record's reduced-rest exceptions are not modeled; the strict figure is used."""
    hours = int(_record("SAG_RATES_REST_PERIOD_12_HOURS", shooting_date, rules_dir).params["rest_hours"])
    return next_call - dismissal < timedelta(hours=hours)


def weekly_rest_violated(last_dismissal: datetime, first_call: datetime, shooting_date: date, rules_dir: Path | None = None) -> bool:
    """True when the gap between workweeks is shorter than the weekly rest period (56 hours); exceptions not modeled."""
    hours = int(_record("SAG_RATES_WEEKLY_REST_56_HOURS", shooting_date, rules_dir).params["weekly_rest_hours"])
    return first_call - last_dismissal < timedelta(hours=hours)


def hold_days_total_cents(
    cast_member: CastMember,
    hold_dates: list[date],
    rules_dir: Path | None = None,
) -> int:
    """
    Total hold day cost for a cast member across multiple dates.
    Each date is computed independently (P&H rate may change mid-shoot).
    """
    return sum(
        hold_day_cost_cents(cast_member, d, rules_dir)
        for d in hold_dates
    )
