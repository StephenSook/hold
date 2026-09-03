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
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from api.hold.registry import RuleRecord, load_rules

# Curly quotes, em and en dashes, and the soft hyphen, written as escapes so this file holds
# none of the characters it normalizes away.
_QUOTE_MARKS = {"\u2019": "'", "\u2018": "'", "\u201c": '"', "\u201d": '"', "\u2014": "-", "\u2013": "-", "\u00ad": ""}


_LINE_END_HYPHEN = re.compile(r"(?<=[A-Za-z])-[ \t]*\n[ \t]*(?=[A-Za-z])")  # only a word broken across a line


def normalize(text: str) -> str:
    """Straighten quote marks, map dashes to a hyphen, drop soft hyphens, collapse whitespace.
    Words, numbers and hyphens are untouched, so "1-2 hours" never reads as "12 hours"."""
    for src, dst in _QUOTE_MARKS.items():
        text = text.replace(src, dst)
    return re.sub(r"\s+", " ", text).strip()


def snapshot_variants(text: str) -> tuple[str, str]:
    """Two readings of a snapshot: a hyphen at a line end kept (a real hyphen) and dropped (an
    extraction artifact). A quote matches when it matches either reading."""
    return normalize(_LINE_END_HYPHEN.sub("-", text)), normalize(_LINE_END_HYPHEN.sub("", text))


_LETTER_HYPHEN = re.compile(r"(?<=[A-Za-z])-(?=[A-Za-z])")


def quote_matches(quote: str, variants: tuple[str, str]) -> bool:
    """A quote matches a snapshot reading verbatim, or with hyphens between two letters treated
    as optional on both sides (PDF reading-order extraction joins words hyphenated at a line end,
    so "half-hour" arrives as "halfhour"). A hyphen touching a digit is never optional."""
    nq = normalize(quote)
    if any(nq in v for v in variants):
        return True
    return _LETTER_HYPHEN.sub("", nq) in _LETTER_HYPHEN.sub("", variants[0])


# ---------------------------------------------------------------------------
# Numeric params must be stated by evidence. A quote proves its sentence; the numbers in
# `params` are transcribed by hand, so each one must appear in the quote, in a second verbatim
# fragment named in the note (evidence: "..."; evidence[<snapshot>]: "..." for another listed
# snapshot), be derived from evidenced numbers (derived: 7 = 5 + 2), or be a counted assumption
# (assumption: 1.0). A number that meets none of these is reported. What this proves: the quote
# exists, each fragment exists in its snapshot, the arithmetic holds, and the assumption count
# is pinned. What it cannot prove: that a fragment belongs to the param it backs, so the records
# that use derived:, evidence: or assumption: are pinned by name in api/tests/test_quotes.py.
# ---------------------------------------------------------------------------

_WORDS = {
    0: "zero", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight",
    9: "nine", 10: "ten", 11: "eleven", 12: "twelve", 13: "thirteen", 14: "fourteen", 15: "fifteen",
    16: "sixteen", 17: "seventeen", 18: "eighteen", 19: "nineteen", 20: "twenty", 21: "twenty-one",
    22: "twenty-two", 24: "twenty-four", 30: "thirty", 40: "forty", 45: "forty-five", 48: "forty-eight",
    50: "fifty", 56: "fifty-six", 60: "sixty", 90: "ninety", 100: "one hundred", 500: "five hundred",
    1000: "one thousand",
}
_EVIDENCE = re.compile(r'evidence(?:\[([^\]]+)\])?: "([^"]+)"')
_DERIVED = re.compile(r"derived: ([0-9.]+) = ([0-9.+\-*/() ]+?)(?=[;,.]|$)")
_ASSUMPTION = re.compile(r"assumption: ([0-9.]+)")


def _plain(value: float) -> set[str]:
    out = {f"{value:g}"}
    if float(value).is_integer() and int(value) in _WORDS:
        out.add(_WORDS[int(value)])
    return out


