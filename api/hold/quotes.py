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
_DERIVED = re.compile(r"derived: ([0-9.]+) = ([0-9.]+) \+ ([0-9.]+)")  # addition of two evidenced numbers, nothing else
_ASSUMPTION = re.compile(r"assumption: ([0-9.]+)")
_CLOCK = re.compile(r"^\d{1,2}:\d{2}$")
_LEAD = r"(?<![\w.$])"  # a number starts at a word edge, never inside another number or a price
_END = r"(?![\d.,]?\d)"  # and ends there too: 257 is not 257.50, 1 is not 1.5, 2,896 is not 2,896.99


def _num(value: float) -> str:
    """A regex alternation for one number: digits, or the word with an optional "(N)" after it.
    Every digit form ends where the number ends (no decimal or thousands continuation)."""
    if float(value).is_integer():
        digits = str(int(value))
        alts = [re.escape(digits) + _END]
        if int(value) in _WORDS:
            alts.append(rf"{re.escape(_WORDS[int(value)])}(?: \({digits}\))?")
        return "(?:" + "|".join(alts) + ")"
    if value % 1 == 0.5:
        whole = int(value)
        alts = [rf"{whole}\.5", rf"{whole} 1/2"]
        if whole in _WORDS:
            alts.append(rf"{_WORDS[whole]} and (?:one[- ]half|a half)")
        return "(?:" + "|".join(alts) + ")"
    return re.escape(f"{value:g}")


def _money(dollars: float) -> str:
    if float(dollars).is_integer():
        return rf"(?:{re.escape(f'{int(dollars):,}')}|{int(dollars)})(?:\.00)?{_END}"
    return re.escape(f"{dollars:,.2f}") + _END


def _clock(value: str) -> list[str]:
    """Spellings of a clock time: 22:00, 10:00 p.m., 10 p.m., 12:00 midnight, 5:00 A.M."""
    hour, minute = (int(x) for x in value.split(":"))
    h12 = hour % 12 or 12
    meridiem = "a" if hour < 12 else "p"
    minutes = f":{minute:02d}" if minute else f"(?::{minute:02d})?"
    out = [rf"\b{hour:02d}:{minute:02d}\b", rf"\b{h12}{minutes}\s?{meridiem}\.?m\b\.?"]
    if (hour, minute) == (0, 0):
        out.append(r"\bmidnight\b")
    if (hour, minute) == (12, 0):
        out.append(r"\bnoon\b")
    return out


def number_candidates(key: str, value: object) -> list[re.Pattern[str]]:
    """The spellings a source may use for one param value, with the unit the key names: a minutes
    value must read as minutes (or a half hour), an hours value as hours, a rate as dollars, a
    share as a percentage, a clock time as a time. Bare numbers are accepted only for ages and
    for keys that name no unit (ratios)."""
    k = key.lower()
    if isinstance(value, str):
        return [re.compile(p, re.IGNORECASE) for p in _clock(value)] if _CLOCK.match(value) else []
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return []
    v = float(value)
    num = _num(v)
    pats: list[str] = []
    if "cents" in k:
        pats.append(rf"\$\s?{_money(v / 100)}(?!\d|,\d)")
    elif "bps" in k:
        pats.append(rf"{_LEAD}{_num(v / 100)}\s?(?:%|percent)")
    elif "percent" in k:
        pats.append(rf"{_LEAD}{num}\s?(?:%|percent)")
    elif "usd" in k:
        pats.append(rf"\$\s?{_money(v)}(?!\d|,\d)")
        pats.append(rf"{_LEAD}{num} dollars")
    elif "minutes" in k:
        pats.append(rf"{_LEAD}{num}[- ]?minutes?\b")
        if v == 30:
            pats += [r"(?:one[- ])?half(?: \(1/2\))?[- ]hour", r"half[- ]an[- ]hour", r"1/2[- ]hour", r"\b30[- ]minute"]
        if v == 15:
            pats.append(r"quarter[- ]hour")
        if v >= 60 and v % 60 == 0:
            pats.append(rf"{_LEAD}{_num(v / 60)}[- ]?hours?\b")
    elif "hours" in k:
        pats.append(rf"{_LEAD}{num}[- ]?hours?\b")
    elif "days" in k:
        pats.append(rf"{_LEAD}{num}[- ]?(?:business |consecutive |calendar |working )?days?\b")
    elif "age" in k:
        pats.append(rf"{_LEAD}{num}\b")
        if k == "age_max":
            pats.append(rf"{_LEAD}{_num(v + 1)}\b")  # "not attained the age of sixteen (16)", "9 years to 16 years"
    elif "multiplier" in k:
        return []  # only an assumption: marker can carry it
    else:
        pats.append(rf"{_LEAD}{num}\b")
    return [re.compile(p, re.IGNORECASE) for p in pats]


def _evidenced(text: str, patterns: list[re.Pattern[str]]) -> bool:
    return any(p.search(text) for p in patterns)


def _plain(value: float) -> list[re.Pattern[str]]:
    return [re.compile(rf"{_LEAD}{_num(value)}\b", re.IGNORECASE)]


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
    derived = {float(lhs): (float(a), float(b)) for lhs, a, b in _DERIVED.findall(note)}
    assumed = {float(v) for v in _ASSUMPTION.findall(note)}
    assumed_count = 0
    for key, value in record.params.items():
        if isinstance(value, bool) or not isinstance(value, (int, float, str)):
            continue
        if isinstance(value, str) and not _CLOCK.match(value):
            continue
        candidates = number_candidates(key, value)
        if candidates and _evidenced(text, candidates):
            continue
        if isinstance(value, str):
            problems.append(Problem(record.id, f"param {key}={value} is not stated as a clock time by the quote or an evidence fragment"))
            continue
        shown = f"{float(value):g}"
        expr = derived.get(float(value))
        if expr is not None:
            a, b = expr
            if abs(a + b - float(value)) < 1e-9 and _evidenced(text, _plain(a)) and _evidenced(text, _plain(b)):
                continue
            problems.append(Problem(record.id, f"param {key}={shown} derived from {a:g} + {b:g} but an operand is not evidenced or the sum is wrong"))
            continue
        if float(value) in assumed:
            assumed_count += 1
            continue
        problems.append(Problem(record.id, f"param {key}={shown} is not stated with its unit by the quote or an evidence fragment (add evidence: \"...\", derived: a = b + c, or assumption: ...)"))
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
