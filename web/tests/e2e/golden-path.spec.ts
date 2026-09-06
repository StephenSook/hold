import fs from 'node:fs'
import { fileURLToPath } from 'node:url'
import { expect, test, type Page } from '@playwright/test'

/**
 * The figures come from docs/FACTS.json, which a real run writes and CI recomputes. CI rule 8
 * forbids an unverified figure becoming an assertion, and a typed digit here would be worse than
 * unverified: the suite would DEFEND it, so correcting the engine would read as a regression.
 */
const FACTS = JSON.parse(
  fs.readFileSync(fileURLToPath(new URL('../../../docs/FACTS.json', import.meta.url)), 'utf8'),
) as {
  hold_days_before: number
  hold_days_after: number
  illegal_days_before: number
  illegal_days_after: number
  benchmark_matched: string
}

/**
 * The golden path (PLAN.md task 5.7), against uvicorn serving the built app and /api from one
 * origin, with HOLD_FAKE_EXTERNALS=1 so no key is needed.
 *
 * Every assertion here is about an OUTCOME, never about a click having happened. The three
 * failure modes this kind of test usually dies of are a disabled button, a guessed selector and
 * an empty screen, so: selectors are test ids or accessible roles and never Tailwind classes,
 * every action waits for the state that makes it possible, and each step asserts the state it
 * produced before the next one runs.
 */

const dismissGate = async (page: Page) => {
  // The load-in is skipped on a repeat view within a session. Wait it out on the first.
  await expect(page.getByTestId('gate')).toBeHidden({ timeout: 20_000 })
}

test.describe('the board', () => {
  test('loads the hand-built order with its hold days and its illegal day', async ({ page }) => {
    await page.goto('/#/board')
    await dismissGate(page)

    const board = page.getByTestId('stripboard')
    await expect(board).toBeVisible()

    // Every scene in the demo schedule is on the board, and the count comes from the fixture
    // rather than from a digit typed here.
    const sceneCount = JSON.parse(
      fs.readFileSync(fileURLToPath(new URL('../../src/fixtures/demo-board.json', import.meta.url)), 'utf8'),
    ).schedule.scenes.length as number
    await expect(page.getByTestId(/^strip-/)).toHaveCount(sceneCount)

    // Exactly one day is illegal before the solve, and it names its rules.
    const illegal = page.getByTestId(/^open-verdict-/)
    await expect(illegal).toHaveCount(FACTS.illegal_days_before)
    await expect(illegal.first()).toContainText('ILLEGAL')
    await expect(illegal.first()).toContainText('RULE')

    // The figure is the one the project computes, not one this test typed.
    await expect(page.getByTestId('figure-hold-days')).toContainText(String(FACTS.hold_days_before))
  })

  test('a verdict names every rule with the sentence from its source', async ({ page }) => {
    await page.goto('/#/board')
    await dismissGate(page)

    await page.getByTestId(/^open-verdict-/).first().click()
    const dialog = page.getByRole('dialog')
    await expect(dialog).toBeVisible()
    await expect(dialog).toContainText('ILLEGAL')

    // Open the first rule and read the statute, not our summary of it.
    const firstRule = dialog.getByTestId(/^violation-/).first()
    await firstRule.click()
    const quote = dialog.locator('blockquote').first()
    await expect(quote).toBeVisible()
    // The quote is a real sentence from a real source, so it is long and it cites somewhere.
    await expect(quote).not.toBeEmpty()
    expect((await quote.innerText()).length).toBeGreaterThan(40)
    await expect(dialog.getByRole('link', { name: /CCR|Code|Ga\.|Handbook/i }).first()).toHaveAttribute(
      'href',
      /^https?:\/\//,
    )

    await page.keyboard.press('Escape')
    await expect(dialog).toBeHidden()
  })

  test('dragging a strip past a day break moves it to that day', async ({ page }) => {
    await page.goto('/#/board')
    await dismissGate(page)

    const dayOfStrip = async (id: string) =>
      await page.getByTestId(`strip-${id}`).getAttribute('data-day')

    const before = await dayOfStrip('s1')
    expect(before).toBe('0')

    // Keyboard drag rather than a mouse drag: it is the accessible path, it is deterministic,
    // and a mouse drag against an animated list is the classic flaky e2e. The waits are not
    // padding: dnd-kit recomputes the droppable rects between moves, and pressing two arrows in
    // the same millisecond asks it to decide against measurements it has not taken yet.
    const strip = page.getByTestId('strip-s1')
    await strip.focus()
    await page.keyboard.press('Space')
    await expect(page.getByRole('status')).toContainText(/is over/i, { timeout: 5_000 })
    for (let i = 0; i < 2; i += 1) {
      await page.keyboard.press('ArrowDown')
      await page.waitForTimeout(250)
    }
    await page.keyboard.press('Space')

    await expect(async () => {
      expect(await dayOfStrip('s1')).not.toBe(before)
    }).toPass({ timeout: 10_000 })
  })

  test('solving reorders the board, removes the hold days and clears the illegal day', async ({ page }) => {
    await page.goto('/#/board')
    await dismissGate(page)

    const orderBefore = await page.getByTestId(/^strip-/).evaluateAll((els) =>
      els.map((e) => e.getAttribute('data-scene')),
    )

    await page.getByTestId('solve').click()

    // Wait on the solver's answer, never on a timer: this is a real CP-SAT run.
    await expect(page.getByTestId('pass2-status')).toContainText(/OPTIMAL|FEASIBLE/, { timeout: 90_000 })

    const orderAfter = await page.getByTestId(/^strip-/).evaluateAll((els) =>
      els.map((e) => e.getAttribute('data-scene')),
    )
    expect(orderAfter).not.toEqual(orderBefore)
    expect(orderAfter.slice().sort()).toEqual(orderBefore.slice().sort())

    await expect(page.getByTestId('figure-hold-days')).toContainText(String(FACTS.hold_days_after))
    // FACTS says the solved plan has no illegal day. This asserts that, rather than asserting
    // that one particular day stopped being illegal.
    expect(FACTS.illegal_days_after).toBe(0)
    await expect(page.getByTestId(/^open-verdict-/)).toHaveCount(0)
  })
})

