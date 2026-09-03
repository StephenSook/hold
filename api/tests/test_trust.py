"""
Task 2.6: Coogan trust facts for five states (PLAN.md D17), display only, Georgia explicitly absent.
Every record is verbatim-verified by test_quotes.py; this module checks the facts HOLD displays.
"""
from __future__ import annotations

from pathlib import Path

from api.hold.legality_checker import rule_applies_to_minor
from api.hold.schemas import CastMember
from api.hold.trust import NO_TRUST_STATUTE, TRUST_STATES, trust_facts, trust_records

RULES = Path(__file__).parents[2] / "rules"
_MINOR = CastMember(id="cM", letter="M", age=14, resident_state="CA", day_rate_cents=83400, rate_tier="low_budget")


def test_five_states_and_georgia_explicitly_absent() -> None:
    facts = trust_facts(RULES)
    assert set(facts) == set(TRUST_STATES) == {"CA", "NY", "IL", "LA", "NM"}
    assert "GA" not in facts
    assert "Georgia" in NO_TRUST_STATUTE["GA"] and "GA" not in TRUST_STATES


def test_percent_and_contract_thresholds() -> None:
    facts = trust_facts(RULES)
    assert {s: f.percent for s, f in facts.items()} == dict.fromkeys(TRUST_STATES, 15)
    assert {s: f.threshold_usd for s, f in facts.items()} == {"CA": 0, "NY": 0, "IL": 0, "LA": 500, "NM": 1000}


def test_illinois_definition_stops_at_sixteen() -> None:
    record = next(r for r in trust_records(RULES) if r.id == "IL_820_ILCS_206_90_a_child_performer_under_16")
    assert record.params["covers_under_age"] == 16


def test_trust_records_are_verified_display_facts_that_never_apply() -> None:
    records = trust_records(RULES)
    assert len(records) == 9
    for r in records:
        assert r.verified == "VERIFIED", r.id
        assert r.params["kind"] == "trust", r.id
        assert not rule_applies_to_minor(r, _MINOR, "CA"), r.id
        assert not rule_applies_to_minor(r, _MINOR, "GA"), r.id
