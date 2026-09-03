# Evidence honesty log

Task 5.12 asks for a log of any evidence row that could not be captured. Three could not, all for
the same reason, and this file states it rather than leaving the rows blank.

## What could not be captured, and why

Every IBM Bob account available to this project reached zero Bobcoins during Phase 2 on
2026-09-02 (three gauge screenshots in this directory, each at 50 of 50 spent). The plan tiers
were not renewed, so from commit `f00aa11` onward no Bob session could be started.

| Row | State | Why |
|---|---|---|
| `/review` SARIF over `api/hold/` and `api/agents/` | not captured | requires a Bob session; no account has coins |
| Lane-enforcement record with a real refusal SHA | not captured as a refusal | the write-scoped modes exist and their regexes are tested (`api/tests/test_bob_lane_enforcement.py`, twelve allow and refuse cases run in CI), but no Bob session remained in which to trigger and record an actual refusal |
| Session-store export after Phase 2 | not captured | the export in this directory is the last one taken while a session existed |
| Self-referential MCP server called by Bob (task 1.11) | server built, never called by Bob | `api/hold/mcp_server.py` and `.bob/mcp.json` ship and a test drives the server over the protocol; the "Bob calls `run_residual` from a Plan session" half needs an account |

## What was captured

| Evidence | File |
|---|---|
| Session store export (task count, cost) | `bob-usage-evidence.json` |
| Per-commit attribution and the build trace | `ATTRIBUTION.md` |
| Bobcoin exhaustion, three accounts | `bobcoins-stephen-20260902-p1.png`, `bobcoins-stephen-20260902-p1-account2.png`, `bobcoins-stephen-20260902-p2-account3.png` |
| Lane definitions and what enforces them | `lane-enforcement.md` |
| The aggregate served at runtime | `/api/status.bob_usage`, held to these files by `api/tests/test_bob_usage.py` |

No day-0 gauge screenshot exists for any account: the earliest captures are the exhaustion ones
taken on 2026-09-02, the same calendar day the build started. That absence is stated here instead
of being reconstructed after the fact.
