"""
Task 2.10: quote verification for the rules registry (D4: cite or refuse).

Every VERIFIED record's `quote` must be a substring of the committed text snapshot of its
`source_url` under rules/sources/, after a whitespace, hyphen and quote-mark normalization
that absorbs PDF extraction artifacts without changing any word. Every UNVERIFIABLE record
must carry a reason in rules/verification.json and a note in the record. PENDING is refused.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from api.hold.registry import RuleRecord, load_rules

# Curly quotes, em and en dashes, and the soft hyphen, written as escapes so this file holds
# none of the characters it normalizes away.
_QUOTE_MARKS = {"\u2019": "'", "\u2018": "'", "\u201c": '"', "\u201d": '"', "\u2014": "-", "\u2013": "-", "\u00ad": ""}


def normalize(text: str) -> str:
    """Straighten quote marks, drop hyphens and soft hyphens, collapse whitespace. Words are untouched."""
    for src, dst in _QUOTE_MARKS.items():
        text = text.replace(src, dst)
    return re.sub(r"\s+", " ", text.replace("-", "")).strip()


def snapshot_url(path: Path) -> str:
    """The source URL recorded on a snapshot's first line ('# Snapshot of <url>', '# Excerpt of <url>')."""
    first = path.read_text(encoding="utf-8").splitlines()[0]
    marker = " of "
    if not first.startswith("#") or marker not in first:
        raise ValueError(f"{path.name}: first line does not name its source URL")
    return first.split(marker, 1)[1].strip()


@dataclass(frozen=True)
class Problem:
    record_id: str
    what: str


def verify_rules(rules_dir: Path, sources_dir: Path, verification_path: Path) -> tuple[list[Problem], dict[str, int]]:
    """Check every record. Returns (problems, counts). An empty problem list is the only pass."""
    records: list[RuleRecord] = load_rules(rules_dir)
    ver = json.loads(verification_path.read_text(encoding="utf-8"))
    entries: dict[str, dict[str, object]] = ver.get("records", {})
    snapshots: dict[str, dict[str, object]] = ver.get("snapshots", {})
    problems: list[Problem] = []
    counts = {"records": len(records), "verified": 0, "unverifiable": 0}

    for name in snapshots:
        if not (sources_dir / name).exists():
            problems.append(Problem("<snapshots>", f"listed snapshot missing on disk: {name}"))
    for path in sources_dir.glob("*.txt"):
        if path.name not in snapshots:
            problems.append(Problem("<snapshots>", f"snapshot on disk not listed in verification.json: {path.name}"))

    texts: dict[str, str] = {}
    for r in records:
        entry = entries.get(r.id)
        if entry is None:
            problems.append(Problem(r.id, "no entry in verification.json"))
            continue
        status = entry.get("status")
        if r.verified != status:
            problems.append(Problem(r.id, f"yaml says {r.verified}, verification.json says {status}"))
        if status == "VERIFIED":
            counts["verified"] += 1
            snap = entry.get("snapshot")
            if not isinstance(snap, str) or not (sources_dir / snap).exists():
                problems.append(Problem(r.id, f"VERIFIED without a snapshot on disk: {snap!r}"))
                continue
            if snapshot_url(sources_dir / snap) != r.source_url:
                problems.append(Problem(r.id, f"snapshot {snap} was fetched from a different URL than source_url"))
            if snap not in texts:
                texts[snap] = normalize((sources_dir / snap).read_text(encoding="utf-8"))
            if normalize(r.quote) not in texts[snap]:
                problems.append(Problem(r.id, f"quote is not a verbatim substring of {snap}"))
        elif status == "UNVERIFIABLE":
            counts["unverifiable"] += 1
            if not entry.get("reason"):
                problems.append(Problem(r.id, "UNVERIFIABLE without a reason in verification.json"))
            if not r.note:
                problems.append(Problem(r.id, "UNVERIFIABLE without a note on the record"))
        else:
            problems.append(Problem(r.id, f"status {status!r} is not VERIFIED or UNVERIFIABLE (PENDING is refused)"))
    for rid in entries:
        if rid not in {r.id for r in records}:
            problems.append(Problem(rid, "verification.json names a record that no longer exists"))
    return problems, counts
