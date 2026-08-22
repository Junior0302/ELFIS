import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '../auth'
import {
  financialApi,
  formatEuro,
  formatKpiValue,
  severityLabel,
  type FinancialOverview,
  type Kpi,
} from '../services/financialApi'
import { WorkspaceKpiCard, WorkspacePageHeader } from '../workspaces'

const REFRESH_INTERVAL_MS = 60_000

const STATUS_COLORS: Record<Kpi['status'], string> = {
  ok: 'var(--ok, #22c55e)',
  warning: 'var(--warn, #f59e0b)',
  critical: 'var(--danger, #ef4444)',
  neutral: 'var(--muted, #94a3b8)',
}

function fmtPeriod(period: string): string {
  // "2026-07" → "juil. 26" ; "2026-S30" → "S30" ; "2026" → "2026"
  const monthMatch = /^(\d{4})-(\d{2})$/.exec(period)
  if (monthMatch) {
    const d = new Date(Number(monthMatch[1]), Number(monthMatch[2]) - 1, 1)
    return d.toLocaleDateString('fr-FR', { month: 'short', year: '2-digit' })
  }
  const weekMatch = /^\d{4}-(S\d{2})$/.exec(period)
  if (weekMatch) return weekMatch[1]
  return period
}

function fmtDate(value?: string | null): string {
  if (!value) return '—'
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString('fr-FR')
}

function TrendBadge({ kpi }: { kpi: Kpi }) {
  const { direction, delta_pct, delta } = kpi.trend
  if (direction === 'flat') return <span className="muted">stable</span>
  const arrow = direction === 'up' ? '▲' : '▼'
  const text =
    delta_pct != null
      ? `${arrow} ${Math.abs(delta_pct).toFixed(1)}%`
      : `${arrow} ${formatEuro(Math.abs(delta))}`
  return <span style={{ color: direction === 'up' ? '#22c55e' : '#ef4444' }}>{text}</span>
}

function KpiCard({ kpi }: { kpi: Kpi }) {
  return (
    <div
      className="workspace-kpi-card-wrap"
      style={{ borderLeft: `3px solid ${STATUS_COLORS[kpi.status]}` }}
    >
      <WorkspaceKpiCard
        title={kpi.label}
        value={formatKpiValue(kpi)}
        accentBar={false}
        supportingText={kpi.hint || undefined}
        footer={<TrendBadge kpi={kpi} />}
      />
    </div>
  )
}

function HealthGauge({ score, grade }: { score: number; grade: string }) {
  const radius = 52
  const circumference = 2 * Math.PI * radius
  const filled = (score / 100) * circumference
  const color = score >= 65 ? '#22c55e' : score >= 50 ? '#f59e0b' : '#ef4444'
  return (
    <svg viewBox="0 0 130 130" width="130" height="130" role="img" aria-label={`Score ${score}`}>
      <circle cx="65" cy="65" r={radius} fill="none" stroke="rgba(148,163,184,0.25)" strokeWidth="10" />
      <circle
        cx="65"
        cy="65"
        r={radius}
        fill="none"
        stroke={color}
        strokeWidth="10"
        strokeLinecap="round"
        strokeDasharray={`${filled} ${circumference - filled}`}
        transform="rotate(-90 65 65)"
      />
      <text x="65" y="60" textAnchor="middle" fontSize="26" fontWeight="700" fill="currentColor">
        {Math.round(score)}
      </text>
      <text x="65" y="82" textAnchor="middle" fontSize="14" fill={color} fontWeight="600">
        {grade}
      </text>
    </svg>
  )
}

function BarChart({
  points,
}: {
  points: Array<{ period: string; revenue: number; expenses: number }>
}) {
  const width = 640
  const height = 200
  const max = Math.max(1, ...points.map((p) => Math.max(p.revenue, p.expenses)))
  const slot = width / Math.max(1, points.length)
  const bar = Math.min(16, slot / 3)
  return (
    <svg viewBox={`0 0 ${width} ${height + 24}`} style={{ width: '100%', height: 'auto' }} role="img">
      {points.map((p, i) => {
        const x = i * slot + slot / 2
        const hr = (p.revenue / max) * height
        const he = (p.expenses / max) * height
        return (
          <g key={p.period}>
            <rect x={x - bar - 1} y={height - hr} width={bar} height={hr} fill="#22c55e" rx="2">
              <title>{`${fmtPeriod(p.period)} — revenus ${formatEuro(p.revenue)}`}</title>
            </rect>
            <rect x={x + 1} y={height - he} width={bar} height={he} fill="#ef4444" rx="2">
              <title>{`${fmtPeriod(p.period)} — dépenses ${formatEuro(p.expenses)}`}</title>
            </rect>
            <text x={x} y={height + 16} textAnchor="middle" fontSize="10" fill="currentColor" opacity="0.6">
              {fmtPeriod(p.period)}
            </text>
          </g>
        )
      })}
    </svg>
  )
}

