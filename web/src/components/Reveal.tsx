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
 *
 * The clip is what makes the reveal work and it is also what cut the bottom off every descender.
 * The display sizes set a line height below 1 (0.9 at the largest), so the line box ends above
 * the font's descender and `overflow-hidden` took the tails off the y in "you", the g and the y
 * in "legally". The mask is given room for them in padding and the same amount is taken back in
 * margin, so the descenders are inside the clip and the vertical rhythm of the page is unchanged.
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
        <span key={line} className="block overflow-hidden pb-[0.24em] -mb-[0.24em]">
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
