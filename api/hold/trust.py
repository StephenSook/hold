"""
Task 2.6: Coogan trust facts for five states (PLAN.md D17), display only.

Every record lives in rules/trust.yaml with params.kind: trust, which rule_applies_to_minor refuses,
so nothing here is ever a scheduling constraint. Georgia has no trust set-aside; that absence is a
stated fact, not a missing record.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from api.hold.registry import RuleRecord, is_trust_record, load_rules

TRUST_STATES: tuple[str, ...] = ("CA", "NY", "IL", "LA", "NM")

NO_TRUST_STATUTE: dict[str, str] = {
    "GA": "No Georgia trust set-aside for child performers was found in Ga. Comp. R. & Regs. 300-7-1 or on "
    "the Department of Labor's Schedule of Hours of Performance (checked 2026-09-02); HOLD claims none.",
}


@dataclass(frozen=True)
class TrustFacts:
    state: str
    percent: int
    threshold_usd: int
    records: tuple[RuleRecord, ...]


def trust_records(rules_dir: Path | str) -> list[RuleRecord]:
    return [r for r in load_rules(rules_dir) if is_trust_record(r)]


def trust_facts(rules_dir: Path | str) -> dict[str, TrustFacts]:
    """One entry per state that has records; a state absent here has no trust set-aside on file."""
    by_state: dict[str, list[RuleRecord]] = {}
    for r in trust_records(rules_dir):
        by_state.setdefault(str(r.params["state"]), []).append(r)
    facts: dict[str, TrustFacts] = {}
    for state, records in by_state.items():
        percents = {int(r.params["percent"]) for r in records if "percent" in r.params}
        if len(percents) != 1:
            raise ValueError(f"{state}: trust records must state exactly one percentage, found {sorted(percents)}")
        threshold = max((int(r.params.get("threshold_usd", 0)) for r in records), default=0)
        facts[state] = TrustFacts(state=state, percent=percents.pop(), threshold_usd=threshold, records=tuple(records))
    return facts
