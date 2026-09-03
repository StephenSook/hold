# HOLD: Agent Instructions

**Project:** HOLD - provably cheapest film shooting schedule optimizer with child-performer
and SAG-AFTRA legality verdicts.

**Repo:** github.com/StephenSook/hold | Apache-2.0

**Team:**
- Stephen: `api/`, `bench/`, `rules/`, `scripts/`, `data/`, `docs/` (except `docs/design/`),
  `security/`, `specs/`, `web/android/`, `web/ios/`, `web/src/native/`,
  `web/capacitor.config.ts`, root files.
- Deem: `web/` (except the four native paths above), `docs/design/`.

---

## Bob evidence protocol

- `Tool: IBM-Bob` trailer on every Bob-authored commit, added at commit time.
- Test count in every engine commit subject: `feat(solver): model, 12 tests`
- Five write-scoped custom modes in `.bob/custom_modes.yaml`. Use the right mode for the
  right lane. Rules per mode in `.bob/rules-*/AGENTS.md`.
- Real Plan-mode outputs under `.bob/plans/`. Spec Kit artifacts under `specs/`.
- Session store export at every phase boundary: `uv run python scripts/export_bob_evidence.py`
- Screenshots at day 0, end of each phase, exhaustion. See PLAN.md section "IBM Bob evidence
  protocol" for the full procedure.

---

## Hard rules (override everything else)

1. **PLAN.md is the spec.** Do not re-litigate a locked Decision (D1-D17). If PLAN.md is
   ambiguous, ask one precise question.

2. **Proof before pixels.** Task order: Phase 0 then Phase 1 exactly as numbered. The
   Wednesday 22:00 gate (residual 8/8 green in CI) is the first deliverable.

3. **Cite or refuse.** No legal value ships without a verbatim quote, citation, source URL,
   and effective dates. Louisiana caps are refused, not guessed.

4. **No em-dashes anywhere.** Code, comments, commit messages, docs, product copy, this file.
   Colon for elaboration. Comma or parentheses for an aside. Period for a clause break.
   Hyphen for a range.

5. **Headline numbers from docs/FACTS.json only.** Written by `scripts/facts.py` from a
   real run. Never type a number by hand.

6. **Tests are hermetic.** CI gates run bare with no pipe on the exit path. A skipped guard
   is a false green.

7. **Stage named paths only.** Never `git add -A`. Run
   `git ls-files | grep -iE '\.pdf$|\.env$|^private/'` before every push and expect nothing.

8. **Do not touch web/** except `web/android`, `web/ios`, `web/src/native`, and
   `web/capacitor.config.ts`. Those are the only web paths in Stephen's lane.

9. **Do not copy text from private/ or any PDF into a tracked file.**

10. **One logical change per commit.** Subject 100 characters or fewer. Status-only PLAN.md
    changes are their own commits.

---

## Shared contracts (schema owners)

| Contract | Owner | File |
|---|---|---|
| `ScheduleInput` | Stephen | `api/hold/schemas.py` |
| `ExtractResult` | Stephen | `api/hold/schemas.py` |
| `Verdict` | Stephen | `api/hold/schemas.py` |
| `SolveResult` | Stephen | `api/hold/schemas.py` |
| SSE events | Stephen | `api/hold/schemas.py` |
| `/api/status` | Stephen | `api/routes/status.py` |
| Rules record | Stephen | `rules/schema.json` |
| `docs/FACTS.json` | Stephen | written by `scripts/facts.py` |

Contract changes: announce in PLAN.md Shared Contracts first, `CONTRACT:` commit prefix.

---

## MCP server (self-referential, task 1.11)

`.bob/mcp.json` registers HOLD's own MCP server (`api/hold/mcp_server.py`, the MCP Python SDK over
stdio) so an MCP client can call `solve_schedule`, `check_legality`, `lookup_rule` and
`run_residual` while working on HOLD. It is never mounted in production.
`api/tests/test_mcp_server.py` spawns it and calls it through the protocol. Bob never invoked it:
every Bob account was exhausted before the server existed, so the "Bob calls run_residual from a
Plan session" half of the task did not happen and PLAN.md says so.

---

## What never gets committed

`private/`, `*.pdf`, `.env`, anything under `docs/video/raw/`, `*.jks`,
`*.keystore`, `rules/sources-cache/`, assistant config files.
