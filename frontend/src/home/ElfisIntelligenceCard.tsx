import { Link } from 'react-router-dom'
import { ElfisButtonLink } from '../unified-platform'
import {
  InsightList,
  type Insight,
  type InsightAction,
} from '../insight-framework'
import type { HomeSignal } from './homeSignals'
import { mapHomeSignalsToInsights } from './homeInsights'

type ElfisIntelligenceCardProps = {
  signals: HomeSignal[]
  unreadNotifications: number
  embedded?: boolean
}

function renderInsightAction(action: InsightAction, _insight: Insight) {
  if (!action.href || action.disabled) {
    return (
      <button
        key={action.id}
        type="button"
        className={`elf-insight-action${action.primary ? ' elf-insight-action--primary' : ''}`}
        disabled={action.disabled}
        onClick={action.onClick}
      >
        {action.label}
      </button>
    )
  }
  return (
    <Link
      key={action.id}
      to={action.href}
      className={`elf-insight-action${action.primary ? ' elf-insight-action--primary' : ''}`}
    >
      {action.label}
    </Link>
  )
}

export function ElfisIntelligenceCard({
  signals,
  unreadNotifications,
  embedded = false,
}: ElfisIntelligenceCardProps) {
  const insights = mapHomeSignalsToInsights(signals)

  return (
    <section
      className={`cockpit-intel ${embedded ? 'cockpit-intel--embedded' : ''}`.trim()}
      id="home-intel"
      aria-labelledby="home-intel-title"
      data-cockpit-intel="v1"
    >
      <div className="elfis-home__section-head elfis-home__section-head--compact">
        <h2 id="home-intel-title">ELFIS Intelligence</h2>
        <p>Conseils déterministes — Insight Framework.</p>
      </div>
      <InsightList
        insights={insights}
        variant="inline"
        className="cockpit-intel__insights"
        emptyMessage="Aucun signal prioritaire."
        renderAction={renderInsightAction}
      />
      <p className="cockpit-intel__disclaimer">
        Pas d’IA générative sur Home — recommandations à partir de signaux réels uniquement.
      </p>
      <div className="cockpit-intel__actions">
        {unreadNotifications > 0 ? (
          <ElfisButtonLink to="/notifications" variant="primary">
            Tout traiter
          </ElfisButtonLink>
        ) : null}
      </div>
    </section>
  )
}
