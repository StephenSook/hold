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


def test_the_call_sheet_case_prompt_is_the_committed_sample() -> None:
    """Round seven, finding 2: the prompt drifted from the sample (it lacked the AGREEMENT line) while the
    gold answered with the rate from the sample; the two are held together here."""
    root = Path(__file__).resolve().parents[2]
    evalset = json.loads((root / "api" / "agents" / "hold_agent" / "evalset.json").read_text(encoding="utf-8"))
    case = next(c for c in evalset["eval_cases"] if c["eval_id"] == "extract_callsheet")
    inv = case["conversation"][0]
    prompt = inv["user_content"]["parts"][0]["text"].strip()
    assert prompt == (root / "data" / "demo" / "samples" / "callsheet-day3.txt").read_text(encoding="utf-8").strip()
    gold = json.loads("".join(p.get("text", "") for p in inv["final_response"]["parts"]))
    assert gold["status"] == "ok" and gold["questions"] == []


# ---------------------------------------------------------------------------
# The gate. Everything above tests the recorder; this tests the record.
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]
RECORDS = [
    (ROOT / "api" / "agents" / "hold_agent", ROOT / "docs" / "adk_eval.json"),
    (ROOT / "api" / "agents" / "event_agent", ROOT / "docs" / "adk_eval_events.json"),
]


@pytest.mark.parametrize(("agent_dir", "record_path"), RECORDS, ids=lambda p: p.name)
def test_the_recorded_eval_is_green_and_covers_every_case(agent_dir: Path, record_path: Path) -> None:
    """A recorded eval with a failing case is a failing build, and so is a case nobody scored.

    Until this existed the only thing CI checked about the eval was that FACTS quoted the record
    faithfully, which is a consistency check between two files and says nothing about whether the
    agent works. A record can be internally perfect and report three failures.
    """
    record = json.loads(record_path.read_text(encoding="utf-8"))
    evalset = json.loads((agent_dir / "evalset.json").read_text(encoding="utf-8"))
    expected = {case["eval_id"] for case in evalset["eval_cases"]}

    assert record["failed"] == 0, f"{record_path.name}: {record['failed']} case(s) failed"
    assert record["passed"] == len(expected)
    assert set(record["cases"]) == expected, "the record must score every case in the eval set and no others"
    for eval_id, case in record["cases"].items():
        assert case["status"] == "PASSED", f"{eval_id} is {case['status']}"
        assert case["metrics"], f"{eval_id} passed with no metric recorded, which is not a measurement"
        for name, metric in case["metrics"].items():
            assert metric["score"] >= metric["threshold"], f"{eval_id}/{name} scored below its own threshold"


@pytest.mark.parametrize(("agent_dir", "record_path"), RECORDS, ids=lambda p: p.name)
def test_the_recorded_eval_describes_the_agent_that_exists_now(agent_dir: Path, record_path: Path) -> None:
    """Rewrite the prompt, add a tool, change the model or edit a case, and the record stops being
    evidence about anything that ships. Without this the file reads 4 passed forever: a result has
    no expiry of its own, and the agent it scored can be replaced underneath it in one edit.

    The remedy the failure asks for is to re-run the eval, never to update the hash.
    """
    from scripts.adk_eval import fingerprint

    record = json.loads(record_path.read_text(encoding="utf-8"))
    assert record["agent_fingerprint"] == fingerprint(agent_dir), (
        f"{record_path.name} was recorded against a different agent, prompt, model, criteria or eval set. "
        f"Re-run it: uv run python scripts/adk_eval.py --agent {agent_dir.relative_to(ROOT)} --out {record_path.relative_to(ROOT)}"
    )


def test_the_interpreter_evalset_is_generated_not_pasted() -> None:
    """The prompt in each case is the context block the service builds, so it cannot drift from it."""
    from scripts.event_evalset import render

    assert (ROOT / "api" / "agents" / "event_agent" / "evalset.json").read_text(encoding="utf-8") == render()


def test_the_interpreter_golds_are_valid_proposals_the_engine_would_accept() -> None:
    """An expected answer the API's own schema refuses cannot prove the interpreter, and one the
    engine would reject proves only that the model can produce unusable JSON convincingly.

    "Would accept" is asserted by running it. An earlier version of this only checked that the
    payload was non-empty, which is a weaker claim than its own docstring made: a payload of
    {"scene_id": "s99"} is non-empty and the engine refuses it.
    """
    from api.hold.schemas import EventProposal, ScheduleInput, SetEvent
    from api.hold.set_events import apply_set_event

    schedule = ScheduleInput.model_validate(_demo())
    evalset = json.loads((ROOT / "api" / "agents" / "event_agent" / "evalset.json").read_text(encoding="utf-8"))
    ok = 0
    for case in evalset["eval_cases"]:
        text = "".join(p.get("text", "") for p in case["conversation"][0]["final_response"]["parts"])
        proposal = EventProposal.model_validate_json(text)
        if proposal.status == "ok":
            assert proposal.kind is not None
            _, change = apply_set_event(
                schedule,
                SetEvent(kind=proposal.kind, payload=proposal.event_payload(), source="agent"),
            )
            assert change, case["eval_id"]
            ok += 1
        else:
            assert proposal.questions, f"{case['eval_id']} refuses without saying what it needs"
    assert ok >= 3, "the eval set must contain applicable events, not only refusals"


def _demo() -> dict[str, object]:
    return {
        k: v
        for k, v in json.loads((ROOT / "data" / "demo" / "hold-demo.json").read_text(encoding="utf-8")).items()
        if not k.startswith("_")
    }
