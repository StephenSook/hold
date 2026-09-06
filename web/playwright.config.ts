import { defineConfig, devices } from '@playwright/test'

/**
 * The golden path (PLAN.md task 5.7).
 *
 * The server under test is uvicorn serving BOTH the built app and /api from one origin, which is
 * what Cloud Run runs. Testing against `vite preview` would be easier and would have missed the
 * production outage found on 2026-09-05, where the SPA fallback answered registerSW.js with HTML:
 * that bug lived in the FastAPI static route and no amount of front-end testing could see it.
 *
 * HOLD_FAKE_EXTERNALS=1 makes /api/extract answer from the committed fixture and no model is
 * called, so this needs no key and no account.
 */
const PORT = Number(process.env.HOLD_E2E_PORT ?? 8123)
const BASE = process.env.HOLD_E2E_BASE ?? `http://127.0.0.1:${PORT}`

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false, // the API holds one job store and one solver thread
  forbidOnly: !!process.env.CI,
  // No retries, deliberately. A golden path that passes on the second attempt is a green gate
  // over a surface that is flaky for a judge too, and this suite is the gate for exactly that
  // surface. A flake here is a finding, not something to absorb.
  retries: 0,
  workers: 1,
  timeout: 120_000,
  expect: { timeout: 20_000 },
  reporter: process.env.CI ? [['github'], ['list']] : 'list',
  use: {
    baseURL: BASE,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'mobile-webkit', use: { ...devices['iPhone 14'] }, testMatch: /mobile\.spec\.ts/ },
  ],
  webServer: process.env.HOLD_E2E_BASE
    ? undefined
    : {
        // Run from the repository root so uvicorn finds api/ and web/dist.
        command: `cd .. && uv run uvicorn api.main:app --host 127.0.0.1 --port ${PORT}`,
        url: `${BASE}/api/status`,
        reuseExistingServer: !process.env.CI,
        timeout: 180_000,
        env: { HOLD_FAKE_EXTERNALS: '1', HOLD_SOLVE_TIME_LIMIT_S: '20' },
        stdout: 'pipe',
        stderr: 'pipe',
      },
})
