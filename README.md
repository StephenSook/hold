# HOLD

> The provably cheapest film shooting schedule, and a legality verdict for every day a child
> performer is on set, with the statute sentence on screen. Built for the Agentic Cinema:
> The Blockbuster Hackathon, IBM partner track.

[![residual](https://github.com/StephenSook/hold/actions/workflows/ci.yml/badge.svg?job=residual)](https://github.com/StephenSook/hold/actions/workflows/ci.yml)
[![Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

Live: https://hold-fwmdq7fc3q-uc.a.run.app/api/status (Cloud Run). Walkthrough for judges: [JUDGE.md](JUDGE.md).

---

## The problem

A shooting schedule decides two things nobody on a low-budget set has time to compute by hand:
how many days each performer is paid to wait between their scenes, and whether a day with a
minor on set is legal at all. The hour caps, curfews, turnaround and meal rules come from state
law, the union handbook and the low-budget agreements, and each one names a different number.
An assistant director juggles them on a whiteboard and finds out about the violation after it
has been paid for.

## What HOLD does

HOLD takes the scene list, who is in each scene, the shooting days and the rate tier, and
returns the cheapest order to shoot in and a verdict for every day.

1. **The cheapest order.** A CP-SAT model assigns scenes to days and orders them to minimize
   the hold days a performer is paid for, with every applicable rule as a hard constraint. It
   proves optimality or reports the bound it stopped at; the two are never blended.
2. **The verdict.** Every day is checked by an independent, plain-Python checker against the
   Georgia and California child-performer rules, the SAG-AFTRA young-performer handbook and
   the low-budget agreements. An illegal day names each rule it breaks with the citation, the
   limit, the computed value and the verbatim sentence from the source.
3. **The set changes, the plan follows.** A late actor, a dropped scene or a weather cover
   arrives as an event over HTTP or on a Confluent Cloud topic. The API re-solves from the
   latest plan and streams the new objective and verdicts back over server-sent events and a
   second topic.

An agent on Gemini turns a call sheet, a one-line schedule or a plain-English note into that
typed input, and refuses to guess anything the document does not state.

## The three proofs

Every number below is read from [`docs/FACTS.json`](docs/FACTS.json), which `scripts/facts.py`
writes from a real run and CI recomputes; a mismatch fails the build.

1. **The residual.** The benchmark CP-SAT model against the published proven optima of the
   academic talent-scheduling benchmark (MIT-licensed data): 8/8 instances matched, re-run on
   every push with no key and no account.
2. **The dollars.** On the constructed demo, the hand-built plan has 4 hold days and 1 illegal
   day; the solved plan has 0 hold days and 0 illegal days, removing $4,069.92 of payroll at the
   published SAG-AFTRA low-budget day rate plus pension and health, and the solver proves the
   optimum. The plain-Python recount agrees with the solver to the cent.
3. **The verdict.** Every rule record carries a quote that CI verifies as a verbatim substring
   of a committed snapshot of its source, and every number a record carries is evidenced by
   that source, except one that its source does not state: see the hold-day multiplier below. The agent's eval set (run against the tool-bearing agent; the extraction route's schema
   path is covered by the recorded live goldens) passes 4 of 4 cases at the last recorded run.

## Architecture, as the runtime reports it

`/api/status` self-reports what is live; nothing on it is typed by hand.

| Layer | What runs | Where it is reported |
|---|---|---|
| Solver | OR-Tools CP-SAT, pass 1 (legality with named rule assumptions) and pass 2 (order, days, hold-day cost) | `headline`, `benchmark_matched`, `ortools_version` |
| Rules | 70 records across Georgia, California, four Coogan-trust states and SAG-AFTRA, quotes verified in CI | `docs/FACTS.json` rules block |
| Agent | Gemini 3.1 Flash Lite on Vertex AI through the Google Agent Development Kit; guarded tools; a tool-less extraction twin | `runtime.gemini_model`, `runtime.gemini_location`, `runtime.adk_version`, `runtime.extraction` |
| Streaming | In-process bus, plus a Confluent Cloud bridge on `hold.set-events` and `hold.verdicts` once the broker is connected | `runtime.confluent` reports connected or not connected, counts, last error |
| Hosting | Cloud Run, deployed from CI through Workload Identity Federation, secrets in Secret Manager | `runtime.mode` |
| Evidence | The IBM Bob session export and attribution counts | `bob_usage` |

An architecture diagram lands with task 5.6. Routes: `/api/solve`, `/api/jobs/{id}`,
`/api/events` (SSE), `/api/set-events`, `/api/extract`, `/api/rules`, `/api/bench`,
`/api/status`, `/api/docs`.

## Quick start

Prerequisites: `uv` and `jq`. No key and no account are needed for anything below.

```bash
git clone https://github.com/StephenSook/hold && cd hold
uv sync
uv run pytest api/tests/test_residual.py -v            # proof 1: the benchmark residual, 8/8
uv run python scripts/facts.py --check                 # proof 2: recompute FACTS from a real run
uv run pytest api/tests -q -m "not network"            # the hermetic suite
HOLD_FAKE_EXTERNALS=1 uv run uvicorn api.main:app --port 8000   # local API; fixtures answer /api/extract
uv run python scripts/simulate_set_day.py --api http://localhost:8000   # solve, then three set events re-solved
curl -s https://hold-fwmdq7fc3q-uc.a.run.app/api/status | jq            # the live headline
```

Live extraction and the Confluent leg stay off until `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION=global`
and the `CONFLUENT_*` variables from [`.env.example`](.env.example) are set: fixtures answer extraction
and the in-process bus is the transport. The deployed instance has them. `scripts/simulate_set_day.py --transport confluent` runs the same day over the cluster.

## Honesty panel

- Two panels, never one blended number: optimality is proven on the benchmark model and on the
  demo; the extended model reports "best found" with the solver's bound whenever it stops early.
- The demo schedule is constructed and says so. No public corpus of real stripboards was found
  (searched 2026-08-27 to 2026-09-02).
- The infeasibility core lists the rules that each alone make a day impossible; the checker lists
  every violation.
- Hold days: under the SAG-AFTRA low-budget agreements a day between work days is paid only on
  an overnight location (SAGindie FAQ, quoted in `rules/sag_rates.yaml`); the demo declares one.
  The Basic Agreement pays consecutive employment, with a day-performer exception when a firm pick-up date
  is more than 10 calendar days out (14 for films not shot entirely in the USA); HOLD does not model that
  exception. HOLD counts every calendar day
  between a performer's first and last working day that they do not work, listed as a shoot day
  or not.
- The rest-period, forced-call and meal-penalty rules (task 2.11) exist as cent-exact library
  functions with their records and tests. The optimizer minimizes hold days; it does not yet
  price forced calls or meal penalties into the objective.
- Every rule quote is verbatim from a committed snapshot under `rules/sources/` and checked in
  CI. Every number a rule carries is evidenced by its source but one: the hold-day rate multiplier
  is 1.0 because the FAQ says the consecutive day is paid and names no multiplier, so the tier day
  rate is taken at face value. That record says `assumption:`, and FACTS counts it as the single
  assumed parameter. A page that refuses scripted
  fetches is captured from a browser and the snapshot header says so; a quote with no snapshot
  at all would be labeled UNVERIFIABLE and excluded from claims (none is, at this writing).
- Louisiana hour caps are unverified, so the registry carries no record for them and the
  jurisdiction has no Louisiana shoot state: such a shoot is `other` and gets the SAG-AFTRA
  records only. Its Coogan trust records are real and display only.
- The solver runs on the server. The phone app is not in this repository yet; when it lands it
  displays and caches rather than solving.
- Practitioner interview: five practitioners were written to on 2026-09-02; no reply as of
  2026-09-03. Nothing here claims a working assistant director has used HOLD.

## Streaming

`POST /api/set-events` applies an event to the latest plan (solved or still solving, so
consecutive events chain), queues a re-solve and mirrors the event onto `hold.set-events` with
its job id. A consumer in the API re-solves events that other producers publish on that topic
and mirrors every verdict onto `hold.verdicts`. The response names the transport that carried
the event; the in-process bus is the whole transport whenever the broker is unconfigured or
refuses a publish, and `/api/status` says which one is live. On the deployed instance and the
live cluster, an event produced by the simulation script came back as a verdict on the second
topic in under a second.

## How IBM Bob was used

_See `docs/bob-evidence/` for the session export, screenshots and the per-commit breakdown;
`/api/status.bob_usage` serves the committed aggregate._

| Evidence | Location |
|---|---|
| Session store export (counts, tokens, cost) | `docs/bob-evidence/bob-usage-evidence.json` |
| Attribution breakdown | `docs/bob-evidence/ATTRIBUTION.md` |
| Build trace | the Build trace section of `docs/bob-evidence/ATTRIBUTION.md` (every commit, in order) |
| Bobcoin screenshots | `docs/bob-evidence/bobcoins-*.png` |
| Lane-enforcement record | `docs/bob-evidence/lane-enforcement.md` |
| Spend table | the summary table of `docs/bob-evidence/ATTRIBUTION.md` and `total_cost_usd` in the export |

Trailer `Tool: IBM-Bob` on every Bob-authored commit. Test count in every engine commit
subject. Five write-scoped custom modes: `solver-engine`, `agent-runtime`, `mobile-shell`,
`frontend`, `evidence-writer`. Real Plan-mode outputs under `.bob/plans/`. Spec Kit
artifacts under `specs/`. The self-referential MCP server (task 1.11, `api/hold/mcp_server.py`, registered in
`.bob/mcp.json`) exposes `solve_schedule`, `check_legality`, `lookup_rule` and `run_residual` over stdio and is
driven by a test through the protocol; Bob never invoked it, because every Bob account was exhausted before
it existed.

## License

Apache-2.0. See [LICENSE](LICENSE).

Third-party notices: [docs/THIRD_PARTY_NOTICES.md](docs/THIRD_PARTY_NOTICES.md), generated from the
installed dependency metadata.
