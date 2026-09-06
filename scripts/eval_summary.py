#!/usr/bin/env python
"""
Print the recorded eval results as markdown, for a CI run summary.

Reading a record is not the same as trusting one: this prints what is on disk and says when it was
run and against which agent, so a summary that looks green while describing yesterday's agent is
visible as such rather than reassuring.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORDS = ("docs/adk_eval.json", "docs/adk_eval_events.json")


def render(root: Path = ROOT) -> str:
    lines: list[str] = []
    for name in RECORDS:
        path = root / name
        if not path.exists():
            lines.append(f"**{name}** is missing: nothing was recorded.")
            continue
        record = json.loads(path.read_text(encoding="utf-8"))
        lines.append(
            f"**{record['eval_set_id']}** ({record.get('agent_module', '?')}): "
            f"{record['passed']} passed, {record['failed']} failed, "
            f"model {record.get('model', '?')}, run at {record.get('run_at', '?')}"
        )
        lines.extend(f"- {case['status']}  {eval_id}" for eval_id, case in sorted(record["cases"].items()))
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    sys.stdout.write(render())
