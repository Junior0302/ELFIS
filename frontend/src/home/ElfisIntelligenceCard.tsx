import { Link } from 'react-router-dom'
import { ElfisButtonLink } from '../unified-platform'
import {
  InsightList,
  type Insight,
  type InsightAction,
} from '../insight-framework'
import type { HomeSignal } from './homeSignals'
import { mapHomeSignalsToInsights } from './homeInsights'
import { PlatformHomeSection } from './PlatformHomeSection'

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
    <PlatformHomeSection
      id="home-intel"
      title="ELFIS Intelligence"
      description="Signaux déterministes — pas d’IA générative inventée."
      level={3}
      className={`cockpit-intel ph-intel ${embedded ? 'cockpit-intel--embedded' : ''}`.trim()}
      actions={
        unreadNotifications > 0 ? (
          <ElfisButtonLink to="/notifications" variant="secondary">
            Notifications
          </ElfisButtonLink>
        ) : undefined
      }
    >
      <div data-cockpit-intel="v1">
        <InsightList
          insights={insights}
          variant="inline"
          className="cockpit-intel__insights"
          emptyMessage="Aucun élément prioritaire détecté."
          renderAction={renderInsightAction}
        />
      </div>
    </PlatformHomeSection>
  )
}
