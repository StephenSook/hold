"""
Tasks 3.1 and 3.3: the ADK agent and its guardrails, tested without a model call. The live
extraction gate (a sample call sheet into ExtractResult with status ok) needs Vertex AI
credentials and is recorded in PLAN.md when it runs.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from google.adk.tools.function_tool import FunctionTool

from api.agents.hold_agent import root_agent
from api.agents.hold_agent.callbacks import ALLOWED_TOOLS, guard_tool_call
from api.agents.hold_agent.runner import MAX_LLM_CALLS, is_configured
from api.agents.hold_agent.tools import check_legality, lookup_rule, optimize_schedule
from api.hold.config import GEMINI_MODEL
from api.hold.schemas import ExtractResult
from api.main import app

ROOT = Path(__file__).parents[2]


def _demo() -> dict[str, Any]:
    raw = json.loads((ROOT / "data" / "demo" / "hold-demo.json").read_text())
    return {k: v for k, v in raw.items() if not k.startswith("_")}


class _Rogue:
    name = "delete_everything"


def test_agent_shape() -> None:
    assert root_agent.name == "hold_agent"
    assert root_agent.model == GEMINI_MODEL
    assert root_agent.output_schema is None  # with tools and a schema this model loops on tool calls and never answers (3.4 trace)
    names = {str(getattr(t, "name", None) or getattr(t, "__name__", "")) for t in root_agent.tools}
    assert names == set(ALLOWED_TOOLS) == {"check_legality", "optimize_schedule", "lookup_rule"}
    assert root_agent.before_tool_callback is guard_tool_call
    assert MAX_LLM_CALLS == 3  # thought turn, optional tool turn, structured final answer


def test_guard_refuses_a_tool_outside_the_allowlist() -> None:
    refusal = guard_tool_call(_Rogue(), {}, _Ctx())  # type: ignore[arg-type]
    assert refusal is not None and "not allowed" in refusal["error"]
    assert refusal["allowed"] == sorted(ALLOWED_TOOLS)


def test_guard_refuses_an_invalid_argument_with_a_named_field() -> None:
    tool = FunctionTool(check_legality)
    refusal = guard_tool_call(tool, {"schedule": _demo(), "day_index": -1}, _Ctx())  # type: ignore[arg-type]
    assert refusal is not None and refusal["field"] == "day_index", refusal
    missing = guard_tool_call(FunctionTool(lookup_rule), {}, _Ctx())  # type: ignore[arg-type]
    assert missing is not None and missing["field"] == "rule_id"
    bad_schedule = guard_tool_call(tool, {"schedule": {"scenes": []}, "day_index": 0}, _Ctx())  # type: ignore[arg-type]
    assert bad_schedule is not None and bad_schedule["field"].startswith("schedule")
    assert guard_tool_call(tool, {"schedule": _demo(), "day_index": 0}, _Ctx()) is None  # type: ignore[arg-type]


def test_tools_answer_with_plain_dicts() -> None:
    verdict = check_legality(_demo(), 0)
    assert verdict["status"] in {"LEGAL", "ILLEGAL", "UNDETERMINED"} and verdict["day"] == 0
    out_of_range = check_legality(_demo(), 99)
    assert out_of_range["error"] and out_of_range["field"] == "day_index"
    rule = lookup_rule("GA_300_7_1_03_earliest_call")
    assert rule["citation"] and rule["quote"] and rule["source_url"]
    unknown = lookup_rule("NOPE")
    assert unknown["error"] and "GA_300_7_1_03_earliest_call" in unknown["known_ids"]
    solved = optimize_schedule(_demo())
    assert solved["pass2"]["status"] == "OPTIMAL" and solved["pass2"]["hold_days"] == 0
    assert solved["checker"]["agrees"] is True and solved["day_scene_ids"]


def test_extract_live_path_needs_a_project(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOLD_FAKE_EXTERNALS", "0")
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    assert is_configured() is False
    response = TestClient(app).post("/api/extract", json={"text": "INT. KITCHEN - DAY"})
    assert response.status_code == 503 and "GOOGLE_CLOUD_PROJECT" in response.json()["detail"]


def test_evalset_loads_and_names_the_tool_trajectory() -> None:
    """Task 3.4 draft: four text cases in ADK eval format; the score itself needs credentials."""
    from google.adk.evaluation.eval_set import EvalSet

    folder = ROOT / "api" / "agents" / "hold_agent"
    evalset = EvalSet.model_validate_json((folder / "evalset.json").read_text())
    assert [c.eval_id for c in evalset.eval_cases] == ["extract_callsheet", "nl_constraints", "ambiguity_refusal", "rule_lookup_trajectory"]
    lookup = evalset.eval_cases[-1]
    assert lookup.conversation is not None
    tool_uses = lookup.conversation[0].intermediate_data.tool_uses  # type: ignore[union-attr]
    assert [(t.name, t.args) for t in tool_uses] == [("lookup_rule", {"rule_id": "GA_300_7_1_03_earliest_call"})]
    config = json.loads((folder / "test_config.json").read_text())
    assert set(config["criteria"]) == {"tool_trajectory_avg_score", "final_response_match_v2"}


def test_extract_reports_an_unexpected_failure_as_502_with_the_cause(monkeypatch: pytest.MonkeyPatch) -> None:
    """A live failure inside the agent must reach the caller as a named error, never a blank 500."""
    import api.routes.extract as extract_route

    monkeypatch.setenv("HOLD_FAKE_EXTERNALS", "0")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "hold-2026")

    async def boom(*args: object, **kwargs: object) -> ExtractResult:
        raise RuntimeError("model endpoint said no")

    monkeypatch.setattr(extract_route, "run_extract", boom)
    response = TestClient(app).post("/api/extract", json={"text": "INT. KITCHEN - DAY"})
    assert response.status_code == 502
    detail = response.json()["detail"]
    assert "RuntimeError" in detail
    assert "model endpoint said no" not in detail  # the message may carry internal paths; it goes to the log only


def test_extraction_agent_carries_no_tools() -> None:
    """Extraction is one structured answer; the tools belong to the conversational agent only."""
    from api.agents.hold_agent.agent import extract_agent

    assert extract_agent.name == "hold_extract"
    assert extract_agent.tools == []
    assert extract_agent.output_schema is ExtractResult
    assert extract_agent.model == GEMINI_MODEL


class _Ctx:
    """Stand-in for ToolContext: the guard reads and writes invocation-scoped state."""

    def __init__(self) -> None:
        self.state: dict[str, Any] = {}


def test_guard_ends_a_refusal_loop_with_a_terminal_answer() -> None:
    """Live diagnosis: the model retried check_legality with an empty schedule until the call ceiling.
    After the budget the guard answers with a terminal instruction instead of another refusal."""
    from api.agents.hold_agent.callbacks import MAX_TOOL_CALLS_PER_REQUEST, guard_tool_call

    tool = FunctionTool(check_legality)
    ctx = _Ctx()
    bad = {"schedule": {"scenes": None, "cast": None, "days": None}, "day_index": 0}
    refusals = [guard_tool_call(tool, bad, ctx) for _ in range(MAX_TOOL_CALLS_PER_REQUEST)]  # type: ignore[arg-type]
    assert all(r is not None and r.get("field") for r in refusals)
    terminal = guard_tool_call(tool, bad, ctx)  # type: ignore[arg-type]
    assert terminal is not None and "instruction" in terminal
    assert "no more tool calls" in terminal["error"] and "needs_clarification" in terminal["instruction"]
    assert guard_tool_call(tool, {"schedule": _demo(), "day_index": 0}, ctx) is not None  # type: ignore[arg-type]  # budget spent: even a valid call is refused now
    assert guard_tool_call(tool, {"schedule": _demo(), "day_index": 0}, _Ctx()) is None  # type: ignore[arg-type]  # a new request starts fresh


def test_guard_refuses_a_tool_call_it_cannot_count() -> None:
    """Round five, finding 6: without state the budget could not be counted and every call went through
    (ten valid calls, ten allowances). A call the guard cannot count is refused, fail closed."""
    from types import SimpleNamespace

    from api.agents.hold_agent.callbacks import guard_tool_call

    tool = SimpleNamespace(name="lookup_rule")
    answer = guard_tool_call(tool, {"rule_id": "GA_300_7_1_03_earliest_call"}, None)  # type: ignore[arg-type]
    assert answer is not None and "count" in answer["error"]
    answer = guard_tool_call(tool, {"rule_id": "GA_300_7_1_03_earliest_call"}, SimpleNamespace())  # type: ignore[arg-type]
    assert answer is not None and "count" in answer["error"]


def test_malformed_base64_is_a_client_error_not_a_500(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOLD_FAKE_EXTERNALS", "0")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "hold-2026")
    response = TestClient(app).post("/api/extract", json={"text": "x", "image_base64": "%%%not-base64%%%", "mime_type": "image/png"})
    assert response.status_code == 422 and "image_base64" in response.json()["detail"]


def test_extraction_error_never_carries_the_model_text() -> None:
    from api.agents.hold_agent.runner import ExtractionError, parse_extract_result

    with pytest.raises(ExtractionError) as info:
        parse_extract_result("PRIVATE-CALL-SHEET-ALPHA")
    assert "PRIVATE-CALL-SHEET-ALPHA" not in str(info.value)
    assert "not an ExtractResult" in str(info.value)
