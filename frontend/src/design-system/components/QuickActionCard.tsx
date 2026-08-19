import type { ReactNode, MouseEventHandler } from 'react'
import { Link } from 'react-router-dom'
import { cx } from './cx'

export type QuickActionCardProps = {
  title: string
  description?: string
  icon?: ReactNode
  badge?: ReactNode
  disabled?: boolean
  disabledReason?: string
  href?: string
  onClick?: MouseEventHandler<HTMLButtonElement>
  accent?: boolean
  compact?: boolean
  className?: string
}

/**
 * Shortcut card — real <a>/<Link> or <button>, never a clickable div.
 * No permission logic; caller decides visibility/disabled.
 */
export function QuickActionCard({
  title,
  description,
  icon,
  badge,
  disabled = false,
  disabledReason,
  href,
  onClick,
  accent = true,
  compact = false,
  className,
}: QuickActionCardProps) {
  const body = (
    <>
      <div className="ds-quick-action__top">
        {icon ? <span className="ds-quick-action__icon" aria-hidden>{icon}</span> : null}
        {badge ? <span className="ds-quick-action__badge">{badge}</span> : null}
      </div>
      <strong className="ds-quick-action__title">{title}</strong>
      {description ? <span className="ds-quick-action__desc muted">{description}</span> : null}
      {disabled && disabledReason ? (
        <span className="ds-quick-action__reason">{disabledReason}</span>
      ) : null}
    </>
  )

  const classes = cx(
    'ds-quick-action',
    accent && 'ds-quick-action--accent',
    compact && 'ds-quick-action--compact',
    disabled && 'is-disabled',
    className,
  )

  if (href && !disabled) {
    const isExternal = /^https?:\/\//i.test(href)
    if (isExternal) {
      return (
        <a className={classes} href={href}>
          {body}
        </a>
      )
    }
    return (
      <Link className={classes} to={href}>
        {body}
      </Link>
    )
  }

  return (
    <button
      type="button"
      className={classes}
      onClick={onClick}
      disabled={disabled}
      aria-disabled={disabled || undefined}
      title={disabled ? disabledReason : undefined}
    >
      {body}
    </button>
  )
}
