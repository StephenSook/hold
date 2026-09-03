"""
Task 5.2: every model or vendor named on a judge-facing surface (README, docs) is one that
/api/status.runtime reports, runtime-purity names never appear (D5: no watsonx or Granite in
the running system), and streaming is phrased as conditional while Confluent is not connected.
Mutation-tested both ways so the guard cannot be vacuous.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from api.hold.claims import VOCABULARY, claim_problems, judge_facing_surfaces
from api.routes.status import build_status

ROOT = Path(__file__).parents[2]


def _runtime() -> dict[str, Any]:
    runtime: dict[str, Any] = build_status()["runtime"]
    return runtime


def test_judge_facing_surfaces_claim_only_what_the_runtime_reports() -> None:
    runtime = _runtime()
    surfaces = judge_facing_surfaces(ROOT)
    assert {p.name for p in surfaces} >= {"README.md", "THREAT_MODEL.md"}
    problems = [f"{p.name}: {m}" for p in surfaces for m in claim_problems(p.read_text(encoding="utf-8"), runtime)]
    assert problems == [], "\n".join(problems)


def test_the_guard_is_not_vacuous() -> None:
    """At least one vocabulary term is present on the surfaces, so a clean run means something."""
    text = "\n".join(p.read_text(encoding="utf-8") for p in judge_facing_surfaces(ROOT))
    assert any(pattern.search(text) for pattern, _ in VOCABULARY), "no vendor or model named anywhere"


def test_mutation_a_surface_naming_an_unreported_model_goes_red() -> None:
    runtime = _runtime()
    assert claim_problems("The extractor runs on claude-3 through anthropic.", runtime)
    assert claim_problems("Verdicts come from watsonx and a Granite model.", runtime)


def test_mutation_a_runtime_reporting_nothing_goes_red() -> None:
    runtime = _runtime()
    silent = {**runtime, "ortools_version": "unknown", "gemini_model": "", "adk_version": ""}
    assert claim_problems("CP-SAT proves the order; Gemini through ADK extracts.", silent)
    assert claim_problems("CP-SAT proves the order; Gemini through ADK extracts.", runtime) == []


def test_streaming_is_conditional_while_confluent_is_not_connected() -> None:
    runtime = _runtime()
    assert runtime["confluent"]["connected"] is False
    assert claim_problems("Confluent is connected and streaming verdicts live.", runtime)
    assert claim_problems("Streaming: Confluent connected at submission time; live state at /api/status.", runtime) == []
