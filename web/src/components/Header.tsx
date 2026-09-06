import { NavLink, useLocation } from 'react-router-dom'
import { HoldMark } from './HoldMark'
import { SwapText } from './SwapText'
import { ThemeToggle } from './ThemeToggle'
import { illegalDaysBefore } from '@/state/demo'
import { cn } from '@/lib/cn'

/**
 * Day points at the day that cannot legally be shot, not at day one.
 *
 * Day one of the demo is legal, holds a single scene and demonstrates nothing: a reader who
 * clicks Day landed on the least interesting screen in the product. The illegal day is the one
 * carrying seven violations and the statute text, which is the thing worth showing. Derived from
 * the fixture rather than typed, so it follows the demo instead of going stale beside it.
 *
 * `match` exists because the link is no longer a prefix of every day route: with /day/3 in the
 * bar, browsing to /day/1 would leave Day unlit while the reader is plainly on a day.
 */
const NAV = [
  { to: '/board', label: 'Board', match: '/board' },
  { to: `/day/${illegalDaysBefore[0]?.day ?? 0}`, label: 'Day', match: '/day' },
  { to: '/import', label: 'Import', match: '/import' },
  { to: '/judge', label: 'Judge', match: '/judge' },
]

/**
 * The header is the head block of a call sheet: a hairline rail with the production on the
 * left, the sections across it, and nothing decorative. It does not float and it does not
 * round, because the paperwork it comes from does neither.
 */
export function Header() {
  const { pathname } = useLocation()
  return (
    <header className="sticky top-0 z-50 border-b border-rail bg-board/85 pt-[var(--safe-top)] backdrop-blur-sm">
      <div className="mx-auto flex h-14 max-w-[1440px] items-center gap-3 pe-[calc(1rem+var(--safe-right))] ps-[calc(1rem+var(--safe-left))] sm:gap-6 sm:pe-[calc(2rem+var(--safe-right))] sm:ps-[calc(2rem+var(--safe-left))]">
        <NavLink to="/" className="group/swap flex shrink-0 items-center gap-2.5" aria-label="HOLD, home">
          <HoldMark className="h-5 w-5 text-bone" />
          {/* At 390 px the wordmark is the 48 px that pushes Import and Judge off the rail. The
              mark carries the identity on its own and the page title carries the name. */}
          <span className="display-wide hidden text-16 leading-none text-bone xs:inline sm:inline">
            HOLD
          </span>
        </NavLink>

        <span className="hidden h-4 w-px bg-rail sm:block" aria-hidden="true" />

        <nav className="flex min-w-0 items-center gap-3.5 overflow-x-auto sm:gap-5" aria-label="Sections">
          {NAV.map((item) => {
            const active = pathname === item.match || pathname.startsWith(`${item.match}/`)
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={cn(
                  'group/swap script-label shrink-0 text-11 transition-colors',
                  active ? 'text-bone' : 'text-bone-faint hover:text-bone',
                )}
              >
                <SwapText>{item.label}</SwapText>
                <span
                  className={cn('mt-1 block h-px origin-left transition-transform duration-300', active ? 'scale-x-100 bg-bone' : 'scale-x-0 bg-rail')}
                  aria-hidden="true"
                />
              </NavLink>
            )
          })}
        </nav>

        <div className="ml-auto flex shrink-0 items-center gap-4">
          <ThemeToggle />
        </div>
      </div>
    </header>
  )
}
