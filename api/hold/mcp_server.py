"""
Task 1.11: HOLD's own MCP server, so an MCP client can solve a schedule, judge a day, look up a
rule and run the benchmark residual. The first three tools are the same functions the ADK agent's
guarded tools call (api/agents/hold_agent/tools.py); every answer is a plain dict.

Two transports, and the difference between them is the point.

  stdio   the full server, capped only by the solver's own limit. IBM Bob registers this in
          .bob/mcp.json and calls it while the code is being written.

              uv run python -m api.hold.mcp_server

  http    the same four tools on the deployed origin at /mcp, so a reader can point their own MCP
          client at the live service and run the solver themselves rather than taking our word
          for it. A claimed integration that only ever runs inside our own process is a claim
          nobody outside can check.

Every tool on the HTTP transport is capped, and each description says its cap. The public origin
is one Cloud Run instance that also serves the app, and CP-SAT will spend a full minute on a hard
instance, so an uncapped public solver is a way to take the site down by using it as intended. A
caller should learn the cap from the tool rather than from a timeout.
"""
from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from typing import Any

from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.responses import Response

from api.agents.hold_agent.tools import check_legality as _check_legality
from api.agents.hold_agent.tools import lookup_rule as _lookup_rule
from api.agents.hold_agent.tools import optimize_schedule as _optimize_schedule
from api.hold.instance import parse_dzn
from api.hold.model import solve_benchmark

ROOT = Path(__file__).resolve().parents[2]
BENCH = ROOT / "bench"

PUBLIC_SOLVE_S = float(os.environ.get("HOLD_MCP_HTTP_SOLVE_S", "5"))
PUBLIC_BENCH_S = float(os.environ.get("HOLD_MCP_HTTP_BENCH_S", "10"))


@contextmanager
def _capped(seconds: float) -> Iterator[None]:
    """Hold the solver to a time limit for the duration of one public tool call.

    The tools read HOLD_SOLVE_TIME_LIMIT_S at call time, so the cap is applied where the limit is
    read and restored afterwards. It is set and unset around a single synchronous call, which is
    what the MCP server gives us; a request that ran the solver on a thread would need the limit
    threaded through the call instead, and that is worth knowing before anyone makes it async.
    """
    key = "HOLD_SOLVE_TIME_LIMIT_S"
    previous = os.environ.get(key)
    os.environ[key] = str(seconds)
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = previous


def _residual(names: list[str] | None, time_limit_s: float) -> dict[str, Any]:
    """Solve benchmark instances and compare each cost to the published optimum."""
    optima = {
        k: v
        for k, v in json.loads((BENCH / "optima.json").read_text(encoding="utf-8")).items()
        if not k.startswith("_")  # "_note" is documentation
    }
    if names is not None and not names:
        return {"error": "names is empty; pass null for every instance or a list of instance names", "instances": sorted(optima)}
    rows: list[dict[str, Any]] = []
    for name in names if names is not None else sorted(optima):
        if name not in optima:
            rows.append({"name": name, "error": "not in bench/optima.json", "known": sorted(optima)})
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


_INSTRUCTIONS = (
    "Film schedule optimizer and child-performer legality checker. Tools answer with plain JSON "
    "objects; an object with an `error` key is a refusal, not a result."
)

server = MCPServer(name="hold", instructions=_INSTRUCTIONS)


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
    return _residual(names, time_limit_s)


