import type { ReactNode } from 'react'
import { cx } from './cx'

export type StatTrend = {
  value: string
  direction: 'up' | 'down' | 'neutral'
  label: string
  /** Independent from direction — e.g. expense down can be positive. */
  sentiment?: 'positive' | 'negative' | 'neutral'
}

export type StatCardProps = {
  label: string
  value: string
  description?: string
  icon?: ReactNode
  trend?: StatTrend
  metadata?: ReactNode
  variant?: 'default' | 'accent' | 'neutral'
  loading?: boolean
  action?: ReactNode
  className?: string
}

export function StatCard({
  label,
  value,
  description,
  icon,
  trend,
  metadata,
  variant = 'default',
  loading = false,
  action,
  className,
}: StatCardProps) {
  const sentiment = trend?.sentiment ?? 'neutral'
  return (
    <article
      className={cx('ds-stat-card', `ds-stat-card--${variant}`, loading && 'is-loading', className)}
      aria-busy={loading || undefined}
    >
      <div className="ds-stat-card__top">
        <p className="ds-stat-card__label">{label}</p>
        {icon ? <span className="ds-stat-card__icon" aria-hidden>{icon}</span> : null}
      </div>
      {loading ? (
        <div className="ds-stat-card__skeleton" aria-hidden />
      ) : (
        <p className="ds-stat-card__value">{value}</p>
      )}
      {description ? <p className="ds-stat-card__description">{description}</p> : null}
      {trend ? (
        <p
          className={cx(
            'ds-stat-card__trend',
            `ds-stat-card__trend--${trend.direction}`,
            `ds-stat-card__trend--sentiment-${sentiment}`,
          )}
        >
          <span aria-hidden>
            {trend.direction === 'up' ? '↑' : trend.direction === 'down' ? '↓' : '→'}
          </span>{' '}
          <span>
            {trend.value} — {trend.label}
          </span>
        </p>
      ) : null}
      {metadata ? <div className="ds-stat-card__meta">{metadata}</div> : null}
      {action ? <div className="ds-stat-card__action">{action}</div> : null}
    </article>
  )
}
