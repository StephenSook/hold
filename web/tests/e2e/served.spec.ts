import fs from 'node:fs'
import { fileURLToPath } from 'node:url'
import { expect, test } from '@playwright/test'

/**
 * What the origin serves.
 *
 * On 2026-09-05 production served the app and the app did not run: every file Vite writes at the
 * root of dist came back as index.html with content-type text/html, and the browser threw
 * "Unexpected token '<'" on every route. CI, the deploy and the served HTML were all green.
 * These are the assertions that would have failed.
 */
// Read from the build rather than hard-coded. A hard-coded list goes stale the moment the PWA
// plugin changes what it emits, and a spec that names a file which no longer exists fails for a
// reason that has nothing to do with the defect it was written for.
const DIST = fileURLToPath(new URL('../../dist', import.meta.url))
const ROOT_FILES = fs
  .readdirSync(DIST, { withFileTypes: true })
  .filter((entry) => entry.isFile() && entry.name !== 'index.html')
  .map((entry) => entry.name)

test('the build emits root files for this to be about', () => {
  // Without this the loop below is a test suite with no tests in it, which passes.
  expect(ROOT_FILES.length).toBeGreaterThan(2)
  expect(ROOT_FILES).toContain('sw.js')
})

for (const file of ROOT_FILES) {
  test(`/${file} is served as itself and not as the app`, async ({ request }) => {
    const response = await request.get(`/${file}`)
    expect(response.status()).toBe(200)
    const type = response.headers()['content-type'] ?? ''
    expect(type).not.toContain('text/html')
    expect(await response.text()).not.toContain('<!doctype html>')
  })
}

test('the module entry is javascript', async ({ page, request }) => {
  await page.goto('/')
  const src = await page.locator('script[type=module]').first().getAttribute('src')
  expect(src).toBeTruthy()
  const response = await request.get(src!.replace(/^\.\//, '/'))
  expect(response.status()).toBe(200)
  expect(response.headers()['content-type'] ?? '').not.toContain('text/html')
})

test('no route throws in the console', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', (e) => errors.push(String(e)))
  page.on('console', (m) => {
    if (m.type() === 'error') errors.push(m.text())
  })
  for (const route of ['#/', '#/board', '#/day/3', '#/import', '#/judge']) {
    await page.goto(`/${route}`, { waitUntil: 'networkidle' })
    await page.waitForTimeout(1200)
  }
  expect(errors, `console errors: ${errors.join(' | ')}`).toEqual([])
})

test('the api answers on the same origin the app is served from', async ({ request }) => {
  const response = await request.get('/api/status')
  expect(response.status()).toBe(200)
  const body = await response.json()
  expect(body.headline_source).toBe('docs/FACTS.json')
})
