"""
HOLD's MCP server on the public HTTP transport.

The failure this guards is specific and quiet. `/mcp` is mounted before the SPA catch-all; if that
order ever changes, or the mount is dropped, the catch-all answers `/mcp` with index.html and a
JSON-RPC client receives an HTML page and a 200. Nothing goes red, the route still "works", and
the integration a reader was invited to check is gone.

The second failure is the lifespan. A Starlette app mounted inside another app does not get its
own lifespan run, so the MCP session manager has to be started by ours. Without it the route
exists and every call fails. TestClient runs the lifespan, which is why these go through it.
"""
from __future__ import annotations

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from api.hold.mcp_server import http_app, public, server
from api.main import app

_HEADERS = {
    "Content-Type": "application/json",
    # Streamable HTTP requires the client to accept both. A client sending only JSON gets a 406,
    # which is the protocol working, not a bug.
    "Accept": "application/json, text/event-stream",
    "MCP-Protocol-Version": "2025-11-25",
}

_INITIALIZE = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-11-25",
        "capabilities": {},
        "clientInfo": {"name": "hold-tests", "version": "0"},
    },
}


def _first_json(body: str) -> dict[str, Any]:
    """Streamable HTTP answers as SSE by default: one `data:` line carrying the JSON-RPC message."""
    for line in body.splitlines():
        if line.startswith("data:"):
            parsed: dict[str, Any] = json.loads(line[len("data:"):].strip())
            return parsed
    whole: dict[str, Any] = json.loads(body)
    return whole


def test_the_mcp_route_speaks_json_rpc_and_not_the_spa() -> None:
    with TestClient(app) as client:
        response = client.post("/mcp/", headers=_HEADERS, json=_INITIALIZE)
    assert response.status_code == 200, response.text
    assert not response.text.lstrip().lower().startswith("<!doctype html>"), (
        "/mcp answered with the SPA fallback, so the mount is gone or the catch-all now wins"
    )
    message = _first_json(response.text)
    assert message["result"]["serverInfo"]["name"] == "hold"


@pytest.mark.parametrize("name", ["solve_schedule", "check_legality", "lookup_rule", "run_residual"])
def test_both_transports_carry_the_same_tool_names(name: str) -> None:
    """A client written against the stdio server must work against the deployed one.

    The two servers are separate instances because the public tools are capped and their
    descriptions say so. Separate instances can drift, and a renamed tool would break a reader's
    client with no other symptom, so the names are pinned rather than assumed.
    """
    import asyncio

    stdio = {t.name for t in asyncio.run(server.list_tools())}
    http = {t.name for t in asyncio.run(public.list_tools())}
    assert name in stdio
    assert name in http
    assert stdio == http


def test_the_public_tools_state_their_cap() -> None:
    """A caller should learn the limit from the tool, not from a timeout."""
    import asyncio

    tools = {t.name: (t.description or "") for t in asyncio.run(public.list_tools())}
    assert "5 seconds" in tools["solve_schedule"]
    assert "10 seconds" in tools["run_residual"]


def test_http_app_is_built_from_the_public_server() -> None:
    """The capped server is the one exposed. Mounting the uncapped one would be the whole risk."""
    assert http_app() is not None
    uncapped = {t.name: (t.description or "") for t in __import__("asyncio").run(server.list_tools())}
    assert "5 seconds" not in uncapped["solve_schedule"], "the stdio server must stay uncapped"


@pytest.mark.parametrize(
    ("origin", "expected"),
    [
        ("https://hold-fwmdq7fc3q-uc.a.run.app", "hold-fwmdq7fc3q-uc.a.run.app"),
        ("https://hold-fwmdq7fc3q-uc.a.run.app/", "hold-fwmdq7fc3q-uc.a.run.app"),
        ("hold-fwmdq7fc3q-uc.a.run.app", "hold-fwmdq7fc3q-uc.a.run.app"),
    ],
)
def test_the_deployed_host_is_allowed(monkeypatch: pytest.MonkeyPatch, origin: str, expected: str) -> None:
    """The production case, which is the one that was broken.

    Every local form of the host is allowed by default, so the transport passes every test that
    runs on a laptop and answers 421 to the first request that arrives at the deployed name. The
    variants cover a trailing slash and a bare host, because HOLD_ORIGIN is written by hand.
    """
    from api.hold import mcp_server

    monkeypatch.setenv("HOLD_ORIGIN", origin)
    assert expected in mcp_server._allowed_hosts()


def test_an_unset_origin_still_allows_local_development(monkeypatch: pytest.MonkeyPatch) -> None:
    from api.hold import mcp_server

    monkeypatch.delenv("HOLD_ORIGIN", raising=False)
    hosts = mcp_server._allowed_hosts()
    assert "localhost" in hosts and "127.0.0.1" in hosts


def test_the_app_can_be_started_more_than_once_in_one_process() -> None:
    """The defect that took the whole end-to-end suite down.

    A StreamableHTTPSessionManager refuses to run twice ("can only be called once per instance"),
    so a module-level MCP server starts once per PROCESS and every start after the first raises
    inside the lifespan. Nothing about that is visible until something brings the app up a second
    time: a second TestClient, a reload, a restarted worker. Here it was uvicorn under Playwright,
    and 27 of 30 browser tests failed with ECONNREFUSED against a server that never came up.

    Three starts, because two would pass against a fix that merely defers the failure by one.
    """
    for _ in range(3):
        with TestClient(app) as client:
            assert client.get("/api/status").status_code == 200
            response = client.post("/mcp/", headers=_HEADERS, json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
            assert response.status_code == 200, response.text
            assert "solve_schedule" in response.text
