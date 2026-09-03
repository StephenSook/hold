"""Task 3.4: the adk eval summary is parsed from the run log into docs/adk_eval.json, and FACTS reads it."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.adk_eval import parse_summary

SAMPLE = """
Eval Run Summary
hold_extraction_v1:
  Tests passed: 1
  Tests failed: 3
********************************************************************
Eval Set Id: hold_extraction_v1
Eval Id: rule_lookup_trajectory
Overall Eval Status: FAILED
********************************************************************
Eval Set Id: hold_extraction_v1
Eval Id: nl_constraints
Overall Eval Status: PASSED
---------------------------------------------------------------------
Metric: tool_trajectory_avg_score, Status: PASSED, Score: 1.0, Threshold: 1.0
---------------------------------------------------------------------
Metric: final_response_match_v2, Status: PASSED, Score: 0.9, Threshold: 0.8
---------------------------------------------------------------------
Invocation Details:
"""


def test_parse_summary_reads_counts_cases_and_metrics() -> None:
    summary = parse_summary(SAMPLE)
    assert summary["eval_set_id"] == "hold_extraction_v1"
    assert summary["passed"] == 1 and summary["failed"] == 3
    assert summary["cases"]["rule_lookup_trajectory"]["status"] == "FAILED"
    assert summary["cases"]["nl_constraints"]["status"] == "PASSED"
    assert summary["cases"]["nl_constraints"]["metrics"]["final_response_match_v2"] == {"status": "PASSED", "score": 0.9, "threshold": 0.8}


def test_parse_summary_refuses_a_log_without_a_summary() -> None:
    import pytest

    with pytest.raises(ValueError, match="no Eval Run Summary"):
        parse_summary("nothing here")


def test_facts_reads_the_recorded_eval_when_present(tmp_path: Path) -> None:
    from api.hold.facts import load_adk_eval

    assert load_adk_eval(tmp_path) is None  # no record: adk_eval stays null, never invented
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "adk_eval.json").write_text(json.dumps({"passed": 4, "failed": 0, "cases": {}, "run_at": "2026-09-03T00:00:00+00:00", "model": "gemini-3.1-flash-lite"}))
    assert load_adk_eval(tmp_path) == {"passed": 4, "failed": 0, "cases": {}, "run_at": "2026-09-03T00:00:00+00:00", "model": "gemini-3.1-flash-lite"}


def test_parse_history_reads_per_case_status_and_metric_scores() -> None:
    """adk eval writes .adk/eval_history/*.evalset_result.json; the console prints counts only, so the
    per-case record comes from that file, with ADK's EvalStatus enum ints named."""
    from scripts.adk_eval import parse_history

    history = {
        "eval_set_id": "hold_extraction_v1",
        "creation_timestamp": 1788451609.35,
        "eval_case_results": [
            {"eval_id": "rule_lookup_trajectory", "final_eval_status": 1, "overall_eval_metric_results": [{"metric_name": "tool_trajectory_avg_score", "score": 1.0, "threshold": 1.0, "eval_status": 1}, {"metric_name": "final_response_match_v2", "score": 0.9, "threshold": 0.8, "eval_status": 1}]},
            {"eval_id": "ambiguity_refusal", "final_eval_status": 2, "overall_eval_metric_results": [{"metric_name": "final_response_match_v2", "score": 0.5, "threshold": 0.8, "eval_status": 2}]},
        ],
    }
    cases = parse_history(history)
    assert cases["rule_lookup_trajectory"]["status"] == "PASSED"
    assert cases["rule_lookup_trajectory"]["metrics"]["final_response_match_v2"] == {"status": "PASSED", "score": 0.9, "threshold": 0.8}
    assert cases["ambiguity_refusal"]["status"] == "FAILED"
    assert cases["ambiguity_refusal"]["metrics"]["final_response_match_v2"]["status"] == "FAILED"


def test_models_invoked_lists_every_model_the_log_sent_requests_to() -> None:
    from scripts.adk_eval import models_invoked

    log = "x - Sending out request, model: gemini-3.1-flash-lite, backend: VERTEX_AI\ny - Sending out request, model: gemini-2.5-flash, backend: VERTEX_AI\nz - Sending out request, model: gemini-3.1-flash-lite, backend: VERTEX_AI\n"
    assert models_invoked(log) == ["gemini-2.5-flash", "gemini-3.1-flash-lite"]


def test_every_json_expectation_in_the_eval_set_is_a_valid_extract_result() -> None:
    """Round six, finding 2: an expected answer the API's own schema refuses cannot prove the extraction path."""
    from api.hold.schemas import ExtractResult

    evalset = json.loads((Path(__file__).resolve().parents[2] / "api" / "agents" / "hold_agent" / "evalset.json").read_text(encoding="utf-8"))
    parsed = 0
    for case in evalset["eval_cases"]:
        text = "".join(p.get("text", "") for p in case["conversation"][0]["final_response"]["parts"]).strip()
        if text.startswith("{"):
            ExtractResult.model_validate_json(text)
            parsed += 1
    assert parsed >= 3


def test_history_is_paired_by_counts_and_a_mismatch_is_refused(tmp_path: Path) -> None:
    """Round six, finding 5: the recorder overlaid the newest result file onto any log, so a log with
    three failures could be recorded with four PASSED cases from an older run."""
    from scripts.adk_eval import pick_history

    (tmp_path / "old.evalset_result.json").write_text(json.dumps({"creation_timestamp": 1.0, "eval_case_results": [{"eval_id": "a", "final_eval_status": 1, "overall_eval_metric_results": []}]}))
    (tmp_path / "new.evalset_result.json").write_text(json.dumps({"creation_timestamp": 2.0, "eval_case_results": [{"eval_id": "a", "final_eval_status": 2, "overall_eval_metric_results": []}]}))
    assert pick_history(tmp_path, passed=1, failed=0).name == "old.evalset_result.json"
    assert pick_history(tmp_path, passed=0, failed=1).name == "new.evalset_result.json"
    with pytest.raises(ValueError, match="no result file"):
        pick_history(tmp_path, passed=2, failed=2)
    assert pick_history(tmp_path, passed=0, failed=1, not_before=1.5).name == "new.evalset_result.json"
    with pytest.raises(ValueError, match="no result file"):
        pick_history(tmp_path, passed=1, failed=0, not_before=1.5)


def test_facts_adk_eval_equals_the_recorded_file() -> None:
    """A hand edit of either docs/adk_eval.json or the adk_eval block in FACTS fails here."""
    from api.hold.facts import load_adk_eval

    root = Path(__file__).resolve().parents[2]
    facts = json.loads((root / "docs" / "FACTS.json").read_text(encoding="utf-8"))
    assert facts["adk_eval"] == load_adk_eval(root)
