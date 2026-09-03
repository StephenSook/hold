# HOLD in ninety seconds

Nothing below needs a key, an account or a local install until step 6. The web app is a separate
task and is not described here; every step is the API and the repository.

1. **The headline, self-reported.** Open https://hold-fwmdq7fc3q-uc.a.run.app/api/status. The
   `headline` block is read from the committed `docs/FACTS.json`; `runtime` says which model,
   location and transport are live right now and whether extraction is configured; `bob_usage`
   is the committed IBM Bob evidence aggregate.
2. **The routes.** https://hold-fwmdq7fc3q-uc.a.run.app/api/docs lists every endpoint with its
   schema. Everything under `/api` is unauthenticated on purpose.
3. **A solve.** In the Swagger page, `POST /api/solve` with the body of
   [`data/demo/hold-demo.json`](data/demo/hold-demo.json) (drop the keys that start with an
   underscore; they are labels). The answer is a job id. `GET /api/jobs/{id}` returns the order,
   the day assignment, the pass-2 cost with its status (OPTIMAL or FEASIBLE with a bound) and one
   pass-1 verdict per day.
4. **The verdict.** In that job, `result.pass1[n].verdict` on an illegal day carries
   `violations`: rule id, citation, limit, computed value, the verbatim quote and the source URL.
   `core_rule_ids` are the rules that each alone make the day impossible. The demo's solved plan
   has none; the hand-built order in [`data/demo/before-order.json`](data/demo/before-order.json)
   has one illegal day and four hold days.
5. **The set changes.** `POST /api/set-events` with
   `{"kind": "scene_dropped", "payload": {"scene_id": "s6"}, "source": "ui"}`. The response names
   the new job, the plan it edited and the transport that carried the event; `GET /api/events?job_id=...&limit=5&timeout_s=10`
   streams the objective and the verdicts as they land. Once the broker is connected (see `runtime.confluent` on the status page) the same event goes on
   `hold.set-events` and the verdicts come back on `hold.verdicts`.
6. **The residual, on your machine.** `git clone https://github.com/StephenSook/hold && cd hold && uv sync && uv run pytest api/tests/test_residual.py -v`
   solves the eight published talent-scheduling instances and compares each cost to the proven
   optimum. `uv run python scripts/facts.py --check` recomputes every headline number.
7. **The rules.** [`rules/`](rules/) holds the records; [`rules/sources/`](rules/sources/) the
   snapshots each quote is verified against; `uv run pytest api/tests/test_quotes.py -v` runs the
   check. `GET /api/rules` serves the records.
8. **The agent.** [`docs/adk_eval.json`](docs/adk_eval.json) is the recorded eval run, written by
   `scripts/adk_eval.py` from ADK's own result file. The live extraction goldens are under
   [`data/fixtures/extraction/`](data/fixtures/extraction/), each recorded from a real call.
9. **IBM Bob.** [`docs/bob-evidence/`](docs/bob-evidence/): the session export, the attribution
   breakdown with the build trace, the Bobcoin screenshots and the lane-enforcement record.
