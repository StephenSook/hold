import { useCallback, useMemo, useState } from 'react'
import {
  DndContext,
  DragOverlay,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from '@dnd-kit/core'
import { restrictToVerticalAxis, restrictToParentElement } from '@dnd-kit/modifiers'
import { SortableContext, sortableKeyboardCoordinates, useSortable, verticalListSortingStrategy } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { LayoutGroup, motion } from 'motion/react'
import type { ScheduleInput } from '@/types/contracts'
import { usePrefersReducedMotion } from '@/hooks/useReducedMotion'
import { Strip } from './Strip'
import { DayBreak } from './DayBreak'
import { moveStrip, reindexDays, withTotals, type BoardRow } from './model'

/**
 * The board.
 *
 * One flat sortable list. Strips move, day breaks do not, and a strip's day is decided by where
 * it lands relative to the breaks, exactly as on a physical board.
 *
 * The layout animation is the product's one orchestrated moment: when the solved order arrives,
 * every strip travels to its new position at once. Motion's layout animation is doing that, so
 * it is suppressed for the strip being dragged (dnd-kit owns that transform) and for anyone who
 * has asked for reduced motion, who gets the same new order with no travel.
 */
/*
 * 550 ms with a long-tail ease, not the full second the plan sketched. Forty rows all
 * departing at once and settling slowly reads as more expensive than a slower linear move, and
 * it keeps the interaction inside the 200 ms INP budget for the frame that starts it. The full
 * second belongs to the whole beat: the strips land, then the totals and the verdict follow.
 */
const TRAVEL = { layout: { duration: 0.55, ease: [0.16, 1, 0.3, 1] } } as const

function SortableRow({
  row,
  schedule,
  dayCount,
  animate,
  flaggedDays,
  onOpenVerdict,
  orderVersion,
}: {
  row: BoardRow
  schedule: ScheduleInput
  dayCount: number
  animate: boolean
  flaggedDays: Set<number>
  onOpenVerdict: (day: number) => void
  orderVersion: number
}) {
  const sortable = useSortable({ id: row.id, disabled: row.kind === 'break' })
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = sortable

  const style = {
    transform: CSS.Translate.toString(transform),
    transition,
    opacity: isDragging ? 0 : 1,
  }

  if (row.kind === 'break') {
    return (
      <motion.li layout={animate} layoutDependency={orderVersion} transition={TRAVEL} className="list-none">
        <DayBreak
          day={row.day}
          dayCount={dayCount}
          schedule={schedule}
          sceneIds={row.sceneIds}
          pagesEighths={row.pagesEighths}
          verdict={row.verdict}
          onOpenVerdict={onOpenVerdict}
        />
      </motion.li>
    )
  }

  return (
    <motion.li
      layout={animate && !isDragging}
      layoutDependency={orderVersion}
      transition={TRAVEL}
      className="list-none"
    >
      <Strip
        ref={setNodeRef}
        style={style}
        scene={row.scene}
        cast={schedule.cast}
        flagged={flaggedDays.has(row.day)}
        {...attributes}
        {...listeners}
        aria-roledescription="Strip. Press space to lift it, then the arrow keys to move it and space to drop it."
        aria-label={`Scene ${row.scene.number}, ${row.scene.int_ext} ${row.scene.set}, ${row.scene.day_night}`}
      />
    </motion.li>
  )
}

export interface StripboardProps {
  schedule: ScheduleInput
  rows: BoardRow[]
  onRowsChange: (rows: BoardRow[]) => void
  onOpenVerdict: (day: number) => void
  /** Suppress the layout animation, for example while the solved order is being applied. */
  animate?: boolean
  label?: string
  /**
   * Bumped whenever the order actually changes. Motion measures every row on every render
   * without this, which on a forty-row board is forty forced reflows per render.
   */
  orderVersion?: number
}

export function Stripboard({
  schedule,
  rows,
  onRowsChange,
  onOpenVerdict,
  animate = true,
  label = 'Shooting schedule stripboard',
  orderVersion = 0,
}: StripboardProps) {
  const reduced = usePrefersReducedMotion()
  const [activeId, setActiveId] = useState<string | null>(null)
  const dayCount = schedule.days.length

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  )

  const flaggedDays = useMemo(() => {
    const flagged = new Set<number>()
    for (const row of rows) if (row.kind === 'break' && row.verdict?.status === 'ILLEGAL') flagged.add(row.day)
    return flagged
  }, [rows])

  const ids = useMemo(() => rows.map((r) => r.id), [rows])
  const activeRow = rows.find((r) => r.id === activeId)

  const onDragStart = useCallback((event: DragStartEvent) => setActiveId(String(event.active.id)), [])

  const onDragEnd = useCallback(
    (event: DragEndEvent) => {
      setActiveId(null)
      const { active, over } = event
      if (!over || active.id === over.id) return
      const moved = moveStrip(rows, String(active.id), String(over.id))
      onRowsChange(withTotals(reindexDays(moved, dayCount), schedule))
    },
    [rows, onRowsChange, dayCount, schedule],
  )

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      modifiers={[restrictToVerticalAxis, restrictToParentElement]}
      onDragStart={onDragStart}
      onDragEnd={onDragEnd}
      onDragCancel={() => setActiveId(null)}
      accessibility={{
        announcements: {
          onDragStart: ({ active }) => `Lifted ${describe(rows, String(active.id))}.`,
          onDragOver: ({ active, over }) =>
            over ? `${describe(rows, String(active.id))} is over ${describe(rows, String(over.id))}.` : '',
          onDragEnd: ({ active, over }) =>
            over
              ? `Dropped ${describe(rows, String(active.id))} at ${describe(rows, String(over.id))}.`
              : `${describe(rows, String(active.id))} returned to its place.`,
          onDragCancel: ({ active }) => `Cancelled. ${describe(rows, String(active.id))} returned to its place.`,
        },
      }}
    >
      <LayoutGroup>
        <SortableContext items={ids} strategy={verticalListSortingStrategy}>
          <ul aria-label={label} className="board-surface relative isolate flex flex-col bg-board-2">
            {rows.map((row) => (
              <SortableRow
                key={row.id}
                row={row}
                schedule={schedule}
                dayCount={dayCount}
                animate={animate && !reduced}
                flaggedDays={flaggedDays}
                onOpenVerdict={onOpenVerdict}
                orderVersion={orderVersion}
              />
            ))}
          </ul>
        </SortableContext>
      </LayoutGroup>

      <DragOverlay dropAnimation={{ duration: 180, easing: 'cubic-bezier(0.22, 1, 0.36, 1)' }}>
        {activeRow?.kind === 'strip' ? <Strip scene={activeRow.scene} cast={schedule.cast} dragging /> : null}
      </DragOverlay>
    </DndContext>
  )
}

/** What a screen reader hears when a strip is lifted, moved or dropped. */
function describe(rows: BoardRow[], id: string): string {
  const row = rows.find((r) => r.id === id)
  if (!row) return id
  if (row.kind === 'break') return `the end of day ${row.day + 1}`
  return `scene ${row.scene.number}, ${row.scene.int_ext} ${row.scene.set}`
}
