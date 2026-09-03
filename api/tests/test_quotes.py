"""
Task 2.10: every rule record's quote is verbatim from a committed snapshot, or labeled UNVERIFIABLE.
This test fails, never skips: a record without a status, a PENDING status, a missing snapshot, a
quote that is not a substring of its snapshot, or a snapshot fetched from a different URL is red.
"""
from __future__ import annotations

import json
import shutil
import tempfile
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


def _matches(key: str, value: object, text: str) -> bool:
    return any(pattern.search(text) for pattern in number_candidates(key, value))


def test_number_candidates_cover_the_ways_sources_write_numbers() -> None:
    assert _matches("age_max", 15, "not attained the age of sixteen (16) years")  # exclusive upper bound phrasing
    assert _matches("ph_rate_bps", 2100, "contribution is 21% for performers")
    assert _matches("max_meal_extension_minutes", 30, "longer than one half (1/2) hour")
    assert _matches("day_rate_cents", 83400, "Low Budget Daily Rate: $834")
    assert _matches("threshold_usd", 500, "compensation of five hundred dollars or more")
    assert _matches("max_location_hours", 9.5, "maximum of 9.5 hours on the set")
    assert _matches("max_work_hours_school_day", 5, "not more than five (5) hours of work")
    assert _matches("min_meal_duration_minutes", 30, "alternative 30-minute meal break")
    assert not _matches("min_meal_duration_minutes", 6, "within six (6) hours of start time")


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


def _mutated(tmp_path: Path, yaml_name: str, old: str, new: str) -> list[str]:
    rules_copy = Path(tempfile.mkdtemp(dir=tmp_path)) / "rules"  # a fresh copy per mutation
    shutil.copytree(RULES, rules_copy)
    target = rules_copy / yaml_name
    text = target.read_text()
    assert text.count(old) == 1, (old, text.count(old))
    target.write_text(text.replace(old, new))
    problems, _ = verify_rules(rules_copy, rules_copy / "sources", rules_copy / "verification.json")
    return [p.record_id for p in problems]


def test_a_number_must_carry_its_unit_in_the_evidence(tmp_path: Path) -> None:
    """Round three, finding 2: a bare digit elsewhere in the sentence must not evidence a param."""
    assert "GA_300_7_1_03_first_meal_within_6_hours" in _mutated(tmp_path, "ga.yaml", "min_meal_duration_minutes: 30", "min_meal_duration_minutes: 6")  # "six (6) hours" is not six minutes
    assert "GA_300_7_1_03_ages_9_15_location_hours" in _mutated(tmp_path, "ga.yaml", "max_location_hours: 10\n    age_min: 9\n    age_max: 15", "max_location_hours: 12\n    age_min: 9\n    age_max: 15")  # "12:00 midnight" is not 12 hours
    assert "SAG_RATES_PH_21_PCT" in _mutated(tmp_path, "sag_rates.yaml", "ph_rate_bps: 2100", "ph_rate_bps: 21")  # "21%" is 2100 bps, not 21
    assert "GA_300_7_1_03_school_night_curfew" in _mutated(tmp_path, "ga.yaml", 'curfew_school_night: "22:00"\n    age_min: 9', 'curfew_school_night: "23:00"\n    age_min: 9')  # a clock time is checked too


def test_derived_is_addition_of_evidenced_numbers_only(tmp_path: Path) -> None:
    assert "SAG_MINORS_9_15_WORK_HOURS_NON_SCHOOL" in _mutated(
        tmp_path, "sag_minors.yaml", "max_work_hours_non_school_day: 7\n", "max_work_hours_non_school_day: 10\n"
    )
    assert "SAG_MINORS_9_15_WORK_HOURS_NON_SCHOOL" in _mutated(
        tmp_path, "sag_minors.yaml", "derived: 7 = 5 + 2;", "derived: 7 = 5 * 2 - 3;"
    )


def test_assumed_and_derived_values_are_pinned_exactly() -> None:
    from api.hold.registry import load_rules

    notes = {r.id: r.note for r in load_rules(RULES)}
    assert "assumption: 1.0 " in notes["SAG_RATES_HOLD_DAY_FULL_RATE"]
    assert "derived: 7 = 5 + 2;" in notes["SAG_MINORS_9_15_WORK_HOURS_NON_SCHOOL"]
    assert "derived: 8 = 6 + 2;" in notes["SAG_MINORS_16_17_WORK_HOURS_NON_SCHOOL"]


def test_word_numbers_match_whole_words_only() -> None:
    assert not any(pattern.search("done and dusted") for pattern in number_candidates("max_work_hours", 1))
    assert any(pattern.search("one (1) hour of rest") for pattern in number_candidates("min_rest_minutes", 60))
    assert any(pattern.search("no later than 10:00 p.m.") for pattern in number_candidates("curfew_school_night", "22:00"))
    assert any(pattern.search("and 12:00 midnight on") for pattern in number_candidates("curfew_non_school_night", "00:00"))
    assert not any(pattern.search("no later than 10:00 p.m.") for pattern in number_candidates("curfew_school_night", "23:00"))
