import type { ReactNode } from 'react'
import { cx } from './cx'
import { Progress } from './Progress'

export type MetricCardProps = {
  title: string
  value: string
  subtitle?: string
  status?: ReactNode
  progress?: number
  supportingText?: string
  footer?: ReactNode
  action?: ReactNode
  variant?: 'default' | 'accent' | 'muted'
  className?: string
}

/** Rich indicator card — no metric calculation. */
export function MetricCard({
  title,
  value,
  subtitle,
  status,
  progress,
  supportingText,
  footer,
  action,
  variant = 'default',
  className,
}: MetricCardProps) {
  return (
    <article className={cx('ds-metric-card', `ds-metric-card--${variant}`, className)}>
      <header className="ds-metric-card__header">
        <h3 className="ds-metric-card__title">{title}</h3>
        {status ? <div className="ds-metric-card__status">{status}</div> : null}
      </header>
      <p className="ds-metric-card__value">{value}</p>
      {subtitle ? <p className="ds-metric-card__subtitle">{subtitle}</p> : null}
      {typeof progress === 'number' ? (
        <Progress value={progress} label={`${title} : ${Math.round(progress)} pour cent`} />
      ) : null}
      {supportingText ? <p className="ds-metric-card__support">{supportingText}</p> : null}
      {action ? <div className="ds-metric-card__action">{action}</div> : null}
      {footer ? <footer className="ds-metric-card__footer">{footer}</footer> : null}
    </article>
  )
}
