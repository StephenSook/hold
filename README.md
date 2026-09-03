# HOLD

> Provably cheapest film shooting schedule. CP-SAT solver. Child-performer and SAG-AFTRA
> legality verdicts with citations. Built for the Agentic Cinema: The Blockbuster Hackathon,
> IBM partner track.

[![residual](https://github.com/StephenSook/hold/actions/workflows/ci.yml/badge.svg?job=residual)](https://github.com/StephenSook/hold/actions/workflows/ci.yml)
[![Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

---

## What it does

HOLD takes a list of scenes and who is in each one, and computes the cheapest possible order
to shoot them in. Not a good order, the provably cheapest one. Then it checks every shooting
day against child-performer law and the SAG-AFTRA contract and reports whether each day is
legal, and if not, every rule you broke and where each one is written down.

**Three things on screen:**

1. **The residual.** CP-SAT solver against the published proven optima of the academic
   talent-scheduling benchmark (8 medium instances, MIT-licensed data). Difference: 0.
   Re-run on every push in CI with no key and no account.
2. **The dollars.** A realistic schedule with its hold days disappearing (contract penalties
   are PLAN.md task 2.11 and are not modeled yet). The published SAG-AFTRA rate card on screen
   so anyone with a calculator can check.
3. **The verdict.** An illegal day names every violated rule: citation, limit, computed
   value, over-by, the verbatim sentence from the statute, a deep link.

---

## Quick start

Prerequisites: `uv`, `jq` (Node 22 once the web app lands).

```bash
git clone https://github.com/StephenSook/hold && cd hold
uv sync
uv run pytest api/tests -q                       # 268 hermetic tests, no key, no account
HOLD_FAKE_EXTERNALS=1 uv run uvicorn api.main:app --port 8000   # local API, fixtures instead of Gemini
uv run python scripts/simulate_set_day.py --api http://localhost:8000   # solve, then three set events re-solved
curl -s https://hold-fwmdq7fc3q-uc.a.run.app/api/status | jq            # the live headline
```

Live instance: https://hold-fwmdq7fc3q-uc.a.run.app (Cloud Run, one instance; the web app lands with its own tasks, the API and `/api/status` are up now).

---

## Honesty panel

- Two panels, never one blended number: optimality is proven on the benchmark model; the
  extended model reports "best found" with the solver's bound.
- The demo schedule is constructed and says so in the UI. No public corpus of real
  stripboards was found (searched 2026-08-27 to 2026-09-02).
- The infeasibility core from the solver is sufficient, not minimal. The independent checker
  lists every violation; the core explains why no legal timing exists.
- No industry-wide savings figure is published.
- The solver runs on the server. The phone displays and caches.
- Louisiana hour caps are unverified; the registry refuses them rather than guessing.
- Hold days: under the SAG-AFTRA low-budget agreements a day between work days is paid only on an overnight
  location (SAGindie FAQ, quoted in `rules/sag_rates.yaml`); the demo declares one. The Basic Agreement pays
  consecutive employment everywhere. HOLD counts every calendar day between a performer's first and last
  working day that they do not work, listed as a shoot day or not; the FAQ states the unlisted-weekday case
  and a weekend inside the span is counted the same way, which is HOLD's reading.
- Every rule quote is verbatim from a committed snapshot under `rules/sources/` and checked in CI, and every
  number in a record's params is stated by that quote, by a second verified fragment, or by a stated
  derivation (one value is a labeled assumption: a paid hold day at the tier day rate); the one record
  whose page refuses scripted fetches is labeled UNVERIFIABLE and excluded from claims.
- Streaming: connected at submission time; live state at `/api/status`.
- Practitioner interview: _pending_

---

## How IBM Bob was used

_Evidence table populated at each phase boundary. See `docs/bob-evidence/` for session
exports, screenshots, and the ATTRIBUTION.md per-commit breakdown._

| Evidence | Location |
|---|---|
| Session store export (counts, tokens, cost) | `docs/bob-evidence/bob-usage-evidence.json` |
| Attribution breakdown | `docs/bob-evidence/ATTRIBUTION.md` |
| Build trace | `docs/bob-evidence/build-trace.md` |
| Bobcoin screenshots | `docs/bob-evidence/bobcoins-*.png` |
| Lane-enforcement record | `docs/bob-evidence/lane-enforcement.md` |
| Spend table | _populated at phase boundary_ |

Trailer `Tool: IBM-Bob` on every Bob-authored commit. Test count in every engine commit
subject. Five write-scoped custom modes: `solver-engine`, `agent-runtime`, `mobile-shell`,
`frontend`, `evidence-writer`. Real Plan-mode outputs under `.bob/plans/`. Spec Kit
artifacts under `specs/`. Self-referential MCP server calling the solver while building it.

---

## Architecture

_Diagram at `docs/architecture.svg` after Phase 5. Runtime self-reported at `/api/status`._

---

## License

Apache-2.0. See [LICENSE](LICENSE).

Third-party notices: [docs/THIRD_PARTY_NOTICES.md](docs/THIRD_PARTY_NOTICES.md) (populated
at Phase 5).
