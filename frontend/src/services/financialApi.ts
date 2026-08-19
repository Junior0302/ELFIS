// Client API Financial Dashboard V1 — le frontend n'effectue aucun calcul,
// toutes les valeurs proviennent du Financial Engine (/financial/*).

import { createApiError } from '../apiErrors'

export type KpiTrend = {
  direction: 'up' | 'down' | 'flat'
  delta: number
  delta_pct: number | null
  previous: number
}

export type Kpi = {
  id: string
  label: string
  value: number
  unit: 'EUR' | 'count'
  format: 'currency' | 'integer'
  status: 'ok' | 'warning' | 'critical' | 'neutral'
  trend: KpiTrend
  hint: string
}

export type FinancialAlert = {
  id: string
  code: string
  severity: 'info' | 'warning' | 'critical'
  title: string
  message: string
  action: string
  source: string
  value: number | null
  created_at: string
}

export type TrendPoint = {
  period: string
  label: string
  revenue: number
  expenses: number
  result: number
}

export type TrendBlock = {
  points: TrendPoint[]
  comparison: {
    revenue: KpiTrend
    expenses: KpiTrend
    result: KpiTrend
  }
}

export type FinancialTrends = {
  monthly: TrendBlock
  weekly: TrendBlock
  yearly: TrendBlock
}

export type FinancialCharts = {
  revenue_vs_expenses: Array<{ period: string; revenue: number; expenses: number }>
  treasury: Array<{ period: string; value: number }>
  expense_breakdown: Array<{ category: string; amount: number; count: number; pct: number }>
  categories: Array<{ category: string; amount: number; count: number; pct: number }>
  ca_evolution: Array<{ period: string; value: number }>
}

export type HealthComponent = {
  id: string
  label: string
  score: number
  max_score: number
  detail: string
}

export type HealthScore = {
  score: number | null
  grade: string | null
  state: 'active' | 'setup'
  components: HealthComponent[]
  message: string | null
}

export type SyncState = {
  connections: number
  errors: number
  last_sync_at: string | null
  age_hours: number | null
  failed_runs_7d: number
  ok_runs_7d: number
  status: 'fresh' | 'aging' | 'stale' | 'error' | 'none'
}

export type ActivityItem = {
  type: string
  label: string
  amount: number
  date: string
  meta: string
  created_at: string | null
}

export type FinancialOverview = {
  computed_at: string
  has_data: boolean
  kpis: Kpi[]
  alerts: FinancialAlert[]
  health: HealthScore
  charts: FinancialCharts
  trends: FinancialTrends
  sync: SyncState
  documents_to_process: number
  recent_activity: ActivityItem[]
  recommendations: string[]
}

export type PlatformFinancialOverview = {
  organizations_total: number
  organizations_active: number
  organizations_setup: number
  average_score: number | null
  organizations_without_sync: number
  sync_errors: number
  critical_alerts: number
  warning_alerts: number
  organizations: Array<{
    organization_id: number
    name: string
    score: number | null
    grade: string | null
    state: string
    treasury: number
    revenue: number
    sync_status: string
    critical_alerts: number
    warning_alerts: number
  }>
}

function apiRoot(): string {
  const raw = (import.meta.env.VITE_API_URL as string | undefined)?.trim()
  if (raw) return raw.replace(/\/$/, '')
  return '/api'
}

function headers(token: string, orgId?: number | null): HeadersInit {
  const h: Record<string, string> = { Authorization: `Bearer ${token}` }
  if (orgId != null) h['X-Organization-Id'] = String(orgId)
  return h
}

async function parse<T>(
  res: Response,
  ctx?: { organizationId?: number | null },
): Promise<T> {
  const text = await res.text()
  let body: unknown = null
  try {
    body = text ? JSON.parse(text) : null
  } catch {
    body = text
  }
  if (!res.ok) {
    const detail = (body as { detail?: unknown })?.detail
    const detailStr = typeof detail === 'string' ? detail : undefined
    const requestId =
      res.headers.get('x-request-id') || res.headers.get('x-correlation-id') || null
    throw createApiError(res.status, detailStr, {
      endpoint: (() => {
        try {
          return new URL(res.url).pathname
        } catch {
          return '/api/financial/*'
        }
      })(),
      organizationId: ctx?.organizationId,
      requestId,
    })
  }
  return body as T
}

function suffix(refresh: boolean): string {
  return refresh ? '?refresh=true' : ''
}

export const formatEuro = (value: number): string =>
  new Intl.NumberFormat('fr-FR', {
    style: 'currency',
    currency: 'EUR',
    maximumFractionDigits: Math.abs(value) >= 1000 ? 0 : 2,
  }).format(value)

export const formatKpiValue = (kpi: Kpi): string =>
  kpi.format === 'currency' ? formatEuro(kpi.value) : String(Math.round(kpi.value))

export const severityLabel = (severity: FinancialAlert['severity']): string => {
  const map: Record<string, string> = {
    info: 'Info',
    warning: 'Vigilance',
    critical: 'Critique',
  }
  return map[severity] || severity
}

export const financialApi = {
  async overview(token: string, orgId: number, refresh = false) {
    const res = await fetch(`${apiRoot()}/financial/overview${suffix(refresh)}`, {
      headers: headers(token, orgId),
    })
    return parse<FinancialOverview>(res, { organizationId: orgId })
  },

  async kpis(token: string, orgId: number, refresh = false) {
    const res = await fetch(`${apiRoot()}/financial/kpis${suffix(refresh)}`, {
      headers: headers(token, orgId),
    })
    return parse<{ kpis: Kpi[] }>(res, { organizationId: orgId })
  },

  async trends(token: string, orgId: number, refresh = false) {
    const res = await fetch(`${apiRoot()}/financial/trends${suffix(refresh)}`, {
      headers: headers(token, orgId),
    })
    return parse<FinancialTrends>(res, { organizationId: orgId })
  },

  async charts(token: string, orgId: number, refresh = false) {
    const res = await fetch(`${apiRoot()}/financial/charts${suffix(refresh)}`, {
      headers: headers(token, orgId),
    })
    return parse<FinancialCharts>(res, { organizationId: orgId })
  },

  async alerts(token: string, orgId: number, refresh = false) {
    const res = await fetch(`${apiRoot()}/financial/alerts${suffix(refresh)}`, {
      headers: headers(token, orgId),
    })
    return parse<{ alerts: FinancialAlert[] }>(res, { organizationId: orgId })
  },

  async healthScore(token: string, orgId: number, refresh = false) {
    const res = await fetch(`${apiRoot()}/financial/health-score${suffix(refresh)}`, {
      headers: headers(token, orgId),
    })
    return parse<HealthScore>(res, { organizationId: orgId })
  },

  async platformOverview(token: string) {
    const res = await fetch(`${apiRoot()}/platform/financial/overview`, {
      headers: headers(token),
    })
    return parse<PlatformFinancialOverview>(res)
  },
}
