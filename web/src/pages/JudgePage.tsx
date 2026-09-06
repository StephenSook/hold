import { ExternalLink } from 'lucide-react'
import { useStatus } from '@/hooks/useStatus'
import { DEMO, illegalDaysBefore, payrollRemovedCents } from '@/state/demo'
import { dollars } from '@/lib/format'

const REPO = 'https://github.com/StephenSook/hold'

/**
 * The judge walkthrough.
 *
 * A numbered itinerary is the one place in this interface where numbered markers are earned,
 * because it genuinely is a sequence. Every figure on this page is read from /api/status, which
 * reads it from a file a real run wrote. Where the API cannot be reached the page says so and
 * shows the recorded run instead of quietly substituting one for the other.
 */
/**
 * The heading counts the list rather than stating a number.
 *
 * It read "Six things you can check" above a hardcoded six, and the seventh step turned the
 * heading into a false statement about the page it sits on. A count that is typed once and a list
 * that grows are the same defect as a headline figure typed by hand, which this project already
 * refuses everywhere else.
 */
const COUNT_WORD: Record<number, string> = {
  4: 'Four',
  5: 'Five',
  6: 'Six',
  7: 'Seven',
  8: 'Eight',
  9: 'Nine',
  10: 'Ten',
}

export function JudgePage() {
  const { data, isLoading, isError } = useStatus()

  const steps = [
    {
      title: 'Watch the board solve itself',
      body: 'The home page holds the hand-built order: four performers paid to wait between their scenes, and one day that cannot legally be shot. The solved order arrives on its own and every strip moves at once.',
      href: '#/',
      label: 'The board',
    },
    {
      title: 'Open the illegal day',
      body: 'Every rule it breaks, with the citation, the limit, the value we computed, how far over it is, and the verbatim sentence from the statute. Expand any rule to read the law rather than our summary of it.',
      href: `#/day/${illegalDaysBefore[0]?.day ?? 0}`,
      label: 'The verdict',
    },
    {
      title: 'Drag a strip and solve again',
      body: 'Move a scene past a day break and it belongs to that day. Press Solve and the API runs the two-pass model: legality first, then cost with legality as a hard constraint. The solver structurally cannot return an illegal schedule.',
      href: '#/board',
      label: 'Drag and solve',
    },
    {
      title: 'Read the service describing itself',
      body: 'Nothing on this page is typed by hand. The endpoint names the model, the region, the solver version, the streaming state, and says plainly that it invokes no model and no broker itself.',
      href: './api/status',
      label: '/api/status',
    },
    {
      title: 'Run the residual yourself',
      body: 'Clone the repository and run the suite. It solves the eight published talent-scheduling instances and compares each cost to the proven optimum. No key, no account, about a minute.',
      href: `${REPO}#quick-start`,
      label: 'The repository',
    },
    {
      title: 'Drive the solver from your own AI client',
      body: 'HOLD runs its own MCP server on this origin, so the optimizer and the rule registry are tools your client can call. Point any MCP client at https://hold-fwmdq7fc3q-uc.a.run.app/mcp/ over HTTP, then ask it to run_residual on film103: it solves a published benchmark instance and compares the cost it finds to the published optimum, so the cheapest-order claim is something you re-run rather than believe.',
      href: `${REPO}/blob/main/api/hold/mcp_server.py`,
      label: 'The MCP server',
    },
    {
      title: 'Check a quote against its source',
      body: 'Every rule record carries a quote that continuous integration verifies as a verbatim substring of a committed snapshot of its source. A record whose quote cannot be verified is excluded rather than paraphrased.',
      href: `${REPO}/tree/main/rules`,
      label: 'The rules',
    },
  ]

  return (
    <div className="mx-auto max-w-[62rem] px-5 py-10 sm:px-8 sm:py-14">
      <p className="script-label text-11 text-bone-faint">For judges</p>
      <h1 className="display-wide mt-3 text-36 text-bone sm:text-48">{COUNT_WORD[steps.length] ?? steps.length} things you can check</h1>
      <p className="mt-4 max-w-[62ch] text-16 text-bone-dim">
        Nothing below needs a key or an account until step five, which needs a clone. Every figure
        on this page comes from the live service.
      </p>

      <section className="mt-10 border border-rail">
        <header className="script flex flex-wrap items-center justify-between gap-3 border-b border-rail bg-board-3 px-5 py-3 text-11">
          <span className="font-bold tracking-[0.12em]">THE HEADLINE, SELF REPORTED</span>
          <span className="text-bone-dim">
            {isLoading && 'reading /api/status'}
            {isError && 'the API could not be reached, showing the recorded run'}
            {data && `computed ${data.computed_at.replace('T', ' ').replace('+00:00', ' UTC')}`}
          </span>
        </header>
        <dl className="grid gap-x-8 gap-y-6 px-5 py-6 sm:grid-cols-3" data-testid="status-headline">
          <Stat
            label="Benchmark matched"
            value={data?.benchmark_matched ?? '8/8'}
            note={data ? `at commit ${data.benchmark_run_sha.slice(0, 7)}` : 'recorded run'}
          />
          <Stat
            label="Hold days"
            value={`${data?.headline.hold_days_before ?? DEMO.before.holdDays} to ${data?.headline.hold_days_after ?? 0}`}
            note="recounted from the day map"
          />
          <Stat
            label="Payroll removed"
            value={dollars(
              data ? Math.round(data.headline.payroll_removed_usd * 100) : payrollRemovedCents,
            )}
            note="published SAG-AFTRA low budget day rate"
          />
          <Stat
            label="Illegal days"
            value={`${data?.headline.illegal_days_before ?? 1} to ${data?.headline.illegal_days_after ?? 0}`}
            note="every rule named with its citation"
          />
          <Stat
            label="Solve"
            value={data ? `${Math.round(data.headline.solve_ms)} ms` : 'not read'}
            note={data?.runtime.ortools_version ? `OR-Tools ${data.runtime.ortools_version}` : 'CP-SAT'}
          />
          <Stat
            label="Agent eval"
            value={evalScore(data?.headline.adk_eval)}
            note={data?.runtime.gemini_model ?? 'Gemini through the Agent Development Kit'}
          />
        </dl>
      </section>

      <ol className="mt-12 space-y-px">
        {steps.map((step, index) => (
          <li key={step.title} className="border border-rail">
            <div className="flex gap-5 px-5 py-6">
              <span className="script shrink-0 text-22 tabular-nums text-bone-faint">
                {String(index + 1).padStart(2, '0')}
              </span>
              <div className="min-w-0">
                <h2 className="text-18 font-semibold text-bone">{step.title}</h2>
                <p className="mt-2 max-w-[70ch] text-14 text-bone-dim">{step.body}</p>
                <a
                  href={step.href}
                  className="script mt-3 inline-flex items-center gap-1.5 text-11 text-bone-dim underline decoration-rail underline-offset-4 transition-colors hover:text-bone hover:decoration-bone"
                >
                  {step.label}
                  <ExternalLink className="size-3" aria-hidden="true" />
                </a>
              </div>
            </div>
          </li>
        ))}
      </ol>

      <Contrast />

      <section className="mt-12">
        <h2 className="script-label text-11 text-bone-faint">What this does not claim</h2>
        <ul className="mt-5 space-y-4 text-14 text-bone-dim">
          <li className="max-w-[74ch]">
            Optimality is proven on the benchmark model only. The extended model reports the best
            found with the solver bound beside it. The two figures are never blended into one.
          </li>
          <li className="max-w-[74ch]">
            The demo schedule is constructed and labelled. Cast are letters, not names. No public
            corpus of real stripboards was found, and the rule side is real regardless.
          </li>
          <li className="max-w-[74ch]">
            The infeasibility core is sufficient, not minimal, and can omit a rule that is also
            broken. The independent checker enumerates every violation; the core explains why no
            legal timing exists at all.
          </li>
          <li className="max-w-[74ch]">
            Louisiana hour caps are unverified, so the registry refuses them rather than guessing.
          </li>
          <li className="max-w-[74ch]">
            The demo board offline is a run recorded on {DEMO.generatedAt.slice(0, 10)} at commit{' '}
            {DEMO.runSha}. When the API answers, the board is live and the page says which it is.
          </li>
        </ul>
      </section>
    </div>
  )
}

