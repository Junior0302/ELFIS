import { Link } from 'react-router-dom'
import type { DayDomainCard } from './homeSignals'

type DaySummarySectionProps = {
  cards: DayDomainCard[]
}

/**
 * Pulse journée V3 — une seule bande horizontale (glance), pas 4 cartes redondantes.
 */
export function DaySummarySection({ cards }: DaySummarySectionProps) {
  return (
    <section className="cockpit-day cockpit-day--pulse" aria-labelledby="home-day-title" data-cockpit-day="v3">
      <div className="elfis-home__section-head elfis-home__section-head--compact cockpit-day__head">
        <h2 id="home-day-title">Résumé journée</h2>
        <p>États réels — sans KPI inventés.</p>
      </div>
      <ul className="cockpit-day__pulse" role="list">
        {cards.map((card) => (
          <li key={card.id}>
            <article className={`cockpit-day-chip cockpit-day-chip--${card.statusTone}`}>
              <div className="cockpit-day-card__head">
                <h3 className="cockpit-day-card__title">{card.title}</h3>
                <span className={`cockpit-day-card__status is-${card.statusTone}`}>{card.status}</span>
              </div>
              <p className="cockpit-day-card__summary">{card.summary}</p>
              {card.actionTo ? (
                <Link className="cockpit-day-card__action" to={card.actionTo}>
                  {card.actionLabel}
                </Link>
              ) : null}
            </article>
          </li>
        ))}
      </ul>
    </section>
  )
}
