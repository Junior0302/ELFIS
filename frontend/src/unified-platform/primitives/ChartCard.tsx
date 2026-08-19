/**
 * ChartCard — surface neutre pour graphiques (wrapper DS card pattern).
 * Dims : body clamp 300–420 ; hero 340–480 ; weak-data = hauteur réduite.
 */

import type { ReactNode } from 'react'
import { cx } from '../../design-system'
import { EmptyState } from '../../design-system'

export type ChartCardVariant = 'default' | 'hero'

export type ChartCardProps = {
  title: string
  description?: string
  children?: ReactNode
  actions?: ReactNode
  footer?: ReactNode
  loading?: boolean
  empty?: boolean
  /** Série insuffisante / 1 barre — pas de hauteur énorme. */
  weakData?: boolean
  emptyTitle?: string
  emptyDescription?: string
  weakTitle?: string
  weakDescription?: string
  variant?: ChartCardVariant
  className?: string
}

export function ChartCard({
  title,
  description,
  children,
  actions,
  footer,
  loading,
  empty,
  weakData,
  emptyTitle = 'Graphique indisponible',
  emptyDescription,
  weakTitle = 'Historique insuffisant',
  weakDescription = 'Pas assez de points pour afficher une évolution fiable.',
  variant = 'default',
  className,
}: ChartCardProps) {
  return (
    <article
      className={cx(
        'up-chart-card',
        variant === 'hero' && 'up-chart-card--hero',
        weakData && 'up-chart-card--weak',
        loading && 'is-loading',
        className,
      )}
      data-chart-card="v1"
      data-chart-variant={variant}
      data-chart-weak={weakData ? '1' : undefined}
      aria-busy={loading || undefined}
    >
      <header className="up-chart-card__header">
        <div>
          <h3 className="up-chart-card__title">{title}</h3>
          {description ? <p className="up-chart-card__desc muted">{description}</p> : null}
        </div>
        {actions ? <div className="up-chart-card__actions">{actions}</div> : null}
      </header>
      <div className="up-chart-card__body">
        {loading ? (
          <EmptyState title="Chargement" description="Préparation du graphique…" />
        ) : empty ? (
          <EmptyState title={emptyTitle} description={emptyDescription} />
        ) : weakData ? (
          <EmptyState title={weakTitle} description={weakDescription} />
        ) : (
          children
        )}
      </div>
      {footer ? <footer className="up-chart-card__footer">{footer}</footer> : null}
    </article>
  )
}
