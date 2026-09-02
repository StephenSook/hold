# Solver Engine Rules

Lane: `api/hold/`, `api/tests/`, `api/routes/`, `bench/`, `rules/`, `scripts/`, `data/`,
`pyproject.toml`, `uv.lock`

## Non-negotiable rules

1. **Cite or refuse.** No legal value ships without a verbatim quote, citation, source URL,
   and effective dates. If a value cannot be verified, record it as UNVERIFIABLE and exclude
   it from claims. Louisiana caps are refused, not guessed.

2. **No em-dashes.** Not in code, not in comments, not in commit messages, not in docstrings.
   Colon for elaboration. Comma or parentheses for an aside. Period for a clause break.
   Hyphen for a range.

3. **Test count in every engine commit subject.** Example:
   `feat(solver): CP-SAT benchmark model, 1 test`
   Count the tests you add or modify. Include it.

4. **Tool: IBM-Bob trailer on every Bob-authored commit.**
   `git commit --trailer "Tool: IBM-Bob"`
   Never add the trailer afterwards. If you forget, that commit goes without it - do not amend.

5. **Stage named paths only.** Never `git add -A`. Run
   `git ls-files | grep -iE '\.pdf$|\.env$|^private/'` before every push and expect nothing.

6. **Tests are hermetic.** No test hits the live URL or fetches a source. Network tests carry
   `@pytest.mark.network` and are deselected by default. A skipped guard is a false green.

7. **Never touch:** `web/src/`, `web/android/`, `web/ios/`, `docs/design/`, `api/agents/`,
   `api/main.py`, `Dockerfile`.

8. **Headline numbers from FACTS.json only.** Never type a number by hand into README, docs,
   or the video script. `scripts/facts.py` writes `docs/FACTS.json` from a real run.

9. **One logical change per commit.** Subject 100 characters or fewer.

10. **Status commits are atomic.** PLAN.md status changes are their own commits, never bundled
    with code. Format: `status: <id> WIP|DONE <yyyy-mm-dd> <HH:MM> Stephen`
