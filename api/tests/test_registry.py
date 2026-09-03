"""
Task 2.1: Tests for the rules registry loader.
D4: citation and quote are required; a record missing either raises RegistryError.
"""
from __future__ import annotations

import json
import textwrap
from datetime import date
from pathlib import Path

import pytest

from api.hold.registry import RegistryError, RuleRecord, get_rule, load_rules

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_yaml(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(textwrap.dedent(content), encoding="utf-8")
    return p


VALID_RECORD_YAML = """\
- id: TEST_RULE_001
  jurisdiction: GA
  authority: Georgia Department of Labor
  citation: Ga. Comp. R. & Regs. 300-7-1-.03(2)(a)
  title: Minor performer school night curfew
  quote: |
    Minors who are between the ages of nine (9) and fifteen (15) years old shall
    not be permitted to work later than 10:00 p.m. on any night preceding a
    school day.
  source_url: https://rules.sos.ga.gov/gac/300-7-1
  valid_from: "2020-01-01"
  valid_to: null
  params: null
  verified: PENDING
  note: null
"""


# ---------------------------------------------------------------------------
# Schema validation tests
# ---------------------------------------------------------------------------


def test_valid_record_loads(tmp_path: Path) -> None:
    """A well-formed record loads without error."""
    _write_yaml(tmp_path, "test.yaml", VALID_RECORD_YAML)
    records = load_rules(tmp_path)
    assert len(records) == 1
    r = records[0]
    assert r.id == "TEST_RULE_001"
    assert r.jurisdiction == "GA"
    assert "10:00 p.m." in r.quote
    assert r.valid_to is None


def test_missing_citation_raises(tmp_path: Path) -> None:
    """A record without citation raises RegistryError (D4)."""
    yaml = VALID_RECORD_YAML.replace(
        "  citation: Ga. Comp. R. & Regs. 300-7-1-.03(2)(a)",
        "  citation: ",
    )
    _write_yaml(tmp_path, "bad.yaml", yaml)
    with pytest.raises(RegistryError, match="citation"):
        load_rules(tmp_path)


def test_missing_quote_raises(tmp_path: Path) -> None:
    """A record without quote raises RegistryError (D4)."""
    # Replace the block scalar with an empty value
    bad = VALID_RECORD_YAML.replace(
        "  quote: |\n    Minors who are between the ages of nine (9) and fifteen (15) years old shall\n    not be permitted to work later than 10:00 p.m. on any night preceding a\n    school day.\n",
        "  quote: \n",
    )
    _write_yaml(tmp_path, "bad.yaml", bad)
    with pytest.raises(RegistryError, match="quote"):
        load_rules(tmp_path)


def test_missing_required_field_raises(tmp_path: Path) -> None:
    """A record without authority raises RegistryError."""
    yaml = VALID_RECORD_YAML.replace(
        "  authority: Georgia Department of Labor",
        "  authority: ",
    )
    _write_yaml(tmp_path, "bad.yaml", yaml)
    with pytest.raises(RegistryError, match="authority"):
        load_rules(tmp_path)


# ---------------------------------------------------------------------------
# Temporal filtering
# ---------------------------------------------------------------------------


def test_temporal_filter_includes_current(tmp_path: Path) -> None:
    """A record valid on shooting_date is included."""
    _write_yaml(tmp_path, "test.yaml", VALID_RECORD_YAML)
    records = load_rules(tmp_path, shooting_date=date(2026, 10, 5))
    assert len(records) == 1


def test_temporal_filter_excludes_future(tmp_path: Path) -> None:
    """A record with valid_from in the future is excluded."""
    yaml = VALID_RECORD_YAML.replace(
        '  valid_from: "2020-01-01"',
        '  valid_from: "2030-01-01"',
    )
    _write_yaml(tmp_path, "test.yaml", yaml)
    records = load_rules(tmp_path, shooting_date=date(2026, 10, 5))
    assert len(records) == 0


def test_temporal_filter_excludes_expired(tmp_path: Path) -> None:
    """A record with valid_to before shooting_date is excluded."""
    yaml = VALID_RECORD_YAML.replace(
        "  valid_to: null",
        '  valid_to: "2025-12-31"',
    )
    _write_yaml(tmp_path, "test.yaml", yaml)
    records = load_rules(tmp_path, shooting_date=date(2026, 10, 5))
    assert len(records) == 0


# ---------------------------------------------------------------------------
# Jurisdiction filtering
# ---------------------------------------------------------------------------


def test_jurisdiction_filter(tmp_path: Path) -> None:
    """Only records matching the jurisdiction filter are returned."""
    _write_yaml(tmp_path, "test.yaml", VALID_RECORD_YAML)
    assert len(load_rules(tmp_path, jurisdictions={"GA"})) == 1
    assert len(load_rules(tmp_path, jurisdictions={"CA"})) == 0


# ---------------------------------------------------------------------------
# get_rule helper
# ---------------------------------------------------------------------------


def test_get_rule_found(tmp_path: Path) -> None:
    """get_rule returns the matching record by id."""
    _write_yaml(tmp_path, "test.yaml", VALID_RECORD_YAML)
    r = get_rule(tmp_path, "TEST_RULE_001")
    assert r is not None
    assert isinstance(r, RuleRecord)


def test_get_rule_not_found(tmp_path: Path) -> None:
    """get_rule returns None for an unknown id."""
    _write_yaml(tmp_path, "test.yaml", VALID_RECORD_YAML)
    assert get_rule(tmp_path, "NONEXISTENT") is None


# ---------------------------------------------------------------------------
# Multiple records and files
# ---------------------------------------------------------------------------


def test_multiple_records_in_file(tmp_path: Path) -> None:
    """Two records in one YAML file both load correctly."""
    two_records = VALID_RECORD_YAML + """\
- id: TEST_RULE_002
  jurisdiction: CA
  authority: California DIR
  citation: 8 CCR 11760(e)
  title: Max work hours age 9-15 non-school day
  quote: |
    Minors from nine (9) years of age to fifteen (15) years of age:
    eight (8) hours of work on non-school days.
  source_url: https://www.dir.ca.gov/iwc/wageorders/IWCArticle12.pdf
  valid_from: "2020-01-01"
  valid_to: null
  params: null
  verified: PENDING
  note: null
"""
    _write_yaml(tmp_path, "multi.yaml", two_records)
    records = load_rules(tmp_path)
    assert len(records) == 2
    ids = {r.id for r in records}
    assert "TEST_RULE_001" in ids
    assert "TEST_RULE_002" in ids


def test_files_with_underscore_prefix_skipped(tmp_path: Path) -> None:
    """Files starting with _ are ignored (reserved for schema/docs)."""
    _write_yaml(tmp_path, "_schema.yaml", VALID_RECORD_YAML)
    records = load_rules(tmp_path)
    assert len(records) == 0


def test_schema_jurisdictions_cover_the_five_trust_states() -> None:
    """Contract change announced in PLAN.md Shared Contracts (6b75832): NY, IL, LA, NM join the enum for task 2.6."""
    schema = json.loads((Path(__file__).parents[2] / "rules" / "schema.json").read_text())
    assert {"CA", "GA", "NY", "IL", "LA", "NM", "SAG-AFTRA"} <= set(schema["properties"]["jurisdiction"]["enum"])
