import { expect, test } from '@playwright/test'

/**
 * The agent, reachable.
 *
 * `root_agent` carries the three tools and the allowlist that guards them, and no route ran it:
 * every path went to the tool-less extraction twin. So the tools were defined, unit-tested and
 * unreachable on the deployed service, and the guardrail had never executed in production.
 *
 * The suite runs with HOLD_FAKE_EXTERNALS=1, so the route answers with a recorded result that
 * labels itself. What is being proven here is the surface: that a reader can ask, and that the
 * trajectory is shown rather than only the sentence.
 */
test('a question reaches the agent and the answer shows what it called', async ({ page }) => {
  await page.goto('/#/board')

  const panel = page.getByTestId('ask-agent')
  await expect(panel).toBeVisible()

  await page.getByTestId('ask-input').fill('Why can day 4 not be shot legally?')
  await page.getByTestId('ask-submit').click()

  const result = page.getByTestId('ask-result')
  await expect(result).toBeVisible({ timeout: 30_000 })

  // The trajectory is the point. An answer with no visible tool call is an assertion.
  const calls = page.getByTestId('ask-tool-call')
  await expect(calls.first()).toBeVisible()
  await expect(calls).toHaveCount(2)
  await expect(result).toContainText('check_legality')
  await expect(result).toContainText('lookup_rule')

  // And it says it is recorded rather than implying a model ran.
  await expect(result).toContainText('recorded answer')
})

test('the ask button refuses an empty question rather than posting one', async ({ page }) => {
  await page.goto('/#/board')
  await expect(page.getByTestId('ask-submit')).toBeDisabled()
  await page.getByTestId('ask-input').fill('   ')
  await expect(page.getByTestId('ask-submit')).toBeDisabled()
})
