import { motion } from 'motion/react'
import { cn } from '@/lib/cn'

/**
 * A masked line reveal.
 *
 * The lines are authored, not measured: a headline this short reads better with its ragging
 * chosen than with it left to the browser, and authoring them also removes the whole class of
 * bugs where a re-split on font load leaves a line stranded off screen.
 *
 * Each line is real text inside a clip, so a screen reader hears the sentence once and in order,
 * and under reduced motion MotionConfig drops the travel and keeps the fade.
 */
export function Reveal({
  lines,
  className,
  lineClassName,
  delay = 0,
  as: Tag = 'h1',
}: {
  lines: string[]
  className?: string
  lineClassName?: string
  delay?: number
  as?: 'h1' | 'h2' | 'p'
}) {
  return (
    <Tag className={className}>
      {lines.map((line, index) => (
        <span key={line} className="block overflow-hidden">
          <motion.span
            className={cn('block', lineClassName)}
            initial={{ y: '108%', opacity: 0 }}
            animate={{ y: '0%', opacity: 1 }}
            transition={{ duration: 0.95, delay: delay + index * 0.085, ease: [0.16, 1, 0.3, 1] }}
          >
            {line}
          </motion.span>
        </span>
      ))}
    </Tag>
  )
}
