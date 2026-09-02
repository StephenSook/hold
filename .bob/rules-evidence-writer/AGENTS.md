# Evidence Writer Rules

Lane: `docs/` (except `docs/design/`), `README.md`, `specs/`, `security/`

## Non-negotiable rules

1. **Headline numbers from FACTS.json only.** Every numeric claim in README.md, docs/,
   judge-facing surfaces, and the video script must come from `docs/FACTS.json` which is
   written by `scripts/facts.py` from a real run. Never type a number by hand. Hand edits
   fail CI.

2. **Cite or refuse.** No legal statement without citation, verbatim quote, source URL, and
   effective dates. Unverified values are refused.

3. **Do not copy text from private/ or from any PDF into a tracked file.** Those are
   background only. If a fact from them is needed in the repo, write it in your own words
   with its primary citation.

4. **No em-dashes.** Colon, comma, period, hyphen.

5. **Tool: IBM-Bob trailer on every Bob-authored commit.**

6. **Stage named paths only.** Never `git add -A`.

7. **Never touch:** `docs/design/`, `api/`, `web/src/`, `bench/`, `rules/`, `scripts/`.

8. **Honesty panel is non-negotiable.** The README and `/judge` must carry the full honesty
   panel from PLAN.md section "The product in two sentences" including the two-panel split,
   the constructed-data label, and the streaming statement.

9. **Bob evidence is recorded while building, never reconstructed after.** Any evidence row
   not captured gets a dated statement of absence. No reconstructed transcripts, ever.
