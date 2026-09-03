"""Task 1.11: HOLD's own MCP server over stdio. The test drives it the way any MCP client would: spawn
the process, list the tools, call two of them and read the structured results."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

ROOT = Path(__file__).resolve().parents[2]


def _demo() -> dict[str, Any]:
    raw = json.loads((ROOT / "data" / "demo" / "hold-demo.json").read_text(encoding="utf-8"))
    return {k: v for k, v in raw.items() if not k.startswith("_")}


def _payload(result: Any) -> dict[str, Any]:
    if getattr(result, "structuredContent", None):
        return dict(result.structuredContent)
    text = next(c.text for c in result.content if getattr(c, "type", "") == "text")
    return dict(json.loads(text))


async def _drive() -> dict[str, Any]:
    params = StdioServerParameters(command=sys.executable, args=["-m", "api.hold.mcp_server"], cwd=str(ROOT), env={"HOLD_FAKE_EXTERNALS": "1", "PATH": "/usr/bin:/bin"})
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        tools = await session.list_tools()
        names = sorted(t.name for t in tools.tools)
        rule = _payload(await session.call_tool("lookup_rule", {"rule_id": "GA_300_7_1_03_earliest_call"}))
        day = _payload(await session.call_tool("check_legality", {"schedule": _demo(), "day_index": 0}))
        bad = _payload(await session.call_tool("lookup_rule", {"rule_id": "NOT_A_RULE"}))
        return {"names": names, "rule": rule, "day": day, "bad": bad}


def test_mcp_server_lists_and_answers_the_four_tools() -> None:
    out = asyncio.run(_drive())
    assert out["names"] == ["check_legality", "lookup_rule", "run_residual", "solve_schedule"]
    assert out["rule"]["id"] == "GA_300_7_1_03_earliest_call" and "5:00" in out["rule"]["quote"]
    assert out["day"]["status"] in ("LEGAL", "ILLEGAL", "UNDETERMINED")
    assert "error" in out["bad"]


def test_bob_registers_the_server() -> None:
    cfg = json.loads((ROOT / ".bob" / "mcp.json").read_text(encoding="utf-8"))
    hold = cfg["mcpServers"]["hold"]
    assert hold["args"][-1] == "api.hold.mcp_server" and "-m" in hold["args"]
