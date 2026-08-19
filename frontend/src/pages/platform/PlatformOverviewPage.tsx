import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type PlatformDashboard, type PlatformServiceHealth } from '../../api'
import { useAuth } from '../../auth'
import PlatformKpiCard from '../../components/platform/PlatformKpiCard'
import { PlatformBarChart, PlatformDonut } from '../../components/platform/PlatformMiniCharts'
import { EmptyState, ErrorState, Skeleton } from '../../ui/UiStates'

export default function PlatformOverviewPage() {
  const { token } = useAuth()
  const [dashboard, setDashboard] = useState<PlatformDashboard | null>(null)
  const [services, setServices] = useState<PlatformServiceHealth[]>([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [period, setPeriod] = useState<'24h' | '7d' | '30d'>('24h')

  const load = useCallback(() => {
    if (!token) return
    setLoading(true)
    setError('')
    Promise.all([api.platformDashboard(token, period), api.platformHealthServices(token)])
      .then(([dash, health]) => {
        setDashboard(dash)
        setServices(health.services)
      })
      .catch((reason) => setError(reason instanceof Error ? reason.message : 'Synthèse indisponible'))
      .finally(() => setLoading(false))
  }, [token, period])

  useEffect(() => {
    load()
  }, [load])

  if (loading && !dashboard) {
    return (
      <div className="pc-page">
        <Skeleton rows={6} />
      </div>
    )
  }

  if (error && !dashboard) {
    return (
      <div className="pc-page">
        <ErrorState message={error} onRetry={load} />
      </div>
    )
  }

  if (!dashboard) {
    return (
      <div className="pc-page">
        <EmptyState title="Aucune donnée dashboard" description="Le backend n’a renvoyé aucun indicateur." />
      </div>
    )
  }

  const periodLabel = period === '24h' ? '24 h' : period === '7d' ? '7 j' : '30 j'

  return (
    <div className="pc-page">
      <div className="pc-page-intro">
        <p className="pc-lede">
          Centre de commandement — état plateforme sur la période sélectionnée (données API
          dashboard uniquement).
        </p>
        <div className="pc-period-toggle" role="group" aria-label="Période">
          {(['24h', '7d', '30d'] as const).map((p) => (
            <button
              key={p}
              type="button"
              className={period === p ? 'pc-btn' : 'pc-btn pc-btn-ghost'}
              onClick={() => setPeriod(p)}
              aria-pressed={period === p}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {error && <div className="platform-alert">{error}</div>}

      <section className="pc-section" aria-labelledby="pc-kpi-heading">
        <h2 id="pc-kpi-heading" className="pc-section-title">
          Indicateurs clés
        </h2>
        <div className="pc-kpi-grid">
          <PlatformKpiCard
            icon="▦"
            title="Organisations"
            value={dashboard.organizations_total}
            period={periodLabel}
            tone="neutral"
            href="/elfadmin/organisations"
          />
          <PlatformKpiCard
            icon="☺"
            title="Utilisateurs"
            value={dashboard.users_total}
            period={periodLabel}
            tone="neutral"
            href="/elfadmin/utilisateurs"
          />
          <PlatformKpiCard
            icon="◎"
            title="Abonnements actifs"
            value={dashboard.subscriptions_active}
            period={periodLabel}
            tone="ok"
            href="/elfadmin/abonnements"
          />
          <PlatformKpiCard
            icon="◔"
            title="Essais"
            value={dashboard.subscriptions_trialing}
            period={periodLabel}
            tone="neutral"
            href="/elfadmin/abonnements"
          />
          <PlatformKpiCard
            icon="!"
            title="Impayés"
            value={dashboard.subscriptions_past_due}
            period={periodLabel}
            tone={dashboard.subscriptions_past_due > 0 ? 'warn' : 'ok'}
            href="/elfadmin/abonnements"
          />
          <PlatformKpiCard
            icon="▤"
            title="Documents traités"
            value={dashboard.documents_processed_today}
            period="Aujourd’hui"
            tone="neutral"
            href="/elfadmin/documents"
          />
          <PlatformKpiCard
            icon="✦"
            title="Utilisation IA"
            value={dashboard.ai_analyses_today}
            period="Aujourd’hui"
            tone="neutral"
            href="/elfadmin/ia"
          />
          <PlatformKpiCard
            icon="⚠"
            title="Incidents ouverts"
            value={dashboard.incidents_open}
            period={periodLabel}
            tone={dashboard.incidents_open > 0 ? 'danger' : 'ok'}
            href="/elfadmin/incidents"
          />
        </div>
      </section>

      <section className="pc-section pc-charts-row" aria-labelledby="pc-trends-heading">
        <h2 id="pc-trends-heading" className="pc-section-title">
          Activité & répartition
        </h2>
        <div className="pc-charts-grid">
          <PlatformBarChart
            title={`Charge opérationnelle (${periodLabel})`}
            items={[
              { label: 'Jobs pending', value: dashboard.jobs_pending },
              { label: 'Jobs running', value: dashboard.jobs_running },
              { label: 'Jobs failed', value: dashboard.jobs_failed },
              { label: 'Dead letter', value: dashboard.jobs_dead_letter },
              { label: 'Events DL', value: dashboard.events_dead_letter },
              { label: 'OCR attente', value: dashboard.extractions_awaiting_ocr },
              { label: 'Review compta', value: dashboard.proposals_requires_review },
            ]}
          />
          <PlatformDonut
            title="Abonnements"
            parts={[
              { label: 'Actifs', value: dashboard.subscriptions_active },
              { label: 'Essais', value: dashboard.subscriptions_trialing },
              { label: 'Impayés', value: dashboard.subscriptions_past_due },
              { label: 'Annulés', value: dashboard.subscriptions_cancelled },
            ]}
          />
        </div>
        <p className="pc-meta-line">
          Calculé à {new Date(dashboard.computed_at).toLocaleString('fr-FR')} · Orgs actives{' '}
          {dashboard.organizations_active} · Suspendues {dashboard.organizations_suspended} ·
          Propositions compta {dashboard.accounting_proposals_today} · Mails échoués{' '}
          {dashboard.email_deliveries_failed}
        </p>
      </section>

      <section className="pc-section" aria-labelledby="pc-health-heading">
        <div className="pc-section-head">
          <h2 id="pc-health-heading" className="pc-section-title">
            Santé des services
          </h2>
          <Link to="/elfadmin/system-health" className="pc-link">
            Health Center →
          </Link>
          <Link to="/elfadmin/developer" className="pc-link">
            Dev Cockpit →
          </Link>
        </div>
        {services.length === 0 ? (
          <EmptyState title="Aucun service" description="Donnée indisponible pour /platform/health/services." />
        ) : (
          <div className="pc-service-strip">
            {services.map((s) => (
              <article key={s.service} className={`pc-service-chip status-${s.status.toLowerCase()}`}>
                <strong>{s.service}</strong>
                <span className="pc-service-status">{s.status}</span>
                <p>{s.message || '—'}</p>
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
