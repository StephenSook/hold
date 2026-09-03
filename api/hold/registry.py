"""
Task 2.1: Rules registry loader for HOLD.

Loads rule records from YAML files under rules/*.yaml.
Enforces schema: every record must have citation and quote.
Records missing either are UNVERIFIABLE and excluded from claims.
Filters by temporal validity (valid_from <= shooting_date <= valid_to).

D4: Cite or refuse. No legal value ships without verbatim quote + citation.
D13: This registry feeds the checker (source of truth for violations).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RuleRecord:
    """One rule record loaded from a rules/*.yaml file."""

    id: str
    jurisdiction: str
    authority: str
    citation: str
    title: str
    quote: str
    source_url: str
    valid_from: date
    valid_to: date | None
    params: dict[str, Any]
    verified: str   # "VERIFIED", "UNVERIFIABLE", "PENDING"
    note: str


class RegistryError(ValueError):
    """Raised when a rule record fails schema validation."""


def _parse_date(s: str) -> date:
    return date.fromisoformat(s)


def _load_yaml_records(path: Path) -> list[dict[str, Any]]:
    """
    Minimal YAML parser for our rule files.
    Handles only the subset of YAML we emit: string scalars, null, block mappings.
    No PyYAML dependency (mirrors the lane-enforcement test pattern).
    """
    text = path.read_text(encoding="utf-8")

    records: list[dict[str, Any]] = []
    current: dict[str, Any] = {}
    in_quote_block = False
    quote_lines: list[str] = []
    quote_indent = 0
    in_params_block = False

    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]

        # New top-level record (starts with "- id:")
        if re.match(r"^- id:\s*", line):
            if current:
                if in_quote_block:
                    current["quote"] = " ".join(quote_lines).strip()
                    in_quote_block = False
                    quote_lines = []
                records.append(current)
            current = {"id": re.sub(r"^- id:\s*", "", line).strip().strip("\"'")}
            in_params_block = False
            i += 1
            continue

        # Inside a record
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue

        # Detect block scalar for quote (quote: |)
        m = re.match(r"^  (quote):\s*\|", line)
        if m:
            in_quote_block = True
            in_params_block = False
            quote_lines = []
            quote_indent = len(line) - len(line.lstrip()) + 2
            i += 1
            continue

        if in_quote_block:
            # Block scalar ends when indentation drops
            if line and not line.startswith(" " * quote_indent):
                current["quote"] = " ".join(quote_lines).strip()
                in_quote_block = False
                quote_lines = []
                # Re-process this line
                continue
            else:
                quote_lines.append(stripped)
                i += 1
                continue

        # Detect start of params block
        # "  params: null" or "  params: ~"  -> None, no sub-block
        # "  params:"  (empty)               -> start sub-block (sub-keys follow)
        m_params = re.match(r"^  params:\s*(.*)", line)
        if m_params:
            val = m_params.group(1).strip().strip("\"'")
            if val.lower() in ("null", "~"):
                current["params"] = None
                in_params_block = False
            else:
                # Empty or has inline content: start sub-block
                current["params"] = {}
                in_params_block = True
            i += 1
            continue

        # Parse params sub-keys (4-space indent)
        if in_params_block:
            m_sub = re.match(r"^    (\w+):\s*(.*)", line)
            if m_sub:
                pk, pv = m_sub.group(1), m_sub.group(2).strip().strip("\"'")
                if not isinstance(current.get("params"), dict):
                    current["params"] = {}
                # Coerce numeric values
                try:
                    current["params"][pk] = int(pv)
                except ValueError:
                    try:
                        current["params"][pk] = float(pv)
                    except ValueError:
                        current["params"][pk] = pv
                i += 1
                continue
            else:
                in_params_block = False
                # fall through to process current line as top-level field

        # Regular key: value pairs (indented under the record)
        m = re.match(r"^  (\w+):\s*(.*)", line)
        if m:
            key, val = m.group(1), m.group(2).strip().strip("\"'")
            if val.lower() == "null" or val == "~" or val == "":
                current[key] = None
            else:
                current[key] = val
        i += 1

    if current:
        if in_quote_block:
            current["quote"] = " ".join(quote_lines).strip()
        records.append(current)

    return records


def _validate_record(raw: dict[str, Any], source_file: str) -> RuleRecord:
    """
    Validate one raw record dict against the rules schema.
    Raises RegistryError if required fields are missing.
    D4: citation and quote are non-negotiable.
    """
    rid = raw.get("id", "<unknown>")

    for required in ("id", "jurisdiction", "authority", "citation", "title",
                     "source_url", "valid_from", "verified"):
        if not raw.get(required):
            raise RegistryError(
                f"Rule {rid!r} in {source_file}: missing required field {required!r}"
            )

    # D4: cite or refuse
    if not raw.get("citation"):
        raise RegistryError(f"Rule {rid!r} in {source_file}: missing citation (D4)")
    if not raw.get("quote"):
        raise RegistryError(
            f"Rule {rid!r} in {source_file}: missing quote (D4). "
            f"Mark verified='UNVERIFIABLE' and supply a placeholder to pass, "
            f"or obtain the verbatim text."
        )

    params_raw = raw.get("params")
    params: dict[str, Any] = {}
    if isinstance(params_raw, dict):
        params = params_raw

    valid_to_raw = raw.get("valid_to")

    return RuleRecord(
        id=str(raw["id"]),
        jurisdiction=str(raw["jurisdiction"]),
        authority=str(raw["authority"]),
        citation=str(raw["citation"]),
        title=str(raw["title"]),
        quote=str(raw["quote"]),
        source_url=str(raw["source_url"]),
        valid_from=_parse_date(str(raw["valid_from"])),
        valid_to=_parse_date(str(valid_to_raw)) if valid_to_raw else None,
        params=params,
        verified=str(raw["verified"]),
        note=str(raw.get("note") or ""),
    )


def is_trust_record(rule: RuleRecord) -> bool:
    """A Coogan trust record (task 2.6): a display fact, never a scheduling constraint."""
    return str(rule.params.get("kind", "")) == "trust"


def is_penalty_record(rule: RuleRecord) -> bool:
    """A SAG-AFTRA penalty or rest record (task 2.11): read by api/hold/penalties.py, never a minor's rule."""
    return str(rule.params.get("kind", "")) == "penalty"


def load_rules(
    rules_dir: Path | str,
    shooting_date: date | None = None,
    jurisdictions: set[str] | None = None,
) -> list[RuleRecord]:
    """
    Load all rule records from rules_dir/*.yaml.

    Args:
        rules_dir: Directory containing *.yaml rule files.
        shooting_date: If given, filter to records valid on this date.
        jurisdictions: If given, filter to these jurisdictions only.

    Returns:
        List of validated RuleRecord instances.

    Raises:
        RegistryError: If any record fails validation.
    """
    rules_dir = Path(rules_dir)
    records: list[RuleRecord] = []

    for yaml_file in sorted(rules_dir.glob("*.yaml")):
        if yaml_file.name.startswith("_"):
            continue
        raw_records = _load_yaml_records(yaml_file)
        for raw in raw_records:
            record = _validate_record(raw, yaml_file.name)
            records.append(record)

    if shooting_date is not None:
        records = [
            r for r in records
            if r.valid_from <= shooting_date and (r.valid_to is None or shooting_date <= r.valid_to)
        ]

    if jurisdictions is not None:
        records = [r for r in records if r.jurisdiction in jurisdictions]

    return records


def get_rule(
    rules_dir: Path | str,
    rule_id: str,
    shooting_date: date | None = None,
) -> RuleRecord | None:
    """Return a single rule by id, or None if not found."""
    for record in load_rules(rules_dir, shooting_date=shooting_date):
        if record.id == rule_id:
            return record
    return None
