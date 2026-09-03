"""
Task 1.11: HOLD's own MCP server over stdio, so an MCP client (IBM Bob's `.bob/mcp.json` registers it)
can solve a schedule, judge a day, look up a rule and run the benchmark residual while working on the
code. The first three tools are the same functions the ADK agent's guarded tools call
(api/agents/hold_agent/tools.py); every answer is a plain dict. Never mounted in production.

    uv run python -m api.hold.mcp_server
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mcp.server import MCPServer

from api.agents.hold_agent.tools import check_legality as _check_legality
from api.agents.hold_agent.tools import lookup_rule as _lookup_rule
from api.agents.hold_agent.tools import optimize_schedule as _optimize_schedule
from api.hold.instance import parse_dzn
from api.hold.model import solve_benchmark

ROOT = Path(__file__).resolve().parents[2]
BENCH = ROOT / "bench"

server = MCPServer(name="hold", instructions="Film schedule optimizer and child-performer legality checker. Tools answer with plain JSON objects; an object with an `error` key is a refusal, not a result.")


@server.tool()
def solve_schedule(schedule: dict[str, Any]) -> dict[str, Any]:
    """Find the cheapest legal scene order and day assignment for a HOLD ScheduleInput, then re-judge every day."""
    return _optimize_schedule(schedule)


@server.tool()
def check_legality(schedule: dict[str, Any], day_index: int) -> dict[str, Any]:
    """Judge one shooting day of a HOLD ScheduleInput against child-performer law and the SAG-AFTRA rules."""
    return _check_legality(schedule, day_index)


@server.tool()
def lookup_rule(rule_id: str) -> dict[str, Any]:
    """Return one rule record by id: citation, title, the verbatim quote, source URL, params and note."""
    return _lookup_rule(rule_id)


@server.tool()
def run_residual(names: list[str] | None = None, time_limit_s: float = 60.0) -> dict[str, Any]:
    """Solve the benchmark instances under bench/instances/medium and compare each cost to the published
    optimum in bench/optima.json. Returns per-instance status, cost, published cost and whether they match."""
    optima = json.loads((BENCH / "optima.json").read_text(encoding="utf-8"))
    chosen = names or sorted(optima)
    rows: list[dict[str, Any]] = []
    for name in chosen:
        if name not in optima:
            rows.append({"name": name, "error": "not in bench/optima.json"})
            continue
        result = solve_benchmark(parse_dzn(BENCH / "instances" / "medium" / f"{name}.dzn"), time_limit_s=time_limit_s)
        published = optima[name]
        rows.append({
            "name": name, "status": result.status, "holding": result.holding, "total": result.total,
            "published_holding": published["holding"], "published_total": published["total"],
            "matched": result.status == "OPTIMAL" and result.holding == published["holding"] and result.total == published["total"],
        })
    matched = sum(1 for r in rows if r.get("matched"))
    return {"instances": rows, "matched": f"{matched}/{len(rows)}"}


def main() -> None:
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
