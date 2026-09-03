#!/usr/bin/env python
"""
Task 3.6: write docs/FACTS.json from a real run (PLAN.md D7). Usage:

    uv run python scripts/facts.py            # run the demo, write docs/FACTS.json
    uv run python scripts/facts.py --check    # recompute and compare the deterministic fields

Nobody types a headline number by hand; README, /api/status, the video and the submission read this file.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.hold.facts import DETERMINISTIC_FIELDS, compute_facts  # noqa: E402

FACTS = ROOT / "docs" / "FACTS.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="recompute and compare with the committed file")
    parser.add_argument("--time-limit", type=float, default=60.0, help="CP-SAT time limit per solve, seconds")
    args = parser.parse_args()
    fresh = compute_facts(ROOT, time_limit_s=args.time_limit)
    if args.check:
        committed = json.loads(FACTS.read_text(encoding="utf-8"))
        diffs = [(k, committed.get(k), fresh[k]) for k in DETERMINISTIC_FIELDS if committed.get(k) != fresh[k]]
        for key, old, new in diffs:
            print(f"MISMATCH {key}: committed {old!r}, fresh run {new!r}")
        print("FACTS check:", "clean" if not diffs else f"{len(diffs)} field(s) differ")
        return 1 if diffs else 0
    FACTS.write_text(json.dumps(fresh, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {FACTS.relative_to(ROOT)} at {fresh['run_sha']}: "
          f"hold days {fresh['hold_days_before']} -> {fresh['hold_days_after']}, "
          f"illegal days {fresh['illegal_days_before']} -> {fresh['illegal_days_after']}, "
          f"payroll removed ${fresh['payroll_removed_usd']:,.2f}, benchmark {fresh['benchmark_matched']}, "
          f"pass 2 {fresh['pass2_status']} in {fresh['solve_ms']} ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