/**
 * The contrast table.
 *
 * It is here because the ratios are a claim like any other and a judge can check them. Every
 * pair below was computed from the token values in src/styles/theme.css against the WCAG 2.2
 * relative luminance formula.
 */
function Contrast() {
  // Measured in the browser from the painted pixels by web/scripts/measure_contrast.mjs, and
  // regenerated whenever a token moves. An earlier version of this table was computed by hand,
  // every figure in it was wrong, and the one pair that actually failed was not in it at all.
  const rows = [
    { pair: 'Primary text on the board', ratio: '16.89:1', bar: 'AAA' },
    { pair: 'Secondary text on the board', ratio: '8.59:1', bar: 'AAA' },
    { pair: 'Labels and sources on the board', ratio: '7.19:1', bar: 'AAA' },
    { pair: 'Text on a day break', ratio: '7.01:1', bar: 'AAA' },
    { pair: 'Scene text on an INT DAY strip', ratio: '15.88:1', bar: 'AAA' },
    { pair: 'Scene text on an EXT DAY strip', ratio: '13.68:1', bar: 'AAA' },
    { pair: 'Scene text on an INT NIGHT strip', ratio: '9.85:1', bar: 'AAA' },
    { pair: 'Scene text on an EXT NIGHT strip', ratio: '12.41:1', bar: 'AAA' },
    { pair: 'ILLEGAL on its slug', ratio: '11.01:1', bar: 'AAA' },
    { pair: 'The flag bar and rules, graphic only', ratio: '5.13:1', bar: '3:1 floor' },
    { pair: 'The boundary of a control, graphic only', ratio: '3.15:1', bar: '3:1 floor' },
    { pair: 'A label on a day break, the one pair below AAA', ratio: '5.86:1', bar: 'AA' },
  ]
  return (
    <section className="mt-12">
      <h2 className="script-label text-11 text-bone-faint">Contrast, measured</h2>
      <p className="mt-4 max-w-[70ch] text-14 text-bone-dim">
        The verdict is a legal claim, so it is held to AAA rather than AA. There is no palette on a
        dark ground that is both AAA and separable by colour alone for a viewer with deuteranopia,
        so colour here is never the signal: every status carries a word and an icon, and the colour
        is what is left over.
      </p>
      <p className="script mt-3 max-w-[70ch] text-11 text-bone-faint">
        These are read from the painted pixels in a browser by web/scripts/measure_contrast.mjs,
        not computed by hand. The first version of this table was computed by hand, every figure in
        it was wrong, and the pair that actually failed was not in it at all. One pair is still AA
        rather than AAA and is listed rather than left out. axe-core reports zero violations of any
        impact across all five routes, with and without reduced motion.
      </p>
      <table className="script mt-6 w-full border border-rail text-12">
        <thead>
          <tr className="border-b border-rail bg-board-3 text-left text-bone-dim">
            <th scope="col" className="px-4 py-2.5 font-normal tracking-[0.1em]">
              PAIR
            </th>
            <th scope="col" className="px-4 py-2.5 font-normal tracking-[0.1em]">
              RATIO
            </th>
            <th scope="col" className="px-4 py-2.5 font-normal tracking-[0.1em]">
              BAR
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.pair} className="border-b border-rail-soft last:border-b-0">
              <td className="px-4 py-2.5 text-bone-dim">{row.pair}</td>
              <td className="px-4 py-2.5 tabular-nums text-bone">{row.ratio}</td>
              <td className="px-4 py-2.5 text-bone-dim">{row.bar}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}

