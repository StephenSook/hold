#!/usr/bin/env python
"""
Task 3.4: run `adk eval` against Vertex AI (or read an existing run log) and record the summary in
docs/adk_eval.json, which scripts/facts.py copies into FACTS as adk_eval. Nothing is typed by hand.

    GOOGLE_CLOUD_PROJECT=hold-2026 GOOGLE_CLOUD_LOCATION=global GOOGLE_GENAI_USE_ENTERPRISE=true \\
      uv run python scripts/adk_eval.py                 # run the eval, then record
    uv run python scripts/adk_eval.py --log path.log    # record from a log you already have
"""
from __future__ import annotations

import argparse
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--log", type=Path, help="parse this log instead of running adk eval")
    args = parser.parse_args()
    if args.log:
        log = args.log.read_text(encoding="utf-8")
    else:
        cmd = ["uv", "run", "adk", "eval", str(AGENT), str(AGENT / "evalset.json"), "--config_file_path", str(AGENT / "test_config.json")]
        run = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
        log = run.stdout + run.stderr
    summary = parse_summary(log)
    record = {
        **summary,
        "run_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "model": os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite"),
        "location": os.environ.get("GOOGLE_CLOUD_LOCATION", "global"),
        "criteria": json.loads((AGENT / "test_config.json").read_text(encoding="utf-8"))["criteria"],
        "written_by": "scripts/adk_eval.py from a real adk eval run",
    }
    OUT.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}: passed {record['passed']}, failed {record['failed']}")
    return 0 if record["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
