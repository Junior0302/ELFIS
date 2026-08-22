/**
 * Carte KPI workspace — MetricCard DS + accent discret via tokens workspace.
 * Aucun calcul métier : valeurs fournies par l’appelant uniquement.
 */

import type { ReactNode } from 'react'
import { MetricCard, type MetricCardProps, cx } from '../design-system'

export type WorkspaceKpiCardProps = Omit<MetricCardProps, 'variant'> & {
  icon?: ReactNode
  /** Accent barre latérale discrète (défaut true). */
  accentBar?: boolean
}

export function WorkspaceKpiCard({
  icon,
  accentBar = true,
  className,
  title,
  status,
  ...rest
}: WorkspaceKpiCardProps) {
  return (
    <MetricCard
      {...rest}
      title={title}
      variant="default"
      status={
        status || icon ? (
          <div className="workspace-kpi-card__status">
            {icon ? <span className="workspace-kpi-card__icon">{icon}</span> : null}
            {status}
          </div>
        ) : undefined
      }
      className={cx(
        'workspace-kpi-card',
        accentBar && 'workspace-kpi-card--accent-bar',
        className,
      )}
    />
  )
}
