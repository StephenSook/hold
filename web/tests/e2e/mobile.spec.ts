import { expect, test } from '@playwright/test'

/**
 * The phone (PLAN.md task 3.10), on WebKit at 390 px, which is the device an assistant director
 * actually reads a day on.
 *
 * This file exists partly because the mobile-webkit project in playwright.config.ts matched no
 * spec at all, so it ran zero tests and reported success. A project with nothing in it is the
 * quietest false green there is.
 */
test('the day view puts the verdict first and reads at 390 px', async ({ page }) => {
  await page.goto('/#/day/3')
  await expect(page.getByTestId('gate')).toBeHidden({ timeout: 20_000 })

  const verdict = page.getByTestId('day-verdict')
  await expect(verdict).toBeVisible()
  await expect(verdict).toContainText('ILLEGAL')

  // The verdict is above the scenes: on set the only question is whether the day is legal.
  const verdictBox = await verdict.boundingBox()
  const firstStrip = page.getByTestId(/^strip-/).first()
  await expect(firstStrip).toBeVisible()
  const stripBox = await firstStrip.boundingBox()
  expect(verdictBox!.y).toBeLessThan(stripBox!.y)

  // Nothing scrolls sideways. A board that scrolls sideways on a phone is unusable one-handed.
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - window.innerWidth,
  )
  expect(overflow).toBeLessThanOrEqual(1)
})

test('the primary targets in the thumb zone are big enough to hit', async ({ page }) => {
  await page.goto('/#/day/3')
  await expect(page.getByTestId('gate')).toBeHidden({ timeout: 20_000 })

  // The row's own bar is 64 dp and up for the primary targets. The day-to-day navigation at the
  // bottom of the view is what a thumb reaches for.
  const links = page.getByRole('link', { name: /^Day \d+$/ })
  const count = await links.count()
  expect(count).toBeGreaterThan(0)
  for (let i = 0; i < count; i += 1) {
    const box = await links.nth(i).boundingBox()
    expect(box!.height, 'a primary target in the thumb zone').toBeGreaterThanOrEqual(64)
  }
})

test('the statute is readable without pinching', async ({ page }) => {
  await page.goto('/#/day/3')
  await expect(page.getByTestId('gate')).toBeHidden({ timeout: 20_000 })

  await page.getByTestId(/^violation-/).first().click()
  const quote = page.locator('blockquote').first()
  await expect(quote).toBeVisible()
  const size = await quote.evaluate((el) => parseFloat(getComputedStyle(el).fontSize))
  expect(size, 'the statute quote font size').toBeGreaterThanOrEqual(14)
})
