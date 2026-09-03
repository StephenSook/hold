"""
Task 3.6: docs/FACTS.json is written only by scripts/facts.py from a real run (PLAN.md D7).
A hand edit fails here because the deterministic fields are recomputed; README and docs are
held to the same numbers, digits or spelled out.
"""
from __future__ import annotations

import json
from pathlib import Path

from api.hold.facts import DETERMINISTIC_FIELDS, HEADLINE_FIELDS, compute_facts, headline_mismatches
from api.hold.registry import load_rules

ROOT = Path(__file__).parents[2]
FACTS = ROOT / "docs" / "FACTS.json"


def _rules_dollars() -> set[float]:
    """Dollar figures the rules registry states (day rates and the like) may appear in prose freely."""
    return {float(v) / 100 for r in load_rules(ROOT / "rules") for k, v in r.params.items() if k.endswith("_cents")}


def test_facts_has_the_eight_headline_fields() -> None:
    facts = json.loads(FACTS.read_text())
    assert set(HEADLINE_FIELDS) <= set(facts), sorted(set(HEADLINE_FIELDS) - set(facts))
    assert facts["constructed"] is True  # D8: the demo is constructed data and says so


def test_facts_reproduces_from_a_fresh_run() -> None:
    fresh = compute_facts(ROOT, time_limit_s=30.0)
    committed = json.loads(FACTS.read_text())
    for key in DETERMINISTIC_FIELDS:
        assert committed[key] == fresh[key], (key, committed[key], fresh[key])


def test_readme_and_docs_numerals_match_facts() -> None:
    facts = json.loads(FACTS.read_text())
    allow = _rules_dollars()
    # docs/bob-evidence holds generated logs of commit subjects (history, not claims), so it is not scanned.
    texts = [ROOT / "README.md", *sorted(p for p in (ROOT / "docs").rglob("*.md") if "bob-evidence" not in p.parts)]
    problems = [f"{p.name}: {m}" for p in texts for m in headline_mismatches(p.read_text(), facts, allow)]
    assert problems == [], "\n".join(problems)


def test_headline_guard_catches_a_wrong_numeral() -> None:
    facts = {"hold_days_before": 4, "hold_days_after": 0, "illegal_days_before": 1, "illegal_days_after": 0,
             "payroll_removed_usd": 1234.5, "benchmark_matched": "8/8"}
    assert headline_mismatches("The plan cut four hold days and 1 illegal day to zero hold days.", facts, set()) == []
    assert headline_mismatches("It removed seven hold days.", facts, set())
    assert headline_mismatches("Two illegal days became none.", facts, set())
    assert headline_mismatches("It matched 7/8 benchmark instances.", facts, set())
    assert headline_mismatches("$999 of payroll removed.", facts, set())
    assert headline_mismatches("$1,234.50 of payroll removed.", facts, set()) == []
    assert headline_mismatches("A paid hold day at the $834 day rate.", facts, {834.0}) == []


def test_eval_case_counts_in_prose_are_held_to_facts() -> None:
    """A hand-typed "passes 4 of 4 cases" survived a recorded 2 of 4 (3646ba0); the scan holds both numbers."""
    from api.hold.facts import headline_mismatches

    facts = {"hold_days_before": 4, "hold_days_after": 0, "illegal_days_before": 1, "illegal_days_after": 0, "benchmark_matched": "8/8", "payroll_removed_usd": 4069.92, "adk_eval": {"passed": 2, "failed": 2}}
    assert headline_mismatches("The eval set passes 4 of 4 cases.", facts, []) != []
    assert headline_mismatches("The eval set passes 2 of 4 cases.", facts, []) == []
    assert headline_mismatches("The eval set passes two of four cases.", facts, []) == []
    assert headline_mismatches("The eval set passes 4 of 4 cases.", {**facts, "adk_eval": None}, []) != []  # no run recorded: no claim allowed
