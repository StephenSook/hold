import { forwardRef } from 'react'
import type { CSSProperties, HTMLAttributes } from 'react'
import type { CastMember, Scene } from '@/types/contracts'
import { castChip, eighths, isMinor, stripColour } from '@/lib/format'
import { cn } from '@/lib/cn'

/**
 * One strip.
 *
 * A strip is a single slat of card with the scene printed straight onto it. Every scheduling
 * product on the market draws it as a table row with a border around each cell, which is why
 * none of them feel like a board. There are no internal borders here: the fields are separated
 * by rhythm and weight, and the slat has one hairline at the top and bottom so it reads as
 * sitting in the board's channel.
 *
 * The colour is the industry code and it is never decoration: white INT day, yellow EXT day,
 * blue INT night, green EXT night. It is also never the only signal, because INT/EXT and D/N
 * are printed on the strip exactly as they are on the card, which is what makes the board
 * readable to someone who cannot separate the blue from the green.
 */
const SURFACE = {
  white: 'bg-strip-white',
  yellow: 'bg-strip-yellow',
  blue: 'bg-strip-blue',
  green: 'bg-strip-green',
} as const

export interface StripProps extends HTMLAttributes<HTMLDivElement> {
  scene: Scene
  cast: CastMember[]
  dragging?: boolean
  flagged?: boolean
  style?: CSSProperties
}

export const Strip = forwardRef<HTMLDivElement, StripProps>(function Strip(
  { scene, cast, dragging = false, flagged = false, className, ...rest },
  ref,
) {
  const colour = stripColour(scene.int_ext, scene.day_night)
  const byId = new Map(cast.map((c) => [c.id, c]))
  const members = scene.cast_ids.map((id) => byId.get(id)).filter((c): c is CastMember => Boolean(c))

  return (
    <div
      ref={ref}
      {...rest}
      data-testid={`strip-${scene.id}`}
      data-scene={scene.id}
      data-colour={colour}
      className={cn(
        'script group/strip relative grid select-none items-center text-ink',
        'grid-cols-[2.75rem_2.25rem_1fr_1.5rem_3.5rem] gap-x-3 px-2.5 py-2',
        'sm:grid-cols-[3rem_2.5rem_minmax(0,1fr)_1.75rem_4rem_minmax(5rem,9rem)_minmax(0,7rem)] sm:gap-x-4 sm:px-3.5 sm:py-0 sm:h-11',
        'border-y border-y-black/15 shadow-[inset_0_1px_0_rgba(255,255,255,0.28),inset_0_-1px_0_rgba(0,0,0,0.10)]',
        SURFACE[colour],
        dragging ? 'z-20 cursor-grabbing shadow-[0_10px_24px_rgba(0,0,0,0.45)]' : 'cursor-grab',
        className,
      )}
    >
      {/* A day this strip sits in is illegal. The bar is graphic, and the word is on the day
          break where the verdict actually lives, so this never claims the scene is illegal. */}
      {flagged && <span className="absolute inset-y-0 left-0 w-1 bg-flag" aria-hidden="true" />}

      <span className="text-13 font-bold tabular-nums">{scene.number}</span>
      <span className="text-11 tracking-[0.06em]">{scene.int_ext}</span>
      <span className="truncate text-13 font-bold uppercase">{scene.set}</span>
      <span className="text-11">{scene.day_night === 'DAY' ? 'D' : 'N'}</span>
      <span className="text-12 tabular-nums">{eighths(scene.pages_eighths)}</span>

      <span className="hidden items-center gap-1 sm:flex">
        {members.map((member) => (
          <span
            key={member.id}
            title={isMinor(member.age) ? `Cast ${member.letter}, minor, age ${member.age}` : `Cast ${member.letter}`}
            className={cn(
              'inline-flex h-5 min-w-5 items-center justify-center px-1 text-11 leading-none',
              isMinor(member.age)
                ? 'bg-ink font-bold text-strip-white'
                : 'border border-black/35 text-ink',
            )}
          >
            {castChip(member.letter, member.age)}
          </span>
        ))}
      </span>

      <span className="hidden truncate text-11 sm:block">{scene.location_id}</span>

      {/* Below the small breakpoint the cast row moves under the set, because a phone on set
          reads one strip at a time and the cast is the half that decides the day. */}
      <span className="col-span-5 flex items-center gap-1 pt-1 sm:hidden">
        {members.map((member) => (
          <span
            key={member.id}
            className={cn(
              'inline-flex h-5 min-w-5 items-center justify-center px-1 text-11 leading-none',
              isMinor(member.age) ? 'bg-ink font-bold text-strip-white' : 'border border-black/35 text-ink',
            )}
          >
            {castChip(member.letter, member.age)}
          </span>
        ))}
        <span className="ml-auto text-11">{scene.location_id}</span>
      </span>
    </div>
  )
})
