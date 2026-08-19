import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useAuth } from '../../auth'
import AuditEmptyState from '../../components/audit/AuditEmptyState'
import AuditErrorState from '../../components/audit/AuditErrorState'
import AuditEventDetailsDrawer from '../../components/audit/AuditEventDetailsDrawer'
import AuditFiltersBar, {
  DEFAULT_AUDIT_FILTERS,
  filtersBarToApi,
  type AuditFiltersBarValue,
} from '../../components/audit/AuditFiltersBar'
import AuditPagination from '../../components/audit/AuditPagination'
import AuditSkeleton from '../../components/audit/AuditSkeleton'
import AuditSummaryCards from '../../components/audit/AuditSummaryCards'
import AuditTimeline from '../../components/audit/AuditTimeline'
import { downloadAuditExport, getAuditEvents, getAuditStatistics } from '../../services/auditApi'
import type { AuditEvent, AuditPeriodHours, AuditStatistics } from '../../types/audit'

const PAGE_SIZE = 25
const EXPORT_CONFIRM_THRESHOLD = 1000

function parseFiltersFromSearch(params: URLSearchParams): AuditFiltersBarValue {
  const hoursRaw = Number(params.get('hours') || 24)
  const hours = ([1, 24, 168, 720].includes(hoursRaw) ? hoursRaw : 24) as AuditPeriodHours
  const successRaw = params.get('success') || ''
  return {
    ...DEFAULT_AUDIT_FILTERS,
    hours,
    useCustomRange: Boolean(params.get('date_from') || params.get('date_to')),
    date_from: params.get('date_from') || '',
    date_to: params.get('date_to') || '',
    category: params.get('category') || '',
    severity: params.get('severity') || '',
    status: params.get('status') || '',
    action: params.get('action') || '',
    service: params.get('service') || '',
    product: params.get('product') || '',
    success: successRaw === 'true' || successRaw === 'false' ? successRaw : '',
    actor_email: params.get('actor_email') || '',
    organization_id: params.get('organization_id') || '',
    q: params.get('q') || '',
    target_type: params.get('target_type') || '',
    target_id: params.get('target_id') || '',
    correlation_id: params.get('correlation_id') || '',
    request_id: params.get('request_id') || '',
    actor_user_id: params.get('actor_user_id') || '',
  }
}

function filtersToSearch(value: AuditFiltersBarValue, offset: number): URLSearchParams {
  const p = new URLSearchParams()
  if (!value.useCustomRange && value.hours !== 24) p.set('hours', String(value.hours))
  if (value.useCustomRange && value.date_from) p.set('date_from', value.date_from)
  if (value.useCustomRange && value.date_to) p.set('date_to', value.date_to)
  if (value.category) p.set('category', value.category)
  if (value.severity) p.set('severity', value.severity)
  if (value.status) p.set('status', value.status)
  if (value.action) p.set('action', value.action)
  if (value.service) p.set('service', value.service)
  if (value.product) p.set('product', value.product)
  if (value.success) p.set('success', value.success)
  if (value.actor_email) p.set('actor_email', value.actor_email)
  if (value.organization_id) p.set('organization_id', value.organization_id)
  if (value.q) p.set('q', value.q)
  if (value.target_type) p.set('target_type', value.target_type)
  if (value.target_id) p.set('target_id', value.target_id)
  if (value.correlation_id) p.set('correlation_id', value.correlation_id)
  if (value.request_id) p.set('request_id', value.request_id)
  if (value.actor_user_id) p.set('actor_user_id', value.actor_user_id)
  if (offset > 0) p.set('offset', String(offset))
  return p
}

function periodLabel(filters: AuditFiltersBarValue): string {
  if (filters.useCustomRange) {
    return `du ${filters.date_from || '…'} au ${filters.date_to || '…'}`
  }
  if (filters.hours === 1) return 'dernière heure'
  if (filters.hours === 24) return '24 dernières heures'
  if (filters.hours === 168) return '7 derniers jours'
  return '30 derniers jours'
}

