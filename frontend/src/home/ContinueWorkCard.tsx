import type { CSSProperties } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { getWorkspaceByProductId, getAvailableWorkspaces } from '../workspaces'
import { ElfisEmptyState } from '../unified-platform'
import { PlatformHomeSection } from './PlatformHomeSection'
import { openWorkspaceSpace } from './openWorkspaceSpace'

export type ContinueWorkItem = {
  id: string
  letter: string
  accent: string
  title: string
  meta: string
  status: string
  statusTone: 'warn' | 'info' | 'neutral'
  timeLabel: string
  to: string
  historyTo?: string | null
  productId?: string | null
  spaceLabel?: string
}

type ContinueWorkCardProps = {
  items: ContinueWorkItem[]
}

function StatusDot({ tone }: { tone: ContinueWorkItem['statusTone'] }) {
  return <span className={`home-continue-row__dot home-continue-row__dot--${tone}`} aria-hidden />
}

export function ContinueWorkCard({ items }: ContinueWorkCardProps) {
  const navigate = useNavigate()
  const emptyActions = getAvailableWorkspaces().map((w) => ({
    label: `Ouvrir ${w.label}`,
    to: w.rootPath!,
    productId: w.engineProductId,
    accent: w.accent.primary,
  }))

  if (items.length === 0) {
    return (
      <PlatformHomeSection
        id="home-continue"
        title="À reprendre"
        description="Aucune reprise récente enregistrée."
        level={2}
        className="home-continue cockpit-continue ph-resume"
      >
        <div data-cockpit-continue="v1">
          <ElfisEmptyState
            title="Tout est à jour"
            description="Ouvrez un espace pour démarrer une session. ELFIS mémorisera votre dernier contexte."
            action={
              <div className="home-continue__actions">
                {emptyActions.map((action) => (
                  <button
                    key={action.to}
                    type="button"
                    className="home-continue__pill"
                    style={{ '--resume-accent': action.accent } as CSSProperties}
                    onClick={() =>
                      openWorkspaceSpace(navigate, {
                        route: action.to,
                        engineProductId: action.productId,
                      })
                    }
                  >
                    {action.label}
                  </button>
                ))}
              </div>
            }
          />
        </div>
      </PlatformHomeSection>
    )
  }

  return (
    <PlatformHomeSection
      id="home-continue"
      title="À reprendre"
      description="Reprises basées sur votre dernière activité plateforme."
      level={2}
      className="home-continue cockpit-continue ph-resume"
    >
      <ul className="home-continue__list" data-cockpit-continue="v1">
        {items.map((item) => (
          <li key={item.id}>
            <div
              className="home-continue-row"
              style={{ '--resume-accent': item.accent } as CSSProperties}
            >
              <span className="home-continue-row__mark" aria-hidden>
                {item.letter}
              </span>
              <div className="home-continue-row__body">
                <strong className="home-continue-row__title">{item.title}</strong>
                <span className="home-continue-row__meta">{item.meta}</span>
                {item.spaceLabel ? (
                  <span className="ph-resume__space">{item.spaceLabel}</span>
                ) : null}
              </div>
              <div className="home-continue-row__status">
                <span>
                  <StatusDot tone={item.statusTone} />
                  {item.status}
                </span>
                <time>{item.timeLabel}</time>
              </div>
              <div className="home-continue-row__ctas">
                <button
                  type="button"
                  className="home-continue-row__cta"
                  onClick={() =>
                    openWorkspaceSpace(navigate, {
                      route: item.to,
                      engineProductId: item.productId,
                    })
                  }
                >
                  Reprendre
                </button>
                {item.historyTo ? (
                  <Link to={item.historyTo} className="home-continue-row__cta home-continue-row__cta--ghost">
                    Historique
                  </Link>
                ) : null}
              </div>
            </div>
          </li>
        ))}
      </ul>
    </PlatformHomeSection>
  )
}

/** Construit 0–1 item de reprise depuis lastProduct (registry). */
export function buildContinueItemsFromRegistry(
  lastId: string | null,
  lastAt: string | null,
  formatLastSeen: (iso: string | null) => string,
  historyRouteFor: (productId: string | undefined) => string | null,
): ContinueWorkItem[] {
  if (!lastId || !lastAt) return []
  const workspace = getWorkspaceByProductId(lastId)
  if (!workspace?.rootPath || workspace.availability !== 'available') return []

  return [
    {
      id: `resume-${workspace.id}`,
      letter: workspace.label.charAt(0).toUpperCase(),
      accent: workspace.accent.primary,
      title: workspace.label,
      meta: `Dernière session · ${workspace.engineLabel}`,
      status: 'En cours',
      statusTone: 'neutral',
      timeLabel: formatLastSeen(lastAt),
      to: workspace.rootPath,
      historyTo: historyRouteFor(workspace.engineProductId ?? undefined),
      productId: workspace.engineProductId,
      spaceLabel: workspace.label,
    },
  ]
}
