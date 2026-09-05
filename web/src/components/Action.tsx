import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { cn } from '@/lib/cn'

/**
 * The one button shape in the interface.
 *
 * A 44 px square holding the icon, then the label, with a hairline around both. There is no
 * brand colour to fill it with, so hovering inverts it: bone rises from the bottom edge and the
 * type flips to the board colour. Affordance by inversion rather than by hue is what keeps the
 * page's only colours meaning something.
 */
interface Shared {
  icon?: ReactNode
  children: string
  variant?: 'primary' | 'quiet'
  className?: string
}

const base =
  'group/action script-label relative inline-flex h-11 shrink-0 cursor-pointer items-stretch overflow-hidden border text-11 transition-colors'

const skin = {
  primary: 'border-bone text-bone',
  quiet: 'border-rail text-bone-dim hover:border-bone-faint hover:text-bone',
} as const

function Inner({ icon, children }: { icon?: ReactNode; children: string }) {
  return (
    <>
      <span
        aria-hidden="true"
        className="absolute inset-0 origin-bottom scale-y-0 bg-bone transition-transform duration-300 ease-[cubic-bezier(0.65,0,0.35,1)] group-hover/action:scale-y-100 group-focus-visible/action:scale-y-100"
      />
      {icon && (
        <span className="relative z-1 flex w-11 items-center justify-center border-r border-current transition-colors group-hover/action:text-board group-focus-visible/action:text-board">
          {icon}
        </span>
      )}
      <span className="relative z-1 flex items-center px-4 transition-colors group-hover/action:text-board group-focus-visible/action:text-board">
        {children}
      </span>
    </>
  )
}

export function ActionLink({ to, icon, children, variant = 'primary', className }: Shared & { to: string }) {
  return (
    <Link to={to} className={cn(base, skin[variant], className)}>
      <Inner icon={icon}>{children}</Inner>
    </Link>
  )
}

export function ActionAnchor({ href, icon, children, variant = 'quiet', className }: Shared & { href: string }) {
  return (
    <a href={href} target="_blank" rel="noopener noreferrer" className={cn(base, skin[variant], className)}>
      <Inner icon={icon}>{children}</Inner>
    </a>
  )
}

export function ActionButton({
  onClick,
  icon,
  children,
  variant = 'primary',
  className,
  disabled,
  type = 'button',
}: Shared & { onClick?: () => void; disabled?: boolean; type?: 'button' | 'submit' }) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={cn(base, skin[variant], disabled && 'cursor-not-allowed opacity-45', className)}
    >
      <Inner icon={icon}>{children}</Inner>
    </button>
  )
}
