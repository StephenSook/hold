import { useMemo } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { DEMO } from '@/state/demo'
import { VerdictCard } from '@/verdict/VerdictCard'
import { Strip } from '@/board/Strip'
import { eighths, hhmm, shootDate } from '@/lib/format'

/**
 * One shooting day, for a phone on set.
 *
 * The verdict is first, because on set the only question is whether the day is legal. Then the
 * call and wrap, then the scenes as strips. Targets in the thumb zone are 64 px and up, and
 * every status carries a word and an icon as well as a colour.
 */
export function DayPage() {
  const params = useParams()
  const index = Number.parseInt(params.day ?? '0', 10)
  const day = Number.isFinite(index) ? Math.max(0, Math.min(index, DEMO.schedule.days.length - 1)) : 0

  const shootDay = DEMO.schedule.days[day]
  const verdict = DEMO.before.verdicts.find((v) => v.day === day) ?? null
  const scenes = useMemo(() => {
    const sceneIds = DEMO.before.dayMap[String(day)] ?? []
    return sceneIds
      .map((id) => DEMO.schedule.scenes.find((scene) => scene.id === id))
      .filter((scene): scene is NonNullable<typeof scene> => Boolean(scene))
  }, [day])
  const pages = scenes.reduce((sum, scene) => sum + scene.pages_eighths, 0)

  return (
    <div className="mx-auto max-w-[46rem] px-4 py-6 sm:px-6 sm:py-10">
      <Link
        to="/board"
        className="script-label inline-flex h-11 items-center gap-2 text-11 text-bone-dim transition-colors hover:text-bone"
      >
        <ArrowLeft className="size-3.5" aria-hidden="true" />
        The board
      </Link>

      <header className="mt-4">
        <p className="script-label text-11 text-bone-faint">
          Day {day + 1} of {DEMO.schedule.days.length}
        </p>
        <h1 className="display-wide mt-2 text-28 text-bone">{shootDate(shootDay.date)}</h1>
        <dl className="script mt-4 flex flex-wrap gap-x-8 gap-y-2 text-12 text-bone-dim">
          <div>
            <dt className="inline text-bone-faint">CALL </dt>
            <dd className="inline tabular-nums">{hhmm(shootDay.call)}</dd>
          </div>
          <div>
            <dt className="inline text-bone-faint">WRAP </dt>
            <dd className="inline tabular-nums">{hhmm(shootDay.wrap)}</dd>
          </div>
          <div>
            <dt className="inline text-bone-faint">PAGES </dt>
            <dd className="inline tabular-nums">{eighths(pages)}</dd>
          </div>
          <div>
            <dt className="inline text-bone-faint">SCENES </dt>
            <dd className="inline tabular-nums">{scenes.length}</dd>
          </div>
          {shootDay.school_day && (
            <div>
              <dt className="inline text-bone-faint">SCHOOL </dt>
              <dd className="inline">IN SESSION</dd>
            </div>
          )}
        </dl>
      </header>

      {verdict ? (
        <div className="mt-7 border border-rail" data-testid="day-verdict">
          <VerdictCard verdict={verdict} date={shootDate(shootDay.date)} />
        </div>
      ) : (
        <p className="script mt-7 border border-rail px-4 py-6 text-12 text-bone-dim">
          No verdict has been computed for this day.
        </p>
      )}

      <section className="mt-10">
        <h2 className="script-label text-11 text-bone-faint">Scenes</h2>
        {scenes.length === 0 ? (
          <p className="mt-4 text-14 text-bone-dim">
            Nothing is scheduled on this day. Drag a strip onto it from the board.
          </p>
        ) : (
          <ul className="mt-4 border border-rail">
            {scenes.map((scene) => (
              <li key={scene.id}>
                <Strip scene={scene} cast={DEMO.schedule.cast} flagged={verdict?.status === 'ILLEGAL'} />
              </li>
            ))}
          </ul>
        )}
      </section>

      <nav className="mt-10 flex items-center justify-between gap-4">
        {day > 0 ? (
          <Link
            to={`/day/${day - 1}`}
            className="script-label flex h-16 min-w-[7rem] items-center justify-center border border-rail px-4 text-11 text-bone-dim transition-colors hover:border-bone-faint hover:text-bone"
          >
            Day {day}
          </Link>
        ) : (
          <span />
        )}
        {day < DEMO.schedule.days.length - 1 && (
          <Link
            to={`/day/${day + 1}`}
            className="script-label ml-auto flex h-16 min-w-[7rem] items-center justify-center border border-rail px-4 text-11 text-bone-dim transition-colors hover:border-bone-faint hover:text-bone"
          >
            Day {day + 2}
          </Link>
        )}
      </nav>
    </div>
  )
}
