# Agent Runtime Rules

Lane: `api/agents/`, `api/main.py`, `Dockerfile`, `api/hold/streaming.py`,
`api/hold/mcp_server.py`

## Non-negotiable rules

1. **The ADK API server is never mounted.** google-adk runs through a `Runner` behind our
   own FastAPI routes only. Never call `app.mount` with an ADK server.

2. **One Gemini call per extract request.** `POST /api/extract` has a 30-second timeout and
   one Gemini call per request. No retry loops inside a single request.

3. **A human confirms before anything solves.** The agent extracts into `ExtractResult`. The
   UI confirms. The solver never runs on unconfirmed data.

4. **Guardrails are not optional.** `before_tool_callback` allowlists the three tools
   (`check_legality`, `optimize_schedule`, `lookup_rule`) and validates arguments with
   Pydantic. An invalid argument is refused with a named field error.

5. **HOLD_FAKE_EXTERNALS=1 returns the golden fixture without calling Gemini.** Every test
   that would call Gemini must check this env var first.

6. **No em-dashes.** Colon, comma, period, hyphen. Never an em-dash.

7. **Tool: IBM-Bob trailer on every Bob-authored commit.**

8. **Stage named paths only.** Never `git add -A`.

9. **Never touch:** `web/src/`, `bench/`, `rules/`, `api/tests/`, `api/hold/model.py`,
   `api/hold/instance.py`, `api/hold/checker.py`.