def number_candidates(key: str, value: float) -> set[str]:
    """The spellings a source may use for one param value, keyed by the param's unit suffix."""
    out = _plain(value)
    if key.endswith("_minutes"):
        out |= _plain(value / 60)
        if value == 30:
            out |= {"half", "1/2"}
        if value == 15:
            out.add("quarter")
    if key.endswith("_cents"):
        dollars = value / 100
        out |= {f"${dollars:,.0f}", f"${dollars:,.2f}", f"{dollars:,.0f}", f"{dollars:.0f}"}
    if key.endswith("_bps"):
        pct = value / 100
        out |= {f"{pct:g}%", f"{pct:g} percent"}
    if key.endswith("_usd"):
        out |= {f"${value:,.0f}", f"${value:.0f}", f"{value:,.0f}"}
    if key == "age_max":
        out |= _plain(value + 1)  # "not attained the age of sixteen (16)", "9 years to 16 years"
    if key.endswith("_hours") and value % 1 == 0.5:
        whole = int(value)
        out |= {f"{whole} 1/2", f"{_WORDS.get(whole, '')} and one-half", f"{_WORDS.get(whole, '')} and a half"}
    return {c for c in out if c and not c.startswith(" and")}


def _states(text: str, candidate: str) -> bool:
    """Digit candidates match as whole numbers ("5" is not inside "15"); words match as substrings."""
    if re.fullmatch(r"[0-9.]+", candidate):
        return re.search(rf"(?<![0-9.]){re.escape(candidate)}(?![0-9.])", text) is not None
    return candidate.lower() in text


def _safe_eval(expr: str) -> float | None:
    if not re.fullmatch(r"[0-9.+\-*/() ]+", expr):
        return None
    try:
        return float(eval(expr, {"__builtins__": {}}))  # noqa: S307 - digits and operators only, checked above
    except (SyntaxError, ZeroDivisionError, TypeError, ValueError):
        return None


def params_evidence_problems(
    record: RuleRecord,
    own_snapshot: str,
    variants_by_snapshot: Mapping[str, tuple[str, str]],
) -> tuple[list[Problem], int]:
    """Problems for numeric params no evidence states, and the count of params marked assumption."""
    problems: list[Problem] = []
    note = record.note or ""
    evidence: list[str] = []
    for snap_name, fragment in _EVIDENCE.findall(note):
        target = snap_name or own_snapshot
        variants = variants_by_snapshot.get(target)
        if variants is None:
            problems.append(Problem(record.id, f"evidence names a snapshot that is not listed: {target}"))
            continue
        if not quote_matches(fragment, variants):
            problems.append(Problem(record.id, f"evidence fragment is not a verbatim substring of {target}: {fragment!r}"))
            continue
        evidence.append(normalize(fragment))
    text = " ".join([normalize(record.quote), *evidence]).lower()
    derived = {float(lhs): expr for lhs, expr in _DERIVED.findall(note)}
    assumed = {float(v) for v in _ASSUMPTION.findall(note)}
    assumed_count = 0
    for key, value in record.params.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        if any(_states(text, c) for c in number_candidates(key, float(value))):
            continue
        expr = derived.get(float(value))
        if expr is not None:
            result = _safe_eval(expr)
            operands = re.findall(r"[0-9]+(?:\.[0-9]+)?", expr)
            if result is not None and abs(result - float(value)) < 1e-9 and all(
                any(_states(text, c) for c in _plain(float(o))) for o in operands
            ):
                continue
            problems.append(Problem(record.id, f"param {key}={value:g} derived from {expr!r} but an operand is not evidenced or the arithmetic is wrong"))
            continue
        if float(value) in assumed:
            assumed_count += 1
            continue
        problems.append(Problem(record.id, f"param {key}={value:g} is not stated by the quote or an evidence fragment (add evidence: \"...\", derived: ..., or assumption: ...)"))
    return problems, assumed_count


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
    counts = {"records": len(records), "verified": 0, "unverifiable": 0, "assumed_params": 0}

    for name in snapshots:
        if not (sources_dir / name).exists():
            problems.append(Problem("<snapshots>", f"listed snapshot missing on disk: {name}"))
    for path in sources_dir.glob("*.txt"):
        if path.name not in snapshots:
            problems.append(Problem("<snapshots>", f"snapshot on disk not listed in verification.json: {path.name}"))

    texts: dict[str, tuple[str, str]] = {}
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
                texts[snap] = snapshot_variants((sources_dir / snap).read_text(encoding="utf-8"))
            if not quote_matches(r.quote, texts[snap]):
                problems.append(Problem(r.id, f"quote is not a verbatim substring of {snap}"))
                continue
            for name in snapshots:
                if name not in texts and (sources_dir / name).exists():
                    texts[name] = snapshot_variants((sources_dir / name).read_text(encoding="utf-8"))
            param_problems, assumed = params_evidence_problems(r, snap, texts)
            problems.extend(param_problems)
            counts["assumed_params"] += assumed
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
