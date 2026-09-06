"""
Task 5.2: what the judge-facing surfaces may claim. A vendor or model name on the README or in
docs must be one /api/status.runtime reports; runtime-purity names never appear (D5); while the
Confluent leg is not connected, any sentence naming it must say so or condition it.
"""
from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

Runtime = dict[str, Any]

# (pattern on the surface, predicate on the runtime that backs the claim, what backs it)
VOCABULARY: list[tuple[re.Pattern[str], Callable[[Runtime], bool]]] = [
    (re.compile(r"\bgemini\b", re.IGNORECASE), lambda r: str(r.get("gemini_model", "")).startswith("gemini") and _extraction_configured(r)),
    (re.compile(r"\b(google-adk|adk)\b", re.IGNORECASE), lambda r: bool(r.get("adk_version")) and _extraction_configured(r)),
    (re.compile(r"\b(cp-sat|or-tools|ortools)\b", re.IGNORECASE), lambda r: r.get("ortools_version") not in (None, "", "unknown")),
    (re.compile(r"\bvertex\b", re.IGNORECASE), lambda r: bool(r.get("gemini_location")) and _extraction_configured(r)),
    (re.compile(r"\b(confluent|kafka)\b", re.IGNORECASE), lambda r: isinstance(r.get("confluent"), dict)),
]
_BACKING = ["runtime.gemini_model with extraction.configured", "runtime.adk_version with extraction.configured", "runtime.ortools_version", "runtime.gemini_location with extraction.configured", "runtime.confluent"]


def _extraction_configured(runtime: Runtime) -> bool:
    """Naming the model is not enough: the deployed instance must be able to call it."""
    extraction = runtime.get("extraction") or {}
    return bool(extraction.get("configured"))

# Never on a judge-facing surface: not in the running system (D5), and the repo's own rule 0.
FORBIDDEN = re.compile(r"\b(watsonx|granite|claude|anthropic|openai|gpt-[0-9a-z.]+)\b", re.IGNORECASE)

# Model-looking names that must match the reported model exactly when they appear.
_MODEL_ID = re.compile(r"\b(gemini-[0-9][0-9a-z.\-]*)\b", re.IGNORECASE)
_CONDITIONAL = re.compile(r"submission time|not connected|until|once|task 4\.1|PLAN\.md|connected: ?false|not yet|will ", re.IGNORECASE)


def judge_facing_surfaces(root: Path) -> list[Path]:
    """README and JUDGE.md plus docs, minus the generated evidence logs under docs/bob-evidence and the
    generated license inventory (docs/THIRD_PARTY_NOTICES.md names every dependency's copyright holder;
    that is a legal notice, not a claim about the running system).

    The .svg is here because an architecture diagram is a claims surface in picture form: every
    component named on it is a present-tense statement about the running system, and a diagram
    that no guard reads is the easiest place in the repository to leave a name the code does not
    back. Its text is extracted before it is checked, so the markup itself is never mistaken for
    prose."""
    docs = sorted(
        p
        for p in (root / "docs").rglob("*")
        if p.suffix in {".md", ".svg"} and "bob-evidence" not in p.parts and p.name != "THIRD_PARTY_NOTICES.md"
    )
    return [root / "README.md", root / "JUDGE.md", *docs]


# Element content that is code rather than prose. A font-family in a stylesheet is not a claim
# about the running system, and neither is a string in a script.
_NOT_PROSE = {"style", "script", "metadata", "defs"}


def _svg_prose(raw: str) -> str:
    """
    The words a viewer reads in an SVG.

    This parses rather than pattern-matching, because stripping tags with a regex is wrong in both
    directions and both were demonstrated: `<text foo=">" class="watsonx">` leaks the attribute
    into the result, so a class name becomes a false claim, and a `<style>` block's contents are
    kept, so a font-family fails the guard. A parser knows what a text node is.
    """
    try:
        root = ElementTree.fromstring(raw)
    except ElementTree.ParseError:
        # Unparseable markup is not a reason to let a surface through unchecked. Fall back to the
        # whole document, which over-reports rather than under-reports.
        return raw

    words: list[str] = []

    def walk(element: ElementTree.Element) -> None:
        tag = element.tag.rsplit("}", 1)[-1].lower()
        if tag in _NOT_PROSE:
            return
        if element.text:
            words.append(element.text)
        for child in element:
            walk(child)
            if child.tail:
                words.append(child.tail)

    walk(root)
    return " ".join(words)


def surface_text(path: Path) -> str:
    """The words on a surface. For an SVG that is its text nodes, and never its markup."""
    raw = path.read_text(encoding="utf-8")
    return _svg_prose(raw) if path.suffix == ".svg" else raw


def claim_problems(text: str, runtime: Runtime) -> list[str]:
    out: list[str] = []
    for m in FORBIDDEN.finditer(text):
        out.append(f"{m.group(0)!r} is named; it is not in the running system")
    for (pattern, backed), backing in zip(VOCABULARY, _BACKING, strict=True):
        hit = pattern.search(text)
        if hit and not backed(runtime):
            out.append(f"{hit.group(0)!r} is named but {backing} does not report it")
    reported_model = str(runtime.get("gemini_model", "")).lower()
    for m in _MODEL_ID.finditer(text):
        if m.group(1).lower() != reported_model:
            out.append(f"model id {m.group(1)!r} is named; runtime reports {reported_model!r}")
    confluent = runtime.get("confluent") or {}
    if not confluent.get("connected"):
        for sentence in re.split(r"(?<=[.!?])\s+|\n", text):
            names_streaming = re.search(r"\b(confluent|kafka)\b", sentence, re.IGNORECASE) and re.search(
                r"\b(connected|live|streams?)\b", sentence, re.IGNORECASE
            )
            if names_streaming and not _CONDITIONAL.search(sentence):
                out.append(f"streaming claimed while confluent.connected is false: {sentence.strip()[:120]}")
    return out