test.describe('import', () => {
  test('reads a document, solves nothing until a person confirms, then hands it to the board', async ({ page }) => {
    await page.goto('/#/import')
    await dismissGate(page)

    await page.getByTestId('import-text').fill('Shoot scene 1 at the police station on the first day.')
    await page.getByTestId('import-submit').click()

    const result = page.getByTestId('extract-result')
    await expect(result).toBeVisible({ timeout: 30_000 })
    // Under fake externals the route says so in its own notes rather than implying a model ran.
    await expect(result).toContainText(/fixture|HOLD_FAKE_EXTERNALS/i)

    // Nothing is confirmed yet, so the board has not been handed anything.
    await page.goto('/#/board')
    await dismissGate(page)
    await expect(page.getByTestId('imported-notice')).toHaveCount(0)

    // Confirming is the handoff. This assertion used to be that a sentence appeared on the import
    // page, which was all confirming did: the extracted schedule was dropped when the page
    // unmounted and the board re-seeded from the demo fixture regardless.
    await page.goto('/#/import')
    await dismissGate(page)
    await page.getByTestId('import-text').fill('Shoot scene 1 at the police station on the first day.')
    await page.getByTestId('import-submit').click()
    await expect(page.getByTestId('extract-result')).toBeVisible({ timeout: 30_000 })
    await page.getByTestId('import-confirm').click()

    await expect(page.getByTestId('imported-notice')).toBeVisible({ timeout: 30_000 })
  })
})

test.describe('an event on set', () => {
  test('a dropped scene re-solves the plan and the new plan arrives over the stream', async ({ page }) => {
    await page.goto('/#/board')
    await dismissGate(page)

    // A set event edits the latest plan, so there has to be one.
    await page.getByTestId('solve').click()
    await expect(page.getByTestId('pass2-status')).toContainText(/OPTIMAL|FEASIBLE/, { timeout: 90_000 })
    const firstJob = await page.getByTestId('job-id').innerText()
    const stripsBefore = await page.getByTestId(/^strip-/).count()

    await page.getByTestId('set-event-scene_dropped').click()

    // The response names a new job, which is the proof the plan was re-solved and not patched.
    await expect(page.getByTestId('job-id')).not.toHaveText(firstJob, { timeout: 90_000 })
    await expect(page.getByTestId('pass2-status')).toContainText(/OPTIMAL|FEASIBLE/, { timeout: 90_000 })
    await expect(page.getByTestId(/^strip-/)).toHaveCount(stripsBefore - 1)

    // The stream carried it. The transport is named rather than assumed.
    await expect(page.getByTestId('event-log')).toContainText(/in-process|confluent/)
  })
})

test.describe('operations that overlap', () => {
  test('resetting during a solve does not let the solve paint the board afterwards', async ({ page }) => {
    await page.goto('/#/board')
    await dismissGate(page)

    await page.getByTestId('solve').click()
    // Reset while it is still solving. An unmount flag alone did not cover this: the poll kept
    // running and painted a live result over a board the person had just reset.
    await expect(page.getByTestId('solve')).toContainText(/Solving/i, { timeout: 10_000 })
    await page.getByTestId('reset').click()

    // The board is back to the hand-built order and stays there.
    await expect(page.getByTestId('figure-hold-days')).toContainText(String(FACTS.hold_days_before))
    await expect(page.getByTestId('pass2-status')).toContainText('not run')
    await page.waitForTimeout(8_000)
    await expect(page.getByTestId('pass2-status')).toContainText('not run')
    await expect(page.getByTestId('figure-hold-days')).toContainText(String(FACTS.hold_days_before))
    await expect(page.getByTestId('solve-error')).toHaveCount(0)
  })
})
