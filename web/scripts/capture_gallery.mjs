/**
 * The gallery images (PLAN.md task 6.4).
 *
 * Real screen captures of the running product at the deployed URL. Not mockups, not renders, not
 * generated art: the demo-credibility rule says a gallery frame is a capture of the thing itself,
 * and a generated one is the exact failure that has cost a previous cycle.
 *
 *   cd web && node scripts/capture_gallery.mjs
 *   cd web && node scripts/capture_gallery.mjs http://127.0.0.1:8000   (against a local server)
 *
 * It lives in the web lane because that is where node_modules is; the images it writes belong
 * with the submission, so they go to docs/submission-assets/.
 *
 * Each shot waits for the state that makes it worth capturing, never for a timer, so a slow cold
 * start produces a late image rather than an empty one.
 */
import { chromium, webkit } from 'playwright'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const BASE = process.argv[2] ?? 'https://hold-fwmdq7fc3q-uc.a.run.app'
const OUT = fileURLToPath(new URL('../../docs/submission-assets/', import.meta.url))
const DESKTOP = { width: 1600, height: 1000 }

const settle = (page, ms) => page.waitForTimeout(ms)

async function openPage(browser, viewport) {
  const context = await browser.newContext({ viewport, deviceScaleFactor: 2 })
  const page = await context.newPage()
  const failures = []
  page.on('pageerror', (e) => failures.push(String(e)))
  page.on('response', (r) => {
    if (r.status() >= 400) failures.push(`${r.status()} ${r.url()}`)
  })
  return { context, page, failures }
}

async function shot(page, name) {
  const file = path.join(OUT, name)
  await page.screenshot({ path: file })
  const bytes = fs.statSync(file).size
  // A capture that is a blank frame is worse than no capture, because it looks like evidence.
  if (bytes < 20_000) throw new Error(`${name} is ${bytes} bytes, which is a blank frame`)
  console.log(`  ${name.padEnd(26)} ${(bytes / 1024).toFixed(0)} KB`)
}

const chrome = await chromium.launch({ headless: true, channel: 'chromium' })
console.log(`capturing from ${BASE}`)

{
  const { context, page, failures } = await openPage(chrome, DESKTOP)

  // 01 and 02: the board, before the solve and after it.
  await page.goto(`${BASE}/#/board`, { waitUntil: 'networkidle', timeout: 60_000 })
  await page.getByTestId('stripboard').waitFor({ timeout: 30_000 })
  await settle(page, 2500)
  await shot(page, '02-stripboard.png')

  await page.getByTestId('solve').click()
  await page.getByTestId('pass2-status').getByText(/OPTIMAL|FEASIBLE/).waitFor({ timeout: 120_000 })
  await settle(page, 1500)
  await shot(page, '01-before-after.png')

  // 03 and 04: the illegal day, then the statute behind one of its rules.
  await page.goto(`${BASE}/#/day/3`, { waitUntil: 'networkidle', timeout: 60_000 })
  await page.getByTestId('day-verdict').waitFor({ timeout: 30_000 })
  await settle(page, 1200)
  await shot(page, '03-illegal-day.png')

  await page.getByTestId(/^violation-/).first().click()
  await page.locator('blockquote').first().waitFor({ timeout: 15_000 })
  await settle(page, 800)
  await shot(page, '04-statute.png')

  // 06: the judge page, scrolled to the measured contrast table.
  await page.goto(`${BASE}/#/judge`, { waitUntil: 'networkidle', timeout: 60_000 })
  await page.getByTestId('status-headline').waitFor({ timeout: 30_000 })
  await settle(page, 2000)
  await shot(page, '06-judge.png')

  if (failures.length) throw new Error(`the deployed origin failed during capture: ${failures.join(' | ')}`)
  await context.close()
}

// 05: the phone, in WebKit, because that is what an assistant director is holding.
{
  const safari = await webkit.launch({ headless: true })
  const context = await safari.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 3 })
  const page = await context.newPage()
  await page.goto(`${BASE}/#/day/3`, { waitUntil: 'networkidle', timeout: 60_000 })
  await page.getByTestId('day-verdict').waitFor({ timeout: 30_000 })
  await settle(page, 1500)
  await shot(page, '05-day-view.png')
  await context.close()
  await safari.close()
}

// 07: the architecture diagram, rendered exactly as a viewer's browser renders it.
{
  const { context, page } = await openPage(chrome, { width: 1220, height: 832 })
  const svg = fs.readFileSync(path.join(OUT, '..', 'architecture.svg'), 'utf8')
  await page.setContent(`<style>html,body{margin:0;background:#101010}</style>${svg}`)
  await settle(page, 900)
  await shot(page, '07-architecture.png')
  await context.close()
}

await chrome.close()
console.log('every frame captured from the running product')
