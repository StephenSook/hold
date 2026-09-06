import { expect, test } from '@playwright/test'

/**
 * Cumulative layout shift, as a gate.
 *
 * Lighthouse scored the deployed judge route 0.52 on this, a measured CLS of 0.247, and the
 * element the browser blamed was the footer. The footer was not the cause. The routes are code
 * split, so the first paint is a Suspense fallback a couple of hundred pixels tall, the real page
 * arrives a few hundred milliseconds later, and the footer, which had been sitting inside the
 * viewport, got pushed two and a half thousand pixels down. Filling the main element to the
 * viewport height keeps the footer at or below the fold from the first frame.
 *
 * 0.1 is the threshold Core Web Vitals calls good. Every route measures 0.000 today, so this has
 * a wide margin and will only fire on a real regression.
 */
const ROUTES = [
  ['landing', '/#/'],
  ['board', '/#/board'],
  ['day', '/#/day/3'],
  ['import', '/#/import'],
  ['judge', '/#/judge'],
] as const

for (const [name, path] of ROUTES) {
  test(`${name} does not shift its layout while loading`, async ({ page }) => {
    await page.addInitScript(() => {
      ;(window as unknown as { __cls: number }).__cls = 0
      new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          const shift = entry as PerformanceEntry & { value: number; hadRecentInput: boolean }
          // A shift the reader caused by interacting is not a defect.
          if (!shift.hadRecentInput) (window as unknown as { __cls: number }).__cls += shift.value
        }
      }).observe({ type: 'layout-shift', buffered: true })
    })

    await page.goto(path)
    await expect(page.locator('h1').first()).toBeVisible({ timeout: 30_000 })
    // The shift this guards against happens when the lazy route chunk resolves, which is after
    // the heading exists. Waiting for the network to settle is what makes the measurement real.
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(1200)

    const cls = await page.evaluate(() => (window as unknown as { __cls: number }).__cls)
    expect(cls, `cumulative layout shift on ${name}`).toBeLessThan(0.1)
  })
}

test('the headline reveal leaves room for its descenders', async ({ page }) => {
  /*
   * The display sizes set a line height below 1, and the reveal wraps every line in an
   * overflow-hidden mask so the line can travel up into view. Together those cut the tails off
   * the y in "you" and the g and y in "legally" on the first screen of the site. The mask carries
   * padding for the descender and takes the same amount back in margin, so this asserts both: the
   * room exists, and it costs the layout nothing.
   */
  await page.goto('/#/')
  const masks = page.locator('h1 > span')
  await expect(masks.first()).toBeVisible()
  const count = await masks.count()
  expect(count).toBeGreaterThan(0)

  for (let i = 0; i < count; i += 1) {
    const box = await masks.nth(i).evaluate((el) => {
      const style = getComputedStyle(el)
      const size = parseFloat(style.fontSize)
      return {
        overflow: style.overflowY,
        padEm: parseFloat(style.paddingBottom) / size,
        marginEm: parseFloat(style.marginBottom) / size,
      }
    })
    expect(box.overflow, 'the mask is what makes the reveal work').toBe('hidden')
    expect(box.padEm, 'the mask must clear the font descender').toBeGreaterThanOrEqual(0.2)
    expect(box.padEm + box.marginEm, 'the room must cost the layout nothing').toBeCloseTo(0, 3)
  }
})
