import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'

/**
 * Accessibility, as a gate rather than as a document (PLAN.md task 4.6).
 *
 * docs/design/axe-report.md has claimed "zero violations of any impact across all five routes"
 * since the web lane shipped, and the harness that produced it was never committed: it lived in a
 * scratch directory and ran once, by hand. A published claim whose check cannot be re-run is a
 * claim about a moment, and two judged surfaces have changed since that moment (the judge page
 * grew a step, the board grew the agent panel).
 *
 * So the assertion here is the published claim itself, not a weaker one. If a route ever carries
 * a violation of any impact, this fails and either the route is fixed or the sentence in the
 * report is corrected. It runs in the existing e2e job, against the built app served by the same
 * origin as the API, so it needs no new infrastructure and cannot quietly stop running.
 */
const ROUTES = [
  ['landing', '/#/'],
  ['board', '/#/board'],
  ['day', '/#/day/3'],
  ['import', '/#/import'],
  ['judge', '/#/judge'],
] as const

for (const [name, path] of ROUTES) {
  test(`${name} has no axe violations`, async ({ page }) => {
    await page.goto(path)
    // The gate is dismissed on the landing route only; elsewhere it never appears.
    await page.keyboard.press('Escape').catch(() => {})
    // Wait for the route's own heading rather than a timer, so a slow chunk cannot produce a
    // clean scan of an empty page.
    await expect(page.locator('h1').first()).toBeVisible({ timeout: 30_000 })
    await page.waitForTimeout(600)

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze()

    const summary = results.violations.map(
      (v) => `${v.impact ?? 'unknown'}  ${v.id}  ${v.nodes.length} node(s)  ${v.help}`,
    )
    expect(summary, `axe violations on ${name}`).toEqual([])
  })
}
