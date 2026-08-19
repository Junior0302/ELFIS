import type { SystemHealthSummary } from '../../types/systemHealth'
import HealthStatusBadge from './HealthStatusBadge'

type Props = {
  summary: SystemHealthSummary
  lastRefresh: Date | null
  refreshing: boolean
  onRefresh: () => void
}

export default function HealthSummaryHeader({ summary, lastRefresh, refreshing, onRefresh }: Props) {
  return (
    <div className="platform-title health-summary-header">
      <div>
        <h1>System Health Center</h1>
        <p>Surveillance globale de la plateforme ELFIS Core</p>
        <div className="health-summary-meta">
          <HealthStatusBadge status={summary.overall_status} />
          <span>Env. {summary.environment}</span>
          {summary.platform_version && <span>v{summary.platform_version}</span>}
          <span>
            Actualisé : {lastRefresh ? lastRefresh.toLocaleTimeString('fr-FR') : '—'}
          </span>
        </div>
        <p className="health-simulated-note">
          Données simulées RC2.1 — aucun monitoring externe réel.
        </p>
      </div>
      <button type="button" className="platform-btn" onClick={onRefresh} disabled={refreshing}>
        {refreshing ? 'Actualisation…' : 'Actualiser'}
      </button>
    </div>
  )
}
