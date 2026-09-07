# HOLD in ninety seconds

Start with the [live board and guided walkthrough](https://hold-fwmdq7fc3q-uc.a.run.app/#/judge).
For a phone, [join the approved iOS TestFlight beta](https://testflight.apple.com/join/guYBH8xE)
or use the [Android download and install instructions](README.md). The iOS beta requires the
TestFlight app. External testing of build 3 was approved and verified on September 7, 2026.

The API and repository checks below need no key or account. Only step 6 needs a local install.

1. **The headline, self-reported.** Open https://hold-fwmdq7fc3q-uc.a.run.app/api/status. The
   `headline` block is read from the committed `docs/FACTS.json`; `runtime` says which model,
   location and transport are live right now and whether extraction is configured; `bob_usage`
   is the committed IBM Bob evidence aggregate.
2. **The routes.** https://hold-fwmdq7fc3q-uc.a.run.app/api/docs lists every endpoint with its
   schema. Everything under `/api` is unauthenticated on purpose. One thing to know before you
   poke at paths: anything that is not a file and not under `/api` answers 200 with the web app,
   because that is how a single-page app is served. A status code alone therefore proves nothing
   about whether a route exists; read the body.
3. **A solve.** In the Swagger page, `POST /api/solve` with the body of
   [`data/demo/hold-demo.json`](data/demo/hold-demo.json) (drop the keys that start with an
   underscore; they are labels). The answer is a job id. `GET /api/jobs/{id}` returns the order,
   the day assignment, the pass-2 cost with its status (OPTIMAL or FEASIBLE with a bound) and one
   pass-1 verdict per day.
4. **The verdict.** In that job, `result.pass1[n]` on an illegal day carries `violations`: rule
   id, citation, limit, computed value, the verbatim quote and the source URL.
   `core_rule_ids` are the rules that each alone make the day impossible. The demo's solved plan
   has none; the hand-built order in [`data/demo/before-order.json`](data/demo/before-order.json)
   has one illegal day and four hold days.
5. **The set changes.** `POST /api/set-events` with
   `{"kind": "scene_dropped", "payload": {"scene_id": "s6"}, "source": "ui"}`. The response names
   the new job, the plan it edited and the transport that carried the event; `GET /api/events?job_id=...&replay=true&limit=5&timeout_s=10`
   streams the objective and the verdicts as they land. Once the broker is connected (see `runtime.confluent` on the status page) the same event goes on
   `hold.set-events` and the verdicts come back on `hold.verdicts`.
6. **The residual, on your machine.** `git clone https://github.com/StephenSook/hold && cd hold && uv sync && uv run pytest api/tests/test_residual.py -v`
   solves the eight published talent-scheduling instances and compares each cost to the proven
   optimum. `uv run python scripts/facts.py --check` recomputes every headline number.
7. **Drive the solver from your own AI client.** HOLD runs its own MCP server on the deployed
   origin, so the schedule optimizer and the rule registry are tools your client can call. Add it
   Any MCP client can call them. To see the server answer with no client at all:

   ```
   curl -sS https://hold-fwmdq7fc3q-uc.a.run.app/mcp/ \
     -H 'Content-Type: application/json' \
     -H 'Accept: application/json, text/event-stream' \
     -H 'MCP-Protocol-Version: 2025-11-25' \
     -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
   ```

   Or point any MCP client at `https://hold-fwmdq7fc3q-uc.a.run.app/mcp/` over HTTP.

   Four tools: `solve_schedule`, `check_legality`, `lookup_rule`, `run_residual`. The one worth
   your time is the last one. `run_residual` with `name: "film103"` solves a published academic
   benchmark instance and compares the cost it finds to the published optimum, so the claim that
   this solver finds the provably cheapest order is something you can re-run rather than believe:

   ```
   {"name": "film103", "status": "OPTIMAL", "holding": 187, "published_holding": 187, "matched": true}
   ```

   Solve time is capped on the public transport, and each tool says its own cap, because the
   origin is one instance that also serves the app. The uncapped server is the same file, over
   stdio, from a clone.

8. **The rules.** [`rules/`](rules/) holds the records; [`rules/sources/`](rules/sources/) the
   snapshots each quote is verified against; `uv run pytest api/tests/test_quotes.py -v` runs the
   check. `GET /api/rules` serves the records.
9. **The agent.** [`docs/adk_eval.json`](docs/adk_eval.json) is the recorded eval run, written by
   `scripts/adk_eval.py` from ADK's own result file. The live extraction goldens are under
   [`data/fixtures/extraction/`](data/fixtures/extraction/), each recorded from a real call.
10. **IBM Bob.** [`docs/bob-evidence/`](docs/bob-evidence/): the session export, the attribution
   breakdown with the build trace, the Bobcoin screenshots and the lane-enforcement record.
