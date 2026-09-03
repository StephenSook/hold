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
    assert root_agent.output_schema is ExtractResult
    names = {str(getattr(t, "name", None) or getattr(t, "__name__", "")) for t in root_agent.tools}
    assert names == set(ALLOWED_TOOLS) == {"check_legality", "optimize_schedule", "lookup_rule"}
    assert root_agent.before_tool_callback is guard_tool_call
    assert MAX_LLM_CALLS == 1


def test_guard_refuses_a_tool_outside_the_allowlist() -> None:
    refusal = guard_tool_call(_Rogue(), {}, None)  # type: ignore[arg-type]
    assert refusal is not None and "not allowed" in refusal["error"]
    assert refusal["allowed"] == sorted(ALLOWED_TOOLS)


def test_guard_refuses_an_invalid_argument_with_a_named_field() -> None:
    tool = FunctionTool(check_legality)
    refusal = guard_tool_call(tool, {"schedule": _demo(), "day_index": -1}, None)  # type: ignore[arg-type]
    assert refusal is not None and refusal["field"] == "day_index", refusal
    missing = guard_tool_call(FunctionTool(lookup_rule), {}, None)  # type: ignore[arg-type]
    assert missing is not None and missing["field"] == "rule_id"
    bad_schedule = guard_tool_call(tool, {"schedule": {"scenes": []}, "day_index": 0}, None)  # type: ignore[arg-type]
    assert bad_schedule is not None and bad_schedule["field"].startswith("schedule")
    assert guard_tool_call(tool, {"schedule": _demo(), "day_index": 0}, None) is None  # type: ignore[arg-type]


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
