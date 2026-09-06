#!/usr/bin/env python
"""
Task 3.4: run `adk eval` against Vertex AI (or read an existing run log) and record the summary in
docs/adk_eval*.json, which scripts/facts.py copies into FACTS as adk_eval. Nothing is typed by hand.

    GOOGLE_CLOUD_PROJECT=hold-2026 GOOGLE_CLOUD_LOCATION=global GOOGLE_GENAI_USE_ENTERPRISE=true \\
      uv run python scripts/adk_eval.py                 # run the eval, then record
    uv run python scripts/adk_eval.py --log path.log    # record from a log you already have
    uv run python scripts/adk_eval.py --agent api/agents/event_agent --out docs/adk_eval_events.json

Each record carries a fingerprint of the agent it scored: the instruction, the tool names, the
model id, the criteria and the eval set bytes. A recorded result says nothing about an agent whose
prompt has since been rewritten, and without the fingerprint nothing could tell the two apart, so
the record read 4 passed forever no matter what the agent had become. api/tests/test_adk_eval.py
recomputes it and turns a stale record into a red build.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import inspect
import json
import os
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "api" / "agents" / "hold_agent"
OUT = ROOT / "docs" / "adk_eval.json"
EVAL_STATUS = {1: "PASSED", 2: "FAILED", 3: "NOT_EVALUATED"}  # google.adk.evaluation.eval_metrics.EvalStatus
_MODEL = re.compile(r"Sending out request, model: (\S+),")


def parse_summary(log: str) -> dict[str, Any]:
    """The Eval Run Summary block: counts, per-case status, per-metric score and threshold."""
    if "Eval Run Summary" not in log:
        raise ValueError("no Eval Run Summary in the log")
    tail = log.split("Eval Run Summary", 1)[1]
    set_match = re.search(r"^(\S+):\n\s+Tests passed: (\d+)\n\s+Tests failed: (\d+)", tail, re.MULTILINE)
    if not set_match:
        raise ValueError("no pass and fail counts in the summary")
    cases: dict[str, dict[str, Any]] = {}
    current: str | None = None
    for line in tail.splitlines():
        eval_id = re.match(r"Eval Id: (\S+)", line.strip())
        status = re.match(r"Overall Eval Status: (\S+)", line.strip())
        metric = re.match(r"Metric: (\S+), Status: (\S+), Score: ([0-9.]+), Threshold: ([0-9.]+)", line.strip())
        if eval_id:
            current = eval_id.group(1)
            cases.setdefault(current, {"status": None, "metrics": {}})
        elif status and current:
            cases[current]["status"] = status.group(1)
        elif metric and current:
            cases[current]["metrics"][metric.group(1)] = {"status": metric.group(2), "score": float(metric.group(3)), "threshold": float(metric.group(4))}
    return {"eval_set_id": set_match.group(1), "passed": int(set_match.group(2)), "failed": int(set_match.group(3)), "cases": cases}


def parse_history(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Per-case status and metric scores from an .adk/eval_history/*.evalset_result.json file."""
    cases: dict[str, dict[str, Any]] = {}
    for case in data.get("eval_case_results", []):
        metrics = {
            str(m["metric_name"]): {"status": EVAL_STATUS.get(int(m["eval_status"]), str(m["eval_status"])), "score": float(m["score"]), "threshold": float(m["threshold"])}
            for m in case.get("overall_eval_metric_results", [])
        }
        cases[str(case["eval_id"])] = {"status": EVAL_STATUS.get(int(case["final_eval_status"]), str(case["final_eval_status"])), "metrics": metrics}
    return cases


def models_invoked(log: str) -> list[str]:
    """Every model the run sent a request to: the agent's model and the judge's."""
    return sorted(set(_MODEL.findall(log)))


