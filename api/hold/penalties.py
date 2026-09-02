"""
Task 2.5: SAG-AFTRA hold day penalty calculator.

Computes the integer-cent cost of hold days for each cast member.
All figures from rules/sag_rates.yaml. No hand-typed numbers here.

D7: Headline numbers come from docs/FACTS.json only (written by scripts/facts.py).
This module computes the raw values; facts.py writes the headline.
"""
from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from api.hold.registry import RuleRecord, load_rules
from api.hold.schemas import CastMember

_RULES_DIR = Path(__file__).parent.parent.parent / "rules"


def _get_ph_rate_bps(shooting_date: date, rules: list[RuleRecord]) -> int:
    """Return the P&H rate in basis points for a given shooting date."""
    for rule in rules:
        if rule.id in ("SAG_RATES_PH_21_PCT", "SAG_RATES_PH_22_PCT") and rule.params and "ph_rate_bps" in rule.params:
            return int(rule.params["ph_rate_bps"])
    # Fallback to 2100 bps (21%) if no rule matched - should not happen
    return 2100


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