function LineChart({
  points,
  color,
}: {
  points: Array<{ period: string; value: number }>
  color: string
}) {
  const width = 640
  const height = 180
  const values = points.map((p) => p.value)
  const max = Math.max(1, ...values)
  const min = Math.min(0, ...values)
  const range = max - min || 1
  const step = width / Math.max(1, points.length - 1)
  const coords = points.map((p, i) => {
    const x = i * step
    const y = height - ((p.value - min) / range) * height
    return { x, y, p }
  })
  const path = coords.map((c, i) => `${i === 0 ? 'M' : 'L'}${c.x.toFixed(1)},${c.y.toFixed(1)}`).join(' ')
  return (
    <svg viewBox={`0 0 ${width} ${height + 24}`} style={{ width: '100%', height: 'auto' }} role="img">
      <path
        d={`${path} L${width},${height} L0,${height} Z`}
        fill={color}
        opacity="0.12"
      />
      <path d={path} fill="none" stroke={color} strokeWidth="2.5" strokeLinejoin="round" />
      {coords.map((c) => (
        <circle key={c.p.period} cx={c.x} cy={c.y} r="3" fill={color}>
          <title>{`${fmtPeriod(c.p.period)} — ${formatEuro(c.p.value)}`}</title>
        </circle>
      ))}
      {coords
        .filter((_, i) => i % 2 === 0)
        .map((c) => (
          <text
            key={`t-${c.p.period}`}
            x={c.x}
            y={height + 16}
            textAnchor="middle"
            fontSize="10"
            fill="currentColor"
            opacity="0.6"
          >
            {fmtPeriod(c.p.period)}
          </text>
        ))}
    </svg>
  )
}

const DONUT_COLORS = ['#6366f1', '#22c55e', '#f59e0b', '#ef4444', '#06b6d4', '#a855f7', '#84cc16', '#f97316']