def _build_public() -> MCPServer:
    """The public server, built in its own scope so its capped tools cannot shadow the stdio ones.

    Same four names on the wire, so a client written against one transport works against the other.
    """
    public = MCPServer(
        name="hold",
        instructions=(
            _INSTRUCTIONS + " This is the live service, and solve time is capped here, so a large "
            "schedule may answer FEASIBLE with a bound rather than OPTIMAL. The uncapped server "
            "runs over stdio from the repository."
        ),
    )

    @public.tool()
    def solve_schedule(schedule: dict[str, Any]) -> dict[str, Any]:  # noqa: D401
        """Find the cheapest legal scene order and day assignment for a HOLD ScheduleInput, then re-judge
        every day. Capped at 5 seconds here: a schedule too large to prove optimal in that time answers
        FEASIBLE with the bound it reached, which is a real answer rather than a failure."""
        with _capped(PUBLIC_SOLVE_S):
            return _optimize_schedule(schedule)

    @public.tool()
    def check_legality(schedule: dict[str, Any], day_index: int) -> dict[str, Any]:  # noqa: D401
        """Judge one shooting day against child-performer law and the SAG-AFTRA rules. Returns every
        violated rule with its citation and the verbatim sentence from the source it was read from."""
        with _capped(PUBLIC_SOLVE_S):
            return _check_legality(schedule, day_index)

    @public.tool()
    def lookup_rule(rule_id: str) -> dict[str, Any]:  # noqa: D401
        """Return one rule record by id: citation, title, the verbatim quote, source URL, params and note.
        Call it with an unknown id and the answer lists the ids that exist."""
        return _lookup_rule(rule_id)

    @public.tool()
    def run_residual(name: str) -> dict[str, Any]:  # noqa: D401
        """Solve ONE named benchmark instance and compare its cost to the published optimum, so the
        cheapest-order claim can be checked instead of believed. One instance per call and 10 seconds
        here; the stdio server runs all eight."""
        return _residual([name], PUBLIC_BENCH_S)

    return public


public = _build_public()


def _allowed_hosts() -> list[str]:
    """The hosts the MCP transport will answer on.

    The SDK enforces DNS-rebinding protection by validating the Host header against a list, and it
    answers 421 Misdirected Request for anything else. The default list is localhost, so a server
    that works perfectly on a laptop rejects every request once it is deployed under a real
    hostname. That is exactly what happened here, and a test caught it rather than a judge.

    The deployed host comes from HOLD_ORIGIN, the same variable the CORS list is built from, so
    there is one place to change when the origin changes. `testserver` is the Host that Starlette's
    TestClient sends.
    """
    # The `host:*` form is the SDK's wildcard for any port, which local development needs: the
    # allowlist is matched against the Host header verbatim, so a fixed "127.0.0.1:8000" rejects
    # the same server started on any other port. The deployed host is exact, and carries no port
    # because Cloud Run terminates TLS on 443.
    hosts = ["localhost", "127.0.0.1", "localhost:*", "127.0.0.1:*", "testserver"]
    origin = os.environ.get("HOLD_ORIGIN", "").strip()
    if origin:
        host = origin.split("://", 1)[-1].rstrip("/")
        if host:
            hosts.append(host)
    return hosts


def _http_app_for(srv: MCPServer) -> Starlette:
    """The Starlette app for one MCP server instance.

    Stateless: the origin is one Cloud Run instance that can be replaced between two requests, and
    a session pinned to a process that has gone away is a confusing failure for a caller who did
    nothing wrong.
    """
    return srv.streamable_http_app(
        streamable_http_path="/",
        stateless_http=True,
        transport_security=TransportSecuritySettings(allowed_hosts=_allowed_hosts(), allowed_origins=["*"]),
    )


class MountedMCP:
    """The ASGI app mounted at /mcp, rebuilt for each application lifespan.

    A StreamableHTTPSessionManager refuses to run twice: "can only be called once per instance".
    A module-level server therefore starts once per PROCESS, and the second start raises. That is
    not a theoretical problem: it took the whole end-to-end suite down, because anything that
    brings the app up a second time in one process, a test client, a reload, a restarted worker,
    hits it. So the server, its app and its session manager are built inside the lifespan and
    dropped when it ends, and this shim forwards to whichever one is currently running.
    """

    def __init__(self) -> None:
        self._app: Starlette | None = None

    @asynccontextmanager
    async def running(self) -> AsyncIterator[None]:
        srv = _build_public()
        self._app = _http_app_for(srv)
        try:
            async with srv.session_manager.run():
                yield
        finally:
            self._app = None

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if self._app is None:
            # Reachable only if something routes here outside the lifespan. Answering plainly beats
            # an AttributeError, and says which of the two things is wrong.
            await Response("the MCP server is not running", status_code=503)(scope, receive, send)
            return
        await self._app(scope, receive, send)


MOUNT = MountedMCP()


def http_app() -> Starlette:
    """A standalone app for tests and for anyone serving the MCP transport on its own."""
    return _http_app_for(_build_public())


def main() -> None:
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