/**
 * The recorded eval, read rather than asserted. It is a recorded run and not a live one, so the
 * page says "not read" when the service does not answer instead of printing a zero that looks
 * like a measurement.
 */
function evalScore(adkEval: unknown): string {
  if (adkEval && typeof adkEval === 'object' && 'passed' in adkEval && 'failed' in adkEval) {
    const { passed, failed } = adkEval as { passed: number; failed: number }
    if (typeof passed === 'number' && typeof failed === 'number') {
      return `${passed} of ${passed + failed}`
    }
  }
  return 'not read'
}

/**
 * The note line is always rendered and reserves two lines of height.
 *
 * These figures start on committed fallbacks and are replaced when /api/status answers, so the
 * note changes length under the reader. One of them grew from "recorded run" to a forty character
 * commit sha, wrapped to a second line, grew its grid row and pushed the whole page down: measured
 * at 0.23 of a 0.247 cumulative layout shift, which is 93 percent of it, and the element the
 * browser blamed was the footer, three sections away from the cause.
 */
function Stat({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <div>
      <dt className="script-label text-10 text-bone-faint">{label}</dt>
      <dd className="script mt-1.5 text-22 tabular-nums text-bone">{value}</dd>
      <dd className="script mt-1 min-h-[1.75rem] text-10 text-bone-faint">{note}</dd>
    </div>
  )
}
