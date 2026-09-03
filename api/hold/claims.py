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
    that is a legal notice, not a claim about the running system)."""
    docs = sorted(p for p in (root / "docs").rglob("*.md") if "bob-evidence" not in p.parts and p.name != "THIRD_PARTY_NOTICES.md")
    return [root / "README.md", root / "JUDGE.md", *docs]


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
