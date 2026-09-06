import fs from 'node:fs'
import { fileURLToPath } from 'node:url'
import { expect, test } from '@playwright/test'

/**
 * The document has to become the input.
 *
 * Before this path existed, "Confirm and solve" set a boolean and printed a sentence, and the
 * board seeded unconditionally from the committed demo fixture. The agent read your call sheet,
 * showed four counts and dropped the result, while the project claimed on its own submission that
 * the document in front of you becomes the input. It did not.
 *
 * These tests are about the seam, so the agent is stubbed at the network boundary: whether Gemini
 * extracts well is what the ADK eval set measures, and it needs a key. What is unproven without a
 * test here is that a schedule which HAS been extracted reaches the solver.
 */
const DEMO = JSON.parse(
  fs.readFileSync(fileURLToPath(new URL('../../src/fixtures/demo-board.json', import.meta.url)), 'utf8'),
) as { schedule: unknown }

test('a confirmed extraction is handed to the board and solved', async ({ page }) => {
  // The agent's answer, at the network boundary. The shape is the contract, not a guess: it is
  // the committed fixture the rest of the suite already solves.
  await page.route('**/api/extract', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ status: 'ok', schedule: DEMO.schedule, questions: [], notes: [] }),
    })
  })

  await page.goto('/#/import')
  await page.getByTestId('import-text').fill('Scene 4 moves to Thursday.')
  await page.getByTestId('import-submit').click()

  const confirm = page.getByTestId('import-confirm')
  await expect(confirm).toBeEnabled()
  await confirm.click()

  // The outcome, not the click: the board is showing THIS schedule and says so.
  await expect(page.getByTestId('imported-notice')).toBeVisible()
  await expect(page.getByTestId('figure-scenes')).toBeVisible()

  // And it solved it without being asked again, which is the half of "confirm and solve" that
  // used to be missing.
  await expect(page.getByTestId('pass2-status')).toContainText(/OPTIMAL|FEASIBLE/, { timeout: 90_000 })
})

test('reset drops the imported schedule and returns to the demo', async ({ page }) => {
  await page.goto('/#/board')
  await page.evaluate((schedule) => {
    sessionStorage.setItem('hold.imported-schedule', JSON.stringify(schedule))
  }, DEMO.schedule)
  await page.reload()
  await expect(page.getByTestId('imported-notice')).toBeVisible()

  await page.getByTestId('reset').click()
  await expect(page.getByTestId('imported-notice')).toBeHidden()

  // Cleared, not merely hidden: a reload must not resurrect it.
  await page.reload()
  await expect(page.getByTestId('imported-notice')).toBeHidden()
})