export default function ActivityCenterPage() {
  const { token, user } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const [filters, setFilters] = useState<AuditFiltersBarValue>(() => parseFiltersFromSearch(searchParams))
  const [advancedOpen, setAdvancedOpen] = useState(false)
  const [offset, setOffset] = useState(() => Math.max(0, Number(searchParams.get('offset') || 0)))
  const [events, setEvents] = useState<AuditEvent[]>([])
  const [total, setTotal] = useState(0)
  const [stats, setStats] = useState<AuditStatistics | null>(null)
  const [selected, setSelected] = useState<AuditEvent | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [loading, setLoading] = useState(true)
  const [exporting, setExporting] = useState(false)
  const [error, setError] = useState('')
  const alive = useRef(true)
  const inFlight = useRef(false)

  // Bouton export : platform admins historiques ont security.audit.export via resolver.
  // Autorité réelle = backend.
  const canExport = Boolean(user?.is_platform_admin)

  const apiFilters = useMemo(
    () => filtersBarToApi(filters, { limit: PAGE_SIZE, offset }),
    [filters, offset],
  )

  const load = useCallback(async () => {
    if (!token || inFlight.current) return
    inFlight.current = true
    setLoading(true)
    setError('')
    try {
      const statsHours = filters.useCustomRange ? 24 : filters.hours
      const [list, statistics] = await Promise.all([
        getAuditEvents(token, apiFilters),
        getAuditStatistics(token, { hours: statsHours }),
      ])
      if (!alive.current) return
      setEvents(list.items)
      setTotal(list.total)
      setStats(statistics)
    } catch (reason) {
      if (!alive.current) return
      setError(reason instanceof Error ? reason.message : 'Activity Center indisponible')
    } finally {
      if (alive.current) {
        setLoading(false)
        inFlight.current = false
      } else {
        inFlight.current = false
      }
    }
  }, [token, apiFilters, filters.hours, filters.useCustomRange])

  useEffect(() => {
    alive.current = true
    return () => {
      alive.current = false
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    setSearchParams(filtersToSearch(filters, offset), { replace: true })
  }, [filters, offset, setSearchParams])

  const onFiltersChange = (next: AuditFiltersBarValue) => {
    setFilters(next)
    setOffset(0)
  }

  const onExport = async () => {
    if (!token || !canExport) return
    if (total > EXPORT_CONFIRM_THRESHOLD) {
      const ok = window.confirm(
        `Exporter ${total} événements en CSV pour la période active ? (limite serveur appliquée)`,
      )
      if (!ok) return
    }
    setExporting(true)
    setError('')
    try {
      const exportFilters = filtersBarToApi(filters, { limit: PAGE_SIZE, offset: 0 })
      await downloadAuditExport(token, exportFilters, 'csv')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Export impossible')
    } finally {
      setExporting(false)
    }
  }

  if (loading && !stats && events.length === 0) {
    return <AuditSkeleton />
  }

  if (error && !stats && events.length === 0) {
    return <AuditErrorState message={error} onRetry={() => void load()} />
  }

  return (
    <div className="audit-page pc-page">
      <header className="audit-page-header pc-section-head">
        <div>
          <p className="pc-lede">
            Chronologie des actions plateforme — période active :{' '}
            <strong>{periodLabel(filters)}</strong>
            {total > 0 ? ` — ${total} événement(s)` : ''}
          </p>
        </div>
        <div className="audit-header-actions pc-period-toggle">
          {canExport && (
            <button
              type="button"
              className="pc-btn"
              onClick={() => void onExport()}
              disabled={loading || exporting}
            >
              {exporting ? 'Export…' : 'Exporter CSV'}
            </button>
          )}
          <button type="button" className="pc-btn pc-btn-ghost" onClick={() => void load()} disabled={loading}>
            Actualiser
          </button>
        </div>
      </header>

      {error && <div className="platform-alert">{error}</div>}
      {total > 10_000 && (
        <div className="platform-alert">
          Résultats très volumineux. Affinez les filtres avant d&apos;exporter (limite serveur).
        </div>
      )}

      {stats && <AuditSummaryCards stats={stats} />}

      <section className="health-section" aria-label="Filtres">
        <h2>Filtres</h2>
        <AuditFiltersBar
          value={filters}
          disabled={loading}
          advancedOpen={advancedOpen}
          onAdvancedToggle={() => setAdvancedOpen((v) => !v)}
          onChange={onFiltersChange}
          onReset={() => {
            setFilters(DEFAULT_AUDIT_FILTERS)
            setAdvancedOpen(false)
            setOffset(0)
          }}
        />
      </section>

      <section className="health-section" aria-label="Timeline">
        <h2>Événements</h2>
        {events.length === 0 ? (
          <AuditEmptyState />
        ) : (
          <AuditTimeline
            events={events}
            selectedId={selected?.id}
            onSelect={(event) => {
              setSelected(event)
              setDrawerOpen(true)
            }}
          />
        )}
        <AuditPagination
          total={total}
          limit={PAGE_SIZE}
          offset={offset}
          disabled={loading}
          onPrev={() => setOffset((o) => Math.max(0, o - PAGE_SIZE))}
          onNext={() => setOffset((o) => o + PAGE_SIZE)}
        />
      </section>

      <AuditEventDetailsDrawer
        open={drawerOpen}
        event={selected}
        onClose={() => setDrawerOpen(false)}
      />
    </div>
  )
}
