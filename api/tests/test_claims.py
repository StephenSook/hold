"""
Task 5.2: every model or vendor named on a judge-facing surface (README, docs) is one that
/api/status.runtime reports, runtime-purity names never appear (D5: no watsonx or Granite in
the running system), and streaming is phrased as conditional while Confluent is not connected.
Mutation-tested both ways so the guard cannot be vacuous.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from api.hold.claims import VOCABULARY, claim_problems, judge_facing_surfaces, surface_text
from api.routes.status import build_status

ROOT = Path(__file__).parents[2]


def _runtime() -> dict[str, Any]:
    """The deployment posture: Vertex configured, fakes off (what the judged instance reports)."""
    import os

    from api.routes.status import reset_cache

    saved = {k: os.environ.get(k) for k in ("GOOGLE_CLOUD_PROJECT", "HOLD_FAKE_EXTERNALS")}
    os.environ["GOOGLE_CLOUD_PROJECT"] = "hold-2026"
    os.environ["HOLD_FAKE_EXTERNALS"] = "0"
    try:
        reset_cache()
        runtime: dict[str, Any] = build_status()["runtime"]
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        reset_cache()
    return runtime


def test_judge_facing_surfaces_claim_only_what_the_runtime_reports() -> None:
    runtime = _runtime()
    surfaces = judge_facing_surfaces(ROOT)
    assert {p.name for p in surfaces} >= {"README.md", "THREAT_MODEL.md"}
    problems = [f"{p.name}: {m}" for p in surfaces for m in claim_problems(surface_text(p), runtime)]
    assert problems == [], "\n".join(problems)


def test_the_guard_is_not_vacuous() -> None:
    """At least one vocabulary term is present on the surfaces, so a clean run means something."""
    text = "\n".join(surface_text(p) for p in judge_facing_surfaces(ROOT))
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


def test_gemini_is_a_claim_only_when_extraction_is_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    """Round four, finding 2: a runtime that names the model but cannot run it backs nothing."""
    from api.routes.status import reset_cache

    monkeypatch.setenv("HOLD_FAKE_EXTERNALS", "0")
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    reset_cache()
    unconfigured = build_status()["runtime"]
    assert unconfigured["extraction"]["configured"] is False and unconfigured["mode"] == "unconfigured"
    assert claim_problems("Gemini through ADK extracts schedules on Vertex AI.", unconfigured)
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "hold-2026")
    reset_cache()
    configured = build_status()["runtime"]
    assert configured["extraction"]["configured"] is True and configured["mode"] == "live"
    assert claim_problems("Gemini through ADK extracts schedules on Vertex AI.", configured) == []
    reset_cache()


def test_present_tense_streaming_claims_are_not_conditional() -> None:
    """Round four, finding 3."""
    runtime = {**_runtime(), "confluent": {**_runtime()["confluent"], "connected": False}}
    assert claim_problems("Confluent adds live verdict streaming.", runtime)
    assert claim_problems("Confluent streams live when it receives an event.", runtime)
    assert claim_problems("Streaming: connected at submission time; live state at /api/status.", runtime) == []


def test_the_architecture_diagram_is_read_as_a_claims_surface() -> None:
    """
    A diagram names components, which is a present-tense statement about the running system. It
    is the easiest place in the repository to leave a name the code does not back, because it is
    the one surface nobody greps.
    """
    diagram = ROOT / "docs" / "architecture.svg"
    assert diagram.is_file(), "docs/architecture.svg is missing (PLAN.md task 5.6)"
    assert diagram in judge_facing_surfaces(ROOT), "the diagram is not in the guard's file set"

    text = surface_text(diagram)
    assert "<svg" not in text and "<path" not in text, "markup is reaching the claim check as if it were prose"
    assert "CP-SAT" in text or "OR-Tools" in text, "the diagram does not name the solver, so it is not the diagram"


def test_a_forbidden_name_in_the_diagram_would_be_caught() -> None:
    """The guard reads an SVG's text nodes and ignores its markup. Both halves proven here."""
    runtime = _runtime()

    from api.hold.claims import _svg_prose

    prose = _svg_prose('<svg xmlns="http://www.w3.org/2000/svg"><text x="0" y="0">Verdicts come from watsonx.</text></svg>')
    assert claim_problems(prose, runtime), "a forbidden name inside a text node was not caught"

    # A class or an id is not a claim, and must not be read as one.
    markup_only = _svg_prose('<svg><g class="watsonx-box" id="granite"><rect/></g></svg>')
    assert claim_problems(markup_only, runtime) == [], "markup was read as prose"
