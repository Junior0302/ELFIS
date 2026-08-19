import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useAuth } from '../../auth'
import HealthAlertPanel from '../../components/system-health/HealthAlertPanel'
import HealthEmptyState from '../../components/system-health/HealthEmptyState'
import HealthErrorState from '../../components/system-health/HealthErrorState'
import HealthServiceCard from '../../components/system-health/HealthServiceCard'
import HealthSkeleton from '../../components/system-health/HealthSkeleton'
import HealthSummaryHeader from '../../components/system-health/HealthSummaryHeader'
import SystemLogTable from '../../components/system-health/SystemLogTable'
import {
  getSystemAlerts,
  getSystemHealth,
  getSystemLogs,
  getSystemMetrics,
} from '../../services/systemHealthApi'
import type {
  HealthStatus,
  SystemAlertsResponse,
  SystemHealthSummary,
  SystemLogsResponse,
  SystemMetricsResponse,
} from '../../types/systemHealth'
import { PlatformBarChart } from '../../components/platform/PlatformMiniCharts'

const REFRESH_MS = 30_000

type StatusFilter = 'all' | HealthStatus | 'critical'

function matchesFilter(status: HealthStatus, filter: StatusFilter): boolean {
  if (filter === 'all') return true
  if (filter === 'critical') return status === 'unhealthy'
  return status === filter
}

export default function SystemHealthPage() {
  const { token } = useAuth()
  const [summary, setSummary] = useState<SystemHealthSummary | null>(null)
  const [alerts, setAlerts] = useState<SystemAlertsResponse | null>(null)
  const [logs, setLogs] = useState<SystemLogsResponse | null>(null)
  const [metrics, setMetrics] = useState<SystemMetricsResponse | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null)
  const [filter, setFilter] = useState<StatusFilter>('all')
  const inFlight = useRef(false)

  const load = useCallback(
    async (opts?: { silent?: boolean }) => {
      if (!token || inFlight.current) return
      inFlight.current = true
      if (!opts?.silent) setLoading(true)
      else setRefreshing(true)
      setError('')
      try {
        const [h, a, l, m] = await Promise.all([
          getSystemHealth(token),
          getSystemAlerts(token),
          getSystemLogs(token, { limit: 100 }),
          getSystemMetrics(token, '24h'),
        ])
        setSummary(h)
        setAlerts(a)
        setLogs(l)
        setMetrics(m)
        setLastRefresh(new Date())
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : 'System Health indisponible')
      } finally {
        inFlight.current = false
        setLoading(false)
        setRefreshing(false)
      }
    },
    [token],
  )

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    if (!token) return
    const id = window.setInterval(() => {
      void load({ silent: true })
    }, REFRESH_MS)
    return () => window.clearInterval(id)
  }, [token, load])

  const filteredServices = useMemo(() => {
    if (!summary) return []
    return summary.services.filter((s) => matchesFilter(s.status, filter))
  }, [summary, filter])

  const disabledCount = useMemo(
    () => summary?.services.filter((s) => s.status === 'disabled').length ?? 0,
    [summary],
  )

  if (loading && !summary) {
    return <HealthSkeleton />
  }

  if (error && !summary) {
    return <HealthErrorState message={error} onRetry={() => void load()} />
  }

  if (!summary) {
    return <HealthEmptyState />
  }

  const filters: Array<{ id: StatusFilter; label: string }> = [
    { id: 'all', label: 'Tous' },
    { id: 'healthy', label: 'Healthy' },
    { id: 'degraded', label: 'Degraded' },
    { id: 'critical', label: 'Critical' },
    { id: 'disabled', label: 'Disabled' },
  ]

  return (
    <div className="pc-page health-center-v2">
      <HealthSummaryHeader
        summary={summary}
        lastRefresh={lastRefresh}
        refreshing={refreshing}
        onRefresh={() => void load({ silent: true })}
      />
      {error && <div className="platform-alert">{error}</div>}

      <div className="pc-kpi-grid pc-kpi-grid-compact">
        <article className="pc-kpi-card pc-kpi-ok">
          <span className="pc-kpi-title">Healthy</span>
          <p className="pc-kpi-value">{summary.healthy_count}</p>
        </article>
        <article className="pc-kpi-card pc-kpi-warn">
          <span className="pc-kpi-title">Degraded</span>
          <p className="pc-kpi-value">{summary.degraded_count}</p>
        </article>
        <article className="pc-kpi-card pc-kpi-danger">
          <span className="pc-kpi-title">Critical</span>
          <p className="pc-kpi-value">{summary.unhealthy_count}</p>
        </article>
        <article className="pc-kpi-card">
          <span className="pc-kpi-title">Disabled</span>
          <p className="pc-kpi-value">{disabledCount}</p>
        </article>
        <article className="pc-kpi-card">
          <span className="pc-kpi-title">Unknown</span>
          <p className="pc-kpi-value">{summary.unknown_count}</p>
        </article>
        <article className="pc-kpi-card">
          <span className="pc-kpi-title">Alertes actives</span>
          <p className="pc-kpi-value">{alerts?.active_count ?? 0}</p>
        </article>
      </div>

      <div className="pc-filter-bar" role="toolbar" aria-label="Filtrer les services">
        {filters.map((f) => (
          <button
            key={f.id}
            type="button"
            className={filter === f.id ? 'pc-btn' : 'pc-btn pc-btn-ghost'}
            aria-pressed={filter === f.id}
            onClick={() => setFilter(f.id)}
          >
            {f.label}
          </button>
        ))}
      </div>

      <section className="health-section">
        <h2 className="pc-section-title">Services</h2>
        {filteredServices.length === 0 ? (
          <HealthEmptyState />
        ) : (
          <div className="health-services-grid pc-health-grid">
            {filteredServices.map((svc) => (
              <HealthServiceCard key={svc.service_id} service={svc} />
            ))}
          </div>
        )}
      </section>

      <section className="health-section">
        <h2 className="pc-section-title">Alertes</h2>
        <HealthAlertPanel alerts={alerts?.alerts || []} />
      </section>

      <section className="health-section">
        <h2 className="pc-section-title">Métriques (24h)</h2>
        <PlatformBarChart
          title="Métriques système"
          items={(metrics?.metrics || []).slice(0, 10).map((m) => ({
            label: m.label,
            value: typeof m.value === 'number' ? m.value : Number(m.value) || 0,
          }))}
        />
      </section>

      <section className="health-section">
        <h2 className="pc-section-title">Logs système</h2>
        <div className="platform-table-wrap pc-table-shell">
          <SystemLogTable entries={logs?.entries || []} />
        </div>
      </section>
    </div>
  )
}
