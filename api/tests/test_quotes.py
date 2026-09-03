"""
Task 2.10: every rule record's quote is verbatim from a committed snapshot, or labeled UNVERIFIABLE.
This test fails, never skips: a record without a status, a PENDING status, a missing snapshot, a
quote that is not a substring of its snapshot, or a snapshot fetched from a different URL is red.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from api.hold.quotes import (
    normalize,
    number_candidates,
    quote_matches,
    snapshot_variants,
    verify_rules,
)

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
    assert normalize("half-hour  meal\nbreak") == "half-hour meal break"
    assert normalize("minors’ work") == "minors' work"
    assert normalize("five hours") != normalize("six hours")
    assert normalize("12 hours") != normalize("1-2 hours")
    assert normalize("seven (7)") != normalize("se-ven (7)")


def test_line_end_hyphen_reads_both_ways() -> None:
    """A hyphen at a line end is either a real hyphen or an extraction artifact; a quote may match either."""
    kept, dropped = snapshot_variants("employ-\nment and non-\nschool")
    assert normalize("employment") in dropped and normalize("employment") not in kept
    assert normalize("non-school") in kept and normalize("non-school") not in dropped


def test_letter_hyphens_are_optional_but_digit_hyphens_are_not() -> None:
    assert quote_matches("one half-hour meal break", snapshot_variants("and one halfhour meal break."))
    assert quote_matches("one halfhour meal break", snapshot_variants("and one half-hour meal break."))
    assert not quote_matches("12 hours", snapshot_variants("at least 1-2 hours"))
    assert not quote_matches("1-2 hours", snapshot_variants("at least 12 hours"))
    assert not quote_matches("12 hours", snapshot_variants("at least 1-\n2 hours"))  # a line-end hyphen between digits stays
    assert quote_matches("employment", snapshot_variants("employ-\nment"))


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


def test_a_mutated_param_turns_the_check_red(tmp_path: Path) -> None:
    """A number in params that no verified sentence states is a fabrication the quote check alone
    cannot see: 30 to 45 minutes must be reported."""
    rules_copy = tmp_path / "rules"
    shutil.copytree(RULES, rules_copy)
    ga = rules_copy / "ga.yaml"
    text = ga.read_text()
    assert text.count("min_meal_duration_minutes: 30") == 1
    ga.write_text(text.replace("min_meal_duration_minutes: 30", "min_meal_duration_minutes: 45"))
    problems, _ = verify_rules(rules_copy, rules_copy / "sources", rules_copy / "verification.json")
    assert [p.record_id for p in problems] == ["GA_300_7_1_03_first_meal_within_6_hours"], problems
    assert "min_meal_duration_minutes=45" in problems[0].what


def test_assumed_params_are_exactly_the_known_set() -> None:
    _, counts = verify_rules(RULES, SOURCES, VERIFICATION)
    assert counts["assumed_params"] == 1, counts  # hold_day_rate_multiplier: the FAQ says the day is paid, not a multiplier


def test_number_candidates_cover_the_ways_sources_write_numbers() -> None:
    assert "sixteen" in number_candidates("age_max", 15)  # exclusive upper bound phrasing
    assert "21%" in number_candidates("ph_rate_bps", 2100)
    assert "half" in number_candidates("max_meal_extension_minutes", 30)
    assert "$834" in number_candidates("day_rate_cents", 83400)
    assert "five hundred" in number_candidates("threshold_usd", 500)


def test_derived_and_evidence_uses_are_exactly_the_known_records() -> None:
    """derived: proves arithmetic and evidence: proves a fragment exists in the snapshot; neither proves the
    fragment belongs to the param. The records that use them are pinned, so a new use is a visible review event."""
    from api.hold.registry import load_rules

    notes = {r.id: r.note for r in load_rules(RULES)}
    assert {rid for rid, n in notes.items() if "derived:" in n} == {
        "SAG_MINORS_9_15_WORK_HOURS_NON_SCHOOL", "SAG_MINORS_16_17_WORK_HOURS_NON_SCHOOL",
    }
    assert {rid for rid, n in notes.items() if "assumption:" in n} == {"SAG_RATES_HOLD_DAY_FULL_RATE"}
    assert {rid for rid, n in notes.items() if 'evidence' in n and '"' in n} == {
        "CA_11760_e_work_hours_9_15_non_school_day", "CA_11760_f_work_hours_16_17_non_school_day",
        "GA_300_7_1_03_ages_9_15_location_hours", "GA_300_7_1_03_ages_9_15_work_hours",
        "GA_300_7_1_03_school_night_curfew", "GA_300_7_1_03_non_school_night_curfew",
        "GA_300_7_1_03_ages_16_17_location_hours", "GA_300_7_1_03_ages_16_17_work_hours",
        "GA_300_7_1_03_ages_16_17_school_night_curfew", "GA_300_7_1_03_ages_16_17_non_school_night_curfew",
        "GA_300_7_1_03_first_meal_within_6_hours",
        "SAG_MINORS_9_15_WORK_HOURS_NON_SCHOOL", "SAG_MINORS_16_17_WORK_HOURS_NON_SCHOOL",
    }
