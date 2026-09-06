import { expect, test } from '@playwright/test'

/**
 * Offline (PLAN.md task 3.11).
 *
 * The row's own acceptance is: "Airplane mode: request fails visibly, cached verdict still
 * renders". That is a machine-checkable sentence and this is the machine checking it, rather
 * than a person looking at a phone once and remembering that it worked.
 *
 * The rule under test is the one the interface must never break: offline it names the time the
 * cache was written and never claims fresh data.
 */
test.describe('offline', () => {
  test('the request fails visibly and the cached verdict still renders', async ({ page, context }) => {
    // Online first, so there is something in the cache to fall back on.
    await page.goto('/#/judge')
    await expect(page.getByTestId('gate')).toBeHidden({ timeout: 20_000 })
    await expect(page.getByTestId('status-headline')).toContainText('8/8', { timeout: 30_000 })

    await context.setOffline(true)
    await page.reload()

    // want 1: the interface says it is offline and when the cache was written.
    const banner = page.getByTestId('offline-banner')
    await expect(banner).toBeVisible({ timeout: 20_000 })
    await expect(banner).toContainText('OFFLINE')

    // want 1: the verdict is still readable with no network at all.
    await page.goto('/#/day/3')
    const verdict = page.getByTestId('day-verdict')
    await expect(verdict).toBeVisible({ timeout: 20_000 })
    await expect(verdict).toContainText('ILLEGAL')
    await expect(verdict).toContainText('8 CCR 11760(e)')

    // want 0: nothing anywhere claims this is live.
    await expect(page.getByTestId('status-live')).toHaveCount(0)
    await context.setOffline(false)
  })

  test('the board says the API could not be reached rather than failing silently', async ({ page, context }) => {
    await page.goto('/#/board')
    await expect(page.getByTestId('gate')).toBeHidden({ timeout: 20_000 })
    await context.setOffline(true)

    await page.getByTestId('solve').click()

    const error = page.getByTestId('solve-error')
    await expect(error).toBeVisible({ timeout: 40_000 })
    await expect(error).toContainText(/did not run/i)

    // And the recorded run is offered, labelled as recorded rather than substituted silently.
    await error.getByRole('button', { name: /recorded run/i }).click()
    await expect(page.getByTestId('fallback-notice')).toContainText(/not a\s+live solve/i)
    await context.setOffline(false)
  })
})
