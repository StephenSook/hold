# Frontend Rules

Lane: `web/` (except `web/android/`, `web/ios/`, `web/src/native/`, `web/capacitor.config.ts`),
`docs/design/`

## Non-negotiable rules

1. **Render from fixtures, not from live data, during development.** Every component must
   render correctly against the JSON fixtures in `data/fixtures/contracts/` before any live
   API is wired. Deem imports the fixture, Stephen owns the schema.

2. **AAA contrast on verdict and primary text.** Minimum 7:1 ratio. Color plus text plus icon
   for every status indicator - never color alone.

3. **Mobile primary targets: 64-76 dp in the thumb zone.**

4. **No em-dashes.** Colon, comma, period, hyphen.

5. **Tool: IBM-Bob trailer on every Bob-authored commit.**

6. **Stage named paths only.** Never `git add -A`.

7. **Never touch:** `api/`, `bench/`, `rules/`, `scripts/`, `web/android/`, `web/ios/`,
   `web/src/native/`, `web/capacitor.config.ts`, `docs/bob-evidence/`, `specs/`.

8. **Contract changes are announced before they are committed.** If a shared contract
   (`api/hold/schemas.py`) needs to change, announce it in PLAN.md Shared Contracts first.
   Use the `CONTRACT:` commit prefix.

9. **`npm run test` maps to `vitest run` excluding `tests/e2e`.** E2E tests run separately
   under `HOLD_FAKE_EXTERNALS=1`.
