import { expect, test } from '@playwright/test'

/**
 * Saying what happened, instead of knowing which button means it.
 *
 * The three buttons above this field have always worked; what they required was that a person
 * already knew HOLD's vocabulary. The interpreter takes the sentence a first AD actually says and
 * proposes one of the same three typed events from it.
 *
 * Two things are being proven here, and the second matters more. First, the surface exists and a
 * reading comes back. Second, nothing is applied by reading: the proposal sits there with a
 * publish button beside it, and the plan on the board does not move until someone presses it.
 * An agent that acted on its own reading would be a faster way to be wrong.
 *
 * The suite runs with HOLD_FAKE_EXTERNALS=1, so the reading is a recorded one and says so.
 */
test('a sentence becomes a typed event, and publishing it is still a human step', async ({ page }) => {
  await page.goto('/#/board')

  const panel = page.getByTestId('event-interpreter')
  await expect(panel).toBeVisible()

  // Solve first, so an event has a plan to edit and the publish button is reachable.
  await page.getByTestId('solve').click()
  await expect(page.getByTestId('job-id')).toBeVisible({ timeout: 120_000 })
  const firstPlan = await page.getByTestId('job-id').textContent()

  await page.getByTestId('event-sentence').fill('B is out on Thursday')
  await page.getByTestId('event-interpret').click()

  const proposal = page.getByTestId('interpret-proposal')
  await expect(proposal).toBeVisible({ timeout: 30_000 })
  // The reading is in the words a person uses, and the typed event is shown beside it.
  await expect(page.getByTestId('interpret-typed')).toContainText('actor_late')
  await expect(proposal).toContainText('fixture')

  // Reading changed nothing. The plan on the board is the one the solve produced.
  await expect(page.getByTestId('job-id')).toHaveText(firstPlan ?? '')

  await page.getByTestId('interpret-publish').click()

  // Publishing did, and it went through the same path the buttons use: a new plan id.
  await expect(page.getByTestId('job-id')).not.toHaveText(firstPlan ?? '', { timeout: 120_000 })
  // And the log says where the edit came from, which is the only reason the source exists.
  await expect(page.getByTestId('event-log')).toContainText('agent', { timeout: 30_000 })
})

test('the read button refuses an empty sentence rather than posting one', async ({ page }) => {
  await page.goto('/#/board')
  await expect(page.getByTestId('event-interpret')).toBeDisabled()
  await page.getByTestId('event-sentence').fill('   ')
  await expect(page.getByTestId('event-interpret')).toBeDisabled()
})
