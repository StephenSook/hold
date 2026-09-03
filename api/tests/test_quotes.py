"""
Task 2.10: every rule record's quote is verbatim from a committed snapshot, or labeled UNVERIFIABLE.
This test fails, never skips: a record without a status, a PENDING status, a missing snapshot, a
quote that is not a substring of its snapshot, or a snapshot fetched from a different URL is red.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from api.hold.quotes import normalize, verify_rules

ROOT = Path(__file__).parents[2]
RULES = ROOT / "rules"
SOURCES = RULES / "sources"
VERIFICATION = RULES / "verification.json"


def test_every_record_is_verified_or_labeled() -> None:
    problems, counts = verify_rules(RULES, SOURCES, VERIFICATION)
    assert problems == [], "\n".join(f"{p.record_id}: {p.what}" for p in problems)
    assert counts["records"] > 0
    assert counts["verified"] + counts["unverifiable"] == counts["records"]
    assert counts["unverifiable"] <= 1, counts  # the one sagaftra.org page that refuses scripted fetches


def test_no_record_is_pending() -> None:
    for yaml in RULES.glob("*.yaml"):
        assert "verified: PENDING" not in yaml.read_text(), yaml.name


def test_normalize_absorbs_extraction_artifacts_only() -> None:
    assert normalize("half-hour  meal\nbreak") == "halfhour meal break"
    assert normalize("minors’ work") == "minors' work"
    assert normalize("five hours") != normalize("six hours")


def test_a_corrupted_quote_turns_the_check_red(tmp_path: Path) -> None:
    """Guard the guard: change one word of one quote and the verifier must report it."""
    rules_copy = tmp_path / "rules"
    shutil.copytree(RULES, rules_copy)
    ga = rules_copy / "ga.yaml"
    text = ga.read_text()
    assert text.count("No work day shall start earlier than 5:00 A.M.") == 1
    ga.write_text(text.replace("No work day shall start earlier than 5:00 A.M.", "No work day shall start earlier than 6:00 A.M."))
    problems, _ = verify_rules(rules_copy, rules_copy / "sources", rules_copy / "verification.json")
    assert [p.record_id for p in problems] == ["GA_300_7_1_03_earliest_call"], problems


def test_a_missing_entry_turns_the_check_red(tmp_path: Path) -> None:
    rules_copy = tmp_path / "rules"
    shutil.copytree(RULES, rules_copy)
    ver = json.loads((rules_copy / "verification.json").read_text())
    del ver["records"]["CA_11760_i_turnaround_12_hours"]
    (rules_copy / "verification.json").write_text(json.dumps(ver))
    problems, _ = verify_rules(rules_copy, rules_copy / "sources", rules_copy / "verification.json")
    assert any(p.record_id == "CA_11760_i_turnaround_12_hours" and "no entry" in p.what for p in problems), problems
