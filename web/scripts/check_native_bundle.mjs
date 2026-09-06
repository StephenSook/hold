/**
 * A native shell that cannot reach the API.
 *
 * The web build talks to a relative /api because one Cloud Run service serves both the app and
 * the routes. The native shells load from capacitor://localhost, where that same relative path
 * resolves to the bundle on disk, so they need VITE_API_BASE baked in at build time.
 *
 * Nothing about a build without it looks wrong. It compiles, it installs, it launches, and the
 * judge page renders and then quietly says the API could not be reached and shows the recorded
 * run instead. That is the failure this checks for, and it was found by looking at a screenshot
 * of the running app, which is the only place it is visible.
 *
 *   node scripts/check_native_bundle.mjs
 *
 * This is not a CI step. The synced bundles are build output and are gitignored, so on a clean
 * checkout there is nothing to inspect and the check would pass by having looked at nothing.
 * It runs as the last step of build:native instead, which is the moment the mistake is made.
 */
import { readdir, readFile } from 'node:fs/promises'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const WEB = join(dirname(fileURLToPath(import.meta.url)), '..')
const ORIGIN = process.env.VITE_API_BASE || 'https://hold-fwmdq7fc3q-uc.a.run.app'

const SHELLS = [
  { name: 'android', dir: join(WEB, 'android/app/src/main/assets/public/assets') },
  { name: 'ios', dir: join(WEB, 'ios/App/App/public/assets') },
]

const problems = []

for (const shell of SHELLS) {
  let files
  try {
    files = (await readdir(shell.dir)).filter((f) => f.endsWith('.js'))
  } catch {
    // A shell that has never been synced is not a failure here. It has no bundle to be wrong.
    console.log(`  ${shell.name.padEnd(8)} not synced, skipped`)
    continue
  }
  if (files.length === 0) {
    problems.push(`${shell.name}: synced but contains no javascript`)
    continue
  }
  let found = false
  for (const file of files) {
    if ((await readFile(join(shell.dir, file), 'utf8')).includes(ORIGIN)) {
      found = true
      break
    }
  }
  if (found) console.log(`  ${shell.name.padEnd(8)} reaches ${ORIGIN}`)
  else problems.push(`${shell.name}: no bundle names ${ORIGIN}, so the app will ask its own origin and fail`)
}

if (problems.length > 0) {
  console.error('a native shell was built without VITE_API_BASE. Run npm run build:native.')
  for (const p of problems) console.error(`  ${p}`)
  process.exit(1)
}
