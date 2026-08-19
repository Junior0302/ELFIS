import type { ReactNode } from 'react'
import { cx } from '../design-system'
import type {
  WidgetContainerProps,
  WidgetDefinition,
  WidgetStatus,
  WidgetVariant,
} from './types'
import './widget-framework.css'

export function WidgetSkeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div className="ew-skeleton" aria-busy="true" aria-label="Chargement">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="ew-skeleton__line" style={{ width: `${92 - i * 10}%` }} />
      ))}
    </div>
  )
}

export function WidgetEmpty({
  title,
  description,
  action,
}: {
  title: string
  description?: string
  action?: ReactNode
}) {
  return (
    <div className="ew-empty" role="status">
      <p className="ew-empty__title">{title}</p>
      {description ? <p className="ew-empty__desc">{description}</p> : null}
      {action ? <div className="ew-empty__action">{action}</div> : null}
    </div>
  )
}

export function WidgetError({
  message,
  onRetry,
}: {
  message: string
  onRetry?: () => void
}) {
  return (
    <div className="ew-error" role="alert">
      <p className="ew-error__title">Données indisponibles</p>
      <p className="ew-error__msg">{message}</p>
      {onRetry ? (
        <button type="button" className="btn secondary" onClick={onRetry}>
          Réessayer
        </button>
      ) : null}
    </div>
  )
}

export function WidgetLoading() {
  return <WidgetSkeleton rows={3} />
}

export function WidgetStatusBadge({ status }: { status: WidgetStatus }) {
  if (status === 'ready' || status === 'idle') return null
  const label: Record<WidgetStatus, string> = {
    idle: '',
    loading: 'Chargement',
    ready: '',
    refreshing: 'Actualisation…',
    empty: 'Vide',
    error: 'Erreur',
  }
  return (
    <span className={cx('ew-status', `ew-status--${status}`)} aria-live="polite">
      {label[status]}
    </span>
  )
}

export function WidgetTitle({ children }: { children: ReactNode }) {
  return <h3 className="ew-title">{children}</h3>
}

export function WidgetDescription({ children }: { children: ReactNode }) {
  return <p className="ew-description">{children}</p>
}

export function WidgetHeader({
  definition,
  onRefresh,
  toolbarExtra,
}: {
  definition: WidgetDefinition
  onRefresh?: () => void
  toolbarExtra?: ReactNode
}) {
  return (
    <header className="ew-header">
      <div className="ew-header__text">
        <WidgetTitle>{definition.title}</WidgetTitle>
        {definition.description ? <WidgetDescription>{definition.description}</WidgetDescription> : null}
      </div>
      <WidgetToolbar definition={definition} onRefresh={onRefresh} extra={toolbarExtra} />
    </header>
  )
}

function RefreshIcon() {
  return (
    <svg
      className="ew-refresh__icon"
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M21 12a9 9 0 1 1-2.64-6.36" />
      <polyline points="21 3 21 9 15 9" />
    </svg>
  )
}

export function WidgetToolbar({
  definition,
  onRefresh,
  extra,
}: {
  definition: WidgetDefinition
  onRefresh?: () => void
  extra?: ReactNode
}) {
  return (
    <div className="ew-toolbar">
      <WidgetStatusBadge status={definition.status} />
      {extra}
      {definition.refreshable && onRefresh ? (
        <button
          type="button"
          className="ew-refresh"
          onClick={onRefresh}
          disabled={definition.status === 'loading' || definition.status === 'refreshing'}
          aria-label={`Actualiser ${definition.title}`}
          title={`Actualiser ${definition.title}`}
        >
          <RefreshIcon />
          <span className="ew-refresh__label">Actualiser</span>
        </button>
      ) : null}
    </div>
  )
}

export function WidgetAction({
  label,
  href,
  onClick,
  tone = 'secondary',
}: {
  label: string
  href?: string
  onClick?: () => void
  tone?: 'primary' | 'secondary' | 'danger'
}) {
  const cls = tone === 'primary' ? 'btn' : tone === 'danger' ? 'btn danger' : 'btn secondary'
  if (href) {
    return (
      <a className={cls} href={href}>
        {label}
      </a>
    )
  }
  return (
    <button type="button" className={cls} onClick={onClick}>
      {label}
    </button>
  )
}

export function WidgetBody({ children }: { children: ReactNode }) {
  return <div className="ew-body">{children}</div>
}

export function WidgetFooter({ children }: { children: ReactNode }) {
  return <footer className="ew-footer">{children}</footer>
}

