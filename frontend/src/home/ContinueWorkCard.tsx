import type { CSSProperties } from 'react'
import { Link } from 'react-router-dom'
import type { HomeAppCard } from './homeCatalog'
import { setLastProductId } from './lastProduct'
import { ElfisEmptyState } from '../unified-platform'

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
  productId?: HomeAppCard['productId']
}

type ContinueWorkCardProps = {
  items: ContinueWorkItem[]
  emptyActions?: {
    label: string
    to: string
    productId?: HomeAppCard['productId']
    accent: string
  }[]
}

function StatusDot({ tone }: { tone: ContinueWorkItem['statusTone'] }) {
  return <span className={`home-continue-row__dot home-continue-row__dot--${tone}`} aria-hidden />
}

export function ContinueWorkCard({ items, emptyActions = [] }: ContinueWorkCardProps) {
  if (items.length === 0) {
    return (
      <section
        className="home-continue cockpit-continue"
        id="home-continue"
        aria-labelledby="home-resume-title"
        data-cockpit-continue="v1"
      >
        <div className="cockpit-pane cockpit-pane--featured">
          <div className="elfis-home__section-head elfis-home__section-head--compact">
            <h2 id="home-resume-title">Continuer votre travail</h2>
            <p>Aucune reprise récente enregistrée.</p>
          </div>
          <ElfisEmptyState
            title="Où reprendre ?"
            description="Ouvrez un espace pour démarrer une session. ELFIS mémorisera votre dernier contexte."
            action={
              <div className="home-continue__actions">
                {emptyActions.map((action) => (
                  <Link
                    key={action.to}
                    to={action.to}
                    className="home-continue__pill"
                    style={{ '--resume-accent': action.accent } as CSSProperties}
                    onClick={() => action.productId && setLastProductId(action.productId)}
                  >
                    {action.label}
                  </Link>
                ))}
              </div>
            }
          />
        </div>
      </section>
    )
  }

  return (
    <section
      className="home-continue cockpit-continue"
      id="home-continue"
      aria-labelledby="home-resume-title"
      data-cockpit-continue="v1"
    >
      <div className="cockpit-pane cockpit-pane--featured">
        <div className="elfis-home__section-head elfis-home__section-head--compact">
          <h2 id="home-resume-title">Continuer votre travail</h2>
          <p>Reprises basées sur votre dernière activité plateforme.</p>
        </div>
        <ul className="home-continue__list">
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
                </div>
                <div className="home-continue-row__status">
                  <span>
                    <StatusDot tone={item.statusTone} />
                    {item.status}
                  </span>
                  <time>{item.timeLabel}</time>
                </div>
                <div className="home-continue-row__ctas">
                  <Link
                    to={item.to}
                    className="home-continue-row__cta"
                    onClick={() => item.productId && setLastProductId(item.productId)}
                  >
                    Reprendre
                  </Link>
                  <Link
                    to={item.to}
                    className="home-continue-row__cta home-continue-row__cta--ghost"
                    onClick={() => item.productId && setLastProductId(item.productId)}
                  >
                    Ouvrir
                  </Link>
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
      </div>
    </section>
  )
}
