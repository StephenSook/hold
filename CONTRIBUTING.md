# Contributing

This is a hackathon entry with a deadline, built by two people. Outside contributions are welcome
after the judging period; during it, an issue is more useful than a pull request.

## Running it

Everything in the README's quick start works from a clean clone with no key and no account. If a
printed command does not work for you, that is a bug and worth an issue on its own:
`docs/fresh-clone.md` records the last time somebody checked, and what it found.

## The rules this repository actually enforces

These are not style preferences. Each one is a CI job that will fail your build.

1. **No headline number is typed by hand.** Every figure on a judge-facing surface is read from
   `docs/FACTS.json`, which `scripts/facts.py` writes from a real run and CI recomputes. A number
   that disagrees fails `api/tests/test_facts.py`.
2. **Cite or refuse.** No legal value ships without a verbatim quote, a citation, a source URL and
   effective dates. A quote is verified in CI as a byte-for-byte substring of a committed snapshot
   of its source. A value that cannot be verified is refused rather than guessed.
3. **Claim only what runs.** A vendor or model named on the README, in `docs/`, or on the
   architecture diagram must be one `/api/status` reports. `api/tests/test_claims.py` checks it.
4. **No em-dashes**, anywhere, including code comments. Colon for elaboration, comma or
   parentheses for an aside, period for a clause break, hyphen for a range.
5. **A gate runs bare.** No pipe on a command's exit path: `cmd | tail` exits with `tail`'s status
   and hides the failure.
6. **A conditionally skipped test is a false green.** If a guard cannot run, make it fail, or make
   the pipeline produce what it needs.
7. **Stage named paths.** Never `git add -A`.

## Tests

```bash
uv sync && uv run pytest api/tests -q -m "not network"
cd web && npm ci && npm run build && npm run test && npx playwright test
```

The end-to-end suite runs against uvicorn serving the built app and the API from one origin, which
is what production runs. It needs no key: `HOLD_FAKE_EXTERNALS=1` makes the extraction route answer
from a committed fixture.

## Commits

Conventional Commits, one logical change each, subject 100 characters or fewer. Say what changed
and why it was wrong before, in the message, in plain sentences.