export function WidgetBadge({ children, tone = 'neutral' }: { children: ReactNode; tone?: string }) {
  return <span className={cx('ew-badge', `ew-badge--${tone}`)}>{children}</span>
}

/** Grille responsive produit-agnostique. */
export function WidgetGrid({
  children,
  className,
  columns,
}: {
  children: ReactNode
  className?: string
  columns?: 'auto' | 2 | 3 | 4 | 8
}) {
  const colClass =
    columns === 2
      ? 'ew-grid--2'
      : columns === 3
        ? 'ew-grid--3'
        : columns === 4
          ? 'ew-grid--4'
          : columns === 8
            ? 'ew-grid--8'
            : 'ew-grid--auto'
  return <div className={cx('ew-grid', colClass, className)}>{children}</div>
}

/** Titre de section dashboard. */
export function WidgetSection({
  id,
  title,
  children,
  className,
}: {
  id: string
  title: string
  children: ReactNode
  className?: string
}) {
  return (
    <section className={cx('ew-section', className)} aria-labelledby={id}>
      <h3 id={id} className="ew-section__title">
        {title}
      </h3>
      {children}
    </section>
  )
}

/** Valeur métrique compacte. */
export function WidgetMetric({
  value,
  detail,
  trend,
}: {
  value: ReactNode
  detail?: ReactNode
  trend?: ReactNode
}) {
  return (
    <div className="ew-metric">
      <div className="ew-metric__value">{value}</div>
      {trend ? <div className="ew-metric__trend">{trend}</div> : null}
      {detail ? <div className="ew-metric__detail">{detail}</div> : null}
    </div>
  )
}

/** Liste générique pour priorités / alertes / activité. */
export function WidgetList({ children, className }: { children: ReactNode; className?: string }) {
  return <ul className={cx('ew-list', className)}>{children}</ul>
}

/** Corps dédié graphique (hauteur cible 210–280px). */
export function WidgetChartBody({
  children,
  summary,
}: {
  children: ReactNode
  summary?: string
}) {
  return (
    <div className="ew-chart-body">
      {children}
      {summary ? (
        <p className="ew-chart-body__summary visually-hidden">{summary}</p>
      ) : null}
    </div>
  )
}

function variantClass(variant?: WidgetVariant): string {
  return `ew-widget--${variant || 'standard'}`
}

export function WidgetContainer({
  definition,
  onRefresh,
  onRetry,
  children,
  className,
  footer,
  toolbarExtra,
}: WidgetContainerProps) {
  const size = definition.size || 'md'
  const variant = definition.variant || 'standard'
  return (
    <section
      className={cx(
        'ew-widget',
        `ew-widget--${size}`,
        `ew-widget--${definition.category}`,
        variantClass(variant),
        className,
      )}
      data-widget-id={definition.id}
      data-widget-status={definition.status}
      data-widget-variant={variant}
      aria-labelledby={`ew-title-${definition.id}`}
    >
      <header className="ew-header">
        <div className="ew-header__text">
          <h3 className="ew-title" id={`ew-title-${definition.id}`}>
            {definition.title}
          </h3>
          {definition.description ? <p className="ew-description">{definition.description}</p> : null}
        </div>
        <WidgetToolbar definition={definition} onRefresh={onRefresh} extra={toolbarExtra} />
      </header>

      <div className="ew-body">
        {definition.status === 'loading' ? <WidgetLoading /> : null}
        {definition.status === 'error' ? (
          <WidgetError message={definition.errorMessage || 'Erreur de chargement'} onRetry={onRetry} />
        ) : null}
        {definition.status === 'empty' ? (
          <WidgetEmpty
            title={definition.emptyTitle || 'Aucune donnée'}
            description={definition.emptyDescription}
          />
        ) : null}
        {definition.status === 'ready' || definition.status === 'refreshing' || definition.status === 'idle'
          ? children
          : null}
      </div>

      {(footer || definition.lastUpdatedAt || definition.source) && (
        <footer className="ew-footer ew-footer--secondary">
          {footer}
          <div className="ew-meta">
            {definition.source ? <span>Source : {definition.source}</span> : null}
            {definition.lastUpdatedAt ? (
              <span>
                MAJ{' '}
                {new Date(definition.lastUpdatedAt).toLocaleString('fr-FR', {
                  dateStyle: 'short',
                  timeStyle: 'short',
                })}
              </span>
            ) : null}
          </div>
        </footer>
      )}
    </section>
  )
}