function DonutChart({
  items,
}: {
  items: Array<{ category: string; amount: number; pct: number }>
}) {
  const radius = 60
  const circumference = 2 * Math.PI * radius
  let offset = 0
  const top = items.slice(0, 8)
  return (
    <div style={{ display: 'flex', gap: '1.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
      <svg viewBox="0 0 150 150" width="150" height="150" role="img">
        {top.map((item, i) => {
          const length = (item.pct / 100) * circumference
          const segment = (
            <circle
              key={item.category}
              cx="75"
              cy="75"
              r={radius}
              fill="none"
              stroke={DONUT_COLORS[i % DONUT_COLORS.length]}
              strokeWidth="18"
              strokeDasharray={`${length} ${circumference - length}`}
              strokeDashoffset={-offset}
              transform="rotate(-90 75 75)"
            >
              <title>{`${item.category} — ${formatEuro(item.amount)} (${item.pct}%)`}</title>
            </circle>
          )
          offset += length
          return segment
        })}
      </svg>
      <ul style={{ listStyle: 'none', margin: 0, padding: 0, fontSize: '0.85rem' }}>
        {top.map((item, i) => (
          <li key={item.category} style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <span
              style={{
                width: 10,
                height: 10,
                borderRadius: 3,
                background: DONUT_COLORS[i % DONUT_COLORS.length],
                display: 'inline-block',
              }}
            />
            {item.category} — {formatEuro(item.amount)} ({item.pct}%)
          </li>
        ))}
      </ul>
    </div>
  )
}

export default function FinancialDashboardPage() {
  const { token, orgId } = useAuth()
  const [data, setData] = useState<FinancialOverview | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  const load = useCallback(
    async (refresh = false) => {
      if (!token || orgId == null) return
      if (refresh) setRefreshing(true)
      setError('')
      try {
        const overview = await financialApi.overview(token, orgId, refresh)
        setData(overview)
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Impossible de charger le tableau de bord financier')
      } finally {
        setLoading(false)
        setRefreshing(false)
      }
    },
    [token, orgId],
  )

  useEffect(() => {
    void load()
    // actualisation automatique — le backend met les calculs en cache (TTL)
    const timer = window.setInterval(() => void load(), REFRESH_INTERVAL_MS)
    return () => window.clearInterval(timer)
  }, [load])

  return (
    <>
      <WorkspacePageHeader
        eyebrow="Finance"
        title="Trésorerie"
        description="Pilotage financier et trésorerie en temps réel"
        actions={
          <button
            type="button"
            className="btn secondary"
            disabled={refreshing}
            onClick={() => void load(true)}
          >
            {refreshing ? 'Actualisation…' : 'Actualiser'}
          </button>
        }
      />

      {error ? <div className="panel form-error">{error}</div> : null}
      {loading ? <div className="loading">Chargement des indicateurs financiers…</div> : null}

      {!loading && data && !data.has_data ? (
        <div className="panel">
          <h3>Bienvenue sur votre tableau de bord financier</h3>
          <p className="muted">
            Connectez votre banque et créez vos premières factures : les KPIs, tendances et le
            score de santé s'activeront automatiquement.
          </p>
        </div>
      ) : null}

      {!loading && data && data.has_data ? (
        <>
          {/* KPI principaux */}
          <div className="workspace-kpi-grid" style={{ marginBottom: '1rem' }}>
            {data.kpis.map((kpi) => (
              <KpiCard key={kpi.id} kpi={kpi} />
            ))}
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
              gap: '1rem',
              marginBottom: '1rem',
            }}
          >
            {/* Health Score */}
            <div className="panel">
              <h3>Santé financière</h3>
              {data.health.state === 'active' && data.health.score != null ? (
                <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
                  <HealthGauge score={data.health.score} grade={data.health.grade || ''} />
                  <ul style={{ listStyle: 'none', margin: 0, padding: 0, fontSize: '0.85rem', flex: 1 }}>
                    {data.health.components.map((c) => (
                      <li key={c.id} style={{ marginBottom: '0.35rem' }} title={c.detail}>
                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                          <span>{c.label}</span>
                          <span className="muted">
                            {c.score}/{c.max_score}
                          </span>
                        </div>
                        <div style={{ background: 'rgba(148,163,184,0.2)', borderRadius: 4, height: 5 }}>
                          <div
                            style={{
                              width: `${(c.score / c.max_score) * 100}%`,
                              background: '#6366f1',
                              height: 5,
                              borderRadius: 4,
                            }}
                          />
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : (
                <p className="muted">{data.health.message}</p>
              )}
            </div>

            {/* Alertes */}
            <div className="panel">
              <h3>Alertes</h3>
              {data.alerts.length === 0 ? (
                <p className="muted">Aucune alerte — tout est sous contrôle.</p>
              ) : (
                <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
                  {data.alerts.map((alert) => (
                    <li key={alert.id} style={{ marginBottom: '0.6rem' }}>
                      <span
                        className={
                          alert.severity === 'critical'
                            ? 'badge danger'
                            : alert.severity === 'warning'
                              ? 'badge warn'
                              : 'badge'
                        }
                      >
                        {severityLabel(alert.severity)}
                      </span>{' '}
                      <strong>{alert.title}</strong>
                      <p className="muted" style={{ margin: '0.15rem 0 0' }}>
                        {alert.message} {alert.action ? <em>— {alert.action}</em> : null}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          {/* Graphiques */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
              gap: '1rem',
              marginBottom: '1rem',
            }}
          >
            <div className="panel">
              <h3>Revenus vs dépenses (12 mois)</h3>
              <BarChart points={data.charts.revenue_vs_expenses} />
            </div>
            <div className="panel">
              <h3>Trésorerie</h3>
              <LineChart points={data.charts.treasury} color="#6366f1" />
            </div>
            <div className="panel">
              <h3>Évolution du chiffre d'affaires</h3>
              <LineChart points={data.charts.ca_evolution} color="#22c55e" />
            </div>
            <div className="panel">
              <h3>Répartition des dépenses</h3>
              {data.charts.expense_breakdown.length === 0 ? (
                <p className="muted">Aucune dépense catégorisée pour le moment.</p>
              ) : (
                <DonutChart items={data.charts.expense_breakdown} />
              )}
            </div>
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
              gap: '1rem',
            }}
          >
            {/* Activité récente */}
            <div className="panel">
              <h3>Activité récente</h3>
              {data.recent_activity.length === 0 ? (
                <p className="muted">Aucune activité récente.</p>
              ) : (
                <table className="table" style={{ width: '100%', fontSize: '0.85rem' }}>
                  <tbody>
                    {data.recent_activity.map((item, i) => (
                      <tr key={`${item.type}-${i}`}>
                        <td>
                          <span className="badge">{item.type}</span>
                        </td>
                        <td>{item.label}</td>
                        <td style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>
                          <span style={{ color: item.amount < 0 ? '#ef4444' : undefined }}>
                            {formatEuro(item.amount)}
                          </span>
                        </td>
                        <td className="muted" style={{ whiteSpace: 'nowrap' }}>
                          {item.date}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>

            {/* Synchronisations + documents */}
            <div className="panel">
              <h3>Synchronisations & documents</h3>
              <div style={{ display: 'flex', gap: '2rem', flexWrap: 'wrap' }}>
                <div>
                  <strong>{data.sync.connections}</strong>
                  <p className="muted">Connexion(s) bancaire(s)</p>
                </div>
                <div>
                  <strong>{fmtDate(data.sync.last_sync_at)}</strong>
                  <p className="muted">Dernière synchronisation</p>
                </div>
                <div>
                  <strong>{data.sync.failed_runs_7d}</strong>
                  <p className="muted">Échec(s) sur 7 jours</p>
                </div>
                <div>
                  <strong>{data.documents_to_process}</strong>
                  <p className="muted">Document(s) à traiter</p>
                </div>
              </div>
              {data.recommendations.length ? (
                <>
                  <h4 style={{ marginBottom: '0.25rem' }}>Recommandations</h4>
                  <ul className="muted" style={{ margin: 0, paddingLeft: '1.1rem' }}>
                    {data.recommendations.map((r) => (
                      <li key={r}>{r}</li>
                    ))}
                  </ul>
                </>
              ) : null}
              <p className="muted" style={{ marginTop: '0.75rem', fontSize: '0.75rem' }}>
                Calculé le {fmtDate(data.computed_at)} — actualisation automatique toutes les 60 s.
              </p>
            </div>
          </div>
        </>
      ) : null}
    </>
  )
}