def pick_history(history_dir: Path, passed: int, failed: int, not_before: float | None = None) -> Path:
    """The result file that belongs to the summary being recorded: pass and fail counts must agree, and
    when the run was started by this script the file must have been created after that start. Anything
    else is refused rather than overlaid (round six, finding 5)."""
    candidates = []
    for path in sorted(history_dir.glob("*.evalset_result.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        data = json.loads(path.read_text(encoding="utf-8"))
        if not_before is not None and float(data.get("creation_timestamp", 0)) < not_before:
            continue
        statuses = [int(c["final_eval_status"]) for c in data.get("eval_case_results", [])]
        if statuses.count(1) == passed and statuses.count(2) == failed:
            candidates.append(path)
    if not candidates:
        raise ValueError(f"no result file under {history_dir} matches passed={passed} failed={failed}" + (" after the run started" if not_before else ""))
    return candidates[0]


def fingerprint(agent_dir: Path) -> str:
    """What was scored, in one hash.

    The first version hashed the instruction, the tool NAMES, the model, the criteria and the eval
    set, and the README claimed it covered "the agent that ships". It did not. Renaming nothing and
    rewriting the body of a tool, the guard callback, or the response schema left the hash
    unchanged, so a recorded score survived changes that plainly alter what the agent does. The
    claim was wider than the check, which is the failure this whole gate exists to prevent, so the
    check moved rather than the claim: the SOURCE of each tool, of the before_tool_callback and of
    the response schema is hashed, not just its name.

    It also resolves the agent through `<pkg>.agent`, which is the module `adk eval` itself loads,
    and asserts the package re-export is the same object. Hashing `__init__` while the eval scored
    `agent.py` meant the two could point at different agents and the gate would not notice.
    """
    module = importlib.import_module(f"api.agents.{agent_dir.name}.agent")
    agent = module.root_agent
    package = importlib.import_module(f"api.agents.{agent_dir.name}")
    if package.root_agent is not agent:
        raise ValueError(
            f"api.agents.{agent_dir.name} and its agent module export different agents; "
            "adk eval scores the agent module and this gate would be describing the other one"
        )
    material = json.dumps(
        {
            "agent": agent.name,
            "model": str(agent.model),
            "instruction": str(agent.instruction),
            "tools": sorted(_source_of(t) for t in agent.tools),
            "before_tool_callback": _source_of(agent.before_tool_callback),
            "output_schema": _source_of(agent.output_schema),
            "criteria": json.loads((agent_dir / "test_config.json").read_text(encoding="utf-8"))["criteria"],
            "evalset": (agent_dir / "evalset.json").read_text(encoding="utf-8"),
        },
        sort_keys=True,
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _source_of(obj: object) -> str:
    """A name and its source text, or just a name when the source cannot be read.

    A callback registered as a list, a partial, or a builtin has no readable source; those fall
    back to the repr, which is worse than nothing only if it is silent about it, so it is not.
    """
    if obj is None:
        return "none"
    if isinstance(obj, list):
        return " | ".join(_source_of(item) for item in obj)
    name = getattr(obj, "__name__", getattr(obj, "name", repr(obj)))
    try:
        return f"{name}::{inspect.getsource(obj)}"  # type: ignore[arg-type]
    except (OSError, TypeError):
        return f"{name}::<source unavailable>"


def _tail(log: str, lines: int = 60) -> str:
    """The end of the run log, labelled, for a failure message. The whole log can be megabytes of
    per-invocation detail; the reason a run failed is at the end of it."""
    tail = "\n".join(log.splitlines()[-lines:])
    return f"--- last {lines} lines of the adk eval log ---\n{tail}\n--- end of log ---"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--log", type=Path, help="parse this log instead of running adk eval")
    parser.add_argument("--agent", type=Path, default=AGENT, help="the agent module directory to evaluate")
    parser.add_argument("--out", type=Path, default=OUT, help="where to write the record")
    args = parser.parse_args()
    agent_dir = args.agent if args.agent.is_absolute() else ROOT / args.agent
    out = args.out if args.out.is_absolute() else ROOT / args.out
    history_dir = agent_dir / ".adk" / "eval_history"
    started: float | None = None
    exit_code: int | None = None
    if args.log:
        log = args.log.read_text(encoding="utf-8")
    else:
        started = datetime.now(UTC).timestamp()
        cmd = ["uv", "run", "adk", "eval", str(agent_dir), str(agent_dir / "evalset.json"), "--config_file_path", str(agent_dir / "test_config.json")]
        run = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
        log = run.stdout + run.stderr
        exit_code = run.returncode
    # A gate whose failure is undiagnosable is a gate that gets disabled. The first run of this on
    # CI reported "passed 0, failed 4" in twenty two seconds and printed nothing else, because the
    # log is captured and only parsed: every model call had failed and the run said so nowhere.
    #
    # The condition is the FAILED COUNT, not the exit code. Gating on the exit code was the first
    # attempt and printed nothing on the very next run, because `adk eval` exits 0 whether its
    # cases pass or fail; the fix for an invisible failure was itself invisible.
    try:
        summary = parse_summary(log)
    except ValueError:
        print(_tail(log), file=sys.stderr)
        raise
    if summary["failed"] or exit_code:
        print(_tail(log), file=sys.stderr)
    history = pick_history(history_dir, summary["passed"], summary["failed"], not_before=started)
    data = json.loads(history.read_text(encoding="utf-8"))
    summary["cases"] = parse_history(data)
    summary["history_file"] = history.name
    summary["run_at"] = datetime.fromtimestamp(float(data["creation_timestamp"]), UTC).replace(microsecond=0).isoformat()
    summary["adk_eval_exit_code"] = exit_code
    record = {
        **summary,
        "recorded_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "model": os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite"),
        "models_invoked": models_invoked(log),
        "location": os.environ.get("GOOGLE_CLOUD_LOCATION", "global"),
        "criteria": json.loads((agent_dir / "test_config.json").read_text(encoding="utf-8"))["criteria"],
        "agent_module": str(agent_dir.relative_to(ROOT)),
        "agent_fingerprint": fingerprint(agent_dir),
        "written_by": "scripts/adk_eval.py from a real adk eval run",
    }
    out.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)}: passed {record['passed']}, failed {record['failed']}")
    return 0 if record["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
