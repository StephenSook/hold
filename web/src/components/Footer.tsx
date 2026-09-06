import { HoldMark } from './HoldMark'

const REPO = 'https://github.com/StephenSook/hold'

/**
 * The footer states what the project is and where to check it, and nothing else. Every link
 * here goes somewhere a stranger can verify a claim made higher up the page.
 */
export function Footer() {
  return (
    <footer className="mt-24 border-t border-rail">
      <div className="mx-auto grid max-w-[1440px] gap-10 px-5 pt-14 pb-[calc(3.5rem+var(--safe-bottom))] sm:grid-cols-[1fr_auto] sm:px-8">
        <div className="max-w-md">
          <div className="flex items-center gap-2.5">
            <HoldMark className="h-5 w-5 text-bone" />
            <span className="display-wide text-16 text-bone">HOLD</span>
          </div>
          <p className="mt-4 text-14 text-bone-dim">
            The provably cheapest film shooting order, and a legality verdict for every day a child
            performer is on set, with the statute sentence on screen.
          </p>
          <p className="script mt-4 text-11 text-bone-faint">
            Apache-2.0. The demo schedule is constructed and labelled: cast are letters, not names.
            The rule side is real.
          </p>
        </div>

        <nav aria-label="Verify" className="script-label flex flex-col gap-3 text-11 sm:text-right">
          <a className="text-bone-dim transition-colors hover:text-bone" href={REPO}>
            Repository
          </a>
          <a className="text-bone-dim transition-colors hover:text-bone" href="./api/status">
            /api/status
          </a>
          <a className="text-bone-dim transition-colors hover:text-bone" href="./api/docs">
            /api/docs
          </a>
          <a className="text-bone-dim transition-colors hover:text-bone" href={`${REPO}/blob/main/JUDGE.md`}>
            Judge walkthrough
          </a>
        </nav>
      </div>
    </footer>
  )
}
