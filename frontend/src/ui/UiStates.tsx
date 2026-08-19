import type { ReactNode } from 'react'

type EmptyProps = {
  title: string
  description?: string
  action?: ReactNode
}

export function EmptyState({ title, description, action }: EmptyProps) {
  return (
    <div className="ui-empty" role="status">
      <p className="ui-empty-title">{title}</p>
      {description ? <p className="muted">{description}</p> : null}
      {action ? <div className="ui-empty-action">{action}</div> : null}
    </div>
  )
}

type ErrorProps = {
  title?: string
  message: string
  onRetry?: () => void
}

export function ErrorState({ title = 'Une erreur est survenue', message, onRetry }: ErrorProps) {
  return (
    <div className="ui-error" role="alert">
      <p className="ui-error-title">{title}</p>
      <p className="muted">{message}</p>
      {onRetry ? (
        <button type="button" className="btn secondary" onClick={onRetry}>
          Réessayer
        </button>
      ) : null}
    </div>
  )
}

type SkeletonProps = {
  rows?: number
  className?: string
}

export function Skeleton({ rows = 3, className = '' }: SkeletonProps) {
  return (
    <div className={`ui-skeleton ${className}`} aria-busy="true" aria-label="Chargement">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="ui-skeleton-line" style={{ width: `${88 - i * 8}%` }} />
      ))}
    </div>
  )
}

type ProgressProps = {
  value: number
  label?: string
}

export function ProgressBar({ value, label }: ProgressProps) {
  const pct = Math.max(0, Math.min(100, Math.round(value)))
  return (
    <div className="ui-progress" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100} aria-label={label || 'Progression'}>
      {label ? <p className="ui-progress-label">{label}</p> : null}
      <div className="ui-progress-track">
        <div className="ui-progress-fill" style={{ width: `${pct}%` }} />
      </div>
      <span className="muted ui-progress-pct">{pct} %</span>
    </div>
  )
}

type BadgeProps = {
  children: ReactNode
  tone?: 'neutral' | 'ok' | 'warn' | 'danger'
}

export function UiBadge({ children, tone = 'neutral' }: BadgeProps) {
  return <span className={`ui-badge ui-badge--${tone}`}>{children}</span>
}
