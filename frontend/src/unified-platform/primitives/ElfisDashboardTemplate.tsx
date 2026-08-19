/**
 * ElfisDashboardTemplate — composition structurelle dashboards (Home / FCC / Sales).
 * Parent layout réel via ElfisPageFrame (pas une décoration autour d’anciens containers).
 *
 * Blind identity : même template DS — seul le contenu métier change.
 * Sections :
 * Header → ContextStrip → KPIGrid → PrimaryAnalysis → SecondaryAnalysis → Operations → RecentActivity
 */

import type { HTMLAttributes, ReactNode } from 'react'
import { cx } from '../../design-system'
import { PlatformGrid, GridItem } from '../PlatformGrid'
import { ElfisPageFrame } from './ElfisPageFrame'
import { ElfisPageHeader, type ElfisPageHeaderProps } from './ElfisPageHeader'

/** Classes layout métier interdites sur le wrapper dashboard (identité visuelle). */
const FORBIDDEN_LAYOUT_CLASS =
  /^(elfis-home|elfis-home--hybrid|up-home--unified|fcc|up-fcc--unified|sales-dashboard|up-sales-dash--unified)$/

export function sanitizeDashboardClassName(className?: string): string | undefined {
  if (!className) return undefined
  const kept = className
    .split(/\s+/)
    .filter(Boolean)
    .filter((c) => !FORBIDDEN_LAYOUT_CLASS.test(c))
  return kept.length ? kept.join(' ') : undefined
}

export type ElfisDashboardTemplateProps = {
  header: ElfisPageHeaderProps | ReactNode
  /** Bandeau / alertes sous le header (ContextStrip). */
  strip?: ReactNode
  /** Rangée KPI (KPIGrid). */
  metrics?: ReactNode
  /** Analyse primaire (charts / focus) — sinon `children` + `aside` 8/4. */
  primaryAnalysis?: ReactNode
  /** Analyse secondaire (6+6 ou grille libre). */
  secondaryAnalysis?: ReactNode
  /** Contenu principal legacy (charts / sections) si pas de primaryAnalysis. */
  children?: ReactNode
  /** Colonne latérale (span 4) — activité / rail (legacy avec children). */
  aside?: ReactNode
  /** Rangée actions / opérations. */
  actions?: ReactNode
  /** Alias explicite Operations (= actions si absent). */
  operations?: ReactNode
  /** Bloc bas pleine largeur (activity / meta) — masqué si vide. */
  footer?: ReactNode
  /** Activité récente — masquée si vide / falsy. */
  recentActivity?: ReactNode
  className?: string
  /** data attribute pour tests / analytics. */
  dashboardId?: string
  /** Si false, pas de ElfisPageFrame (déjà wrap parent). */
  contained?: boolean
  frameClassName?: string
  /** Densité confortable (défaut). */
  density?: 'comfortable' | 'compact'
} & Omit<HTMLAttributes<HTMLDivElement>, 'children'>

function isHeaderProps(h: ElfisPageHeaderProps | ReactNode): h is ElfisPageHeaderProps {
  return (
    typeof h === 'object' &&
    h != null &&
    !('$$typeof' in (h as object)) &&
    'title' in (h as object)
  )
}

function hasContent(node: ReactNode): boolean {
  if (node == null || node === false) return false
  if (typeof node === 'string' && node.trim() === '') return false
  return true
}

export function ElfisDashboardTemplate({
  header,
  strip,
  metrics,
  primaryAnalysis,
  secondaryAnalysis,
  children,
  aside,
  actions,
  operations,
  footer,
  recentActivity,
  className,
  dashboardId,
  contained = true,
  frameClassName,
  density = 'comfortable',
  ...rootRest
}: ElfisDashboardTemplateProps) {
  const headerNode = isHeaderProps(header) ? <ElfisPageHeader {...header} /> : header
  const ops = operations ?? actions
  const activity = recentActivity ?? footer
  const useNamedPrimary = primaryAnalysis != null
  const safeClass = sanitizeDashboardClassName(className)

  const body = (
    <div
      className={cx(
        'up-dashboard',
        density === 'comfortable' && 'up-dashboard--comfortable',
        safeClass,
      )}
      data-elfis-dashboard="v1"
      data-blind-template="v1"
      data-dashboard-id={dashboardId}
      data-dashboard-density={density}
      {...rootRest}
    >
      <div className="up-dashboard__header" data-dashboard-slot="header">
        {headerNode}
      </div>
      {hasContent(strip) ? (
        <div className="up-dashboard__strip" data-dashboard-slot="strip">
          {strip}
        </div>
      ) : null}
      {hasContent(metrics) ? (
        <div className="up-dashboard__metrics" data-dashboard-slot="metrics">
          {metrics}
        </div>
      ) : null}

      {useNamedPrimary ? (
        <>
          <div className="up-dashboard__primary" data-dashboard-slot="primary">
            {primaryAnalysis}
          </div>
          {hasContent(secondaryAnalysis) ? (
            <div className="up-dashboard__secondary" data-dashboard-slot="secondary">
              {secondaryAnalysis}
            </div>
          ) : null}
          {hasContent(children) ? (
            <div className="up-dashboard__extra" data-dashboard-slot="extra">
              {children}
            </div>
          ) : null}
        </>
      ) : (
        <PlatformGrid columns={12} gap={6} className="up-dashboard__grid up-dashboard-grid up-dash-band">
          <GridItem span={12} spanMd={aside ? 8 : 12} className="up-dashboard__main">
            {children}
          </GridItem>
          {aside ? (
            <GridItem span={12} spanMd={4} className="up-dashboard__aside">
              {aside}
            </GridItem>
          ) : null}
        </PlatformGrid>
      )}

      {hasContent(ops) ? (
        <div className="up-dashboard__actions" data-dashboard-slot="actions">
          {ops}
        </div>
      ) : null}
      {hasContent(activity) ? (
        <div className="up-dashboard__footer" data-dashboard-slot="recent-activity">
          {activity}
        </div>
      ) : null}
    </div>
  )

  if (!contained) return body
  return (
    <ElfisPageFrame
      padding="comfortable"
      className={cx('up-dashboard-page', frameClassName)}
    >
      {body}
    </ElfisPageFrame>
  )
}

/** Alias grille dashboard 12/8/4 — gaps tokens plateforme. */
export { PlatformGrid as ElfisDashboardGrid, GridItem as ElfisDashboardGridItem } from '../PlatformGrid'
