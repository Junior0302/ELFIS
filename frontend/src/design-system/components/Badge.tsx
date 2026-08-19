import type { ReactNode } from 'react'
import { cx } from './cx'

export type BadgeTone = 'neutral' | 'accent' | 'ok' | 'warn' | 'danger'

export type BadgeProps = {
  children: ReactNode
  tone?: BadgeTone
  className?: string
}

/**
 * Badge — `accent` follows Pilot theme; ok/warn/danger stay semantic (non-product).
 */
export function Badge({ children, tone = 'neutral', className }: BadgeProps) {
  return (
    <span className={cx('ds-badge', `ds-badge--${tone}`, className)}>{children}</span>
  )
}
